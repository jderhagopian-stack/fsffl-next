from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.context_controlled_profile import (
    OwnerContextControlledPositionPreference,
    OwnerContextControlledPreferenceProfile,
)
from fsffl.behavioral.preference_stability import build_owner_preference_stability_profile
from fsffl.state.models import Position


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def snapshot(day: int, *, rb: float, owner_id: str = "owner") -> OwnerContextControlledPreferenceProfile:
    # Keep the four-position residual decomposition net-zero while varying RB.
    values = {
        Position.QB: 0.0,
        Position.RB: rb,
        Position.WR: -0.8 * rb,
        Position.TE: -0.2 * rb,
    }
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
            context_authority_ids=("behavioral:context",),
            evidence_ids=(f"evidence:{day}:{position.value}",),
        )
        for position, residual in values.items()
    )
    return OwnerContextControlledPreferenceProfile(
        owner_id=owner_id,
        league_family_id="league-family",
        as_of=at(day),
        positions=rows,
        observed_positioned_acquisitions=8,
        estimated_position_count=4,
        mean_confidence=0.75,
        context_training_observation_count=40,
        context_training_owner_count=6,
        context_training_through=at(max(1, day - 1)),
        context_policy_parameter_id="context-policy",
        residual_policy_parameter_id="residual-policy",
        context_model_version="context-model",
        profile_model_version="owner-profile",
    )


def test_stability_profile_exposes_persistence_without_composite_score() -> None:
    result = build_owner_preference_stability_profile(
        [snapshot(3, rb=0.10), snapshot(5, rb=0.14), snapshot(7, rb=0.12)],
        as_of=at(8),
    )

    rb = result.position("RB")
    assert rb.status == "estimated"
    assert rb.available_snapshot_count == 3
    assert rb.positive_snapshot_count == 3
    assert rb.negative_snapshot_count == 0
    assert rb.latest_direction_agreement == 1.0
    assert rb.latest_residual_share == 0.12
    assert rb.earliest_residual_share == 0.10
    assert rb.mean_absolute_change == pytest.approx(0.03)
    assert rb.residual_standard_deviation is not None
    assert not hasattr(rb, "stability_score")


def test_stability_profile_detects_direction_instability_descriptively() -> None:
    result = build_owner_preference_stability_profile(
        [snapshot(3, rb=0.10), snapshot(5, rb=-0.08), snapshot(7, rb=0.04)],
        as_of=at(8),
    )

    rb = result.position(Position.RB)
    assert rb.positive_snapshot_count == 2
    assert rb.negative_snapshot_count == 1
    assert rb.latest_direction_agreement == pytest.approx(2 / 3)
    assert rb.mean_absolute_change == pytest.approx(0.15)


def test_stability_profile_requires_same_owner_and_ignores_future_snapshot() -> None:
    result = build_owner_preference_stability_profile(
        [snapshot(3, rb=0.10), snapshot(5, rb=0.12), snapshot(10, rb=-0.20)],
        as_of=at(6),
    )
    assert result.snapshot_count == 2
    assert result.position("RB").latest_residual_share == 0.12

    with pytest.raises(ValueError, match="share owner"):
        build_owner_preference_stability_profile(
            [snapshot(3, rb=0.10), snapshot(5, rb=0.12, owner_id="other")],
            as_of=at(6),
        )
