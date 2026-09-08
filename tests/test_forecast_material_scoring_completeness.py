from datetime import UTC, datetime

import pytest

from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueRules, LineupRequirement, Position, Provenance, RosterSlot, ScoringRule


AS_OF = datetime(2026, 9, 7, tzinfo=UTC)
END = datetime(2027, 1, 10, tzinfo=UTC)
PROVENANCE = Provenance(source="provider", retrieved_at=AS_OF, effective_at=AS_OF)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
        ),
    )


def _obs(position: Position, metric: ForecastMetric, mean: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=f"player:{position.value.lower()}",
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=AS_OF,
        period_end=END,
        distribution=ForecastDistribution(mean=mean, stddev=max(abs(mean) * 0.1, 1.0)),
        source="ensemble",
        model_version="ensemble-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def test_qb_missing_touchdowns_cannot_be_published_as_full_season_points() -> None:
    # This reproduces the failure shape that produced ~200-point elite QB totals:
    # yardage and interceptions survive, but the scored TD components are absent.
    observations = (
        _obs(Position.QB, ForecastMetric.PASS_YARDS, 4000.0),
        _obs(Position.QB, ForecastMetric.INTERCEPTIONS, 10.0),
        _obs(Position.QB, ForecastMetric.RUSH_YARDS, 650.0),
    )
    assert derive_league_fantasy_point_forecasts(observations, rules=_rules()) == ()


def test_rb_missing_touchdowns_cannot_be_published_as_full_season_points() -> None:
    observations = (
        _obs(Position.RB, ForecastMetric.RUSH_YARDS, 1200.0),
        _obs(Position.RB, ForecastMetric.RECEPTIONS, 60.0),
        _obs(Position.RB, ForecastMetric.REC_YARDS, 500.0),
    )
    assert derive_league_fantasy_point_forecasts(observations, rules=_rules()) == ()


def test_complete_qb_material_scoring_basis_still_scores_full_season() -> None:
    observations = (
        _obs(Position.QB, ForecastMetric.PASS_YARDS, 3935.0),
        _obs(Position.QB, ForecastMetric.PASS_TD, 27.2),
        _obs(Position.QB, ForecastMetric.INTERCEPTIONS, 12.3),
        _obs(Position.QB, ForecastMetric.RUSH_YARDS, 658.6),
        _obs(Position.QB, ForecastMetric.RUSH_TD, 13.1),
    )
    result = derive_league_fantasy_point_forecasts(observations, rules=_rules())
    assert len(result) == 1
    assert result[0].horizon == ForecastHorizon.SEASON
    assert result[0].distribution.mean == pytest.approx(386.06)
    assert result[0].distribution.mean > 300.0


def test_complete_half_ppr_rb_material_scoring_basis_scores_normally() -> None:
    observations = (
        _obs(Position.RB, ForecastMetric.RUSH_YARDS, 1200.0),
        _obs(Position.RB, ForecastMetric.RUSH_TD, 12.0),
        _obs(Position.RB, ForecastMetric.RECEPTIONS, 60.0),
        _obs(Position.RB, ForecastMetric.REC_YARDS, 500.0),
        _obs(Position.RB, ForecastMetric.REC_TD, 5.0),
    )
    result = derive_league_fantasy_point_forecasts(observations, rules=_rules())
    assert len(result) == 1
    assert result[0].distribution.mean == pytest.approx(302.0)
