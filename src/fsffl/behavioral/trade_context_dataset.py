"""Trade-only input validation for the existing context-controlled research model.

This does not estimate preferences, fit parameters, or change live Search. No
known intervening activity is a consistency screen, not proof of a complete
historical ledger or unchanged IR/taxi assignments.
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence

from fsffl.state.history import InMemorySnapshotStore, StateSnapshotStore
from fsffl.state.models import LeagueState
from .action_context import reconstruct_behavioral_action_context
from .context_dataset import (BehavioralContextCalibrationDataset, BehavioralContextCalibrationRow,
    BehavioralContextCoverageIssue, _asset_outcomes)
from .models import BehavioralAssetKind, BehavioralEventKind, OwnerBehaviorEvent


TRADE_CONTEXT_DATASET_VERSION = 'behavioral-trade-context-dataset-v1:known-history-checked'


def trade_context_integrity_issues(event: OwnerBehaviorEvent, *, state: LeagueState,
        team_id: str, known_intervening_activity: bool,
        player_id_by_asset_ref: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Check ownership and recorded-position consistency without inventing context.

    Provider-specific asset references require an explicit mapping when they do
    not already equal canonical player IDs. Unknown identities are not assumed
    unowned. Picks/FAAB and unrecorded roster-slot changes are not certified here.
    """
    issues = []
    if event.kind != BehavioralEventKind.TRADE:
        issues.append('not a completed trade event')
    if state.as_of >= event.occurred_at:
        issues.append('snapshot is not strictly pre-action')
    if known_intervening_activity:
        issues.append('recorded league activity after snapshot requires context reconciliation')
    team = next((t for t in state.team_states if t.team_id == team_id), None)
    if team is None:
        return tuple(issues + ['team is absent from historical snapshot'])
    roster = {r.player_id for r in team.roster}
    players = {p.player_id:p for p in state.players}
    for direction, assets in (('acquired',event.acquired),('disposed',event.disposed)):
        for asset in assets:
            if asset.kind != BehavioralAssetKind.PLAYER:
                continue
            pid = (player_id_by_asset_ref or {}).get(asset.asset_ref,asset.asset_ref)
            if pid not in players:
                issues.append('player identity is unavailable in historical snapshot')
                continue
            if direction == 'disposed' and pid not in roster:
                issues.append('disposed player is absent from the historical owner roster')
            if direction == 'acquired' and pid in roster:
                issues.append('acquired player is already on the historical owner roster')
            if direction == 'acquired' and asset.position is None:
                issues.append('acquired player position is unavailable for the trade outcome')
            if asset.position and asset.position != players[pid].position.value:
                issues.append('recorded player position differs from historical snapshot')
    return tuple(dict.fromkeys(issues))


def build_trade_context_calibration_dataset(events: Sequence[OwnerBehaviorEvent], *,
        snapshots: StateSnapshotStore, league_id_by_event: Mapping[str,str],
        team_id_by_event: Mapping[str,str],
        player_id_by_asset_ref: Mapping[str,str] | None = None) -> BehavioralContextCalibrationDataset:
    """Reuse native pre-action context/outcome extraction with trade-only guards.

    Supply all known completed transaction kinds: waiver/free-agent activity is
    excluded from trade outcomes but still checks whether a snapshot is stale.
    One injected-store lookup per trade; no extra database reads for validation.
    Keep this offline until historical coverage and a versioned policy are validated.
    """
    ordered = sorted(events,key=lambda e:(e.occurred_at,e.event_id))
    if len({e.event_id for e in ordered}) != len(ordered):
        raise ValueError('trade context dataset requires unique event ids')
    times = defaultdict(list)
    for event in ordered:
        times[(event.league_family_id,event.league_external_id)].append(event.occurred_at)
    rows = []; unavailable = []
    trades = [e for e in ordered if e.kind == BehavioralEventKind.TRADE]
    for event in trades:
        def reject(reason):
            unavailable.append(BehavioralContextCoverageIssue(event_id=event.event_id,reason=reason))
        league_id = league_id_by_event.get(event.event_id)
        team_id = team_id_by_event.get(event.event_id)
        if not league_id or not team_id:
            reject('missing canonical league/team identity mapping');continue
        state = snapshots.latest_at_or_before(league_id,event.occurred_at)
        # Reuse the accepted reconstruction, retaining the exact original State.
        result = reconstruct_behavioral_action_context(event,league_id=league_id,team_id=team_id,
            snapshots=InMemorySnapshotStore((state,)) if state is not None else InMemorySnapshotStore())
        if result.context is None:
            reject(result.unavailable_reason or 'historical context unavailable');continue
        history = times[(event.league_family_id,event.league_external_id)]
        intervening = bisect_left(history,event.occurred_at) > bisect_right(history,state.as_of)
        issues = trade_context_integrity_issues(event,state=state,team_id=team_id,
            known_intervening_activity=intervening,player_id_by_asset_ref=player_id_by_asset_ref)
        if issues:
            reject('; '.join(issues));continue
        acquired,disposed,buys,sells,faab_in,faab_out = _asset_outcomes(event)
        rows.append(BehavioralContextCalibrationRow(event_id=event.event_id,owner_id=event.owner_id,
            season=event.season,occurred_at=event.occurred_at,event_kind=event.kind.value,
            acquired_position_counts=acquired,disposed_position_counts=disposed,
            acquired_pick_count=buys,disposed_pick_count=sells,acquired_faab=faab_in,disposed_faab=faab_out,
            context=result.context))
    return BehavioralContextCalibrationDataset(rows=tuple(rows),unavailable=tuple(unavailable),
        total_event_count=len(trades),usable_event_count=len(rows),
        coverage_rate=len(rows)/len(trades) if trades else 0.,model_version=TRADE_CONTEXT_DATASET_VERSION)
