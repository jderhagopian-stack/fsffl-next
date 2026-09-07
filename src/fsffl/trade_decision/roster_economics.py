from __future__ import annotations

from enum import StrEnum

from fsffl.state.models import FrozenModel

from .economic_net import BilateralTradeEconomicNet, EconomicNetStatus
from .roster_legality import TeamRosterLegalityResolution


class RosterAdjustedEconomicStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class RosterAdjustedMarketDelta(FrozenModel):
    team_id: str
    raw_trade_market_delta: float | None = None
    mandatory_cut_market_cost: float | None = None
    roster_adjusted_market_delta: float | None = None
    required_cut_count: int = 0
    cut_player_ids: tuple[str, ...] = ()
    status: RosterAdjustedEconomicStatus
    model_version: str = "next5-roster-adjusted-market-net-v1"


class BilateralRosterAdjustedMarketNet(FrozenModel):
    proposal_id: str
    side_a: RosterAdjustedMarketDelta
    side_b: RosterAdjustedMarketDelta
    model_version: str = "next5-bilateral-roster-adjusted-market-net-v1"


def _adjust_side(net, resolution: TeamRosterLegalityResolution) -> RosterAdjustedMarketDelta:
    raw = net.market.mean_delta if net.market.status == EconomicNetStatus.COMPLETE else None
    cut_cost = resolution.cut_market_value_total
    complete = raw is not None and (resolution.required_cut_count == 0 or cut_cost is not None)
    adjusted = None
    if complete:
        adjusted = raw - (cut_cost or 0.0)
    return RosterAdjustedMarketDelta(
        team_id=net.team_id,
        raw_trade_market_delta=raw,
        mandatory_cut_market_cost=(0.0 if resolution.required_cut_count == 0 else cut_cost),
        roster_adjusted_market_delta=adjusted,
        required_cut_count=resolution.required_cut_count,
        cut_player_ids=tuple(cut.player_id for cut in resolution.cuts),
        status=(
            RosterAdjustedEconomicStatus.COMPLETE
            if complete
            else RosterAdjustedEconomicStatus.INCOMPLETE
        ),
    )


def adjust_bilateral_market_net_for_mandatory_cuts(
    economic_net: BilateralTradeEconomicNet,
    resolutions: tuple[TeamRosterLegalityResolution, ...],
) -> BilateralRosterAdjustedMarketNet:
    """Charge the opportunity cost of required roster cuts exactly once.

    Raw trade economics remain untouched. This Decision-layer view subtracts only
    authoritative market Value actually discarded to make the post-trade active
    roster legal. Missing cut Value fails closed rather than treating roster slots
    as free or fabricating a replacement-cost coefficient.
    """

    by_team = {item.team_id: item for item in resolutions}
    if economic_net.side_a.team_id not in by_team or economic_net.side_b.team_id not in by_team:
        raise ValueError("roster resolutions must cover both trade teams")
    return BilateralRosterAdjustedMarketNet(
        proposal_id=economic_net.proposal_id,
        side_a=_adjust_side(economic_net.side_a, by_team[economic_net.side_a.team_id]),
        side_b=_adjust_side(economic_net.side_b, by_team[economic_net.side_b.team_id]),
    )
