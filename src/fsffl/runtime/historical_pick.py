from __future__ import annotations

from datetime import datetime

from fsffl.state.draft_order_snapshot import HistoricalDraftOrderSnapshot
from fsffl.state.models import DraftPick, LeagueRules
from fsffl.team_utility.draft_order import DraftOrderSimulationResult
from fsffl.value.historical_pick import HistoricalSlotProbability
from fsffl.value.historical_pick_evidence import HistoricalTeamDraftSlotForecast


def build_slot_forecast_from_draft_order(
    *,
    pick: DraftPick,
    result: DraftOrderSimulationResult,
    league_rules: LeagueRules,
) -> HistoricalTeamDraftSlotForecast:
    """Translate Simulation-owned draft-order scenarios into Value evidence.

    Runtime/orchestration is the correct boundary for this adapter because it
    coordinates two authoritative layers without making either depend on the
    other. The adapter does not infer draft order, alter scenario probabilities,
    or calculate asset value. It only marginalizes the Simulation result for the
    pick's original team and preserves timestamp/version/provenance.
    """

    if pick.league_id != result.league_id:
        raise ValueError("draft-order result must describe the pick league")
    if pick.season != result.draft_season:
        raise ValueError("draft-order result must describe the pick draft season")
    if pick.round > league_rules.rookie_draft_rounds:
        raise ValueError("pick is outside the configured rookie draft")

    distribution = result.slot_distribution_for_team(
        pick.original_team_id,
        league_rules=league_rules,
    )
    probabilities = tuple(
        HistoricalSlotProbability(
            slot_in_round=slot,
            probability=probability,
            evidence_as_of=result.as_of,
            model_version=f"{result.model_version}+{result.rule_policy_version}",
            provenance=result.provenance,
        )
        for slot, probability in distribution
        if probability > 0
    )

    return HistoricalTeamDraftSlotForecast(
        pick_id=pick.pick_id,
        as_of=result.as_of,
        probabilities=probabilities,
    )


def exact_slot_from_historical_snapshot(
    *,
    pick: DraftPick,
    snapshot: HistoricalDraftOrderSnapshot,
    league_rules: LeagueRules,
    as_of: datetime,
) -> tuple[int, datetime]:
    """Expose an exact PIT slot only when State proves it was already knowable.

    The returned timestamp is intended for ``exact_slot_known_at`` on
    ``HistoricalPickCoordinateEvidence``. Runtime performs only identity and
    time-boundary validation; it does not infer draft order or asset value.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if pick.league_id != snapshot.league_id:
        raise ValueError("historical draft-order snapshot must describe the pick league")
    if pick.season != snapshot.draft_season:
        raise ValueError("historical draft-order snapshot must describe the pick draft season")
    if pick.round > league_rules.rookie_draft_rounds:
        raise ValueError("pick is outside the configured rookie draft")
    if snapshot.available_at > as_of:
        raise ValueError("historical draft-order snapshot was not knowable at requested as_of")

    return (
        snapshot.exact_slot_for_team(pick.original_team_id, league_rules=league_rules),
        snapshot.available_at,
    )
