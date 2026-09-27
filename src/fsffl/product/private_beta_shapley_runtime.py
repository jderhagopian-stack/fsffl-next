from __future__ import annotations

import hashlib
import json
import logging
from time import perf_counter
from threading import RLock
from typing import Any, Callable

from fsffl.persistence.contracts import ArtifactKey, PersistenceStore, ReusableArtifactRecord, utc_now

from fsffl.forecast.future_contract import FutureForecastContract
from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Position
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar_from_forecast_contract,
)
from fsffl.value.private_beta_activation_data import (
    ACTIVATION_BUNDLE_SHA256,
    ACTIVATION_WORKFLOW_RUN_ID,
    activation_artifact_text,
)
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    SHAPLEY_INTRINSIC_MODEL_VERSION,
)
from fsffl.value.shapley_intrinsic_contract import (
    SHAPLEY_INTRINSIC_CONTRACT_VERSION,
    CompletedSourceFactProvenance,
    ShapleyIntrinsicContract,
    build_shapley_intrinsic_contract,
    build_unavailable_shapley_intrinsic_contract,
)

from .runtime import LiveForecastEvidence, UserRuntimeContext

_SUPPORTED_POSITIONS = {Position.QB, Position.RB, Position.WR, Position.TE}
SHAPLEY_INTRINSIC_ARTIFACT_KIND = "shapley_intrinsic_contract"
SHAPLEY_INTRINSIC_SCOPE_KIND = "league_intrinsic_inputs"

YearOneAuthorityLoader = Callable[[LeagueState], LiveForecastEvidence]
FutureForecastBuilder = Callable[..., FutureForecastContract]
_logger = logging.getLogger("fsffl.product.performance")


def _json_artifact(name: str) -> dict[str, object]:
    raw = json.loads(activation_artifact_text(name))
    if not isinstance(raw, dict):
        raise ValueError(f"private-beta activation artifact must be a JSON object: {name}")
    return raw


# The legacy activation bundle remains metadata/coverage evidence only. It is not
# a Future Forecast producer.
_FACTS = CurrentI1FactsArtifact.from_dict(_json_artifact("current_i1_facts_2026.json"))
_REPORT = _json_artifact("private_beta_activation_build_report.json")
if _REPORT.get("status") != "PASS" or _REPORT.get("model_changes") is not False:
    raise ValueError("embedded private-beta activation bundle is not a governed PASS artifact")


def _year_one_forecasts(evidence: LiveForecastEvidence | None) -> tuple[ForecastObservation, ...]:
    if evidence is None:
        return ()
    return tuple(
        observation
        for observation in evidence.league_scored_forecasts
        if observation.metric == ForecastMetric.FANTASY_POINTS
        and observation.horizon == ForecastHorizon.SEASON
        and observation.position in _SUPPORTED_POSITIONS
    )


def _preseason_source_ids(year_one_evidence: LiveForecastEvidence) -> tuple[str, ...]:
    source_ids = tuple(sorted(set(year_one_evidence.successful_source_ids)))
    if len(source_ids) < 2:
        raise ValueError(
            "preserved preseason Year-1 authority requires at least two independent source ids"
        )
    coverage = getattr(year_one_evidence.runtime_result, "coverage", None)
    if coverage is None:
        raise ValueError("preserved preseason Year-1 authority lacks source-coverage lineage")
    independent = tuple(sorted(set(coverage.independent_source_ids)))
    if independent != source_ids:
        raise ValueError(
            "preserved preseason Year-1 source ids do not match governed independent-source coverage"
        )
    if int(coverage.minimum_independent_sources) < 2:
        raise ValueError("preserved preseason Year-1 coverage weakens the two-source authority")
    if not year_one_evidence.raw_forecasts:
        raise ValueError("preserved preseason Year-1 authority has no frozen raw stat ensemble")
    return source_ids


def _provenance(
    year_one_evidence: LiveForecastEvidence,
    future_contract: FutureForecastContract,
) -> CompletedSourceFactProvenance:
    coverage = _FACTS.metadata.get("coverage_policy", {})
    fact_coverage: dict[str, bool | float | int | str | None] = {}
    if isinstance(coverage, dict):
        fact_coverage.update(
            {
                str(key): value
                for key, value in coverage.items()
                if isinstance(value, (bool, float, int, str)) or value is None
            }
        )
    source_ids = _preseason_source_ids(year_one_evidence)
    fact_coverage.update(
        {
            "rights_classification": str(
                _FACTS.metadata.get("rights_classification", "unclassified")
            ),
            "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
            "activation_workflow_run_id": ACTIVATION_WORKFLOW_RUN_ID,
            "future_forecast_contract_version": future_contract.contract_version,
            "future_forecast_scoring_coordinate": future_contract.scoring_coordinate,
            "year1_forecast_evidence_basis": year_one_evidence.evidence_basis,
            "year1_forecast_evaluation_as_of": (
                year_one_evidence.runtime_result.evaluation_as_of.isoformat()
            ),
            "year1_forecast_runtime_model_version": year_one_evidence.runtime_result.model_version,
            "year1_forecast_source_ids": ",".join(source_ids),
            "year1_forecast_source_count": len(source_ids),
        }
    )
    fact_coverage.update(future_contract.provenance)
    return CompletedSourceFactProvenance(
        source_version=future_contract.forecast_model_version,
        schema_version=future_contract.contract_version,
        providers=source_ids,
        fact_family_coverage=fact_coverage,
    )

def _legacy_provenance_gaps() -> tuple[str, ...]:
    """Optional activation-bundle coverage gaps retained for diagnostics only."""

    coverage = _FACTS.metadata.get("coverage_policy", {})
    if not isinstance(coverage, dict):
        return ("completed_source_coverage_metadata",)
    families = (
        ("roster_continuity", "roster_continuity"),
        ("injury_practice", "injury_practice"),
        ("participation_snaps", "participation_snaps"),
        ("role_opportunity", "role_opportunity"),
    )
    return tuple(sorted(name for key, name in families if coverage.get(key) is not True))


def _intrinsic_rules_payload(league_state: LeagueState) -> dict[str, object]:
    """Only league-rule inputs consumed by vNext scoring + Shapley economics."""

    rules = league_state.league.rules
    return {
        "team_count": rules.team_count,
        "lineup": [
            {"slot": item.slot.value, "count": item.count}
            for item in rules.lineup
        ],
        "scoring": [
            {"stat": item.stat, "points": item.points}
            for item in rules.scoring
        ],
    }


def intrinsic_input_fingerprint(
    context: UserRuntimeContext,
    year_one: tuple[ForecastObservation, ...],
    future_contract: FutureForecastContract,
    source_ids: tuple[str, ...],
    *,
    year_one_evidence: LiveForecastEvidence,
) -> str:
    """Fingerprint only governed inputs actually consumed by production Intrinsic."""

    assert context.league_state is not None
    payload = {
        "evaluation_season": context.league_state.league.season,
        "league_rules": _intrinsic_rules_payload(context.league_state),
        "year_one": [
            {
                "player_id": item.player_id,
                "position": item.position.value,
                "period_start": item.period_start.isoformat(),
                "period_end": item.period_end.isoformat(),
                "mean": item.distribution.mean,
                "stddev": item.distribution.stddev,
                "source": item.source,
                "model_version": item.model_version,
                "as_of": item.as_of.isoformat(),
                "provenance": item.provenance.model_dump(mode="json"),
            }
            for item in sorted(year_one, key=lambda observation: observation.player_id)
        ],
        "year_one_authority": {
            "evidence_basis": year_one_evidence.evidence_basis,
            "source_ids": source_ids,
            "evaluation_as_of": year_one_evidence.runtime_result.evaluation_as_of.isoformat(),
            "runtime_model_version": year_one_evidence.runtime_result.model_version,
        },
        "future_forecast_contract": future_contract.model_dump(mode="json"),
        "intrinsic_contract": {
            "contract_version": SHAPLEY_INTRINSIC_CONTRACT_VERSION,
            "model_version": SHAPLEY_INTRINSIC_MODEL_VERSION,
            "discount": FROZEN_INTRINSIC_DISCOUNT,
            "permutations": FROZEN_SHAPLEY_PERMUTATIONS,
            "seed": FROZEN_SHAPLEY_SEED,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PrivateBetaShapleyContractLoader:
    """Compose governed Year 1 -> versioned future Forecast -> frozen Shapley.

    The concrete Future Forecast provider is injected by hosted composition.
    This downstream loader consumes only the model-neutral Forecast contract and
    never imports model-specific production internals.
    """

    def __init__(
        self,
        *,
        year_one_loader: YearOneAuthorityLoader | None = None,
        persistence_store: PersistenceStore | None = None,
        future_forecast_builder: FutureForecastBuilder | None = None,
        future_forecast_model_version: str = "future-forecast-provider:unconfigured",
        future_missing_fact_family: str = "future_forecast_coordinate",
    ) -> None:
        self._lock = RLock()
        self._year_one_loader = year_one_loader
        self._persistence_store = persistence_store
        self._future_forecast_builder = future_forecast_builder
        self._future_forecast_model_version = str(future_forecast_model_version)
        self._future_missing_fact_family = str(future_missing_fact_family)
        self._cached_key: str | None = None
        self._cached_contract: ShapleyIntrinsicContract | None = None

    @property
    def forecast_model_version(self) -> str:
        """Forecast coordinate used by background lifecycle coalescing."""

        return self._future_forecast_model_version

    def _artifact_key(
        self,
        context: UserRuntimeContext,
        *,
        input_fingerprint: str,
        forecast_model_version: str,
    ) -> ArtifactKey:
        assert context.league_state is not None
        return ArtifactKey(
            artifact_kind=SHAPLEY_INTRINSIC_ARTIFACT_KIND,
            scope_kind=SHAPLEY_INTRINSIC_SCOPE_KIND,
            scope_id=context.league_state.league.league_id,
            input_fingerprint=input_fingerprint,
            model_version=(
                f"{SHAPLEY_INTRINSIC_CONTRACT_VERSION}"
                f"|forecast={forecast_model_version}"
            ),
        )

    def _restore_persisted(
        self,
        context: UserRuntimeContext,
        *,
        input_fingerprint: str,
        forecast_model_version: str,
    ) -> ShapleyIntrinsicContract | None:
        if self._persistence_store is None:
            return None
        record = self._persistence_store.get_reusable_artifact(
            self._artifact_key(
                context,
                input_fingerprint=input_fingerprint,
                forecast_model_version=forecast_model_version,
            )
        )
        if record is None:
            return None
        try:
            contract = ShapleyIntrinsicContract.model_validate(dict(record.payload))
        except (TypeError, ValueError):
            return None
        if contract.contract_version != SHAPLEY_INTRINSIC_CONTRACT_VERSION:
            return None
        if contract.forecast_model_version != forecast_model_version:
            return None
        return contract

    def _persist(
        self,
        context: UserRuntimeContext,
        *,
        input_fingerprint: str,
        forecast_model_version: str,
        contract: ShapleyIntrinsicContract,
    ) -> None:
        if self._persistence_store is None:
            return
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._artifact_key(
                    context,
                    input_fingerprint=input_fingerprint,
                    forecast_model_version=forecast_model_version,
                ),
                payload=contract.model_dump(mode="json"),
                computed_at=utc_now(),
            )
        )

    def intrinsic_input_fingerprint(self, context: UserRuntimeContext) -> str:
        """Resolve the dependency-scoped compatibility identity without Shapley."""

        league_state = context.league_state
        if league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        if self._future_forecast_builder is None or self._year_one_loader is None:
            unavailable = {
                "league_id": league_state.league.league_id,
                "season": league_state.league.season,
                "rules": _intrinsic_rules_payload(league_state),
                "forecast_model_version": self._future_forecast_model_version,
                "configured": False,
            }
            encoded = json.dumps(
                unavailable,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        try:
            evidence = self._year_one_loader(league_state)
            if evidence.evidence_basis != "preseason_baseline":
                raise ValueError(
                    "Frozen Year-1 Intrinsic compatibility requires preseason_baseline evidence"
                )
            year_one = _year_one_forecasts(evidence)
            if not year_one:
                raise ValueError("Preserved preseason Year-1 Forecast evidence is empty")
            source_ids = _preseason_source_ids(evidence)
            future_contract = self._future_forecast_builder(
                league_state=league_state,
                raw_forecasts=evidence.raw_forecasts,
                league_year_one=year_one,
            )
            if not isinstance(future_contract, FutureForecastContract):
                raise ValueError(
                    "Future Forecast provider must return FutureForecastContract"
                )
            h3_player_ids = set(future_contract.player_ids)
            h3_year_one = tuple(
                item for item in year_one if item.player_id in h3_player_ids
            )
            if len(h3_year_one) != len(h3_player_ids):
                raise ValueError(
                    "Governed H3 subjects are missing preserved Year-1 Forecast evidence"
                )
            return intrinsic_input_fingerprint(
                context,
                h3_year_one,
                future_contract,
                source_ids,
                year_one_evidence=evidence,
            )
        except Exception as exc:
            # Lifecycle coalescing must remain fail-closed without turning a
            # required-input problem into a pre-background HTTP exception.
            unavailable = {
                "league_id": league_state.league.league_id,
                "season": league_state.league.season,
                "rules": _intrinsic_rules_payload(league_state),
                "forecast_model_version": self._future_forecast_model_version,
                "availability_error": f"{type(exc).__name__}:{exc}",
            }
            encoded = json.dumps(
                unavailable,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def __call__(self, context: UserRuntimeContext) -> ShapleyIntrinsicContract:
        league_state = context.league_state
        if league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        if self._future_forecast_builder is None:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "A governed Future Forecast provider is not configured for "
                    "the product runtime."
                ),
                missing_required_fact_families=(self._future_missing_fact_family,),
                forecast_model_version=self._future_forecast_model_version,
            )
        if self._year_one_loader is None:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 authority loader is not configured.",
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=self._future_forecast_model_version,
            )
        try:
            evidence = self._year_one_loader(league_state)
        except Exception as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Preserved preseason Year-1 authority is unavailable: "
                    f"{type(exc).__name__}: {exc}"
                ),
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=self._future_forecast_model_version,
            )
        if evidence.evidence_basis != "preseason_baseline":
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Frozen Year-1 Intrinsic requires preseason_baseline evidence; "
                    f"received {evidence.evidence_basis}."
                ),
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=self._future_forecast_model_version,
            )
        year_one = _year_one_forecasts(evidence)
        if not year_one:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 Forecast evidence is empty.",
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=self._future_forecast_model_version,
            )

        try:
            source_ids = _preseason_source_ids(evidence)
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Preserved preseason Year-1 source lineage unavailable: {exc}",
                missing_required_fact_families=("preseason_year1_source_lineage",),
                forecast_model_version=self._future_forecast_model_version,
            )

        try:
            phase_started = perf_counter()
            future_contract = self._future_forecast_builder(
                league_state=league_state,
                raw_forecasts=evidence.raw_forecasts,
                league_year_one=year_one,
            )
            if not isinstance(future_contract, FutureForecastContract):
                raise ValueError(
                    "Future Forecast provider must return FutureForecastContract"
                )
            _logger.info(
                "FSFFL Intrinsic phase future-contract forecast=%s players=%s elapsed=%.3fs",
                future_contract.forecast_model_version,
                len(future_contract.player_ids),
                perf_counter() - phase_started,
            )
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Authoritative future Forecast contract unavailable: {exc}",
                # Preserve the configured missing-evidence classification. The
                # stable Forecast contract is the transport boundary; provider
                # implementation details never escape this loader.
                missing_required_fact_families=(self._future_missing_fact_family,),
                forecast_model_version=self._future_forecast_model_version,
            )

        h3_player_ids = set(future_contract.player_ids)
        h3_year_one = tuple(
            item for item in year_one if item.player_id in h3_player_ids
        )
        if len(h3_year_one) != len(h3_player_ids):
            missing_year_one = sorted(
                h3_player_ids - {item.player_id for item in h3_year_one}
            )
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Governed H3 subjects are missing preserved Year-1 Forecast evidence: "
                    f"{missing_year_one}"
                ),
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=future_contract.forecast_model_version,
            )

        key = intrinsic_input_fingerprint(
            context,
            h3_year_one,
            future_contract,
            source_ids,
            year_one_evidence=evidence,
        )
        with self._lock:
            if key == self._cached_key and self._cached_contract is not None:
                return self._cached_contract

            persisted = self._restore_persisted(
                context,
                input_fingerprint=key,
                forecast_model_version=future_contract.forecast_model_version,
            )
            if persisted is not None:
                self._cached_key = key
                self._cached_contract = persisted
                return persisted

            # Hold the loader lock through the expensive build. The HTTP layer runs
            # this work in a server-side background coordinator, so concurrent
            # browser requests never duplicate the same cold Shapley calculation.
            try:
                phase_started = perf_counter()
                calendar = compose_live_intrinsic_calendar_from_forecast_contract(
                    live_year_one_forecasts=h3_year_one,
                    future_contract=future_contract,
                )
                _logger.info(
                    "FSFFL Intrinsic phase value-adapter forecast=%s players=%s elapsed=%.3fs",
                    future_contract.forecast_model_version,
                    calendar.player_count,
                    perf_counter() - phase_started,
                )
            except ValueError as exc:
                return build_unavailable_shapley_intrinsic_contract(
                    evaluation_season=league_state.league.season,
                    reason=f"Future Forecast contract is not consumable by current Value: {exc}",
                    missing_required_fact_families=("future_forecast_value_adapter",),
                    forecast_model_version=future_contract.forecast_model_version,
                )
            phase_started = perf_counter()
            result = build_live_calendar_shapley_estimates(
                calendar,
                rules=league_state.league.rules,
            )
            _logger.info(
                "FSFFL Intrinsic phase shapley forecast=%s players=%s permutations=%s elapsed=%.3fs",
                future_contract.forecast_model_version,
                calendar.player_count,
                result.permutations,
                perf_counter() - phase_started,
            )
            contract = build_shapley_intrinsic_contract(
                result,
                completed_source_provenance=_provenance(evidence, future_contract),
                # Legacy activation coverage flags remain visible in completed-source
                # provenance but are not required inputs to the authorized vNext path.
                missing_required_fact_families=(),
                forecast_model_version=future_contract.forecast_model_version,
            )
            self._persist(
                context,
                input_fingerprint=key,
                forecast_model_version=future_contract.forecast_model_version,
                contract=contract,
            )
            self._cached_key = key
            self._cached_contract = contract
            return contract
