from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fsffl.forecast.current_runtime import LiveForecastRuntimeResult
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.persistence.session import persist_runtime_snapshot, restore_runtime_snapshot
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.simulation_runtime import build_live_simulation_analytics
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    NflTeamBye,
    Player,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult


AS_OF = datetime(2026, 9, 10, 2, 0, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


class MemoryPersistence:
    def __init__(self) -> None:
        self.user = None
        self.league = None
        self.teams = {}
        self.artifacts = []
        self.market = []

    def get_user_runtime_context(self, *, user_id):
        return self.user if self.user and self.user.user_id == user_id else None

    def put_user_runtime_context(self, record):
        self.user = record

    def get_league_snapshot(self, *, provider, league_id, season):
        row = self.league
        return row if row and (row.provider, row.league_id, row.season) == (provider, league_id, season) else None

    def put_league_snapshot(self, record):
        self.league = record

    def get_team_snapshot(self, *, provider, league_id, team_id):
        return self.teams.get((provider, league_id, team_id))

    def put_team_snapshot(self, record):
        self.teams[(record.provider, record.league_id, record.team_id)] = record

    def get_sync_cursor(self, **kwargs):
        return None

    def put_sync_cursor(self, record):
        pass

    def get_reusable_artifact(self, key):
        return next((row for row in self.artifacts if row.key == key and row.reusable), None)

    def get_latest_reusable_artifact(self, *, artifact_kind, scope_kind, scope_id, model_version):
        rows = [
            row
            for row in self.artifacts
            if row.reusable
            and row.key.artifact_kind == artifact_kind
            and row.key.scope_kind == scope_kind
            and row.key.scope_id == scope_id
            and row.key.model_version == model_version
        ]
        return max(rows, key=lambda row: row.computed_at) if rows else None

    def put_artifact(self, record):
        self.artifacts.append(record)

    def invalidate_scope(self, **kwargs):
        pass

    def append_market_value_snapshot(self, **kwargs):
        self.market.append(kwargs)


def _state() -> LeagueState:
    league_id = "sleeper:artifact-lifecycle"
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Artifact Lifecycle League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                playoff_team_count=1,
                lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
                scoring=(),
            ),
            provider_refs=(ProviderRef(provider="sleeper", external_id="artifact-lifecycle"),),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="a", league_id=league_id, display_name="A"),
            Team(team_id="b", league_id=league_id, display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="pa", slot=RosterSlot.QB),)),
            TeamState(team_id="b", roster=(RosterEntry(player_id="pb", slot=RosterSlot.QB),)),
        ),
        players=(
            Player(player_id="pa", full_name="A QB", position=Position.QB, nfl_team="NE"),
            Player(player_id="pb", full_name="B QB", position=Position.QB, nfl_team="NYJ"),
        ),
        player_states=(
            PlayerState(player_id="pa", as_of=AS_OF, nfl_team="NE", provenance=PROVENANCE),
            PlayerState(player_id="pb", as_of=AS_OF, nfl_team="NYJ", provenance=PROVENANCE),
        ),
        matchups=tuple(
            LeagueMatchup(week=week, team_a_id="a", team_b_id="b", provenance=PROVENANCE)
            for week in range(1, 5)
        ),
        nfl_team_byes=(
            NflTeamBye(season=2026, nfl_team="NE", week=5, provenance=PROVENANCE),
            NflTeamBye(season=2026, nfl_team="NYJ", week=6, provenance=PROVENANCE),
        ),
        provenance=(PROVENANCE,),
    )


def _forecasts() -> tuple[ForecastObservation, ...]:
    return tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.QB,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=AS_OF,
            period_end=AS_OF + timedelta(days=180),
            distribution=ForecastDistribution(mean=mean, stddev=stddev),
            source="fsffl:live_league_scored",
            model_version="next2-live-calibrated-test",
            as_of=AS_OF,
            provenance=PROVENANCE,
        )
        for player_id, mean, stddev in (("pa", 400.0, 80.0), ("pb", 250.0, 60.0))
    )


def _forecast_evidence(forecasts: tuple[ForecastObservation, ...]) -> LiveForecastEvidence:
    runtime_result = LiveForecastRuntimeResult(
        raw_ensemble=forecasts,
        fantasy_point_forecasts=forecasts,
        coverage=LiveEnsembleCoverage(
            independent_source_ids=("test-a", "test-b"),
            excluded_aggregate_source_ids=(),
            active_source_ids=("test-a", "test-b"),
            observation_count=len(forecasts),
            minimum_independent_sources=2,
        ),
        successful_source_ids=("test-a", "test-b"),
        failed_sources=(),
        evaluation_as_of=AS_OF,
    )
    return LiveForecastEvidence(
        raw_forecasts=forecasts,
        league_scored_forecasts=forecasts,
        successful_source_ids=("test-a", "test-b"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=runtime_result,
    )


def test_current_forecast_simulation_and_value_restore_together_after_restart() -> None:
    persistence = MemoryPersistence()
    state = _state()
    forecasts = _forecasts()
    forecast = _forecast_evidence(forecasts)
    simulation = build_live_simulation_analytics(
        state,
        forecasts=forecasts,
        forecast_model_version=forecast.model_version,
        simulation_count=500,
        seed=7,
        generated_at=AS_OF,
    )
    values = CurrentMarketValueRuntimeResult(
        league_state_id=state.state_id,
        estimates=(),
        successful_source_ids=(),
        failed_sources=(),
        errors_by_source_id={},
        roster_player_count=2,
        valued_roster_player_count=0,
        market_context_id="test:artifact-lifecycle",
    )

    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=forecast,
        simulation_analytics=simulation,
        value_evidence=values,
    )

    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state == state
    assert restored.selected_team_id == "a"
    assert restored.forecast_evidence == forecast
    assert restored.simulation_analytics == simulation
    assert restored.value_evidence == values
