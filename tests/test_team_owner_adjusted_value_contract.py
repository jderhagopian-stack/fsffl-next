from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fsffl.trade_decision.contextual_value import (
    ContextualValueAdjustment,
    ContextualValueAdjustmentKind,
    ContextualValueEvidenceLevel,
    TeamOwnerAdjustedValueEstimate,
)
from fsffl.value.models import (
    MarketPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
)


AS_OF = datetime(2026, 9, 8, 12, tzinfo=UTC)
SCALE = ValueScale(scale_id="fsffl-cardinal", version="v1", unit_label="value points")


def _market_baseline() -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id="player-1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=8000.0, stddev=500.0, p10=7400.0, p50=8000.0, p90=8600.0),
        scale=SCALE,
        as_of=AS_OF,
        market_context_id="league-market",
        model_version="market-v1",
        evidence_sources=("market-source",),
    )


def _need_adjustment() -> ContextualValueAdjustment:
    return ContextualValueAdjustment(
        kind=ContextualValueAdjustmentKind.TEAM_NEED,
        authority_id="decision:team-need",
        overlap_group="roster-fit",
        delta_mean=300.0,
        confidence=0.70,
        evidence_level=ContextualValueEvidenceLevel.INFERRED,
        evidence_ids=("roster-state:team-1", "position-strength:RB"),
        source_model_version="team-need-v1",
        explanation="RB need raises contextual acquisition value.",
    )


def _behavior_adjustment() -> ContextualValueAdjustment:
    return ContextualValueAdjustment(
        kind=ContextualValueAdjustmentKind.OWNER_BEHAVIOR,
        authority_id="behavioral:owner-preference-residual",
        overlap_group="owner-preference-residual",
        delta_mean=150.0,
        confidence=0.42,
        evidence_level=ContextualValueEvidenceLevel.INFERRED,
        evidence_ids=("owner-history:owner-1",),
        source_model_version="behavioral-preference-v1",
        residualized_against=("decision:team-need",),
        explanation="Residual owner tendency after controlling for current roster need.",
    )


def test_team_owner_adjusted_value_keeps_market_baseline_and_adds_bounded_non_overlapping_deltas() -> None:
    estimate = TeamOwnerAdjustedValueEstimate(
        team_id="team-1",
        owner_id="owner-1",
        market_baseline=_market_baseline(),
        adjusted_distribution=ValueDistribution(mean=8450.0, stddev=650.0, p10=7650.0, p50=8450.0, p90=9250.0),
        scale=SCALE,
        as_of=AS_OF,
        adjustments=(_need_adjustment(), _behavior_adjustment()),
        adjustment_bound_abs=750.0,
    )

    assert estimate.market_baseline.distribution.mean == 8000.0
    assert estimate.total_adjustment == 450.0
    assert estimate.adjusted_distribution.mean == 8450.0


def test_adjusted_value_rejects_duplicate_overlap_group() -> None:
    duplicate = ContextualValueAdjustment(
        kind=ContextualValueAdjustmentKind.ROSTER_CONSTRUCTION,
        authority_id="decision:roster-construction",
        overlap_group="roster-fit",
        delta_mean=100.0,
        confidence=0.60,
        evidence_level=ContextualValueEvidenceLevel.INFERRED,
        evidence_ids=("depth-state:team-1",),
        source_model_version="roster-construction-v1",
    )
    with pytest.raises(ValidationError, match="overlapping adjustments"):
        TeamOwnerAdjustedValueEstimate(
            team_id="team-1",
            owner_id="owner-1",
            market_baseline=_market_baseline(),
            adjusted_distribution=ValueDistribution(mean=8400.0),
            scale=SCALE,
            as_of=AS_OF,
            adjustments=(_need_adjustment(), duplicate),
            adjustment_bound_abs=750.0,
        )


def test_adjusted_value_rejects_reused_evidence_even_across_different_labels() -> None:
    duplicate_evidence = ContextualValueAdjustment(
        kind=ContextualValueAdjustmentKind.OWNER_BEHAVIOR,
        authority_id="behavioral:owner-history",
        overlap_group="owner-history",
        delta_mean=100.0,
        confidence=0.40,
        evidence_level=ContextualValueEvidenceLevel.INFERRED,
        evidence_ids=("roster-state:team-1",),
        source_model_version="behavioral-v1",
    )
    with pytest.raises(ValidationError, match="cannot reuse evidence"):
        TeamOwnerAdjustedValueEstimate(
            team_id="team-1",
            owner_id="owner-1",
            market_baseline=_market_baseline(),
            adjusted_distribution=ValueDistribution(mean=8400.0),
            scale=SCALE,
            as_of=AS_OF,
            adjustments=(_need_adjustment(), duplicate_evidence),
            adjustment_bound_abs=750.0,
        )


def test_adjusted_value_rejects_out_of_bound_or_non_additive_result() -> None:
    with pytest.raises(ValidationError, match="exceeds governed absolute bound"):
        TeamOwnerAdjustedValueEstimate(
            team_id="team-1",
            owner_id="owner-1",
            market_baseline=_market_baseline(),
            adjusted_distribution=ValueDistribution(mean=8450.0),
            scale=SCALE,
            as_of=AS_OF,
            adjustments=(_need_adjustment(), _behavior_adjustment()),
            adjustment_bound_abs=400.0,
        )

    with pytest.raises(ValidationError, match="baseline plus additive"):
        TeamOwnerAdjustedValueEstimate(
            team_id="team-1",
            owner_id="owner-1",
            market_baseline=_market_baseline(),
            adjusted_distribution=ValueDistribution(mean=9000.0),
            scale=SCALE,
            as_of=AS_OF,
            adjustments=(_need_adjustment(), _behavior_adjustment()),
            adjustment_bound_abs=750.0,
        )


def test_contextual_value_contract_has_no_multiplicative_adjustment_path() -> None:
    fields = ContextualValueAdjustment.model_fields
    assert "multiplier" not in fields
    assert "factor" not in fields
    assert "weight" not in fields
    assert "delta_mean" in fields
