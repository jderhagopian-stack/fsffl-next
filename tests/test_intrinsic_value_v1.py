from datetime import UTC, datetime

import pytest

from fsffl.forecast.career import MultiYearForecastPoint
from fsffl.forecast.intrinsic_v1 import (
    ForecastEvidenceStrength,
    IntrinsicV1ForecastMethod,
    intrinsic_v1_method,
    materialize_intrinsic_v1_forecast_path,
)
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.intrinsic_v1 import (
    INTRINSIC_VALUE_V1_WEIGHTS,
    IntrinsicV1Confidence,
    estimate_intrinsic_value_v1,
)


AS_OF = datetime(2026, 9, 13, tzinfo=UTC)


def _bounded(y2: float, y3: float) -> tuple[MultiYearForecastPoint, ...]:
    return (
        MultiYearForecastPoint(
            season_offset=1,
            distribution=ForecastDistribution(mean=y2, stddev=20.0),
            cumulative_survival_probability=0.9,
            cumulative_conditional_production_multiplier=0.95,
            transition_model_version="career-test-v1",
        ),
        MultiYearForecastPoint(
            season_offset=2,
            distribution=ForecastDistribution(mean=y3, stddev=30.0),
            cumulative_survival_probability=0.8,
            cumulative_conditional_production_multiplier=0.85,
            transition_model_version="career-test-v1",
        ),
    )


def _path(player_id: str, position: Position, mean: float, bounded=True):
    return materialize_intrinsic_v1_forecast_path(
        player_id=player_id,
        position=position,
        evaluation_as_of=AS_OF,
        base_distribution=ForecastDistribution(mean=mean, stddev=10.0),
        base_forecast_model_version="forecast-test-v1",
        bounded_path=_bounded(mean * 0.9, mean * 0.8) if bounded else None,
    )


def _rules(superflex: bool = True) -> LeagueRules:
    lineup = [
        LineupRequirement(slot=RosterSlot.QB, count=1),
        LineupRequirement(slot=RosterSlot.RB, count=1),
        LineupRequirement(slot=RosterSlot.WR, count=1),
        LineupRequirement(slot=RosterSlot.TE, count=1),
        LineupRequirement(slot=RosterSlot.FLEX, count=0),
    ]
    if superflex:
        lineup.append(LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1))
    return LeagueRules(
        team_count=2,
        roster_size=8,
        lineup=tuple(lineup),
        scoring=(),
    )


def test_frozen_position_horizon_policy():
    assert intrinsic_v1_method(Position.QB, 2) == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert intrinsic_v1_method(Position.QB, 3) == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert intrinsic_v1_method(Position.RB, 2) == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION
    assert intrinsic_v1_method(Position.RB, 3) == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION
    assert intrinsic_v1_method(Position.WR, 2) == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert intrinsic_v1_method(Position.WR, 3) == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION
    assert intrinsic_v1_method(Position.TE, 2) == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION
    assert intrinsic_v1_method(Position.TE, 3) == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION


def test_qb_uses_carry_forward_even_when_bounded_path_exists():
    path = _path("qb1", Position.QB, 300.0)
    assert [point.distribution.mean for point in path.horizons] == [300.0, 300.0, 300.0]
    assert path.horizons[1].method == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert path.horizons[2].evidence_strength == ForecastEvidenceStrength.LOW
    assert path.horizons[1].distribution.stddev == 20.0
    assert path.horizons[2].distribution.stddev == 30.0


def test_wr_selects_carry_y2_and_bounded_y3():
    path = _path("wr1", Position.WR, 200.0)
    assert path.horizons[1].distribution.mean == 200.0
    assert path.horizons[2].distribution.mean == 160.0
    assert path.horizons[1].method == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert path.horizons[2].method == IntrinsicV1ForecastMethod.BOUNDED_CAREER_TRANSITION


def test_missing_bounded_evidence_falls_back_without_fake_precision():
    path = _path("rb1", Position.RB, 180.0, bounded=False)
    assert path.horizons[1].distribution.mean == 180.0
    assert path.horizons[2].distribution.mean == 180.0
    assert path.horizons[1].method == IntrinsicV1ForecastMethod.CONSERVATIVE_CARRY_FORWARD
    assert path.horizons[1].evidence_strength == ForecastEvidenceStrength.LOW
    assert path.horizons[1].cumulative_survival_probability is None


def test_model_a_is_weighted_replacement_adjusted_surplus_and_low_confidence_for_qb():
    paths = {
        "qb1": _path("qb1", Position.QB, 300.0),
        "qb2": _path("qb2", Position.QB, 250.0),
        "qb3": _path("qb3", Position.QB, 200.0),
        "rb1": _path("rb1", Position.RB, 200.0),
        "rb2": _path("rb2", Position.RB, 150.0),
        "wr1": _path("wr1", Position.WR, 220.0),
        "wr2": _path("wr2", Position.WR, 140.0),
        "te1": _path("te1", Position.TE, 160.0),
        "te2": _path("te2", Position.TE, 100.0),
    }
    estimate = estimate_intrinsic_value_v1(
        player_path=paths["qb1"],
        all_player_paths=paths,
        league_id="league",
        rules=_rules(superflex=True),
    )
    assert estimate.value >= 0
    assert estimate.confidence == IntrinsicV1Confidence.LOW
    assert tuple(point.weight for point in estimate.horizons) == INTRINSIC_VALUE_V1_WEIGHTS
    assert estimate.value == pytest.approx(sum(point.weighted_surplus for point in estimate.horizons))


def test_superflex_structurally_lowers_qb_replacement_and_raises_qb_intrinsic_value():
    paths = {
        "qb1": _path("qb1", Position.QB, 300.0),
        "qb2": _path("qb2", Position.QB, 250.0),
        "qb3": _path("qb3", Position.QB, 200.0),
        "qb4": _path("qb4", Position.QB, 150.0),
        "rb1": _path("rb1", Position.RB, 200.0),
        "rb2": _path("rb2", Position.RB, 150.0),
        "wr1": _path("wr1", Position.WR, 220.0),
        "wr2": _path("wr2", Position.WR, 140.0),
        "te1": _path("te1", Position.TE, 160.0),
        "te2": _path("te2", Position.TE, 100.0),
    }
    one_qb = estimate_intrinsic_value_v1(
        player_path=paths["qb1"],
        all_player_paths=paths,
        league_id="league",
        rules=_rules(superflex=False),
    )
    superflex = estimate_intrinsic_value_v1(
        player_path=paths["qb1"],
        all_player_paths=paths,
        league_id="league",
        rules=_rules(superflex=True),
    )
    assert superflex.value < one_qb.value
