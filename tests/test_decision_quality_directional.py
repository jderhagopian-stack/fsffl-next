from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality_directional import (
    DirectionalEvidenceDirection,
    DirectionalEvidenceNormalizationPolicy,
    DirectionalEvidenceScoreRange,
    normalize_directional_decision_quality_component,
)


def policy() -> DirectionalEvidenceNormalizationPolicy:
    return DirectionalEvidenceNormalizationPolicy(
        component_id="future_asset_value",
        authority_id="pit-dynasty-market",
        overlap_group="future_asset_value",
        unfavorable=DirectionalEvidenceScoreRange(score_lower=0, score_center=25, score_upper=50),
        neutral=DirectionalEvidenceScoreRange(score_lower=40, score_center=50, score_upper=60),
        favorable=DirectionalEvidenceScoreRange(score_lower=50, score_center=75, score_upper=100),
        evidence_through=datetime(2022, 6, 1, tzinfo=UTC),
        model_version="directional-research-v1",
        provenance="tests:explicit-directional-ranges",
    )


def test_directional_evidence_preserves_broad_uncertainty_and_latest_cutoff() -> None:
    component = normalize_directional_decision_quality_component(
        direction=DirectionalEvidenceDirection.FAVORABLE,
        as_of=datetime(2022, 8, 9, tzinfo=UTC),
        evidence_through=datetime(2022, 7, 1, tzinfo=UTC),
        confidence=0.7,
        policy=policy(),
    )

    assert component.score_lower == 50
    assert component.score_center == 75
    assert component.score_upper == 100
    assert component.confidence == 0.7
    assert component.evidence_through == datetime(2022, 7, 1, tzinfo=UTC)


def test_directional_evidence_rejects_future_evidence() -> None:
    with pytest.raises(ValueError, match="information unavailable"):
        normalize_directional_decision_quality_component(
            direction=DirectionalEvidenceDirection.UNFAVORABLE,
            as_of=datetime(2022, 8, 9, tzinfo=UTC),
            evidence_through=datetime(2022, 8, 10, tzinfo=UTC),
            confidence=0.5,
            policy=policy(),
        )


def test_directional_policy_has_no_implicit_ranges_and_requires_ordered_centers() -> None:
    with pytest.raises(ValueError, match="ordered"):
        DirectionalEvidenceNormalizationPolicy(
            component_id="bad",
            authority_id="a",
            overlap_group="g",
            unfavorable=DirectionalEvidenceScoreRange(score_lower=60, score_center=70, score_upper=80),
            neutral=DirectionalEvidenceScoreRange(score_lower=40, score_center=50, score_upper=60),
            favorable=DirectionalEvidenceScoreRange(score_lower=20, score_center=30, score_upper=40),
            evidence_through=datetime(2022, 1, 1, tzinfo=UTC),
            model_version="bad-v1",
            provenance="tests",
        )
