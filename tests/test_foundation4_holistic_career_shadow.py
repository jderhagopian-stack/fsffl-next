from __future__ import annotations

import pytest

from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    Position,
    RosterSlot,
)
from fsffl.value.career_forward_intrinsic import (
    CareerTailPlayerFeatures,
    build_career_tail_estimate,
    build_holistic_career_forward_shadow,
    lineup_capacity_signature,
    terminal_artifact_metadata,
)
from fsffl.value.long_term_intrinsic import (
    LongTermAnnualAuthority,
    LongTermIntrinsicPlayerEstimate,
    LongTermIntrinsicShadowContract,
    LongTermModelAuthority,
    LongTermPolicyContribution,
    LongTermWithinModelUncertainty,
)
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


def _rules(*, wr_count: int = 3) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=wr_count),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )


def _current() -> ShapleyIntrinsicContract:
    provenance = ShapleyHorizonProvenance(
        authority="test",
        source="test",
        model_version="test",
    )
    uncertainty = ShapleyHorizonUncertainty(
        forecast_stddev=1.0,
        evidence_path="test",
    )
    contributions = tuple(
        ShapleyIntrinsicHorizonContribution(
            year_index=year,
            target_season=2025 + year,
            raw_shapley_contribution=value,
            discount_factor=1.0 if year == 1 else 0.85 ** (year - 1),
            discounted_contribution=value * (1.0 if year == 1 else 0.85 ** (year - 1)),
            provenance=provenance,
            uncertainty=uncertainty,
        )
        for year, value in ((1, 10.0), (2, 20.0), (3, 30.0))
    )
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
                raw_intrinsic_value=sum(
                    row.discounted_contribution for row in contributions
                ),
                contributions=contributions,  # type: ignore[arg-type]
                diagnostic_h1=DiagnosticH1Evidence(
                    target_season=2026,
                    anticipated_points=0.0,
                    provenance=provenance.model_copy(
                        update={
                            "diagnostic_only": True,
                            "included_in_intrinsic": False,
                        }
                    ),
                    uncertainty=uncertainty,
                    included_in_intrinsic=False,
                ),
            ),
        ),
    )


def _annual(year: int, low: float, center: float, high: float) -> LongTermAnnualAuthority:
    contributions = (
        LongTermPolicyContribution(
            policy_id="baseline",
            central_shapley=low,
            lo80_shapley=max(0.0, low - 1),
            hi80_shapley=low + 1,
            lo90_shapley=max(0.0, low - 2),
            hi90_shapley=low + 2,
            forecast_model_version="test",
            forecast_source="test",
            evidence_path="test",
        ),
        LongTermPolicyContribution(
            policy_id="soft_stack",
            central_shapley=high,
            lo80_shapley=max(0.0, high - 1),
            hi80_shapley=high + 1,
            lo90_shapley=max(0.0, high - 2),
            hi90_shapley=high + 2,
            forecast_model_version="test",
            forecast_source="test",
            evidence_path="test",
        ),
    )
    return LongTermAnnualAuthority(
        year_index=year,
        target_season=2025 + year,
        authority_kind="set_valued",
        supported_policies=("baseline", "soft_stack"),
        policy_contributions=contributions,
        authority_low=low,
        reference_center=center,
        authority_high=high,
        combined_lo80=max(0.0, low - 1),
        combined_hi80=high + 1,
        combined_lo90=max(0.0, low - 2),
        combined_hi90=high + 2,
    )


def _long_term() -> LongTermIntrinsicShadowContract:
    annual = (
        _annual(4, 4.0, 5.0, 6.0),
        _annual(5, 5.0, 6.0, 7.0),
        _annual(6, 6.0, 7.0, 8.0),
        _annual(7, 7.0, 8.0, 9.0),
    )
    return LongTermIntrinsicShadowContract(
        evaluation_season=2026,
        target_years=(2029, 2030, 2031, 2032),
        forecast_contract_version="test",
        forecast_model_version="test",
        permutations=2048,
        base_seed=20260915,
        horizon_seeds=(20260919, 20260920, 20260921, 20260922),
        input_fingerprint="test",
        max_abs_shapley_efficiency_residual=0.0,
        estimates=(
            LongTermIntrinsicPlayerEstimate(
                player_id="p1",
                position=Position.WR,
                annual=annual,
                model_authority=LongTermModelAuthority(
                    low=5.5,
                    reference_center=6.5,
                    high=7.5,
                    width=2.0,
                    exact_horizons=(),
                    unresolved_horizons=(4, 5, 6, 7),
                    policy_sets_by_horizon={
                        "Y4": ("baseline", "soft_stack"),
                        "Y5": ("baseline", "soft_stack"),
                        "Y6": ("baseline", "soft_stack"),
                        "Y7": ("baseline", "soft_stack"),
                    },
                ),
                within_model_uncertainty=LongTermWithinModelUncertainty(
                    combined_outer_80=(4.0, 9.0),
                    combined_outer_90=(3.0, 10.0),
                ),
                percentile_reference=0.50,
                value_index_reference_0_10000=5000,
            ),
        ),
    )


def _features() -> dict[str, CareerTailPlayerFeatures]:
    return {
        "p1": CareerTailPlayerFeatures(
            player_id="p1",
            position=Position.WR,
            age_years=26.0,
            experience_years=4.0,
            current_points=150.0,
            prior_points=140.0,
        )
    }


def test_terminal_artifact_exact_identity_and_holdout_coverage_are_frozen() -> None:
    metadata = terminal_artifact_metadata()

    assert metadata["artifact_id"] == 11260487964
    assert metadata["workflow_run_id"] == 37086000162
    assert metadata["artifact_digest"] == (
        "sha256:505ba72e71ddcb868c1673386f2a516d64e1a087fe2d8d9807572cb24cd99aa6"
    )
    assert metadata["corrected_holdout_outer80_coverage"] == pytest.approx(
        0.6118067978533095
    )
    assert metadata["corrected_holdout_outer90_coverage"] == pytest.approx(
        0.9302325581395349
    )
    assert lineup_capacity_signature(_rules()) == metadata["lineup_capacity_signature"]


def test_terminal_consumer_keeps_model_authority_separate_from_residual_evidence() -> None:
    result = build_career_tail_estimate(_features()["p1"], rules=_rules())

    assert len(result.model_predictions) == 2
    assert result.model_authority.supported_models == (
        "direct_ridge",
        "two_part_state",
    )
    assert result.model_authority.low == pytest.approx(
        min(row.expected_tail_y8_plus for row in result.model_predictions)
    )
    assert result.model_authority.high == pytest.approx(
        max(row.expected_tail_y8_plus for row in result.model_predictions)
    )
    assert result.outcome_uncertainty.corrected_holdout_outer80_coverage == pytest.approx(
        0.6118067978533095
    )
    assert result.outcome_uncertainty.corrected_holdout_outer90_coverage == pytest.approx(
        0.9302325581395349
    )
    assert all(
        row.outer80_is_calibrated_product_interval is False
        and row.outer90_is_calibrated_product_interval is False
        for row in result.model_predictions
    )


def test_terminal_consumer_fails_closed_on_lineup_capacity_mismatch() -> None:
    with pytest.raises(ValueError, match="lineup-capacity signature mismatch"):
        build_career_tail_estimate(_features()["p1"], rules=_rules(wr_count=2))


def test_holistic_raw_value_is_exact_y1_to_y7_plus_tail_without_display_index_math() -> None:
    current = _current()
    long_term = _long_term()
    result = build_holistic_career_forward_shadow(
        current,
        long_term,
        _features(),
        rules=_rules(),
    )
    player = result.estimates[0]
    tail = player.tail_y8_plus.model_authority

    assert player.annual_raw_y1_y3 == (10.0, 20.0, 30.0)
    assert player.model_authority.y1_y3_raw_exact == pytest.approx(60.0)
    assert player.model_authority.y4_y7_authority_low == pytest.approx(22.0)
    assert player.model_authority.y4_y7_reference_center == pytest.approx(26.0)
    assert player.model_authority.y4_y7_authority_high == pytest.approx(30.0)
    assert player.model_authority.low == pytest.approx(60.0 + 22.0 + tail.low)
    assert player.career_forward_raw_reference == pytest.approx(
        60.0 + 26.0 + tail.reference_center
    )
    assert player.model_authority.high == pytest.approx(
        60.0 + 30.0 + tail.high
    )
    assert player.current_intrinsic_raw_discounted_scalar == pytest.approx(
        current.estimates[0].raw_intrinsic_value
    )
    assert player.current_intrinsic_kept_separate is True
    assert player.display_indexes_combined is False
    assert result.display_scaling_applied is False
    assert result.market_inputs_used is False
    assert result.discounting_applied_to_holistic_raw is False
    assert result.cumulative_outcome_sd_authorized is False


def test_holistic_shadow_semantic_identity_is_deterministic() -> None:
    first = build_holistic_career_forward_shadow(
        _current(), _long_term(), _features(), rules=_rules()
    )
    second = build_holistic_career_forward_shadow(
        _current(), _long_term(), _features(), rules=_rules()
    )

    assert first.semantic_fingerprint == second.semantic_fingerprint
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
