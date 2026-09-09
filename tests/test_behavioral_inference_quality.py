from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.context_controlled_profile import OwnerContextControlledPositionPreference, OwnerContextControlledPreferenceProfile
from fsffl.behavioral.historical_context_profile import OwnerHistoricalContextControlledPreferenceResult, OwnerHistoricalContextCoverage
from fsffl.behavioral.inference_quality import build_owner_behavior_inference_quality_profile
from fsffl.behavioral.preference_stability import OwnerPositionPreferenceStability, OwnerPreferenceStabilityProfile
from fsffl.state.models import Position


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def historical() -> OwnerHistoricalContextControlledPreferenceResult:
    residuals = {Position.QB: 0.0, Position.RB: 0.2, Position.WR: -0.16, Position.TE: -0.04}
    rows = tuple(
        OwnerContextControlledPositionPreference(
            position=position,
            observed_acquisition_share=0.25 + residual,
            context_expected_acquisition_share=0.25,
            raw_residual_share=residual,
            shrunk_residual_share=residual,
            confidence=0.75,
            observed_position_acquisitions=2,
            observed_positioned_acquisitions=8,
            status="estimated",
            context_authority_ids=("behavioral:eventwise-context",),
            evidence_ids=(f"event:{position.value}",),
        )
        for position, residual in residuals.items()
    )
    profile = OwnerContextControlledPreferenceProfile(
        owner_id="owner",
        league_family_id="family",
        as_of=at(10),
        positions=rows,
        observed_positioned_acquisitions=8,
        estimated_position_count=4,
        mean_confidence=0.75,
        context_training_observation_count=50,
        context_training_owner_count=8,
        context_training_through=at(9),
        context_policy_parameter_id="context-policy",
        residual_policy_parameter_id="residual-policy",
        context_model_version="context-v2+eventwise",
        profile_model_version="historical-profile-v2",
    )
    coverage = OwnerHistoricalContextCoverage(
        owner_id="owner",
        as_of=at(10),
        eligible_event_count=8,
        estimated_event_count=8,
        eligible_positioned_acquisitions=10,
        estimated_positioned_acquisitions=8,
        event_coverage_rate=1.0,
        acquisition_coverage_rate=0.8,
        unavailable=(),
    )
    return OwnerHistoricalContextControlledPreferenceResult(profile=profile, coverage=coverage)


def stability() -> OwnerPreferenceStabilityProfile:
    rows = tuple(
        OwnerPositionPreferenceStability(
            position=position,
            available_snapshot_count=3,
            first_estimated_at=at(4),
            latest_estimated_at=at(10),
            earliest_residual_share=0.10,
            latest_residual_share=0.12,
            mean_residual_share=0.11,
            residual_standard_deviation=0.01,
            mean_absolute_change=0.02,
            nonzero_snapshot_count=3,
            positive_snapshot_count=3,
            negative_snapshot_count=0,
            latest_direction_agreement=1.0,
            latest_confidence=0.75,
            status="estimated",
        )
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
    )
    return OwnerPreferenceStabilityProfile(
        owner_id="owner",
        league_family_id="family",
        as_of=at(10),
        snapshot_count=3,
        positions=rows,
        source_profile_model_versions=("v1", "v1", "v1"),
    )


def test_quality_keeps_coverage_confidence_and_stability_separate() -> None:
    result = build_owner_behavior_inference_quality_profile(historical(), stability=stability())

    rb = result.position("RB")
    assert rb.residual_confidence == 0.75
    assert rb.event_coverage_rate == 1.0
    assert rb.acquisition_coverage_rate == 0.8
    assert rb.latest_direction_agreement == 1.0
    assert rb.residual_standard_deviation == 0.01
    assert not hasattr(rb, "quality_score")
    assert not hasattr(rb, "combined_confidence")


def test_quality_can_exist_before_stability_is_available() -> None:
    result = build_owner_behavior_inference_quality_profile(historical())
    assert result.position(Position.RB).stability_status == "not_supplied"
    assert result.position(Position.RB).latest_direction_agreement is None


def test_quality_rejects_mismatched_stability_identity() -> None:
    other = stability().model_copy(update={"owner_id": "other"})
    with pytest.raises(ValueError, match="identity"):
        build_owner_behavior_inference_quality_profile(historical(), stability=other)
