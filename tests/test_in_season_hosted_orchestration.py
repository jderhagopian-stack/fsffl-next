from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import fsffl.forecast.in_season_orchestration as orchestration
from fsffl.forecast.in_season_orchestration import (
    build_governed_in_season_outlook,
    canonical_week_window,
    realized_fantasy_points_from_weekly_stats,
    remaining_prior_from_preseason,
)
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperWeeklyStatsSource
from fsffl.state.models import (
    League,
    LeagueRules,
    LineupRequirement,
    NflTeamBye,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
    LeagueState,
)


NOW = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)


def _prov(source: str = "test") -> Provenance:
    return Provenance(source=source, retrieved_at=NOW, effective_at=NOW)


def _state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id="league-1",
            name="Test",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(LineupRequirement(slot=RosterSlot.RB, count=1),),
                scoring=(
                    ScoringRule(stat="rush_yd", points=0.1),
                    ScoringRule(stat="rush_td", points=6.0),
                    ScoringRule(stat="rec", points=0.5),
                    ScoringRule(stat="rec_yd", points=0.1),
                    ScoringRule(stat="rec_td", points=6.0),
                ),
            ),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id="league-1", display_name="A"),
            Team(team_id="b", league_id="league-1", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(Player(player_id="sleeper:player:1", full_name="Runner", position=Position.RB, nfl_team="NYG"),),
        player_states=(
            PlayerState(
                player_id="sleeper:player:1",
                as_of=NOW,
                nfl_team="NYG",
                provenance=_prov(),
            ),
        ),
        nfl_team_byes=(
            NflTeamBye(season=2026, nfl_team="NYG", week=14, provenance=_prov("schedule")),
        ),
    )


def _preseason_forecast() -> ForecastObservation:
    season_start = canonical_week_window(2026, 1)[0]
    season_end = canonical_week_window(2026, 18)[1]
    preseason_at = datetime(2026, 9, 1, tzinfo=UTC)
    return ForecastObservation(
        player_id="sleeper:player:1",
        position=Position.RB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=season_start,
        period_end=season_end,
        distribution=ForecastDistribution(mean=170.0, stddev=34.0, p10=120.0, p50=170.0, p90=220.0),
        source="fsffl:preseason",
        model_version="preseason-v1",
        as_of=preseason_at,
        provenance=Provenance(
            source="fsffl:preseason",
            retrieved_at=preseason_at,
            effective_at=preseason_at,
        ),
    )


def _stats_source_current_week_one() -> SleeperWeeklyStatsSource:
    def get(url: str):
        if url == SleeperWeeklyStatsSource.state_url:
            return {"season": "2026", "week": 1, "season_type": "regular"}
        raise AssertionError(f"no completed-week stats should be requested: {url}")

    return SleeperWeeklyStatsSource(http_get_json=get, clock=lambda: NOW)


def test_sleeper_actuals_are_raw_until_forecast_applies_league_scoring():
    state = _state()
    captured = NOW - timedelta(hours=1)
    line = SleeperWeeklyStatLine(
        player_id="sleeper:player:1",
        season=2026,
        week=1,
        stats={"rush_yd": 100.0, "rush_td": 1.0, "rec": 4.0, "rec_yd": 20.0},
        captured_at=captured,
        source_company="Sportradar",
    )
    actual = realized_fantasy_points_from_weekly_stats(
        state,
        lines=(line,),
        week=1,
        finalized_at=captured,
    )[0]
    assert actual.metric == ForecastMetric.FANTASY_POINTS
    assert actual.actual == pytest.approx(20.0)
    assert actual.provenance.source == "sleeper:weekly_nfl_stats"


def test_preseason_fallback_uses_only_remaining_schedule_share_not_actual_subtraction():
    remaining = remaining_prior_from_preseason(
        _state(),
        preseason_season_forecasts=(_preseason_forecast(),),
        completed_through_week=4,
        as_of=NOW,
    )[0]
    # Weeks 5-18 contain 14 weeks, but NYG's week-14 bye leaves 13 active games.
    assert remaining.horizon == ForecastHorizon.REST_OF_SEASON
    assert remaining.distribution.mean == pytest.approx(130.0)
    assert remaining.source == "fsffl:preseason_remaining_prior"


def test_preseason_fallback_fails_closed_without_valid_season_fantasy_points():
    with pytest.raises(ValueError, match="no valid preseason"):
        remaining_prior_from_preseason(
            _state(),
            preseason_season_forecasts=(),
            completed_through_week=4,
            as_of=NOW,
        )


def test_sleeper_state_marks_only_prior_weeks_completed():
    payloads = {
        SleeperWeeklyStatsSource.state_url: {
            "season": "2026",
            "week": 5,
            "season_type": "regular",
        }
    }
    source = SleeperWeeklyStatsSource(http_get_json=lambda url: payloads[url], clock=lambda: NOW)
    state = source.fetch_nfl_state()
    assert state.completed_through_week == 4


def test_governed_outlook_prefers_healthy_current_ros(monkeypatch):
    period_start = canonical_week_window(2026, 1)[0]
    period_end = canonical_week_window(2026, 18)[1]
    ros = _preseason_forecast().model_copy(
        update={
            "horizon": ForecastHorizon.REST_OF_SEASON,
            "period_start": period_start,
            "period_end": period_end,
            "distribution": ForecastDistribution(mean=200.0, stddev=0.0),
            "source": "fsffl:current_ros",
            "as_of": NOW,
            "provenance": _prov("current_ros"),
        }
    )
    monkeypatch.setattr(
        orchestration,
        "build_in_season_forecasts",
        lambda *args, **kwargs: SimpleNamespace(fantasy_point_forecasts=(ros,)),
    )
    result = build_governed_in_season_outlook(
        _state(),
        preseason_season_forecasts=(_preseason_forecast(),),
        stats_source=_stats_source_current_week_one(),
        clock=lambda: NOW,
    )
    assert result.evidence_basis == "current_rest_of_season"
    assert result.current_failure is None
    assert result.season_outlook[0].distribution.mean == pytest.approx(200.0)


def test_governed_outlook_uses_preserved_prior_when_current_ros_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("wrong horizon or provider unavailable")

    monkeypatch.setattr(orchestration, "build_in_season_forecasts", fail)
    result = build_governed_in_season_outlook(
        _state(),
        preseason_season_forecasts=(_preseason_forecast(),),
        stats_source=_stats_source_current_week_one(),
        clock=lambda: NOW,
    )
    assert result.evidence_basis == "preseason_remaining_prior"
    assert "wrong horizon" in result.current_failure
    assert result.season_outlook[0].distribution.mean == pytest.approx(170.0)


def test_governed_outlook_fails_closed_when_current_and_baseline_are_unavailable(monkeypatch):
    monkeypatch.setattr(
        orchestration,
        "build_in_season_forecasts",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("provider unavailable")),
    )
    with pytest.raises(ValueError, match="no valid preseason"):
        build_governed_in_season_outlook(
            _state(),
            preseason_season_forecasts=(),
            stats_source=_stats_source_current_week_one(),
            clock=lambda: NOW,
        )
