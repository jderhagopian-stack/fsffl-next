from __future__ import annotations

import pytest

from fsffl.forecast.long_horizon_contract import (
    LONG_HORIZON_POLICIES,
    LongHorizonForecastAuthorityContract,
    LongHorizonPolicyForecast,
)
from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.long_term_intrinsic import (
    LONG_TERM_INTRINSIC_HORIZONS,
    LONG_TERM_INTRINSIC_MODEL_VERSION,
    LONG_TERM_INTRINSIC_SCALE,
    build_long_term_intrinsic_shadow,
    long_term_intrinsic_input_fingerprint,
)
from fsffl.value.shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=2,
        roster_size=8,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.WR, count=1),
        ),
        scoring=(),
    )


def _contract(
    *,
    boost_qb1_y4: float = 0.0,
    provenance_marker: str = "a",
    reverse: bool = False,
) -> LongHorizonForecastAuthorityContract:
    players = (
        ("qb1", Position.QB, 240.0),
        ("qb2", Position.QB, 190.0),
        ("qb3", Position.QB, 130.0),
        ("wr1", Position.WR, 210.0),
        ("wr2", Position.WR, 165.0),
        ("wr3", Position.WR, 115.0),
    )
    policy_offsets = {
        "baseline": 0.0,
        "hard_router": 7.0,
        "soft_stack": 14.0,
        "blanket_75_25": 21.0,
    }
    rows = []
    for player_id, position, base in players:
        for year_index in LONG_TERM_INTRINSIC_HORIZONS:
            for policy_id in LONG_HORIZON_POLICIES:
                central = base - 12.0 * (year_index - 4) + policy_offsets[policy_id]
                if player_id == "qb1" and year_index == 4:
                    central += boost_qb1_y4
                rows.append(
                    LongHorizonPolicyForecast(
                        player_id=player_id,
                        position=position,
                        evaluation_season=2026,
                        year_index=year_index,
                        target_season=2026 + year_index - 1,
                        policy_id=policy_id,
                        central_expectation=max(0.0, central),
                        absolute_error_80=12.0,
                        absolute_error_90=24.0,
                        model_version=f"{policy_id}-fixture-v1",
                        source="fixture",
                        evidence_path="frozen-long-horizon-fixture",
                    )
                )
    if reverse:
        rows.reverse()
    return LongHorizonForecastAuthorityContract(
        evaluation_season=2026,
        forecast_model_version="long-horizon-fixture-v1",
        forecast_source="fixture",
        forecasts=tuple(rows),
        provenance={"volatile_marker": provenance_marker},
    )


def _by_id(contract):
    return {item.player_id: item for item in contract.estimates}


def test_shadow_reproduces_equal_year_y4_y7_authority_envelope_without_discount() -> None:
    result = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    qb1 = _by_id(result)["qb1"]

    assert result.status == "shadow_ready"
    assert result.authoritative_for_product_ranking is False
    assert result.current_intrinsic_replaced is False
    assert result.cross_lens_additive is False
    assert result.value_model_version == LONG_TERM_INTRINSIC_MODEL_VERSION
    assert result.permutations == FROZEN_SHAPLEY_PERMUTATIONS
    assert result.base_seed == FROZEN_SHAPLEY_SEED
    assert result.horizon_seeds == tuple(
        FROZEN_SHAPLEY_SEED + horizon for horizon in LONG_TERM_INTRINSIC_HORIZONS
    )
    assert result.display_scale == LONG_TERM_INTRINSIC_SCALE

    annual = qb1.annual
    assert tuple(item.year_index for item in annual) == (4, 5, 6, 7)
    assert qb1.model_authority.low == pytest.approx(
        sum(item.authority_low for item in annual) / 4.0
    )
    assert qb1.model_authority.high == pytest.approx(
        sum(item.authority_high for item in annual) / 4.0
    )
    assert qb1.model_authority.reference_center == pytest.approx(
        (qb1.model_authority.low + qb1.model_authority.high) / 2.0
    )
    assert qb1.model_authority.width == pytest.approx(
        qb1.model_authority.high - qb1.model_authority.low
    )


def test_exact_forecast_cells_do_not_hide_or_blend_unsupported_policies() -> None:
    result = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    rows = _by_id(result)

    qb_y5 = next(item for item in rows["qb1"].annual if item.year_index == 5)
    wr_y5 = next(item for item in rows["wr1"].annual if item.year_index == 5)
    qb_y4 = next(item for item in rows["qb1"].annual if item.year_index == 4)

    assert qb_y5.authority_kind == "exact"
    assert qb_y5.supported_policies == ("blanket_75_25",)
    assert [item.policy_id for item in qb_y5.policy_contributions] == [
        "blanket_75_25"
    ]
    assert qb_y5.authority_low == pytest.approx(qb_y5.authority_high)

    assert wr_y5.authority_kind == "exact"
    assert wr_y5.supported_policies == ("hard_router",)
    assert [item.policy_id for item in wr_y5.policy_contributions] == ["hard_router"]

    assert qb_y4.authority_kind == "set_valued"
    assert set(qb_y4.supported_policies) == {"blanket_75_25", "soft_stack"}
    assert len(qb_y4.policy_contributions) == 2


def test_within_model_uncertainty_remains_separate_and_no_cumulative_sd_is_emitted() -> None:
    result = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    qb1 = _by_id(result)["qb1"]
    uncertainty = qb1.within_model_uncertainty

    lo80, hi80 = uncertainty.combined_outer_80
    lo90, hi90 = uncertainty.combined_outer_90
    assert lo90 <= lo80 <= qb1.model_authority.reference_center <= hi80 <= hi90
    assert uncertainty.cross_horizon_covariance_validated is False
    assert uncertainty.cumulative_standard_deviation_authorized is False
    assert not hasattr(uncertainty, "stddev")


def test_shadow_is_monotone_in_one_annual_forecast_coordinate() -> None:
    baseline = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    higher = build_long_term_intrinsic_shadow(
        _contract(boost_qb1_y4=40.0),
        rules=_rules(),
    )
    base_y4 = next(
        item for item in _by_id(baseline)["qb1"].annual if item.year_index == 4
    )
    higher_y4 = next(
        item for item in _by_id(higher)["qb1"].annual if item.year_index == 4
    )

    by_policy_before = {
        item.policy_id: item.central_shapley for item in base_y4.policy_contributions
    }
    by_policy_after = {
        item.policy_id: item.central_shapley for item in higher_y4.policy_contributions
    }
    assert all(
        by_policy_after[policy] >= by_policy_before[policy]
        for policy in by_policy_before
    )
    assert _by_id(higher)["qb1"].model_authority.reference_center >= (
        _by_id(baseline)["qb1"].model_authority.reference_center
    )


def test_display_ruler_is_separate_rank_calibration_with_full_zero_to_10000_range() -> None:
    result = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    indexes = [item.value_index_reference_0_10000 for item in result.estimates]

    assert max(indexes) == pytest.approx(10000.0)
    assert min(indexes) == pytest.approx(0.0)
    assert all(0.0 <= item.percentile_reference <= 1.0 for item in result.estimates)


def test_input_fingerprint_is_order_stable_and_ignores_audit_only_provenance() -> None:
    first = _contract(provenance_marker="first", reverse=False)
    second = _contract(provenance_marker="second", reverse=True)

    assert long_term_intrinsic_input_fingerprint(first, rules=_rules()) == (
        long_term_intrinsic_input_fingerprint(second, rules=_rules())
    )


def test_shadow_shapley_efficiency_remains_within_numeric_tolerance() -> None:
    result = build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    assert result.max_abs_shapley_efficiency_residual < 1e-8


def test_non_governed_shapley_permutation_count_fails_closed() -> None:
    with pytest.raises(ValueError, match="2,048"):
        build_long_term_intrinsic_shadow(
            _contract(),
            rules=_rules(),
            permutations=256,
        )
