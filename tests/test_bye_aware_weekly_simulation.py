from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.weekly_volatility import FSFFL_2023_2025_WEEKLY_VOLATILITY
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
from fsffl.team_utility import (
    build_bye_aware_weekly_team_scoring_distribution,
    build_bye_aware_weekly_team_scoring_panel,
    optimize_team_lineup,
)


AS_OF = datetime(2026, 9, 5, 22, tzinfo=UTC)
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _forecast(player_id: str, mean: float, stddev: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=150),
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="test",
        model_version="test",
        as_of=AS_OF,
        provenance=PROV,
    )


def _state() -> LeagueState:
    league = League(
        league_id="league:bye",
        name="Bye Test",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=2,
            playoff_team_count=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(),
        ),
    )
    players = (
        Player(player_id="starter", full_name="Starter", position=Position.QB, nfl_team="KC"),
        Player(player_id="bench", full_name="Bench", position=Position.QB, nfl_team="NYJ"),
        Player(player_id="opp", full_name="Opponent", position=Position.QB, nfl_team="BUF"),
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="A"),
            Team(team_id="b", league_id=league.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(
                    RosterEntry(player_id="starter", slot=RosterSlot.QB),
                    RosterEntry(player_id="bench", slot=RosterSlot.BENCH),
                ),
            ),
            TeamState(team_id="b", roster=(RosterEntry(player_id="opp", slot=RosterSlot.QB),)),
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
        matchups=(
            LeagueMatchup(week=5, team_a_id="a", team_b_id="b", provenance=PROV),
            LeagueMatchup(week=6, team_a_id="a", team_b_id="b", provenance=PROV),
        ),
        nfl_team_byes=(
            NflTeamBye(season=2026, nfl_team="KC", week=5, provenance=PROV),
            NflTeamBye(season=2026, nfl_team="NYJ", week=10, provenance=PROV),
            NflTeamBye(season=2026, nfl_team="BUF", week=7, provenance=PROV),
        ),
    )


def test_week_specific_lineup_replaces_player_on_bye_and_uses_weekly_volatility() -> None:
    state = _state()
    forecasts = (
        _forecast("starter", 340.0, 68.0),
        _forecast("bench", 170.0, 51.0),
        _forecast("opp", 255.0, 60.0),
    )

    bye_week = build_bye_aware_weekly_team_scoring_distribution(
        state,
        forecasts,
        team_id="a",
        week=5,
        as_of=AS_OF,
    )
    normal_week = build_bye_aware_weekly_team_scoring_distribution(
        state,
        forecasts,
        team_id="a",
        week=6,
        as_of=AS_OF,
    )

    qb_cv = FSFFL_2023_2025_WEEKLY_VOLATILITY.coefficient_of_variation(Position.QB)
    assert bye_week.mean_points == pytest.approx(170.0 / 17.0)
    assert normal_week.mean_points == pytest.approx(340.0 / 17.0)
    assert bye_week.stddev_points == pytest.approx((170.0 / 17.0) * qb_cv)
    assert normal_week.stddev_points == pytest.approx((340.0 / 17.0) * qb_cv)
    assert "bye_aware_empirical_weekly_volatility" in bye_week.model_version
    assert normal_week.mean_points > bye_week.mean_points

    # Season forecast-error uncertainty must no longer leak into weekly scoring
    # variance. Changing only the season stddev cannot change weekly stddev.
    wider_season_uncertainty = (
        _forecast("starter", 340.0, 340.0),
        _forecast("bench", 170.0, 170.0),
        _forecast("opp", 255.0, 255.0),
    )
    same_week = build_bye_aware_weekly_team_scoring_distribution(
        state,
        wider_season_uncertainty,
        team_id="a",
        week=6,
        as_of=AS_OF,
    )
    assert same_week.stddev_points == pytest.approx(normal_week.stddev_points)


def test_batched_weekly_panel_matches_independent_builds_and_reuses_baseline() -> None:
    state = _state()
    forecasts = (
        _forecast("starter", 340.0, 68.0),
        _forecast("bench", 170.0, 51.0),
        _forecast("opp", 255.0, 60.0),
    )
    baseline = {
        team_id: optimize_team_lineup(
            state,
            forecasts,
            team_id=team_id,
            as_of=AS_OF,
            horizon=ForecastHorizon.SEASON,
            allow_unfilled_slots=True,
        )
        for team_id in ("a", "b")
    }
    panel = build_bye_aware_weekly_team_scoring_panel(
        state,
        forecasts,
        team_ids=("a", "b"),
        weeks=(5, 6),
        as_of=AS_OF,
        baseline_lineups=baseline,
    )
    independent = tuple(
        build_bye_aware_weekly_team_scoring_distribution(
            state,
            forecasts,
            team_id=team_id,
            week=week,
            as_of=AS_OF,
        )
        for team_id in ("a", "b")
        for week in (5, 6)
    )
    assert panel == independent
