from __future__ import annotations

from datetime import UTC, datetime

from fsffl.behavioral.context_controlled_profile import (
    OwnerContextControlledPositionPreference,
    OwnerContextControlledPreferenceProfile,
)
from fsffl.state.models import Position
from fsffl.trade_decision.behavioral_contextual_value import derive_owner_profile_contextual_signal
from fsffl.trade_decision.contextual_value import ContextualValueAdjustmentKind


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def profile(*, rb_status: str = "estimated") -> OwnerContextControlledPreferenceProfile:
    rows = []
    for position, observed, expected, residual in (
        (Position.QB, 0.10, 0.10, 0.0),
        (Position.RB, 0.50, 0.25, 0.20),
        (Position.WR, 0.30, 0.50, -0.16),
        (Position.TE, 0.10, 0.15, -0.04),
    ):
        if position == Position.RB and rb_status == "unavailable":
            rows.append(
                OwnerContextControlledPositionPreference(
                    position=position,
                    status="unavailable",
                    unavailable_reason="insufficient context history",
                )
            )
            continue
        rows.append(
            OwnerContextControlledPositionPreference(
                position=position,
                observed_acquisition_share=observed,
                context_expected_acquisition_share=expected,
                raw_residual_share=observed - expected,
                shrunk_residual_share=residual,
                confidence=0.8,
                observed_position_acquisitions=int(observed * 10),
                observed_positioned_acquisitions=10,
                status="estimated",
                context_authority_ids=("behavioral:context-model",),
                evidence_ids=(f"behavioral:evidence:{position.value}",),
            )
        )
    estimated = [row for row in rows if row.status == "estimated"]
    return OwnerContextControlledPreferenceProfile(
        owner_id="owner",
        league_family_id="league-family",
        as_of=at(10),
        positions=tuple(rows),
        observed_positioned_acquisitions=10,
        estimated_position_count=len(estimated),
        mean_confidence=sum(row.confidence for row in estimated) / len(estimated),
        context_training_observation_count=80,
        context_training_owner_count=8,
        context_training_through=at(8),
        context_policy_parameter_id="behavioral:context-v1",
        residual_policy_parameter_id="behavioral:residual-v1",
        context_model_version="behavioral-context-expectation-v1",
        profile_model_version="owner-behavior-profile-v1",
    )


def test_profile_bridge_exposes_only_context_controlled_owner_behavior() -> None:
    signal = derive_owner_profile_contextual_signal(profile(), position="RB")

    assert signal is not None
    assert signal.kind == ContextualValueAdjustmentKind.OWNER_BEHAVIOR
    assert signal.signal_center == 0.20
    assert signal.confidence == 0.8
    assert signal.overlap_group == "owner-behavior:position:RB"
    assert signal.residualized_against == ("behavioral:context-model",)
    assert "context-controlled-profile" in signal.evidence_ids[-1]
    assert "0.500" in signal.explanation
    assert "0.250" in signal.explanation


def test_profile_bridge_keeps_unavailable_position_out_of_contextual_value() -> None:
    assert derive_owner_profile_contextual_signal(profile(rb_status="unavailable"), position="RB") is None
