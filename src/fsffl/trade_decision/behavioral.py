from __future__ import annotations

from fsffl.behavioral.models import OwnerBehaviorProfile

from .acceptance import (
    AcceptanceEvidenceItem,
    AcceptanceEvidenceKind,
    AcceptanceEvidenceSet,
    TradeAcceptanceView,
    build_unestimated_acceptance_view,
)
from .models import BilateralTradeProposal


def bind_owner_behavior_evidence(
    proposal: BilateralTradeProposal,
    *,
    accepting_team_id: str,
    profile: OwnerBehaviorProfile,
) -> TradeAcceptanceView:
    """Attach observed owner history to NEXT-5 without inventing acceptance odds.

    Behavioral Intelligence remains evidence beside franchise utility. It does not
    alter market Value, rewrite calculated team consequences, or estimate a
    probability. A future calibrated negotiation model may consume the same
    profile/evidence contract without changing this boundary.
    """

    team_ids = {proposal.side_a.team_id, proposal.side_b.team_id}
    if accepting_team_id not in team_ids:
        raise ValueError("accepting team must be one side of the proposal")
    if profile.as_of > proposal.as_of:
        raise ValueError("behavioral profile cannot use evidence after proposal cutoff")
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
    evidence = AcceptanceEvidenceSet(
        proposal_id=proposal.proposal_id,
        focal_team_id=focal_team_id,
        counterparty_team_id=accepting_team_id,
        as_of=proposal.as_of,
        items=(
            AcceptanceEvidenceItem(
                evidence_id=f"owner-behavior:{profile.league_family_id}:{profile.owner_id}:{profile.model_version}",
                kind=AcceptanceEvidenceKind.OWNER_BEHAVIOR,
                observed_at=profile.as_of,
                source="fsffl-behavioral-intelligence",
                source_version=profile.model_version,
                description=description,
            ),
        ),
        model_version="next5-owner-behavior-evidence-v1",
    )
    return build_unestimated_acceptance_view(
        proposal,
        accepting_team_id=accepting_team_id,
        evidence=evidence,
    )
