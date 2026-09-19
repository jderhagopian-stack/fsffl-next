from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.in_season_runtime import (
    NamedInSeasonProjectionFetcher,
    build_in_season_forecasts,
    default_in_season_projection_fetchers,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.season_rollforward import compose_completed_actuals_with_ros
from fsffl.forecast.backtest import RealizedOutcome
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 11, 20, 0, tzinfo=UTC)
PERIOD_START = datetime(2026, 9, 15, tzinfo=UTC)
PERIOD_END = datetime(2027, 1, 5, tzinfo=UTC)


def _provenance(at: datetime = NOW) -> Provenance:
    return Provenance(source="test", retrieved_at=at, effective_at=at)


def _state() -> LeagueState:
    player = Player(player_id="p1", full_name="Test Runner", position=Position.RB, nfl_team="NYG")
    teams = (
        Team(team_id="a", league_id="league-1", display_name="A"),
        Team(team_id="b", league_id="league-1", display_name="B"),
    )
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
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.RB),)),
            TeamState(team_id="b", roster=()),
        ),
        players=(player,),
        player_states=(
            PlayerState(
                player_id="p1",
                as_of=NOW,
                nfl_team="NYG",
                provenance=_provenance(),
            ),
        ),
    )


def _snapshot(provider: str, *, rush_yards: float) -> CurrentProjectionSnapshot:
    at = NOW - timedelta(hours=1)
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=at,
        effective_at=at,
        source_version=f"{provider}-ros-v1",
        usage_class="test",
        rows=(
            CurrentProjectionRow(
                provider=provider,
                external_id=f"{provider}:p1",
                player_name="Test Runner",
                position=Position.RB,
                nfl_team="NYG",
                stats={
                    "rush_yd": rush_yards,
                    "rush_td": 6.0,
                    "rec": 40.0,
                    "rec_yd": 350.0,
                    "rec_td": 3.0,
                },
            ),
        ),
    )


class _Writer:
    def __init__(self) -> None:
        self.revisions = []

    def save_revision(self, revision):
        self.revisions.append(revision)
        return len(self.revisions)


def test_default_ros_sources_are_two_independent_public_horizons():
    fetchers = default_in_season_projection_fetchers(horizon=ForecastHorizon.REST_OF_SEASON)
    assert {item.source_id for item in fetchers} == {"cbs", "razzball"}


def test_default_week_sources_are_two_independent_public_horizons():
    fetchers = default_in_season_projection_fetchers(horizon=ForecastHorizon.WEEK)
    assert {item.source_id for item in fetchers} == {"cbs", "fftoday"}


def test_in_season_runtime_requires_two_sources_and_preserves_ros_horizon():
    source = NamedInSeasonProjectionFetcher(
        source_id="one",
        fetch=lambda season, week: _snapshot("one", rush_yards=700.0),
    )
    with pytest.raises(ValueError, match="at least 2 independent sources"):
        build_in_season_forecasts(
            _state(),
            horizon=ForecastHorizon.REST_OF_SEASON,
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            fetchers=(source,),
            clock=lambda: NOW,
        )


def test_ros_runtime_ensembles_scores_and_persists_source_evidence_without_simulation_authority():
    fetchers = (
        NamedInSeasonProjectionFetcher(
            source_id="one",
            fetch=lambda season, week: _snapshot("one", rush_yards=700.0),
        ),
        NamedInSeasonProjectionFetcher(
            source_id="two",
            fetch=lambda season, week: _snapshot("two", rush_yards=900.0),
        ),
    )
    writer = _Writer()
    result = build_in_season_forecasts(
        _state(),
        horizon=ForecastHorizon.REST_OF_SEASON,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        fetchers=fetchers,
        clock=lambda: NOW,
        history_writer=writer,
    )

    assert result.horizon == ForecastHorizon.REST_OF_SEASON
    assert result.successful_source_ids == ("one", "two")
    assert result.simulation_ready is False
    assert result.uncertainty_authority == "not_promoted_for_in_season_simulation"
    assert len(writer.revisions) == 2
    assert {revision.snapshot.horizon for revision in writer.revisions} == {
        ForecastHorizon.REST_OF_SEASON
    }
    rush = next(item for item in result.raw_ensemble if item.metric == ForecastMetric.RUSH_YARDS)
    assert rush.distribution.mean == pytest.approx(800.0)
    assert rush.horizon == ForecastHorizon.REST_OF_SEASON
    assert result.fantasy_point_forecasts
    assert all(item.horizon == ForecastHorizon.REST_OF_SEASON for item in result.fantasy_point_forecasts)


def test_week_runtime_requires_week_and_never_relabels_as_ros():
    with pytest.raises(ValueError, match="requires week"):
        build_in_season_forecasts(
            _state(),
            horizon=ForecastHorizon.WEEK,
            period_start=PERIOD_START,
            period_end=PERIOD_START + timedelta(days=7),
            fetchers=(),
            clock=lambda: NOW,
        )


def _forecast(
    *,
    horizon: ForecastHorizon = ForecastHorizon.REST_OF_SEASON,
    period_start: datetime = datetime(2026, 9, 9, tzinfo=UTC),
    mean: float = 800.0,
) -> ForecastObservation:
    as_of = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)
    return ForecastObservation(
        player_id="p1",
        position=Position.RB,
        horizon=horizon,
        metric=ForecastMetric.RUSH_YARDS,
        period_start=period_start,
        period_end=datetime(2027, 1, 5, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=100.0, p10=650.0, p50=800.0, p90=950.0),
        source="fsffl:ros",
        model_version="ros-v1",
        as_of=as_of,
        provenance=Provenance(
            source="fsffl:ros",
            retrieved_at=as_of,
            effective_at=as_of,
        ),
    )


def _actual(
    *,
    start: datetime,
    end: datetime,
    value: float = 85.0,
    finalized: datetime | None = None,
) -> RealizedOutcome:
    final = finalized or end
    return RealizedOutcome(
        player_id="p1",
        position=Position.RB,
        metric=ForecastMetric.RUSH_YARDS,
        period_start=start,
        period_end=end,
        actual=value,
        finalized_at=final,
        provenance=Provenance(source="actual", retrieved_at=final, effective_at=final),
    )


def test_season_roll_forward_adds_completed_actual_and_shifts_distribution_without_extra_variance():
    ros = _forecast()
    actual_start = datetime(2026, 9, 1, tzinfo=UTC)
    actual_end = datetime(2026, 9, 8, tzinfo=UTC)
    result = compose_completed_actuals_with_ros(
        completed_actuals=(_actual(start=actual_start, end=actual_end),),
        ros_forecasts=(ros,),
        season_start=datetime(2026, 9, 1, tzinfo=UTC),
    )
    season = result[0]
    assert season.horizon == ForecastHorizon.SEASON
    assert season.distribution.mean == pytest.approx(885.0)
    assert season.distribution.stddev == pytest.approx(100.0)
    assert season.distribution.p10 == pytest.approx(735.0)
    assert season.period_start == datetime(2026, 9, 1, tzinfo=UTC)
    assert season.source == "fsffl:completed-actuals-plus-ros"


def test_week4_acceptance_gate_counts_weeks_1_to_4_once_then_ros_only():
    season_start = datetime(2026, 9, 1, tzinfo=UTC)
    week5_start = datetime(2026, 10, 6, tzinfo=UTC)
    actuals = (
        _actual(start=datetime(2026, 9, 1, tzinfo=UTC), end=datetime(2026, 9, 8, tzinfo=UTC), value=10.0),
        _actual(start=datetime(2026, 9, 8, tzinfo=UTC), end=datetime(2026, 9, 15, tzinfo=UTC), value=20.0),
        _actual(start=datetime(2026, 9, 15, tzinfo=UTC), end=datetime(2026, 9, 22, tzinfo=UTC), value=30.0),
        _actual(start=datetime(2026, 9, 22, tzinfo=UTC), end=datetime(2026, 10, 6, tzinfo=UTC), value=40.0),
    )
    ros = _forecast(period_start=week5_start, mean=800.0)

    season = compose_completed_actuals_with_ros(
        completed_actuals=actuals,
        ros_forecasts=(ros,),
        season_start=season_start,
    )[0]

    assert season.distribution.mean == pytest.approx(900.0)
    assert season.distribution.stddev == pytest.approx(100.0)


def test_season_roll_forward_rejects_overlap_future_leak_and_weekly_evidence():
    ros = _forecast()
    with pytest.raises(ValueError, match="overlaps ROS"):
        compose_completed_actuals_with_ros(
            completed_actuals=(
                _actual(
                    start=datetime(2026, 9, 1, tzinfo=UTC),
                    end=datetime(2026, 9, 10, tzinfo=UTC),
                ),
            ),
            ros_forecasts=(ros,),
            season_start=datetime(2026, 9, 1, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="finalized after"):
        compose_completed_actuals_with_ros(
            completed_actuals=(
                _actual(
                    start=datetime(2026, 9, 1, tzinfo=UTC),
                    end=datetime(2026, 9, 8, tzinfo=UTC),
                    finalized=datetime(2026, 10, 8, tzinfo=UTC),
                ),
            ),
            ros_forecasts=(ros,),
            season_start=datetime(2026, 9, 1, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="REST_OF_SEASON"):
        compose_completed_actuals_with_ros(
            completed_actuals=(),
            ros_forecasts=(_forecast(horizon=ForecastHorizon.WEEK),),
            season_start=datetime(2026, 9, 1, tzinfo=UTC),
        )


def test_season_roll_forward_rejects_overlapping_or_duplicate_actual_periods():
    ros = _forecast(period_start=datetime(2026, 10, 6, tzinfo=UTC))
    overlapping = (
        _actual(
            start=datetime(2026, 9, 1, tzinfo=UTC),
            end=datetime(2026, 9, 15, tzinfo=UTC),
            value=30.0,
        ),
        _actual(
            start=datetime(2026, 9, 8, tzinfo=UTC),
            end=datetime(2026, 9, 15, tzinfo=UTC),
            value=20.0,
        ),
    )
    with pytest.raises(ValueError, match="actual periods overlap"):
        compose_completed_actuals_with_ros(
            completed_actuals=overlapping,
            ros_forecasts=(ros,),
            season_start=datetime(2026, 9, 1, tzinfo=UTC),
        )
