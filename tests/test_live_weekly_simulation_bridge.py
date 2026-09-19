from datetime import UTC, datetime, timedelta
from math import sqrt

import pytest

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.team_utility import (
    TeamScoringDistribution,
    build_regular_season_simulation_input,
    build_weekly_team_scoring_distribution,
    regular_season_game_counts,
    scheduled_matchups_from_league_state,
)


AS_OF = datetime(2026, 9, 5, 22, tzinfo=UTC)
PROVENANCE = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def state(*, with_schedule: bool = True, playoff_team_count: int | None = 1) -> LeagueState:
    league = League(
        league_id="league:weekly",
        name="Weekly League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            playoff_team_count=playoff_team_count,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(),
        ),
    )
    teams = (
        Team(team_id="team:a", league_id=league.league_id, display_name="A"),
        Team(team_id="team:b", league_id=league.league_id, display_name="B"),
    )
    players = (
        Player(player_id="qa", full_name="QA", position=Position.QB),
        Player(player_id="qb", full_name="QB", position=Position.QB),
    )
    matchups = (
        LeagueMatchup(week=1, team_a_id="team:a", team_b_id="team:b", provenance=PROVENANCE),
        LeagueMatchup(week=2, team_a_id="team:a", team_b_id="team:b", provenance=PROVENANCE),
    ) if with_schedule else ()
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=(
            TeamState(team_id="team:a", roster=(RosterEntry(player_id="qa", slot=RosterSlot.QB),)),
            TeamState(team_id="team:b", roster=(RosterEntry(player_id="qb", slot=RosterSlot.QB),)),
        ),
        players=players,
        player_states=(
            PlayerState(player_id="qa", as_of=AS_OF, provenance=PROVENANCE),
            PlayerState(player_id="qb", as_of=AS_OF, provenance=PROVENANCE),
        ),
        matchups=matchups,
    )


def forecasts() -> tuple[ForecastObservation, ...]:
    values = (("qa", 300.0, 60.0), ("qb", 240.0, 40.0))
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
        for player_id, mean, stddev in values
    )


def test_weekly_decomposition_reconstructs_season_mean_and_variance() -> None:
    weekly = build_weekly_team_scoring_distribution(
        state(),
        forecasts(),
        team_id="team:a",
        as_of=AS_OF,
        regular_season_game_count=2,
    )
    assert weekly.mean_points * 2 == pytest.approx(300.0)
    assert weekly.stddev_points * sqrt(2) == pytest.approx(60.0)
    assert "independent_equal_week" in weekly.model_version


def test_schedule_bridge_uses_only_canonical_state() -> None:
    league_state = state()
    schedule = scheduled_matchups_from_league_state(league_state)
    assert [(item.week, item.home_team_id, item.away_team_id) for item in schedule] == [
        (1, "team:a", "team:b"),
        (2, "team:a", "team:b"),
    ]
    assert regular_season_game_counts(league_state) == {"team:a": 2, "team:b": 2}


def test_simulation_input_uses_canonical_playoff_size_and_50k_default() -> None:
    league_state = state()
    scoring = (
        TeamScoringDistribution(team_id="team:a", mean_points=150.0, stddev_points=30.0, model_version="test"),
        TeamScoringDistribution(team_id="team:b", mean_points=120.0, stddev_points=20.0, model_version="test"),
    )
    request = build_regular_season_simulation_input(league_state, scoring=scoring)
    assert request.playoff_team_count == 1
    assert request.simulation_count == 50_000
    assert len(request.schedule) == 2


def test_simulation_bridge_fails_closed_without_schedule_or_playoff_count() -> None:
    scoring = (
        TeamScoringDistribution(team_id="team:a", mean_points=150.0, stddev_points=30.0, model_version="test"),
        TeamScoringDistribution(team_id="team:b", mean_points=120.0, stddev_points=20.0, model_version="test"),
    )
    with pytest.raises(ValueError, match="no regular-season schedule"):
        build_regular_season_simulation_input(state(with_schedule=False), scoring=scoring)
    with pytest.raises(ValueError, match="playoff_team_count"):
        build_regular_season_simulation_input(state(playoff_team_count=None), scoring=scoring)
