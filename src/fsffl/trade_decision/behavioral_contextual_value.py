from __future__ import annotations

from fsffl.behavioral.context_controlled_profile import OwnerContextControlledPreferenceProfile
from fsffl.behavioral.residual_preference import OwnerPositionPreferenceResidual
from fsffl.state.models import Position

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


def derive_owner_profile_contextual_signal(
    profile: OwnerContextControlledPreferenceProfile,
    *,
    position: str | Position,
) -> ContextualValueSignal | None:
    """Expose one governed owner-profile position tendency as contextual evidence.

    This is the preferred profile-level bridge. It prevents downstream callers from
    reaching back into the lower-level residual estimator and guarantees that only
    an already context-controlled, estimated position row can influence contextual
    value. The function remains dimensionless: it does not choose a ValueScale
    effect, mutate universal Market Value, or create acceptance probability.
    """

    row = profile.position(position)
    if row.status != "estimated" or row.shrunk_residual_share is None:
        return None
    if row.observed_acquisition_share is None or row.context_expected_acquisition_share is None:
        return None

    position_value = row.position.value
    evidence_ids = row.evidence_ids + (
        f"behavioral-context-controlled-profile:{profile.league_family_id}:{profile.owner_id}:{profile.model_version}",
    )
    return ContextualValueSignal(
        kind=ContextualValueAdjustmentKind.OWNER_BEHAVIOR,
        authority_id="behavioral:context-controlled-position-preference",
        overlap_group=f"owner-behavior:position:{position_value}",
        signal_center=row.shrunk_residual_share,
        confidence=row.confidence,
        evidence_ids=evidence_ids,
        source_model_version=profile.model_version,
        residualized_against=row.context_authority_ids,
        explanation=(
            f"After controlling for comparable pre-action roster context, owner {profile.owner_id} "
            f"acquired {position_value} at a {row.observed_acquisition_share:.3f} share versus "
            f"{row.context_expected_acquisition_share:.3f} expected; the remaining owner-specific "
            f"residual is {row.shrunk_residual_share:.3f} with confidence {row.confidence:.3f}."
        ),
    )
