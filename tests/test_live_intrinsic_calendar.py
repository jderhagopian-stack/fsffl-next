from datetime import UTC, datetime

from fsffl.forecast.i1_current_facts import CurrentI1MappingResult
from fsffl.forecast.integrated_i1 import I1ForecastInput, I1ForecastResult, STATE_NAMES
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import LeagueRules, LineupRequirement, Position, Provenance, RosterSlot
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar,
)
from fsffl.value.shapley_intrinsic import FROZEN_INTRINSIC_DISCOUNT


def _input(horizon: int) -> I1ForecastInput:
    return I1ForecastInput(
        position=Position.WR,
        age_band="young",
        current_state="usable",
        horizon=horizon,
        current_points=100.0,
        prior_points=75.0,
        experience_years=2,
        evidence=None,
    )


def _mapping() -> CurrentI1MappingResult:
    return CurrentI1MappingResult(
        inputs={"p1": (_input(1), _input(2), _input(3))},
        mapped_source_ids={"p1": "source-p1"},
        unmapped_player_ids=(),
        ambiguous_player_ids=(),
        source_rows_unmatched=(),
        evaluation_season=2026,
        completed_source_season=2025,
    )


def _live_forecast() -> ForecastObservation:
    as_of = datetime(2026, 9, 16, tzinfo=UTC)
    return ForecastObservation(
        player_id="p1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=155.0, stddev=28.0, p10=120.0, p50=155.0, p90=190.0),
        source="fsffl:live_league_scored",
        model_version="fixture-live-v1",
        as_of=as_of,
        provenance=Provenance(
            source="fixture",
            retrieved_at=as_of,
            effective_at=as_of,
            source_version="fixture-v1",
        ),
    )


def _result(horizon: int) -> I1ForecastResult:
    probabilities = {
        "out": 0.05,
        "depth": 0.10,
        "usable": 0.20,
        "starter": 0.35,
        "premium": 0.20,
        "elite": 0.10,
    }
    means = {state: float(index * 40) for index, state in enumerate(STATE_NAMES)}
    # Make h=1 intentionally enormous. If it leaks into the live vector the
    # assertions below fail immediately.
    anticipated = 999.0 if horizon == 1 else (140.0 if horizon == 2 else 120.0)
    return I1ForecastResult(
        probabilities=probabilities,
        persistence_probability=0.95,
        anticipated_points=anticipated,
        state_means=means,
        evidence_path="reduced",
        model_version=f"fixture-h{horizon}",
    )


class _NearPredictor:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def predict(self, item, *, fallback_probabilities=None):
        self.calls.append(item.horizon)
        if item.horizon not in (1, 2):
            raise AssertionError("near predictor must not own h=3")
        return _result(item.horizon)


class _H3Predictor:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def predict(self, item, *, fallback_probabilities=None):
        self.calls.append(item.horizon)
        if item.horizon != 3:
            raise AssertionError("direct h3 predictor owns only h=3")
        return _result(3)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )


def test_calendar_ownership_and_direct_nonrecursive_h3() -> None:
    near = _NearPredictor()
    h3 = _H3Predictor()
    calendar = compose_live_intrinsic_calendar(
        live_year_one_forecasts=(_live_forecast(),),
        mapping=_mapping(),
        h1_h2_predictor=near,
        h3_predictor=h3,
    )

    assert near.calls == [1, 2]
    assert h3.calls == [3]
    assert calendar.evaluation_season == 2026
    assert calendar.completed_source_season == 2025
    assert calendar.player_count == 1

    player = calendar.forecasts[0]
    assert player.year_1.target_season == 2026
    assert player.year_1.anticipated_points == 155.0
    assert player.diagnostic_h1.target_season == 2026
    assert player.diagnostic_h1.horizon == 1
    assert player.diagnostic_h1.diagnostic_only is True
    assert player.year_2.target_season == 2027 and player.year_2.horizon == 2
    assert player.year_3.target_season == 2028 and player.year_3.horizon == 3
    assert player.year_3.source_season == player.year_2.source_season == 2025
    assert player.year_3.regularization_c == 0.25


def test_completed_source_h1_is_hard_excluded_from_live_shapley_vector() -> None:
    calendar = compose_live_intrinsic_calendar(
        live_year_one_forecasts=(_live_forecast(),),
        mapping=_mapping(),
        h1_h2_predictor=_NearPredictor(),
        h3_predictor=_H3Predictor(),
    )
    player = calendar.forecasts[0]
    shapley_input = player.as_shapley_forecast()

    assert player.diagnostic_h1.result.anticipated_points == 999.0
    assert shapley_input.current_points == 155.0
    assert shapley_input.year_2.anticipated_points == 140.0
    assert shapley_input.year_3.anticipated_points == 120.0


def test_post_composition_shapley_discount_reconciliation_is_exact() -> None:
    calendar = compose_live_intrinsic_calendar(
        live_year_one_forecasts=(_live_forecast(),),
        mapping=_mapping(),
        h1_h2_predictor=_NearPredictor(),
        h3_predictor=_H3Predictor(),
    )
    result = build_live_calendar_shapley_estimates(calendar, rules=_rules(), permutations=256, seed=20260915)
    assert len(result.estimates) == 1
    estimate = result.estimates[0]
    expected = (
        estimate.year_1_shapley
        + FROZEN_INTRINSIC_DISCOUNT * estimate.year_2_expected_shapley
        + (FROZEN_INTRINSIC_DISCOUNT ** 2) * estimate.year_3_expected_shapley
    )
    assert abs(estimate.value - expected) <= 1e-12
