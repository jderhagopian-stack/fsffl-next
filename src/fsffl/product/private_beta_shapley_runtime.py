from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Callable

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
from fsffl.value.shapley_intrinsic_contract import (
    CompletedSourceFactProvenance,
    ShapleyIntrinsicContract,
    build_shapley_intrinsic_contract,
    build_unavailable_shapley_intrinsic_contract,
)

from .p0_forecast_runtime import P0_FORECAST_VERSION, P0_SOURCE_SEASON
from .p0_future_forecast_provider import build_p0_future_forecast_contract
from .runtime import LiveForecastEvidence, UserRuntimeContext, league_material_fingerprint

_SUPPORTED_POSITIONS = {Position.QB, Position.RB, Position.WR, Position.TE}
YearOneAuthorityLoader = Callable[[LeagueState], LiveForecastEvidence]


def _json_artifact(name: str) -> dict[str, object]:
    raw = json.loads(activation_artifact_text(name))
    if not isinstance(raw, dict):
        raise ValueError(f"private-beta activation artifact must be a JSON object: {name}")
    return raw


# The legacy activation bundle remains metadata/coverage evidence only. It is not
# the Y2/Y3 producer after P0 promotion.
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

def _missing_fact_families() -> tuple[str, ...]:
    # Preserve the API's explicit evidence-coverage signaling. Missing fact
    # families are not imputed into P0 and cannot change its frozen coefficients.
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


def _cache_key(
    context: UserRuntimeContext,
    year_one: tuple[ForecastObservation, ...],
    future_contract: FutureForecastContract,
    source_ids: tuple[str, ...],
) -> str:
    assert context.league_state is not None
    payload = {
        "league": league_material_fingerprint(context.league_state),
        "year_one": [
            {
                "player_id": item.player_id,
                "mean": item.distribution.mean,
                "stddev": item.distribution.stddev,
                "source": item.source,
                "model_version": item.model_version,
                "as_of": item.as_of.isoformat(),
            }
            for item in sorted(year_one, key=lambda observation: observation.player_id)
        ],
        "preseason_source_ids": source_ids,
        "future_forecast_contract": future_contract.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PrivateBetaShapleyContractLoader:
    """Compose frozen preseason Y1 -> exact P0 Y2/Y3 -> frozen Shapley.

    No model fitting or selection occurs here. The embedded P0 package is a
    byte-verified fitted artifact. League scoring remains downstream through the
    player-specific Year-1 league/standard translation.
    """

    def __init__(
        self,
        *,
        year_one_loader: YearOneAuthorityLoader | None = None,
    ) -> None:
        self._lock = RLock()
        self._year_one_loader = year_one_loader
        self._cached_key: str | None = None
        self._cached_contract: ShapleyIntrinsicContract | None = None

    def __call__(self, context: UserRuntimeContext) -> ShapleyIntrinsicContract:
        league_state = context.league_state
        if league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        if league_state.league.season != P0_SOURCE_SEASON:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "The pinned private-beta P0 package targets "
                    f"evaluation season {P0_SOURCE_SEASON}, not {league_state.league.season}."
                ),
                missing_required_fact_families=("p0_future_forecast_coordinate",),
                forecast_model_version=P0_FORECAST_VERSION,
            )
        if self._year_one_loader is None:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 authority loader is not configured.",
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=P0_FORECAST_VERSION,
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
                forecast_model_version=P0_FORECAST_VERSION,
            )
        if evidence.evidence_basis != "preseason_baseline":
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Frozen Year-1 Intrinsic requires preseason_baseline evidence; "
                    f"received {evidence.evidence_basis}."
                ),
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=P0_FORECAST_VERSION,
            )
        year_one = _year_one_forecasts(evidence)
        if not year_one:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 Forecast evidence is empty.",
                missing_required_fact_families=("preseason_year1_forecast",),
                forecast_model_version=P0_FORECAST_VERSION,
            )

        try:
            source_ids = _preseason_source_ids(evidence)
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Preserved preseason Year-1 source lineage unavailable: {exc}",
                missing_required_fact_families=("preseason_year1_source_lineage",),
                forecast_model_version=P0_FORECAST_VERSION,
            )

        try:
            future_materialization = build_p0_future_forecast_contract(
                league_state=league_state,
                raw_forecasts=evidence.raw_forecasts,
                league_year_one=year_one,
            )
            future_contract = future_materialization.contract
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Authoritative future Forecast contract unavailable: {exc}",
                missing_required_fact_families=("future_forecast_contract",),
                forecast_model_version=P0_FORECAST_VERSION,
            )

        key = _cache_key(context, year_one, future_contract, source_ids)
        with self._lock:
            if key == self._cached_key and self._cached_contract is not None:
                return self._cached_contract

        try:
            calendar = compose_live_intrinsic_calendar_from_forecast_contract(
                live_year_one_forecasts=year_one,
                future_contract=future_contract,
            )
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Future Forecast contract is not consumable by current Value: {exc}",
                missing_required_fact_families=("future_forecast_value_adapter",),
                forecast_model_version=future_contract.forecast_model_version,
            )
        result = build_live_calendar_shapley_estimates(
            calendar,
            rules=league_state.league.rules,
        )
        contract = build_shapley_intrinsic_contract(
            result,
            completed_source_provenance=_provenance(evidence, future_contract),
            missing_required_fact_families=_missing_fact_families(),
            forecast_model_version=P0_FORECAST_VERSION,
        )
        with self._lock:
            self._cached_key = key
            self._cached_contract = contract
        return contract
