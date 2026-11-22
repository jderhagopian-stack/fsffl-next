"""Normalize explicitly identified completed draft allocations; never infer purpose."""
from collections.abc import Mapping
from datetime import datetime
import json
from fsffl.state.historical_draft_allocation import HistoricalDraftPlayerAllocation
from fsffl.state.historical_roster_context import _digest
from fsffl.state.historical_roster_replay import PlayerTransfer
from .sleeper_historical_pick_inventory import _ms


def normalize_sleeper_draft_player_allocation(season_data: Mapping, *, draft_id: str,
        purpose_source_ref: str, roster_identity_source_ref: str,
        source_revision: str, source_observed_at: datetime,
        expected_selection_keys: frozenset[tuple[int, int]] | None = None) -> HistoricalDraftPlayerAllocation | None:
    if not all(s.strip() for s in (draft_id, purpose_source_ref, roster_identity_source_ref, source_revision)):
        raise ValueError('admitted draft purpose, roster identity and source required')
    rows = [d for d in season_data.get('drafts', ())
            if str((d.get('draft') or {}).get('draft_id')) == draft_id]
    if len(rows) != 1:
        raise ValueError('draft must identify exactly one source record')
    raw = rows[0]; draft = raw['draft']
    if draft.get('status') != 'complete' and not raw.get('picks'):
        return None  # Rights can exist before any player has been selected.
    lo = _ms(draft.get('start_time'))
    hi = _ms(draft.get('last_picked')) or source_observed_at
    teams = {str(r['roster_id']) for r in season_data.get('rosters', ())}
    picks = raw.get('picks')
    if picks is None:
        picks = []
    if not isinstance(picks, list):
        raise ValueError('malformed recorded draft selections')
    moves = []; complete = bool(picks) and expected_selection_keys is not None and draft.get('status') == 'complete'
    observed_keys = set(); selected_player_ids = set()
    for p in picks:
        if not isinstance(p, Mapping):
            raise ValueError('malformed draft selection')
        key = (p.get('round'), p.get('draft_slot'))
        if any(type(v) is not int or v < 1 for v in key) or key in observed_keys:
            complete = False
        else:
            observed_keys.add(key)
        pid = p.get('player_id') or (p.get('metadata') or {}).get('player_id')
        owner = str(p.get('roster_id'))
        if pid is None or not str(pid).strip() or owner not in teams:
            complete = False
            continue
        if str(pid) in selected_player_ids:
            raise ValueError('draft allocations require unique selected players')
        selected_player_ids.add(str(pid))
        keeper = p.get('is_keeper')
        if keeper is not None and type(keeper) is not bool:
            complete = False
            continue
        if keeper is True:
            continue  # Explicit retention is not a new acquisition.
        moves.append(PlayerTransfer(str(pid), None, owner))
    if expected_selection_keys is not None and observed_keys != set(expected_selection_keys):
        complete = False
    league = season_data['league']
    return HistoricalDraftPlayerAllocation(draft_id, str(league['league_id']), int(league['season']),
        lo, hi, source_observed_at, _digest(season_data),
        json.dumps((source_revision, purpose_source_ref, roster_identity_source_ref)), tuple(moves), complete)
