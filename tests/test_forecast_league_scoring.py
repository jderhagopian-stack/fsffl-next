from datetime import UTC, datetime

import pytest

from fsffl.forecast.league_scoring import (
    ScoringCoverageStatus,
    classify_scoring_coverage,
    derive_league_fantasy_point_forecasts,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    Position,
    Provenance,
    RosterSlot,
    ScoringRule,
)


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
END = datetime(2027, 1, 10, tzinfo=UTC)
PROVENANCE = Provenance(source="provider", retrieved_at=AS_OF, effective_at=AS_OF)


def _rules(*scoring: ScoringRule) -> LeagueRules:
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
        scoring=tuple(scoring),
    )


def _observation(metric: ForecastMetric, mean: float, stddev: float = 1.0) -> ForecastObservation:
    return ForecastObservation(
        player_id="p1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=AS_OF,
        period_end=END,
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="provider-a",
        model_version="provider-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def test_half_ppr_linear_rules_are_exactly_supported() -> None:
    rules = _rules(
        ScoringRule(stat="rec", points=0.5),
        ScoringRule(stat="rec_yd", points=0.1),
        ScoringRule(stat="rec_td", points=6.0),
    )
    coverage = classify_scoring_coverage(rules)
    assert coverage.status == ScoringCoverageStatus.COMPLETE
    result = derive_league_fantasy_point_forecasts(
        (
            _observation(ForecastMetric.RECEPTIONS, 80.0, 8.0),
            _observation(ForecastMetric.REC_YARDS, 1000.0, 100.0),
            _observation(ForecastMetric.REC_TD, 8.0, 2.0),
        ),
        rules=rules,
    )
    assert len(result) == 1
    assert result[0].metric == ForecastMetric.FANTASY_POINTS
    assert result[0].distribution.mean == pytest.approx(188.0)
    assert result[0].distribution.stddev > 0
    assert "independent_metric_variance" in result[0].model_version


def test_custom_league_coefficients_come_from_rules_not_provider_defaults() -> None:
    rules = _rules(
        ScoringRule(stat="pass_yd", points=0.05),
        ScoringRule(stat="pass_td", points=5.0),
        ScoringRule(stat="pass_int", points=-3.0),
    )
    result = derive_league_fantasy_point_forecasts(
        (
            _observation(ForecastMetric.PASS_YARDS, 4000.0),
            _observation(ForecastMetric.PASS_TD, 30.0),
            _observation(ForecastMetric.INTERCEPTIONS, 10.0),
        ),
        rules=rules,
    )
    assert result[0].distribution.mean == pytest.approx(320.0)


def test_unsupported_offensive_rule_fails_closed() -> None:
    rules = _rules(
        ScoringRule(stat="rec", points=0.5),
        ScoringRule(stat="fum_lost", points=-2.0),
    )
    coverage = classify_scoring_coverage(rules)
    assert coverage.status == ScoringCoverageStatus.INCOMPLETE
    assert coverage.unsupported_rule_stats == ("fum_lost",)
    with pytest.raises(ValueError, match="fum_lost"):
        derive_league_fantasy_point_forecasts(
            (_observation(ForecastMetric.RECEPTIONS, 80.0),),
            rules=rules,
        )


def test_dst_and_kicker_rules_can_be_ignored_only_when_positions_are_absent() -> None:
    rules = _rules(
        ScoringRule(stat="sack", points=1.0),
        ScoringRule(stat="pts_allow_0", points=10.0),
        ScoringRule(stat="fgm_50p", points=5.0),
        ScoringRule(stat="rec", points=0.5),
    )
    coverage = classify_scoring_coverage(rules)
    assert coverage.status == ScoringCoverageStatus.COMPLETE
    assert set(coverage.ignored_non_lineup_rule_stats) == {"fgm_50p", "pts_allow_0", "sack"}


def test_return_and_fumble_recovery_scoring_is_not_silently_ignored() -> None:
    rules = _rules(
        ScoringRule(stat="st_td", points=6.0),
        ScoringRule(stat="fum_rec_td", points=6.0),
    )
    coverage = classify_scoring_coverage(rules)
    assert coverage.status == ScoringCoverageStatus.INCOMPLETE
    assert set(coverage.unsupported_rule_stats) == {"fum_rec_td", "st_td"}
