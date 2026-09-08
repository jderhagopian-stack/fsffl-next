from datetime import UTC, datetime

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.product.intelligence_runtime import build_forecast_lineup_analytics
from fsffl.state.models import League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState, Position, Provenance, RosterEntry, RosterSlot, Team, TeamState

AS_OF = datetime(2026, 9, 5, 20, tzinfo=UTC)


def _forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    provenance = Provenance(source="fsffl:live_league_scored", retrieved_at=AS_OF, effective_at=AS_OF)
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 3, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=points, stddev=15.0),
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v1",
        as_of=AS_OF,
        provenance=provenance,
    )


def _state() -> LeagueState:
    provenance = Provenance(source="sleeper", retrieved_at=AS_OF, effective_at=AS_OF)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=2,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(),
        ),
    )
    players = (
        Player(player_id="p1", full_name="QB One", position=Position.QB, nfl_team="BAL"),
        Player(player_id="p2", full_name="QB Two", position=Position.QB, nfl_team="BUF"),
        Player(player_id="p3", full_name="QB Three", position=Position.QB, nfl_team="KC"),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(Team(team_id="a", league_id="l1", display_name="Alpha"), Team(team_id="b", league_id="l1", display_name="Beta")),
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.BENCH), RosterEntry(player_id="p2", slot=RosterSlot.BENCH))),
            TeamState(team_id="b", roster=(RosterEntry(player_id="p3", slot=RosterSlot.BENCH),)),
        ),
        players=players,
        player_states=tuple(PlayerState(player_id=p.player_id, as_of=AS_OF, nfl_team=p.nfl_team, provenance=provenance) for p in players),
    )


def test_lineup_analytics_uses_next4_and_leaves_undercovered_team_missing() -> None:
    result = build_forecast_lineup_analytics(
        _state(),
        forecasts=(_forecast("p1", Position.QB, 300.0), _forecast("p2", Position.QB, 250.0)),
        forecast_model_version="next8-live-forecast-evidence-v2",
        generated_at=AS_OF,
    )
    rows = {row.team_id: row for row in result.league_view.teams}
    assert rows["a"].optimized_expected_points == 300.0
    assert rows["b"].optimized_expected_points is None
    assert result.unavailable_team_ids == ("b",)
    alpha = next(view for view in result.team_views if view.team_id == "a")
    assert alpha.optimized_lineup is not None
    assert alpha.optimized_lineup.assignments[0].player_id == "p1"
