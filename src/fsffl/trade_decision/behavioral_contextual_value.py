from __future__ import annotations

from fsffl.behavioral.residual_preference import OwnerPositionPreferenceResidual

from .contextual_value import ContextualValueAdjustmentKind
from .contextual_value_estimator import ContextualValueSignal


def derive_owner_behavior_contextual_signal(
    residual: OwnerPositionPreferenceResidual,
) -> ContextualValueSignal | None:
    """Bridge a context-controlled Behavioral residual into contextual value.

    Raw owner transaction counts are intentionally not accepted here. The input
    must already have removed the explicitly identified contextual expectation.
    Missing history remains unestimated rather than being converted to a zero-value
    owner preference.
    """

    if residual.shrunk_residual_share is None:
        return None
    return ContextualValueSignal(
        kind=ContextualValueAdjustmentKind.OWNER_BEHAVIOR,
        authority_id="behavioral:residual-position-preference",
        overlap_group=f"owner-behavior:position:{residual.position}",
        signal_center=residual.shrunk_residual_share,
        confidence=residual.confidence,
        evidence_ids=residual.evidence_ids,
        source_model_version=residual.model_version,
        residualized_against=residual.context_authority_ids,
        explanation=(
            f"Observed {residual.position} acquisition share was "
            f"{residual.observed_acquisition_share:.3f} versus context-explained "
            f"{residual.context_expected_acquisition_share:.3f}; the remaining owner-specific "
            f"residual was shrunk to {residual.shrunk_residual_share:.3f} based on "
            f"{residual.observed_positioned_acquisitions} positioned acquisitions."
        ),
    )
