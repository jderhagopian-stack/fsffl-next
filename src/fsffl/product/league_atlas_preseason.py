from __future__ import annotations

from datetime import datetime

from fsffl.forecast.annual_preseason_snapshot import ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION
from fsffl.forecast.preseason_baseline import state_is_preseason_capture_eligible
from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    NFL_SEASON_SCOPE_KIND,
    decode_annual_preseason_projection_snapshot,
)
from fsffl.persistence.contracts import (
    ArtifactKey,
    PersistenceStore,
    ReusableArtifactRecord,
    canonical_fingerprint,
)
from fsffl.persistence.runtime_cache import LEAGUE_SEASON_SCOPE_KIND
from fsffl.state.models import FrozenModel, LeagueState

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult


LEAGUE_ATLAS_PRESEASON_ARTIFACT_KIND = "league_atlas_preseason_baseline"
LEAGUE_ATLAS_PRESEASON_MODEL_VERSION = "phase3-league-atlas-preseason-v1"


class LeagueAtlasPreseasonTeam(FrozenModel):
    team_id: str
    projected_starter_points: float
    rank: int
    playoff_probability: float
    championship_probability: float
    first_place_probability: float
    expected_wins: float
    expected_finish: float


class LeagueAtlasPreseasonBaseline(FrozenModel):
    league_id: str
    season: int
    state_id: str
    state_as_of: datetime
    forecast_evaluation_as_of: datetime
    forecast_model_version: str
    simulation_model_version: str
    simulation_count: int
    opener_date: str
    opener_coordinate_source: str
    status: str = "frozen"
    teams: tuple[LeagueAtlasPreseasonTeam, ...]
    model_version: str = LEAGUE_ATLAS_PRESEASON_MODEL_VERSION


def league_season_scope_id(state: LeagueState) -> str:
    return f"{state.league.league_id}:{state.league.season}"


def _team_rows(
    simulation: LiveSimulationAnalyticsResult,
) -> tuple[LeagueAtlasPreseasonTeam, ...]:
    outcomes = {row.team_id: row for row in simulation.simulation_result.outcomes}
    finishes = {
        row.team_id: row for row in simulation.simulation_result.finish_distributions
    }
    starter_points: dict[str, float] = {}
    for view in simulation.team_views:
        lineup = view.optimized_lineup
        if lineup is None:
            continue
        starter_points[view.team_id] = sum(
            float(assignment.expected_points) for assignment in lineup.assignments
        )

    ranked = sorted(
        starter_points,
        key=lambda team_id: (-starter_points[team_id], team_id),
    )
    rank_by_team = {team_id: rank for rank, team_id in enumerate(ranked, start=1)}

    rows: list[LeagueAtlasPreseasonTeam] = []
    for team_id in ranked:
        outcome = outcomes.get(team_id)
        finish = finishes.get(team_id)
        if outcome is None:
            continue
        rows.append(
            LeagueAtlasPreseasonTeam(
                team_id=team_id,
                projected_starter_points=starter_points[team_id],
                rank=rank_by_team[team_id],
                playoff_probability=outcome.playoff_probability,
                championship_probability=outcome.championship_probability,
                first_place_probability=outcome.first_place_probability,
                expected_wins=outcome.expected_wins,
                expected_finish=(
                    float(finish.expected_finish)
                    if finish is not None
                    else float(rank_by_team[team_id])
                ),
            )
        )
    return tuple(rows)


def capture_preseason_baseline_if_eligible(
    store: PersistenceStore | None,
    *,
    state: LeagueState,
    forecast: LiveForecastEvidence,
    simulation: LiveSimulationAnalyticsResult,
) -> LeagueAtlasPreseasonBaseline | None:
    """Persist the latest valid pre-opener 50k league baseline automatically.

    This is orchestration/persistence only. It reuses the already-authoritative
    State, Forecast, optimized lineup, and Simulation outputs and never calculates
    a second probability path.
    """

    if store is None or not state_is_preseason_capture_eligible(state):
        return None
    if simulation.simulation_result.simulation_count != 50_000:
        return None
    if simulation.league_view.context.league_state_id != state.state_id:
        return None

    annual = store.get_latest_reusable_artifact(
        artifact_kind=ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        scope_kind=NFL_SEASON_SCOPE_KIND,
        scope_id=str(state.league.season),
        model_version=ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    )
    if annual is None:
        return None
    snapshot = decode_annual_preseason_projection_snapshot(dict(annual.payload))
    # The governed schedule coordinate currently has date precision. Requiring the
    # State date to be strictly before the opener date is deliberately conservative:
    # no same-day post-kickoff snapshot can enter the historical baseline.
    if state.as_of.date() >= snapshot.opener_date:
        return None

    teams = _team_rows(simulation)
    if len(teams) != len(state.teams):
        return None

    baseline = LeagueAtlasPreseasonBaseline(
        league_id=state.league.league_id,
        season=state.league.season,
        state_id=state.state_id,
        state_as_of=state.as_of,
        forecast_evaluation_as_of=forecast.runtime_result.evaluation_as_of,
        forecast_model_version=forecast.model_version,
        simulation_model_version=simulation.simulation_result.model_version,
        simulation_count=simulation.simulation_result.simulation_count,
        opener_date=snapshot.opener_date.isoformat(),
        opener_coordinate_source=snapshot.opener_coordinate_source,
        teams=teams,
    )
    payload = baseline.model_dump(mode="json")
    store.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=LEAGUE_ATLAS_PRESEASON_ARTIFACT_KIND,
                scope_kind=LEAGUE_SEASON_SCOPE_KIND,
                scope_id=league_season_scope_id(state),
                input_fingerprint=canonical_fingerprint(
                    baseline.state_id,
                    baseline.forecast_evaluation_as_of.isoformat(),
                    baseline.forecast_model_version,
                    baseline.simulation_model_version,
                    baseline.simulation_count,
                ),
                model_version=LEAGUE_ATLAS_PRESEASON_MODEL_VERSION,
            ),
            payload=payload,
            computed_at=state.as_of,
        )
    )
    return baseline


def load_preseason_baseline(
    store: PersistenceStore | None,
    *,
    state: LeagueState,
) -> LeagueAtlasPreseasonBaseline | None:
    if store is None:
        return None
    record = store.get_latest_reusable_artifact(
        artifact_kind=LEAGUE_ATLAS_PRESEASON_ARTIFACT_KIND,
        scope_kind=LEAGUE_SEASON_SCOPE_KIND,
        scope_id=league_season_scope_id(state),
        model_version=LEAGUE_ATLAS_PRESEASON_MODEL_VERSION,
    )
    if record is None:
        return None
    baseline = LeagueAtlasPreseasonBaseline.model_validate(record.payload)
    if (
        baseline.league_id != state.league.league_id
        or baseline.season != state.league.season
        or baseline.simulation_count != 50_000
    ):
        return None
    return baseline
