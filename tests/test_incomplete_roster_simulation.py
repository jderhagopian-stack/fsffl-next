from datetime import UTC, datetime, timedelta

from fsffl.forecast import (
    PROVISIONAL_POSITION_FLOOR_SOURCE,
    attach_provisional_position_floor_forecasts,
)
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
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state() -> LeagueState:
    league = League(
        league_id="league:thin",
        name="Thin Roster League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=3,
            playoff_team_count=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=2),),
            scoring=(),
        ),
    )
    players = (
        Player(player_id="a1", full_name="A One", position=Position.QB, nfl_team="NE"),
        Player(player_id="a2", full_name="A Two", position=Position.QB, nfl_team="NYJ"),
        Player(player_id="thin1", full_name="Thin QB", position=Position.QB, nfl_team="BUF"),
        Player(player_id="taxi1", full_name="Taxi QB", position=Position.QB, nfl_team="MIA"),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="Normal"),
            Team(team_id="thin", league_id=league.league_id, display_name="Hungry Dawgs"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(
                    RosterEntry(player_id="a1", slot=RosterSlot.QB),
                    RosterEntry(player_id="a2", slot=RosterSlot.BENCH),
                ),
            ),
            TeamState(
                team_id="thin",
                roster=(
                    RosterEntry(player_id="thin1", slot=RosterSlot.QB),
                    RosterEntry(player_id="taxi1", slot=RosterSlot.TAXI),
                ),
            ),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=AS_OF,
                nfl_team=player.nfl_team,
                provenance=PROV,
            )
            for player in players
        ),
        matchups=tuple(
            LeagueMatchup(
                week=week,
                team_a_id="a",
                team_b_id="thin",
                provenance=PROV,
            )
            for week in range(1, 5)
        ),
        nfl_team_byes=(
            NflTeamBye(season=2026, nfl_team="NE", week=5, provenance=PROV),
            NflTeamBye(season=2026, nfl_team="NYJ", week=6, provenance=PROV),
            NflTeamBye(season=2026, nfl_team="BUF", week=7, provenance=PROV),
            NflTeamBye(season=2026, nfl_team="MIA", week=8, provenance=PROV),
        ),
    )


def _forecast(player_id: str, mean: float, stddev: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=120),
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="fsffl:test",
        model_version="forecast-test",
        as_of=AS_OF,
        provenance=PROV,
    )


def test_position_floor_fallback_is_conservative_and_excludes_taxi() -> None:
    state = _state()
    original = (
        _forecast("a1", 400.0, 55.0),
        _forecast("a2", 250.0, 90.0),
    )
    enriched = attach_provisional_position_floor_forecasts(
        state,
        original,
        as_of=AS_OF,
    )
    fallback = next(item for item in enriched if item.player_id == "thin1")

    assert fallback.source == PROVISIONAL_POSITION_FLOOR_SOURCE
    assert fallback.distribution.mean == 250.0
    assert fallback.distribution.stddev == 90.0
    assert all(item.player_id != "taxi1" for item in enriched)


def test_incomplete_tanking_roster_does_not_block_league_simulation() -> None:
    result = build_live_simulation_analytics(
        _state(),
        forecasts=(
            _forecast("a1", 400.0, 55.0),
            _forecast("a2", 250.0, 90.0),
        ),
        forecast_model_version="next2-test",
        simulation_count=2_000,
        seed=11,
        generated_at=AS_OF,
    )

    assert result.simulation_result.simulation_count == 2_000
    thin = next(view for view in result.team_views if view.team_id == "thin")
    assert len(thin.optimized_lineup.assignments) == 1
    assert len(thin.optimized_lineup.unfilled_slots) == 1
    assert thin.optimized_lineup.unfilled_slots[0].expected_points == 0.0
    assert thin.utility.competitive_outcome is not None
    assert thin.utility.roster_resilience is None
    assert any(
        warning.code == "position_floor_forecast_fallback"
        for warning in result.league_view.context.warnings
    )
    assert any(
        warning.code == "explicit_unfilled_lineup_slots"
        and "Hungry Dawgs" in warning.message
        for warning in result.league_view.context.warnings
    )
