from __future__ import annotations

from fsffl.behavioral import (
    BehavioralEvidenceLevel,
    BehavioralLikelihoodEstimate,
    BehavioralProbabilityBasis,
)
from fsffl.behavioral.models import OwnerBehaviorProfile

from .acceptance import (
    AcceptanceEvidenceItem,
    AcceptanceEvidenceKind,
    AcceptanceEvidenceSet,
    AcceptanceModelStatus,
    AcceptanceProbabilityEstimate,
    TradeAcceptanceView,
    build_unestimated_acceptance_view,
)
from .behavioral_trade_shape import OwnerTradeShapeProposalFit
from .models import BilateralTradeProposal


def bind_owner_behavior_evidence(
    proposal: BilateralTradeProposal,
    *,
    accepting_team_id: str,
    profile: OwnerBehaviorProfile,
    likelihood: BehavioralLikelihoodEstimate | None = None,
    trade_shape_fit: OwnerTradeShapeProposalFit | None = None,
) -> TradeAcceptanceView:
    """Bind governed Behavioral evidence to NEXT-5 without recalculating it.

    The raw profile remains useful when no probability estimate exists. Context-
    controlled proposal-shape fit may also be attached as descriptive acceptance
    evidence. It does not change the probability by itself. When a governed
    BehavioralLikelihoodEstimate is supplied, this boundary may pass its inferred
    or calibrated probability through with explicit provenance and uncertainty.

    This function does not derive odds, alter universal market Value, or compound
    Behavioral evidence with franchise-utility factors. Inferred Behavioral odds
    are provisional Decision evidence; calibration does not by itself promote
    Trade Decision acceptance authority to AUTHORITATIVE.
    """

    team_ids = {proposal.side_a.team_id, proposal.side_b.team_id}
    if accepting_team_id not in team_ids:
        raise ValueError("accepting team must be one side of the proposal")
    if profile.as_of > proposal.as_of:
        raise ValueError("behavioral profile cannot use evidence after proposal cutoff")
    if trade_shape_fit is not None:
        if trade_shape_fit.proposal_id != proposal.proposal_id:
            raise ValueError("trade-shape fit proposal must match acceptance proposal")
        if trade_shape_fit.accepting_team_id != accepting_team_id:
            raise ValueError("trade-shape fit accepting team must match acceptance view")
        if trade_shape_fit.owner_id != profile.owner_id:
            raise ValueError("trade-shape fit owner must match behavioral profile")
        if trade_shape_fit.source_profile_as_of > proposal.as_of:
            raise ValueError("trade-shape fit cannot use evidence after proposal cutoff")
    if likelihood is not None:
        if likelihood.owner_id != profile.owner_id:
            raise ValueError("behavioral likelihood owner must match behavioral profile")
        if likelihood.as_of > proposal.as_of:
            raise ValueError("behavioral likelihood cannot use evidence after proposal cutoff")
        if likelihood.as_of < profile.as_of:
            raise ValueError("behavioral likelihood cannot predate its supporting profile")

    focal_team_id = next(team_id for team_id in team_ids if team_id != accepting_team_id)
    description = (
        f"Observed owner history: {profile.trade_count} completed trades, "
        f"{profile.consolidation_trade_count} consolidation, "
        f"{profile.diversification_trade_count} diversification, "
        f"{profile.balanced_trade_count} balanced; "
        f"draft picks {profile.acquired_pick_count} acquired / "
        f"{profile.disposed_pick_count} disposed; "
        f"{profile.event_count} total recorded transaction events across "
        f"{len(profile.seasons_observed)} season(s)."
    )
    evidence_items = [
        AcceptanceEvidenceItem(
            evidence_id=f"owner-behavior:{profile.league_family_id}:{profile.owner_id}:{profile.model_version}",
            kind=AcceptanceEvidenceKind.OWNER_BEHAVIOR,
            observed_at=profile.as_of,
            source="fsffl-behavioral-intelligence",
            source_version=profile.model_version,
            description=description,
        )
    ]
    if trade_shape_fit is not None:
        if trade_shape_fit.status == "estimated":
            shape_description = (
                f"Proposal shape from accepting owner's perspective={trade_shape_fit.proposed_shape.value}; "
                f"observed historical share={trade_shape_fit.observed_historical_share:.3f}; "
                f"context-expected share={trade_shape_fit.context_expected_share:.3f}; "
                f"context-controlled residual={trade_shape_fit.residual_share:.3f}; "
                f"residual confidence={trade_shape_fit.confidence:.3f}; "
                f"historical coverage={trade_shape_fit.historical_coverage_rate:.3f}."
            )
        else:
            shape_description = (
                f"Proposal shape from accepting owner's perspective={trade_shape_fit.proposed_shape.value}; "
                "context-controlled historical shape fit unavailable."
            )
        evidence_items.append(
            AcceptanceEvidenceItem(
                evidence_id=f"owner-trade-shape-fit:{profile.owner_id}:{trade_shape_fit.model_version}",
                kind=AcceptanceEvidenceKind.OWNER_BEHAVIOR,
                observed_at=trade_shape_fit.source_profile_as_of,
                source="fsffl-behavioral-trade-shape",
                source_version=trade_shape_fit.source_profile_model_version,
                description=shape_description,
            )
        )
    if likelihood is not None:
        evidence_items.append(
            AcceptanceEvidenceItem(
                evidence_id=f"owner-behavior-likelihood:{profile.owner_id}:{likelihood.model_version}",
                kind=AcceptanceEvidenceKind.OWNER_BEHAVIOR,
                observed_at=likelihood.as_of,
                source="fsffl-behavioral-likelihood",
                source_version=likelihood.model_version,
                description=(
                    f"Governed {likelihood.evidence_level.value} owner-response estimate; "
                    f"direction={likelihood.direction.value}; "
                    f"observed trades={likelihood.observed_trade_count}."
                ),
            )
        )

    evidence = AcceptanceEvidenceSet(
        proposal_id=proposal.proposal_id,
        focal_team_id=focal_team_id,
        counterparty_team_id=accepting_team_id,
        as_of=proposal.as_of,
        items=tuple(evidence_items),
        model_version="next5-owner-behavior-evidence-v3",
    )

    if likelihood is None or likelihood.acceptance_probability is None:
        return build_unestimated_acceptance_view(
            proposal,
            accepting_team_id=accepting_team_id,
            evidence=evidence,
        )

    if likelihood.probability_basis not in {
        BehavioralProbabilityBasis.INFERRED,
        BehavioralProbabilityBasis.CALIBRATED,
    }:
        raise ValueError("behavioral probability requires governed inferred or calibrated basis")
    if likelihood.evidence_level not in {
        BehavioralEvidenceLevel.INFERRED,
        BehavioralEvidenceLevel.CALIBRATED,
    }:
        raise ValueError("numeric behavioral probability requires inferred or calibrated evidence")

    # Behavioral evidence is contextual and bounded upstream. This binding is a
    # pass-through only: it neither adds another team-need adjustment nor
    # multiplies this probability by other Decision factors. Trade-shape fit is
    # evidence only unless it is incorporated exactly once by a governed upstream
    # Behavioral likelihood model.
    status = AcceptanceModelStatus.PROVISIONAL_GOVERNED
    estimate = AcceptanceProbabilityEstimate(
        proposal_id=proposal.proposal_id,
        accepting_team_id=accepting_team_id,
        probability_mean=likelihood.acceptance_probability,
        probability_p10=likelihood.probability_interval_low,
        probability_p90=likelihood.probability_interval_high,
        as_of=likelihood.as_of,
        evidence_count=len(evidence.items),
        status=status,
        model_version=(
            likelihood.calibration_model_version
            or likelihood.inference_model_version
            or likelihood.model_version
        ),
        evidence_model_version=evidence.model_version,
    )
    return TradeAcceptanceView(
        proposal_id=proposal.proposal_id,
        accepting_team_id=accepting_team_id,
        evidence=evidence,
        estimate=estimate,
        status=status,
    )
