"""Horizon-preserving asset accounting; not franchise utility or a recommendation."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from fsffl.state.models import FrozenModel
from fsffl.value.models import ValueScale

from .economic_net import BilateralTradeEconomicNet, EconomicNetStatus
from .roster_legality import TeamRosterLegalityResolution


class RosterAdjustedIntrinsicDelta(FrozenModel):
    team_id: str
    scale: ValueScale | None = None
    raw_trade_intrinsic_delta: float | None = None
    mandatory_cut_intrinsic_cost: float | None = None
    roster_adjusted_intrinsic_delta: float | None = None
    cut_player_ids: tuple[str, ...] = ()
    missing_cut_player_ids: tuple[str, ...] = ()
    status: EconomicNetStatus


class BilateralRosterAdjustedIntrinsicNet(FrozenModel):
    proposal_id: str
    side_a: RosterAdjustedIntrinsicDelta
    side_b: RosterAdjustedIntrinsicDelta
    model_version: str = "next5-roster-adjusted-intrinsic-net-v1"


def adjust_bilateral_intrinsic_net_for_mandatory_cuts(
    economic_net: BilateralTradeEconomicNet,
    resolutions: tuple[TeamRosterLegalityResolution, ...],
    *,
    cut_values: Mapping[str, float],
    scale: ValueScale,
) -> BilateralRosterAdjustedIntrinsicNet:
    """Subtract only authoritative required cuts, in the identical native scale.

    The caller binds cut values to the same source/State/horizon as ``scale``.
    Missing or non-finite values withhold the adjusted total. Signed values are
    preserved. No Market cost, display index or replacement premium is used.
    """
    teams = {economic_net.side_a.team_id, economic_net.side_b.team_id}
    if len(resolutions) != 2 or {r.team_id for r in resolutions} != teams:
        raise ValueError("roster resolutions must cover both trade teams exactly once")
    by_team = {r.team_id: r for r in resolutions}
    seen: set[str] = set()
    for resolution in resolutions:
        ids = tuple(c.player_id for c in resolution.cuts)
        if resolution.required_cut_count < 0 or len(ids) != resolution.required_cut_count:
            raise ValueError("required cut count must match actual cuts")
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("mandatory cuts must identify distinct players")
        seen.update(ids)

    def adjust(side):
        net = side.intrinsic
        if net.scale is not None and net.scale != scale:
            raise ValueError("cut values and trade economics must share a native scale")
        ids = tuple(c.player_id for c in by_team[side.team_id].cuts)
        missing = tuple(pid for pid in ids if pid not in cut_values or not isfinite(cut_values[pid]))
        cost = None if missing else sum(cut_values[pid] for pid in ids)
        if cost is not None and not isfinite(cost):
            cost = None
        raw = net.mean_delta if net.status == EconomicNetStatus.COMPLETE else None
        if raw is not None and not isfinite(raw):
            raw = None
        adjusted = raw - cost if raw is not None and cost is not None else None
        if adjusted is not None and not isfinite(adjusted):
            adjusted = None
        return RosterAdjustedIntrinsicDelta(
            team_id=side.team_id, scale=scale,
            raw_trade_intrinsic_delta=raw, mandatory_cut_intrinsic_cost=cost,
            roster_adjusted_intrinsic_delta=adjusted,
            cut_player_ids=ids, missing_cut_player_ids=missing,
            status=EconomicNetStatus.COMPLETE if adjusted is not None else EconomicNetStatus.INCOMPLETE,
        )

    return BilateralRosterAdjustedIntrinsicNet(
        proposal_id=economic_net.proposal_id,
        side_a=adjust(economic_net.side_a), side_b=adjust(economic_net.side_b),
    )
