from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.integrated_i1 import I1ForecastInput, I1ForecastResult, STATE_NAMES
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.i1_scoring_bridge import (
    FROZEN_I1_STANDARD_SCORING,
    LeagueScoringNormalizedI1Predictor,
    build_future_i1_position_scoring_multipliers,
    position_scoring_multipliers,
)
from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    Position,
    Provenance,
    RosterSlot,
    ScoringRule,
)
from fsffl.value.live_intrinsic_calendar import (
    CompletedSourceI1Coordinate,
    LiveCalendarShapleyResult,
    LiveIntrinsicCalendarResult,
    LiveThreeYearPlayerCoordinate,
    LiveYearOneCoordinate,
)
from fsffl.value.shapley_intrinsic import (
    IntrinsicShapleyEstimate,
    full_game_value,
    subset_caps_from_rules,
)
from fsffl.value.shapley_intrinsic_contract import build_shapley_intrinsic_contract


def _rules(*, half_ppr: bool = False) -> LeagueRules:
    scoring = list(FROZEN_I1_STANDARD_SCORING)
    if half_ppr:
        scoring.append(ScoringRule(stat="rec", points=0.5))
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


def _raw_rb_forecasts(player_id: str = "rb") -> tuple[ForecastObservation, ...]:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    metrics = (
        (ForecastMetric.RUSH_YARDS, 400.0),
        (ForecastMetric.RUSH_TD, 0.0),
        (ForecastMetric.RECEPTIONS, 80.0),
        (ForecastMetric.REC_YARDS, 1000.0),
        (ForecastMetric.REC_TD, 10.0),
    )
    return tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.RB,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=now,
            period_end=now + timedelta(days=100),
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="raw-fixture",
            model_version="raw-fixture-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric, mean in metrics
    )


def _fantasy_points(player_id: str, points: float) -> ForecastObservation:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    return ForecastObservation(
        player_id=player_id,
        position=Position.RB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=now,
        period_end=now + timedelta(days=100),
        distribution=ForecastDistribution(mean=points, stddev=10.0),
        source="fixture",
        model_version="fixture-v1",
        as_of=now,
        provenance=provenance,
    )


class _FakeI1:
    def predict(self, item, *, fallback_probabilities=None):
        probabilities = {state: 0.0 for state in STATE_NAMES}
        probabilities["out"] = 0.1
        probabilities["starter"] = 0.9
        means = {state: 0.0 for state in STATE_NAMES}
        means["starter"] = 100.0
        return I1ForecastResult(
            probabilities=probabilities,
            persistence_probability=0.9,
            anticipated_points=90.0,
            state_means=means,
            evidence_path="reduced",
            model_version="fake-i1",
        )


def test_superflex_deploys_stronger_non_qb_over_lower_scoring_qb() -> None:
    rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )
    players = [
        ("q1", "QB", 300.0),
        ("q2", "QB", 290.0),
        ("q3", "QB", 180.0),
        ("q4", "QB", 170.0),
        ("r1", "RB", 250.0),
        ("r2", "RB", 240.0),
    ]
    assert full_game_value(players, subset_caps_from_rules(rules)) == pytest.approx(1080.0)


def test_half_ppr_bridge_changes_future_points_but_not_i1_probabilities() -> None:
    raw = _raw_rb_forecasts()
    league_half = derive_league_fantasy_point_forecasts(raw, rules=_rules(half_ppr=True))
    multipliers = build_future_i1_position_scoring_multipliers(
        raw_forecasts=raw,
        league_year_one=league_half,
        rules=_rules(half_ppr=True),
    )
    assert multipliers[Position.RB] == pytest.approx(1.2)

    item = I1ForecastInput(
        position=Position.RB,
        age_band="prime",
        current_state="starter",
        horizon=2,
        current_points=200.0,
        prior_points=180.0,
        experience_years=3,
    )
    base = _FakeI1().predict(item)
    normalized = LeagueScoringNormalizedI1Predictor(
        _FakeI1(),
        multipliers=multipliers,
    ).predict(item)
    assert normalized.probabilities == base.probabilities
    assert normalized.persistence_probability == base.persistence_probability
    assert normalized.state_means["starter"] == pytest.approx(120.0)
    assert normalized.anticipated_points == pytest.approx(108.0)

    league_standard = derive_league_fantasy_point_forecasts(raw, rules=_rules())
    identity = build_future_i1_position_scoring_multipliers(
        raw_forecasts=raw,
        league_year_one=league_standard,
        rules=_rules(),
    )
    assert identity[Position.RB] == pytest.approx(1.0)


def test_scoring_bridge_fails_closed_when_required_player_cannot_be_normalized() -> None:
    with pytest.raises(ValueError, match="required players"):
        position_scoring_multipliers(
            standard_year_one=(_fantasy_points("p1", 200.0),),
            league_year_one=(
                _fantasy_points("p1", 220.0),
                _fantasy_points("p2", 180.0),
            ),
        )


def _i1_result(points: float) -> I1ForecastResult:
    probabilities = {state: 0.0 for state in STATE_NAMES}
    probabilities["starter"] = 1.0
    means = {state: 0.0 for state in STATE_NAMES}
    means["starter"] = points
    return I1ForecastResult(
        probabilities=probabilities,
        persistence_probability=1.0,
        anticipated_points=points,
        state_means=means,
        evidence_path="reduced",
    )


def test_contract_discloses_effective_seed_for_each_horizon() -> None:
    coordinate = LiveThreeYearPlayerCoordinate(
        player_id="p1",
        position=Position.WR,
        evaluation_season=2026,
        year_1=LiveYearOneCoordinate(
            target_season=2026,
            anticipated_points=150.0,
            stddev=10.0,
            source="fixture",
            model_version="fixture-v1",
        ),
        diagnostic_h1=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=1,
            target_season=2026,
            result=_i1_result(140.0),
            diagnostic_only=True,
        ),
        year_2=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=2,
            target_season=2027,
            result=_i1_result(130.0),
            diagnostic_only=False,
        ),
        year_3=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=3,
            target_season=2028,
            result=_i1_result(120.0),
            diagnostic_only=False,
        ),
    )
    calendar = LiveIntrinsicCalendarResult(
        forecasts=(coordinate,),
        evaluation_season=2026,
        completed_source_season=2025,
    )
    estimate = IntrinsicShapleyEstimate(
        player_id="p1",
        value=10.0 + 0.85 * 8.0 + (0.85**2) * 6.0,
        year_1_shapley=10.0,
        year_2_expected_shapley=8.0,
        year_3_expected_shapley=6.0,
    )
    result = LiveCalendarShapleyResult(
        calendar=calendar,
        estimates=(estimate,),
        seed=1234,
    )
    contract = build_shapley_intrinsic_contract(result)
    assert contract.seed == 1234
    assert contract.horizon_seeds == (1234, 1235, 1236)
