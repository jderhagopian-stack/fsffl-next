from datetime import UTC, datetime

import pytest

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.forecast.regular_season import derive_fantasy_regular_season_forecasts, fantasy_regular_season_weeks
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    NflTeamBye,
    Player,
    PlayerState,
    Position,
    Provenance,
    Team,
    TeamState,
)

NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def _state(*, bye_week: int | None = 8, weeks: tuple[int, ...] = tuple(range(1, 15))) -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=NOW, effective_at=NOW)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
    )
    teams = (
        Team(team_id="a", league_id="l1", display_name="A"),
        Team(team_id="b", league_id="l1", display_name="B"),
    )
    matchups = tuple(
        LeagueMatchup(
            week=week,
            team_a_id="a",
            team_b_id="b",
            provenance=provenance,
        )
        for week in weeks
    )
    byes = () if bye_week is None else (
        NflTeamBye(
            season=2026,
            nfl_team="BAL",
            week=bye_week,
            provenance=provenance,
        ),
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=teams,
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(Player(player_id="p1", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL"),),
        player_states=(PlayerState(player_id="p1", as_of=NOW, nfl_team="BAL", provenance=provenance),),
        matchups=matchups,
        nfl_team_byes=byes,
    )


def _season_forecast(mean: float = 340.0) -> ForecastObservation:
    provenance = Provenance(source="provider", retrieved_at=NOW, effective_at=NOW)
    return ForecastObservation(
        player_id="p1",
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 3, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=85.0, p10=220.0, p50=340.0, p90=460.0),
        source="provider",
        model_version="provider-v1",
        as_of=NOW,
        provenance=provenance,
    )


def test_fantasy_regular_season_projection_counts_only_active_league_weeks() -> None:
    state = _state(bye_week=8)
    result = derive_fantasy_regular_season_forecasts(state, (_season_forecast(),))

    assert len(result) == 1
    forecast = result[0]
    assert forecast.horizon == ForecastHorizon.FANTASY_REGULAR_SEASON
    assert forecast.distribution.mean == pytest.approx(340.0 * 13 / 17)
    assert forecast.distribution.stddev == pytest.approx(85.0 * 13 / 17)
    assert forecast.distribution.p50 == pytest.approx(340.0 * 13 / 17)
    assert "weeks_1_14" in forecast.model_version


def test_bye_after_fantasy_regular_season_preserves_all_fourteen_active_games() -> None:
    state = _state(bye_week=15)
    result = derive_fantasy_regular_season_forecasts(state, (_season_forecast(),))
    assert result[0].distribution.mean == pytest.approx(340.0 * 14 / 17)


def test_missing_bye_uses_structural_nfl_schedule_expectation() -> None:
    state = _state(bye_week=None)
    result = derive_fantasy_regular_season_forecasts(state, (_season_forecast(),))
    assert result[0].distribution.mean == pytest.approx(340.0 * 14 / 18)


def test_fantasy_regular_season_schedule_must_be_contiguous() -> None:
    state = _state(weeks=(1, 2, 4))
    with pytest.raises(ValueError, match="contiguous"):
        fantasy_regular_season_weeks(state)
