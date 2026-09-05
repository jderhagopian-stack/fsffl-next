from datetime import UTC, datetime, timedelta

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
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
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)


AS_OF = datetime(2026, 9, 5, 22, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state() -> LeagueState:
    league = League(
        league_id="league:sim",
        name="Simulation League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            playoff_team_count=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(),
        ),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="A"),
            Team(team_id="b", league_id=league.league_id, display_name="B"),
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


def test_live_simulation_runtime_populates_next7_competitive_metrics() -> None:
    result = build_live_simulation_analytics(
        _state(),
        forecasts=_forecasts(),
        forecast_model_version="next2-test",
        simulation_count=2_000,
        seed=7,
        generated_at=AS_OF,
    )

    assert result.simulation_result.simulation_count == 2_000
    rows = {row.team_id: row for row in result.league_view.teams}
    assert rows["a"].expected_wins is not None
    assert rows["a"].playoff_probability is not None
    assert rows["a"].first_place_probability is not None
    assert rows["a"].optimized_expected_points == 400.0
    assert rows["a"].expected_wins > rows["b"].expected_wins
    assert rows["a"].playoff_probability > rows["b"].playoff_probability
    assert "bye-aware-weekly-lineups" in result.simulation_result.model_version
    assert any(warning.code == "weekly_scoring_decomposition_provisional" for warning in result.league_view.context.warnings)
