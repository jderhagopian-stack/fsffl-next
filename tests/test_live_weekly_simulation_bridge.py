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
    CompletedMatchup,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    build_regular_season_simulation_input,
    build_weekly_team_scoring_distribution,
    regular_season_game_counts,
    scheduled_matchups_from_league_state,
    simulate_regular_season,
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


def test_current_season_simulation_preserves_completed_results_and_simulates_only_future() -> None:
    league_state = state()
    completed_state = league_state.model_copy(
        update={
            "completed_through_week": 1,
            "matchups": (
                LeagueMatchup(
                    week=1,
                    team_a_id="team:a",
                    team_b_id="team:b",
                    team_a_points=101.0,
                    team_b_points=99.0,
                    provenance=PROVENANCE,
                ),
                LeagueMatchup(
                    week=2,
                    team_a_id="team:a",
                    team_b_id="team:b",
                    provenance=PROVENANCE,
                ),
            ),
        }
    )
    weekly = (
        WeeklyTeamScoringDistribution(
            week=2,
            team_id="team:a",
            mean_points=0.0,
            stddev_points=0.0,
            model_version="future-week-test",
        ),
        WeeklyTeamScoringDistribution(
            week=2,
            team_id="team:b",
            mean_points=10.0,
            stddev_points=0.0,
            model_version="future-week-test",
        ),
    )

    request = build_regular_season_simulation_input(
        completed_state,
        weekly_scoring=weekly,
        simulation_count=100,
        seed=7,
        model_version="current-season-test",
    )

    assert request.completed_matchups == (
        CompletedMatchup(
            week=1,
            home_team_id="team:a",
            away_team_id="team:b",
            home_points=101.0,
            away_points=99.0,
        ),
    )
    assert request.schedule == (
        ScheduledMatchup(week=2, home_team_id="team:a", away_team_id="team:b"),
    )

    result = simulate_regular_season(request)
    outcomes = {row.team_id: row for row in result.outcomes}
    finishes = {row.team_id: row for row in result.finish_distributions}

    # Week 1 is factual: A's actual win cannot be redrawn. Week 2 is the only
    # simulated game, so B earns the only remaining win.
    assert outcomes["team:a"].expected_wins == pytest.approx(1.0)
    assert outcomes["team:a"].expected_remaining_wins == pytest.approx(0.0)
    assert outcomes["team:b"].expected_wins == pytest.approx(1.0)
    assert outcomes["team:b"].expected_remaining_wins == pytest.approx(1.0)

    # Final wins tie 1-1. Actual week-1 points are carried into the standings
    # tiebreak, so B's 99 actual + 10 future points beats A's 101 + 0.
    assert finishes["team:b"].rank_probabilities == (1.0, 0.0)
    assert finishes["team:a"].rank_probabilities == (0.0, 1.0)


def test_completed_boundary_fails_closed_when_factual_points_are_missing() -> None:
    incomplete = state().model_copy(update={"completed_through_week": 1})

    with pytest.raises(ValueError, match="completed regular-season matchup lacks factual points"):
        build_regular_season_simulation_input(
            incomplete,
            weekly_scoring=(),
            simulation_count=20,
            seed=7,
            model_version="current-season-test",
        )


def test_simulation_bridge_preserves_regular_season_when_playoff_count_is_missing() -> None:
    scoring = (
        TeamScoringDistribution(team_id="team:a", mean_points=150.0, stddev_points=30.0, model_version="test"),
        TeamScoringDistribution(team_id="team:b", mean_points=120.0, stddev_points=20.0, model_version="test"),
    )
    with pytest.raises(ValueError, match="no regular-season schedule"):
        build_regular_season_simulation_input(state(with_schedule=False), scoring=scoring)
    request = build_regular_season_simulation_input(
        state(playoff_team_count=None), scoring=scoring, simulation_count=20
    )
    assert request.playoff_team_count is None
    result = simulate_regular_season(request)
    assert all(row.playoff_probability is None for row in result.outcomes)
    assert {row.playoff_unavailability_reason for row in result.outcomes} == {
        "playoff_settings_unavailable"
    }
