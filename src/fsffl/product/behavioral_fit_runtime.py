"""Compatibility view of completed-trade evidence, never owner willingness."""
from fsffl.behavioral import (BehavioralDriverKind, BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection, BehavioralLikelihoodDriver, BehavioralLikelihoodEstimate)
from fsffl.trade_decision.owner_history import describe_owner_package_history


def build_trade_behavioral_fit(runtime, proposal, *, focal_team_id,
                               counterparty_profile, focal_owner_id=None):
    """Keep legacy consumers readable without deriving response direction.

    Completed transactions provide observations, not a sample of all offers.
    Competitive state belongs to transaction evaluation and is not owner intent.
    """
    if (counterparty_profile is None or runtime.league_state is None
        or focal_team_id not in {proposal.side_a.team_id,proposal.side_b.team_id}):
        return None
    team_id=next(leg.team_id for leg in (proposal.side_a,proposal.side_b) if leg.team_id!=focal_team_id)
    history=describe_owner_package_history(proposal,team_id=team_id,
        profile=counterparty_profile,player_positions={p.player_id:p.position.value for p in runtime.league_state.players},
        source_state_id=runtime.league_state.state_id,other_owner_id=focal_owner_id)
    if history['status']=='unavailable':
        return None
    return BehavioralLikelihoodEstimate(owner_id=counterparty_profile.owner_id,
        as_of=proposal.as_of,evidence_level=BehavioralEvidenceLevel.OBSERVED,
        direction=BehavioralLikelihoodDirection.NEUTRAL,
        drivers=tuple(BehavioralLikelihoodDriver(kind=BehavioralDriverKind.OWNER_HISTORY,
            direction=BehavioralLikelihoodDirection.NEUTRAL,description=fact,
            evidence_level=BehavioralEvidenceLevel.OBSERVED) for fact in history['facts']),
        observed_trade_count=counterparty_profile.trade_count,
        model_version='next8-behavioral-fit-v2:completed-trade-observations-only')
