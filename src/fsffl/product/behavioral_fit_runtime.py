from __future__ import annotations

from collections import Counter
from typing import Any

from fsffl.behavioral import (
    BehavioralDriverKind,
    BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection,
    BehavioralLikelihoodDriver,
    BehavioralLikelihoodEstimate,
    OwnerBehaviorProfile,
)
from fsffl.state.models import PickAsset, PlayerAsset
from fsffl.trade_decision.models import BilateralTradeProposal


_MODEL_VERSION = "next8-behavioral-fit-v1:transparent-directional"


def _side_for_team(proposal: BilateralTradeProposal, team_id: str):
    return next((side for side in proposal.sides if side.team_id == team_id), None)


def _player_position(league_state, player_id: str) -> str | None:
    player = next((item for item in league_state.players if item.player_id == player_id), None)
    return player.position.value if player is not None else None


def _package_shape(acquired_count: int, disposed_count: int) -> str:
    if acquired_count < disposed_count:
        return "consolidation"
    if acquired_count > disposed_count:
        return "diversification"
    return "balanced"


def _shape_count(profile: OwnerBehaviorProfile, shape: str) -> int:
    return {
        "consolidation": profile.consolidation_trade_count,
        "diversification": profile.diversification_trade_count,
        "balanced": profile.balanced_trade_count,
    }[shape]


def _current_team_view(runtime: Any, team_id: str):
    simulation = runtime.simulation_analytics
    if simulation is None:
        return None
    return next((item for item in simulation.team_views if item.team_id == team_id), None)


def build_trade_behavioral_fit(
    runtime: Any,
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    counterparty_profile: OwnerBehaviorProfile | None,
    focal_owner_id: str | None = None,
) -> BehavioralLikelihoodEstimate | None:
    """Infer directional trade plausibility from transparent Behavioral evidence.

    The estimate is intentionally qualitative. It may combine observed owner
    history with current Team Utility state and package structure, but it never
    creates a numeric acceptance probability or changes Value/Decision authority.
    Every inference is exposed as an explicit driver so Product can explain why
    the fit moved up, down, or stayed mixed.
    """

    if counterparty_profile is None:
        return None
    league_state = runtime.league_state
    if league_state is None:
        return None
    focal_side = _side_for_team(proposal, focal_team_id)
    if focal_side is None:
        return None
    counterparty_side = next((side for side in proposal.sides if side.team_id != focal_team_id), None)
    if counterparty_side is None:
        return None

    # From the counterparty's perspective, they acquire the focal team's outgoing
    # assets and dispose the assets listed on their own side.
    acquired = tuple(focal_side.assets)
    disposed = tuple(counterparty_side.assets)
    drivers: list[BehavioralLikelihoodDriver] = []

    shape = _package_shape(len(acquired), len(disposed))
    observed_shape_count = _shape_count(counterparty_profile, shape)
    shape_counts = {
        "consolidation": counterparty_profile.consolidation_trade_count,
        "diversification": counterparty_profile.diversification_trade_count,
        "balanced": counterparty_profile.balanced_trade_count,
    }
    max_shape_count = max(shape_counts.values(), default=0)
    shape_direction = BehavioralLikelihoodDirection.NEUTRAL
    if counterparty_profile.trade_count >= 3 and max_shape_count > 0:
        leaders = [name for name, count in shape_counts.items() if count == max_shape_count]
        if len(leaders) == 1 and leaders[0] == shape:
            shape_direction = BehavioralLikelihoodDirection.ELEVATED
        elif observed_shape_count == 0:
            shape_direction = BehavioralLikelihoodDirection.REDUCED
    drivers.append(
        BehavioralLikelihoodDriver(
            kind=BehavioralDriverKind.PACKAGE_SHAPE,
            direction=shape_direction,
            description=(
                f"This is a {shape} package for the other owner. Their observed history contains "
                f"{observed_shape_count} {shape} trade(s) across {counterparty_profile.trade_count} total trade(s)."
            ),
            evidence_level=BehavioralEvidenceLevel.OBSERVED,
        )
    )

    acquired_picks = sum(isinstance(asset, PickAsset) for asset in acquired)
    disposed_picks = sum(isinstance(asset, PickAsset) for asset in disposed)
    if acquired_picks or disposed_picks:
        pick_direction = BehavioralLikelihoodDirection.NEUTRAL
        if acquired_picks > disposed_picks:
            if counterparty_profile.acquired_pick_count > counterparty_profile.disposed_pick_count:
                pick_direction = BehavioralLikelihoodDirection.ELEVATED
            elif counterparty_profile.disposed_pick_count > counterparty_profile.acquired_pick_count:
                pick_direction = BehavioralLikelihoodDirection.REDUCED
        elif disposed_picks > acquired_picks:
            if counterparty_profile.disposed_pick_count > counterparty_profile.acquired_pick_count:
                pick_direction = BehavioralLikelihoodDirection.ELEVATED
            elif counterparty_profile.acquired_pick_count > counterparty_profile.disposed_pick_count:
                pick_direction = BehavioralLikelihoodDirection.REDUCED
        drivers.append(
            BehavioralLikelihoodDriver(
                kind=BehavioralDriverKind.OWNER_HISTORY,
                direction=pick_direction,
                description=(
                    f"Their history shows {counterparty_profile.acquired_pick_count} pick acquisition(s) and "
                    f"{counterparty_profile.disposed_pick_count} pick disposal(s); this proposal has them "
                    f"acquiring {acquired_picks} pick(s) and sending {disposed_picks}."
                ),
                evidence_level=BehavioralEvidenceLevel.OBSERVED,
            )
        )

    acquired_positions = Counter(
        position
        for asset in acquired
        if isinstance(asset, PlayerAsset)
        for position in [_player_position(league_state, asset.player_id)]
        if position is not None
    )
    for position, count in sorted(acquired_positions.items()):
        prior_buys = counterparty_profile.acquired_positions.get(position, 0)
        prior_sells = counterparty_profile.disposed_positions.get(position, 0)
        position_direction = BehavioralLikelihoodDirection.NEUTRAL
        if prior_buys > prior_sells:
            position_direction = BehavioralLikelihoodDirection.ELEVATED
        elif prior_sells > prior_buys:
            position_direction = BehavioralLikelihoodDirection.REDUCED
        drivers.append(
            BehavioralLikelihoodDriver(
                kind=BehavioralDriverKind.ROSTER_CONSTRUCTION,
                direction=position_direction,
                description=(
                    f"The other owner would acquire {count} {position}(s). Historically they acquired "
                    f"{prior_buys} and disposed {prior_sells} at that position."
                ),
                evidence_level=BehavioralEvidenceLevel.OBSERVED,
            )
        )

    team_view = _current_team_view(runtime, counterparty_side.team_id)
    if team_view is not None and team_view.utility is not None:
        state = team_view.utility.calculated_competitive_state.value
        receives_players = any(isinstance(asset, PlayerAsset) for asset in acquired)
        receives_picks = any(isinstance(asset, PickAsset) for asset in acquired)
        sends_players = any(isinstance(asset, PlayerAsset) for asset in disposed)
        sends_picks = any(isinstance(asset, PickAsset) for asset in disposed)
        state_direction = BehavioralLikelihoodDirection.NEUTRAL
        explanation = f"Their current calculated competitive state is {state}."
        if state in {"contender", "competitive"} and receives_players and sends_picks:
            state_direction = BehavioralLikelihoodDirection.ELEVATED
            explanation += " The package exchanges future draft capital for current player production, which is directionally consistent with that state."
        elif state in {"developing", "rebuilding"} and receives_picks and sends_players:
            state_direction = BehavioralLikelihoodDirection.ELEVATED
            explanation += " The package exchanges current player production for future draft capital, which is directionally consistent with that state."
        elif state in {"contender", "competitive"} and receives_picks and sends_players:
            state_direction = BehavioralLikelihoodDirection.REDUCED
            explanation += " The package moves current player production out for future draft capital, which is directionally less consistent with that state."
        elif state in {"developing", "rebuilding"} and receives_players and sends_picks:
            state_direction = BehavioralLikelihoodDirection.REDUCED
            explanation += " The package spends future draft capital for current player production, which is directionally less consistent with that state."
        drivers.append(
            BehavioralLikelihoodDriver(
                kind=BehavioralDriverKind.COMPETITIVE_STATE,
                direction=state_direction,
                description=explanation,
                evidence_level=BehavioralEvidenceLevel.INFERRED,
            )
        )

    if focal_owner_id:
        prior_with_focal = counterparty_profile.counterparty_trade_counts.get(focal_owner_id, 0)
        if prior_with_focal:
            drivers.append(
                BehavioralLikelihoodDriver(
                    kind=BehavioralDriverKind.COUNTERPARTY_HISTORY,
                    direction=BehavioralLikelihoodDirection.ELEVATED,
                    description=f"These two owners have completed {prior_with_focal} prior trade(s) with each other.",
                    evidence_level=BehavioralEvidenceLevel.OBSERVED,
                )
            )

    directions = [driver.direction for driver in drivers]
    elevated = directions.count(BehavioralLikelihoodDirection.ELEVATED)
    reduced = directions.count(BehavioralLikelihoodDirection.REDUCED)
    if elevated and not reduced:
        overall = BehavioralLikelihoodDirection.ELEVATED
    elif reduced and not elevated:
        overall = BehavioralLikelihoodDirection.REDUCED
    else:
        overall = BehavioralLikelihoodDirection.NEUTRAL

    return BehavioralLikelihoodEstimate(
        owner_id=counterparty_profile.owner_id,
        as_of=proposal.as_of,
        evidence_level=BehavioralEvidenceLevel.INFERRED,
        direction=overall,
        drivers=tuple(drivers),
        observed_trade_count=counterparty_profile.trade_count,
        model_version=_MODEL_VERSION,
    )
