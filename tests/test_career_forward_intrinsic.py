from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import Provenance

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar_from_future_results,
)
from fsffl.value.shapley_intrinsic_contract import build_shapley_intrinsic_contract
from fsffl.value.career_forward_intrinsic import (
    CAREER_FORWARD_AGGREGATION,
    build_career_forward_intrinsic_shadow,
    build_career_forward_from_canonical_p0,
)
from fsffl.value.career_tail import (
    CAREER_TAIL_SCORING_COORDINATE,
    CareerTailFeatures,
    build_career_tail_authority,
)
from fsffl.value.long_term_intrinsic import (
    LongTermAnnualAuthority,
    LongTermIntrinsicPlayerEstimate,
    LongTermIntrinsicShadowContract,
    LongTermModelAuthority,
    LongTermPolicyContribution,
    LongTermWithinModelUncertainty,
)
from fsffl.value.shapley_intrinsic import FROZEN_SHAPLEY_PERMUTATIONS, FROZEN_SHAPLEY_SEED
from fsffl.value.shapley_intrinsic_contract import (
    DiagnosticH1Evidence,
    ShapleyHorizonProvenance,
    ShapleyHorizonUncertainty,
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
    ShapleyIntrinsicCoverage,
    ShapleyIntrinsicHorizonContribution,
    ShapleyIntrinsicPlayerEstimate,
)


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
        scoring=(),
    )


def _prov(authority: str) -> ShapleyHorizonProvenance:
    return ShapleyHorizonProvenance(
        authority=authority,
        source="fixture",
        model_version="fixture-v1",
        included_in_intrinsic=True,
    )


def _current() -> ShapleyIntrinsicContract:
    raw = (10.0, 20.0, 30.0)
    contributions = tuple(
        ShapleyIntrinsicHorizonContribution(
            year_index=year,
            target_season=2025 + year,
            raw_shapley_contribution=value,
            discount_factor=(1.0, 0.85, 0.85**2)[year - 1],
            discounted_contribution=value * (1.0, 0.85, 0.85**2)[year - 1],
            provenance=_prov(f"y{year}"),
            uncertainty=ShapleyHorizonUncertainty(
                forecast_stddev=5.0 if year == 1 else None,
                state_entropy=0.3 if year > 1 else None,
                evidence_path=f"y{year}-fixture",
            ),
        )
        for year, value in enumerate(raw, start=1)
    )
    typed = (contributions[0], contributions[1], contributions[2])
    discounted = sum(row.discounted_contribution for row in typed)
    return ShapleyIntrinsicContract(
        status=ShapleyIntrinsicAvailability.READY,
        evaluation_season=2026,
        completed_source_season=2025,
        target_years=(2026, 2027, 2028),
        coverage=ShapleyIntrinsicCoverage(
            player_count=1,
            year_1_forecast_players=1,
            year_2_i1_players=1,
            year_3_i1_players=1,
            rich_path_players=1,
            reduced_or_fallback_players=0,
        ),
        estimates=(
            ShapleyIntrinsicPlayerEstimate(
                player_id="p1",
                raw_intrinsic_value=discounted,
                contributions=typed,
                diagnostic_h1=DiagnosticH1Evidence(
                    target_season=2026,
                    anticipated_points=0.0,
                    provenance=ShapleyHorizonProvenance(
                        authority="diagnostic",
                        source="fixture",
                        model_version="fixture-v1",
                        diagnostic_only=True,
                        included_in_intrinsic=False,
                    ),
                    uncertainty=ShapleyHorizonUncertainty(
                        evidence_path="diagnostic"
                    ),
                    included_in_intrinsic=False,
                ),
            ),
        ),
    )


def _policy(policy: str, central: float) -> LongTermPolicyContribution:
    return LongTermPolicyContribution(
        policy_id=policy,
        central_shapley=central,
        lo80_shapley=max(0.0, central - 4.0),
        hi80_shapley=central + 4.0,
        lo90_shapley=max(0.0, central - 8.0),
        hi90_shapley=central + 8.0,
        forecast_model_version="fixture-v1",
        forecast_source="fixture",
        evidence_path="fixture",
    )


def _annual(year: int, base: float, policies: tuple[str, ...]) -> LongTermAnnualAuthority:
    contributions = tuple(
        _policy(policy, base + index * 2.0)
        for index, policy in enumerate(policies)
    )
    centers = [row.central_shapley for row in contributions]
    return LongTermAnnualAuthority(
        year_index=year,
        target_season=2025 + year,
        authority_kind="exact" if len(policies) == 1 else "set_valued",
        supported_policies=policies,
        policy_contributions=contributions,
        authority_low=min(centers),
        reference_center=(min(centers) + max(centers)) / 2.0,
        authority_high=max(centers),
        combined_lo80=min(row.lo80_shapley for row in contributions),
        combined_hi80=max(row.hi80_shapley for row in contributions),
        combined_lo90=min(row.lo90_shapley for row in contributions),
        combined_hi90=max(row.hi90_shapley for row in contributions),
    )


def _long_term() -> LongTermIntrinsicShadowContract:
    annual = (
        _annual(4, 40.0, ("blanket_75_25", "soft_stack")),
        _annual(5, 50.0, ("hard_router",)),
        _annual(6, 60.0, ("blanket_75_25", "hard_router", "soft_stack")),
        _annual(7, 70.0, ("hard_router", "soft_stack")),
    )
    low = sum(row.authority_low for row in annual) / 4.0
    high = sum(row.authority_high for row in annual) / 4.0
    center = (low + high) / 2.0
    return LongTermIntrinsicShadowContract(
        evaluation_season=2026,
        target_years=(2029, 2030, 2031, 2032),
        forecast_contract_version="long-horizon-fixture-v1",
        forecast_model_version="fixture-v1",
        permutations=FROZEN_SHAPLEY_PERMUTATIONS,
        base_seed=FROZEN_SHAPLEY_SEED,
        horizon_seeds=(20260919, 20260920, 20260921, 20260922),
        input_fingerprint="long-term-fixture",
        max_abs_shapley_efficiency_residual=0.0,
        estimates=(
            LongTermIntrinsicPlayerEstimate(
                player_id="p1",
                position=Position.WR,
                annual=annual,
                model_authority=LongTermModelAuthority(
                    low=low,
                    reference_center=center,
                    high=high,
                    width=high - low,
                    exact_horizons=(5,),
                    unresolved_horizons=(4, 6, 7),
                    policy_sets_by_horizon={
                        f"Y{row.year_index}": row.supported_policies
                        for row in annual
                    },
                ),
                within_model_uncertainty=LongTermWithinModelUncertainty(
                    combined_outer_80=(
                        sum(row.combined_lo80 for row in annual) / 4.0,
                        sum(row.combined_hi80 for row in annual) / 4.0,
                    ),
                    combined_outer_90=(
                        sum(row.combined_lo90 for row in annual) / 4.0,
                        sum(row.combined_hi90 for row in annual) / 4.0,
                    ),
                ),
                percentile_reference=0.5,
                value_index_reference_0_10000=5000.0,
            ),
        ),
    )


def test_holistic_raw_aggregation_uses_annual_phi_not_discounted_or_display_values() -> None:
    current = _current()
    long_term = _long_term()
    tail = build_career_tail_authority(
        CareerTailFeatures(
            player_id="p1",
            position=Position.WR,
            age_years=25.0,
            experience_years=3.0,
            current_points=100.0,
            prior_points=80.0,
            current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
        ),
        rules=_rules(),
    )

    result = build_career_forward_intrinsic_shadow(
        current,
        long_term,
        {"p1": tail},
    )
    row = result.estimates[0]

    assert row.current_intrinsic_raw_y1_y3 == pytest.approx(60.0)
    assert row.current_intrinsic_raw_y1_y3 != pytest.approx(
        current.estimates[0].raw_intrinsic_value
    )
    expected_y4_y7 = sum(item.reference_center for item in long_term.estimates[0].annual)
    assert row.long_horizon_raw_y4_y7_reference == pytest.approx(expected_y4_y7)
    assert row.long_horizon_raw_y4_y7_reference != pytest.approx(
        4.0 * long_term.estimates[0].model_authority.reference_center + 1.0
    )
    assert row.raw_career_forward_reference == pytest.approx(
        60.0 + expected_y4_y7 + tail.reference_center
    )
    assert row.aggregation == CAREER_FORWARD_AGGREGATION
    assert row.discounting_applied is False
    assert row.display_index_arithmetic_used is False
    assert row.market_inputs_used is False
    assert row.current_intrinsic_replaced is False
    assert result.long_horizon_contract_version == long_term.contract_version
    assert result.long_horizon_contract_version != long_term.forecast_contract_version


def test_holistic_model_authority_sums_bounds_but_does_not_create_outcome_interval() -> None:
    current = _current()
    long_term = _long_term()
    tail = build_career_tail_authority(
        CareerTailFeatures(
            player_id="p1",
            position=Position.WR,
            age_years=25.0,
            experience_years=3.0,
            current_points=100.0,
            prior_points=80.0,
            current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
        ),
        rules=_rules(),
    )
    result = build_career_forward_intrinsic_shadow(current, long_term, {"p1": tail})
    row = result.estimates[0]
    annual = long_term.estimates[0].annual

    assert row.model_authority.low == pytest.approx(
        60.0 + sum(item.authority_low for item in annual) + tail.model_authority_low
    )
    assert row.model_authority.high == pytest.approx(
        60.0 + sum(item.authority_high for item in annual) + tail.model_authority_high
    )
    assert row.uncertainty.cumulative_outcome_interval_authorized is False
    assert row.uncertainty.cumulative_standard_deviation_authorized is False
    assert row.uncertainty.cross_horizon_covariance_validated is False
    assert row.uncertainty.terminal_y8_plus.outcome_outer_90 == tail.outcome_outer_90


def test_holistic_shadow_requires_identical_full_cohort() -> None:
    current = _current()
    long_term = _long_term()
    with pytest.raises(ValueError, match="identical player cohort"):
        build_career_forward_intrinsic_shadow(current, long_term, {})



def _canonical_p0_future(horizon: int) -> I1ForecastResult:
    probabilities = {
        "out": 0.05, "depth": 0.10, "usable": 0.20,
        "starter": 0.35, "premium": 0.20, "elite": 0.10,
    }
    means = {state: float(index * 35) for index, state in enumerate(STATE_NAMES)}
    return I1ForecastResult(
        probabilities=probabilities,
        persistence_probability=0.9,
        anticipated_points=130.0 - 10.0 * horizon,
        state_means=means,
        evidence_path="rich",
        model_version="canonical-p0-fixture-v1",
    )


def _canonical_p0_year_one() -> ForecastObservation:
    as_of = datetime(2026, 10, 10, tzinfo=UTC)
    return ForecastObservation(
        player_id="p1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=155.0, stddev=22.0, p10=120.0, p50=155.0, p90=190.0),
        source="fixture:canonical-p0",
        model_version="current-y1-fixture-v1",
        as_of=as_of,
        provenance=Provenance(
            source="fixture",
            retrieved_at=as_of,
            effective_at=as_of,
            source_version="fixture-v1",
        ),
    )


def test_canonical_p0_packet_uses_shared_shapley_and_career_contracts():
    year_one = (_canonical_p0_year_one(),)
    future = {"p1": {2: _canonical_p0_future(2), 3: _canonical_p0_future(3)}}
    tail = build_career_tail_authority(
        CareerTailFeatures(
            player_id="p1",
            position=Position.WR,
            age_years=25.0,
            experience_years=3.0,
            current_points=100.0,
            prior_points=80.0,
            current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
        ),
        rules=_rules(),
    )
    composed = build_career_forward_from_canonical_p0(
        live_year_one_forecasts=year_one,
        future_results=future,
        future_source_season=2026,
        rules=_rules(),
        long_term=_long_term(),
        tails={"p1": tail},
    )
    assert composed.player_count == 1
    row = composed.estimates[0]
    assert tuple(item.target_season for item in row.uncertainty.current_y1_y3) == (2026, 2027, 2028)
    assert row.raw_career_forward_reference == pytest.approx(
        row.current_intrinsic_raw_y1_y3
        + row.long_horizon_raw_y4_y7_reference
        + row.terminal_raw_y8_plus_reference
    )
    assert row.aggregation == CAREER_FORWARD_AGGREGATION

    # The convenience adapter must preserve the established Shapley/Career
    # contract result for the same full-cohort canonical packet.
    calendar = compose_live_intrinsic_calendar_from_future_results(
        live_year_one_forecasts=year_one,
        future_results=future,
        future_source_season=2026,
    )
    current = build_shapley_intrinsic_contract(
        build_live_calendar_shapley_estimates(calendar, rules=_rules())
    )
    reference = build_career_forward_intrinsic_shadow(
        current,
        _long_term(),
        {"p1": tail},
    )
    assert row.raw_career_forward_reference == pytest.approx(
        reference.estimates[0].raw_career_forward_reference, abs=1e-9
    )
    assert row.model_authority.low == pytest.approx(
        reference.estimates[0].model_authority.low, abs=1e-9
    )
    assert row.model_authority.high == pytest.approx(
        reference.estimates[0].model_authority.high, abs=1e-9
    )


def test_canonical_p0_composition_fails_closed_on_missing_horizon():
    with pytest.raises(ValueError, match="direct Y2/Y3 only"):
        build_career_forward_from_canonical_p0(
            live_year_one_forecasts=(_canonical_p0_year_one(),),
            future_results={"p1": {2: _canonical_p0_future(2)}},
            future_source_season=2026,
            rules=_rules(),
            long_term=_long_term(),
            tails={"p1": build_career_tail_authority(
                CareerTailFeatures(
                    player_id="p1", position=Position.WR, age_years=25.0,
                    experience_years=3.0, current_points=100.0, prior_points=80.0,
                    current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
                    prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
                ),
                rules=_rules(),
            )},
        )


def test_career_composer_materializer_peak_rss_below_budget():
    """Focused 335-row Career composition RSS benchmark (Linux runner)."""
    import resource

    count = 335
    player_ids = tuple(f"career-bench-{index:03d}" for index in range(count))
    base_current = _current()
    current_estimate = base_current.estimates[0]
    current = base_current.model_copy(
        update={
            "coverage": base_current.coverage.model_copy(
                update={
                    "player_count": count,
                    "year_1_forecast_players": count,
                    "year_2_i1_players": count,
                    "year_3_i1_players": count,
                    "rich_path_players": count,
                }
            ),
            "estimates": tuple(
                current_estimate.model_copy(update={"player_id": player_id})
                for player_id in player_ids
            ),
        }
    )
    base_long = _long_term()
    long_estimate = base_long.estimates[0]
    long_term = base_long.model_copy(
        update={
            "estimates": tuple(
                long_estimate.model_copy(update={"player_id": player_id})
                for player_id in player_ids
            )
        }
    )
    benchmark_rules = _rules()
    tails = {
        player_id: build_career_tail_authority(
            CareerTailFeatures(
                player_id=player_id,
                position=Position.WR,
                age_years=25.0,
                experience_years=3.0,
                current_points=100.0,
                prior_points=80.0,
                current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
                prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
            ),
            rules=benchmark_rules,
        )
        for player_id in player_ids
    }

    result = build_career_forward_intrinsic_shadow(current, long_term, tails)
    peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"career_composer_335_peak_rss_mib={peak_rss_mib:.1f}")
    assert result.player_count == count
    assert peak_rss_mib < 410.0
