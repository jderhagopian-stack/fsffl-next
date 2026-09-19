from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Callable

from fsffl.forecast.i1_artifact import FrozenI1Artifact
from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact, map_current_i1_facts
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Position
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar,
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

from .i1_scoring_bridge import (
    FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
    LeagueScoringNormalizedI1Predictor,
    build_future_i1_position_scoring_multipliers,
)
from .runtime import LiveForecastEvidence, UserRuntimeContext, league_material_fingerprint

_SUPPORTED_POSITIONS = {Position.QB, Position.RB, Position.WR, Position.TE}
YearOneAuthorityLoader = Callable[[LeagueState], LiveForecastEvidence]


def _json_artifact(name: str) -> dict[str, object]:
    raw = json.loads(activation_artifact_text(name))
    if not isinstance(raw, dict):
        raise ValueError(f"private-beta activation artifact must be a JSON object: {name}")
    return raw


_H12 = FrozenI1Artifact.from_dict(_json_artifact("frozen_i1_h12.json"))
_H3 = FrozenI1Artifact.from_dict(_json_artifact("frozen_i1_h3.json"))
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


def _scoped_state(league_state: LeagueState, player_ids: set[str]) -> LeagueState:
    """Limit completed-source mapping to the governed live Forecast universe.

    The global Sleeper state may contain hundreds of unsupported or irrelevant free
    agents. Those records must not block Intrinsic. A player that actually appears
    in the governed Year-1 Forecast universe remains mandatory and fail-closed.
    """

    by_player = {player.player_id: player for player in league_state.players}
    missing = sorted(player_ids - set(by_player))
    if missing:
        raise ValueError(f"governed Year-1 Forecast references unknown canonical players: {missing}")
    scoped_players = tuple(player for player in league_state.players if player.player_id in player_ids)
    scoped_states = tuple(state for state in league_state.player_states if state.player_id in player_ids)
    scoped_team_states = tuple(
        team_state.model_copy(
            update={
                "roster": tuple(entry for entry in team_state.roster if entry.player_id in player_ids),
            }
        )
        for team_state in league_state.team_states
    )
    return league_state.model_copy(
        update={
            "players": scoped_players,
            "player_states": scoped_states,
            "team_states": scoped_team_states,
        }
    )


def _provenance(
    year_one_evidence: LiveForecastEvidence,
    scoring_multipliers: dict[Position, float] | None = None,
) -> CompletedSourceFactProvenance:
    metadata = dict(_FACTS.metadata)
    providers = metadata.get("providers", ())
    if not isinstance(providers, (list, tuple)):
        providers = ()
    coverage = metadata.get("coverage_policy", {})
    fact_coverage: dict[str, bool | float | int | str | None] = {}
    if isinstance(coverage, dict):
        fact_coverage.update(
            {
                str(key): value
                for key, value in coverage.items()
                if isinstance(value, (bool, float, int, str)) or value is None
            }
        )
    fact_coverage.update(
        {
            "provider_neutral_contract": bool(metadata.get("provider_neutral_contract", False)),
            "rights_classification": str(metadata.get("rights_classification", "unclassified")),
            "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
            "activation_workflow_run_id": ACTIVATION_WORKFLOW_RUN_ID,
            "future_i1_scoring_bridge_version": FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
            "year1_forecast_evidence_basis": year_one_evidence.evidence_basis,
            "year1_forecast_evaluation_as_of": year_one_evidence.runtime_result.evaluation_as_of.isoformat(),
            "year1_forecast_runtime_model_version": year_one_evidence.runtime_result.model_version,
        }
    )
    if scoring_multipliers is not None:
        for position, multiplier in sorted(
            scoring_multipliers.items(),
            key=lambda item: item[0].value,
        ):
            fact_coverage[
                f"future_i1_scoring_multiplier_{position.value.lower()}"
            ] = float(multiplier)
    return CompletedSourceFactProvenance(
        source_version=_FACTS.source_version,
        schema_version=_FACTS.schema_version,
        providers=tuple(str(item) for item in providers),
        fact_family_coverage=fact_coverage,
    )


def _missing_fact_families() -> tuple[str, ...]:
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
    scoring_multipliers: dict[Position, float],
) -> str:
    assert context.league_state is not None
    payload = {
        "activation_bundle": ACTIVATION_BUNDLE_SHA256,
        "league": league_material_fingerprint(context.league_state),
        "forecast": [
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
        "future_i1_scoring_bridge": {
            "version": FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
            "multipliers": {
                position.value: multiplier
                for position, multiplier in sorted(
                    scoring_multipliers.items(),
                    key=lambda item: item[0].value,
                )
            },
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PrivateBetaShapleyContractLoader:
    """Attach the validated completed-source bundle to the hosted Value contract.

    This class is product composition only. It does not fit, tune or alter I1,
    Shapley, B4, the calendar coordinate or the raw Value contract. The one-entry
    cache reuses an identical immutable contract until league facts or the governed
    Year-1 Forecast evidence changes.
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
        if league_state.league.season != _FACTS.evaluation_season:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "The pinned private-beta completed-source bundle targets "
                    f"evaluation season {_FACTS.evaluation_season}, not {league_state.league.season}."
                ),
                missing_required_fact_families=("completed_source_i1_facts",),
            )
        if self._year_one_loader is None:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 authority loader is not configured.",
                missing_required_fact_families=("preseason_year1_forecast",),
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
            )
        if evidence.evidence_basis != "preseason_baseline":
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Frozen Year-1 Intrinsic requires preseason_baseline evidence; "
                    f"received {evidence.evidence_basis}."
                ),
                missing_required_fact_families=("preseason_year1_forecast",),
            )
        year_one = _year_one_forecasts(evidence)
        if not year_one:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason="Preserved preseason Year-1 Forecast evidence is empty.",
                missing_required_fact_families=("preseason_year1_forecast",),
            )

        try:
            scoring_multipliers = build_future_i1_position_scoring_multipliers(
                raw_forecasts=evidence.raw_forecasts,
                league_year_one=year_one,
                rules=league_state.league.rules,
            )
        except ValueError as exc:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=f"Future I1 league-scoring normalization unavailable: {exc}",
                missing_required_fact_families=("future_i1_league_scoring_coordinate",),
            )

        key = _cache_key(context, year_one, scoring_multipliers)
        with self._lock:
            if key == self._cached_key and self._cached_contract is not None:
                return self._cached_contract

        year_one_ids = {item.player_id for item in year_one}
        scoped = _scoped_state(league_state, year_one_ids)
        mapping = map_current_i1_facts(scoped, _FACTS)
        if mapping.unmapped_player_ids or mapping.ambiguous_player_ids:
            return build_unavailable_shapley_intrinsic_contract(
                evaluation_season=league_state.league.season,
                reason=(
                    "Completed-source I1 evidence does not uniquely cover every player in the governed "
                    f"Year-1 Forecast universe; unmapped={mapping.unmapped_player_ids}; "
                    f"ambiguous={mapping.ambiguous_player_ids}."
                ),
                missing_required_fact_families=("completed_source_player_mapping",),
            )
        if mapping.mapped_count != len(year_one_ids):
            raise ValueError("completed-source mapping coverage does not equal governed Year-1 Forecast coverage")

        h12 = LeagueScoringNormalizedI1Predictor(
            _H12,
            multipliers=scoring_multipliers,
        )
        h3 = LeagueScoringNormalizedI1Predictor(
            _H3,
            multipliers=scoring_multipliers,
        )
        calendar = compose_live_intrinsic_calendar(
            live_year_one_forecasts=year_one,
            mapping=mapping,
            h1_h2_predictor=h12,
            h3_predictor=h3,
        )
        result = build_live_calendar_shapley_estimates(
            calendar,
            rules=league_state.league.rules,
        )
        contract = build_shapley_intrinsic_contract(
            result,
            completed_source_provenance=_provenance(evidence, scoring_multipliers),
            missing_required_fact_families=_missing_fact_families(),
        )
        with self._lock:
            self._cached_key = key
            self._cached_contract = contract
        return contract
