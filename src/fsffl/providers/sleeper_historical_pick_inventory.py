"""Offline adapters for archived Sleeper draft rights and completed transfers.

Draft purpose, historical roster identity and original issuance are explicit
inputs. Source draft selections establish use, not historical market forecasts.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any

from fsffl.state.historical_pick_inventory import (
    HistoricalPickInventory, HistoricalPickRight, HistoricalPickTransferEvent,
    HistoricalPickUse, build_historical_pick_inventory,
    enumerate_round_pick_allotment,
)
from fsffl.state.historical_roster_replay import DraftPickTransfer


def _ms(value: object) -> datetime | None:
    if type(value) not in (int, float) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def _pick_id(row: Mapping[str, Any]) -> str:
    return f"{int(row['season'])}:{int(row['round'])}:{row['roster_id']}"


def sleeper_linear_draft_allotment(season_data: Mapping[str, Any], *, draft_id: str,
        purpose: str, purpose_source_ref: str, roster_identity_source_ref: str,
        issued_not_before: datetime | None = None, issued_by: datetime | None = None,
        ) -> tuple[tuple[HistoricalPickRight, ...], dict[tuple[str, int, int], str]]:
    """Enumerate one evidenced ordinary linear rookie draft, including untraded rights.

    Other draft mechanisms can supply explicit rights/bindings to the normalizer.
    Neither round count nor draft shape is used to guess startup versus rookie.
    """
    if purpose != "rookie" or not purpose_source_ref.strip() or not roster_identity_source_ref.strip():
        raise ValueError("explicit rookie purpose and historical roster identity evidence required")
    matches = [e for e in season_data.get("drafts", ())
               if str((e.get("draft") or {}).get("draft_id")) == draft_id]
    if len(matches) != 1:
        raise ValueError("draft identity must match exactly one archived record")
    draft = matches[0]["draft"]
    if draft.get("type") != "linear":
        raise ValueError("nonlinear draft needs explicit allotments and bindings")
    rounds = (draft.get("settings") or {}).get("rounds")
    teams = (draft.get("settings") or {}).get("teams")
    if type(rounds) is not int or rounds < 1 or type(teams) is not int or teams < 2:
        raise ValueError("draft team/round settings required")
    rosters = season_data.get("rosters", ())
    user_to_roster = {str(r["owner_id"]): str(r["roster_id"]) for r in rosters
                      if r.get("owner_id") is not None and r.get("roster_id") is not None}
    order = draft.get("draft_order") or {}
    if (len(rosters) != teams or len(user_to_roster) != teams or len(order) != teams
            or len(set(user_to_roster.values())) != teams):
        raise ValueError("draft requires a complete historical original-roster crosswalk")
    if any(str(user) not in user_to_roster for user in order):
        raise ValueError("draft original-owner mapping is unavailable")
    try:
        slot_to_roster = {int(slot): user_to_roster[str(user)] for user, slot in order.items()}
        season = int(draft["season"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("draft season/slot evidence is invalid") from None
    if set(slot_to_roster) != set(range(1, teams + 1)):
        raise ValueError("draft original slots must be a complete unique permutation")
    source = f"{purpose_source_ref};{roster_identity_source_ref}"
    rights = enumerate_round_pick_allotment(draft_season=season, rounds=rounds,
        original_team_ids=tuple(slot_to_roster.values()), source_ref=source,
        issued_not_before=issued_not_before, issued_by=issued_by)
    bindings = {}
    for rnd in range(1, rounds + 1):
        for slot, original in sorted(slot_to_roster.items()):
            pid = f"{season}:{rnd}:{original}"
            bindings[(draft_id, rnd, slot)] = pid
    return tuple(rights), bindings


def normalize_sleeper_historical_pick_inventory(season_data: Mapping[str, Any], *,
        rights: tuple[HistoricalPickRight, ...], draft_pick_bindings: Mapping[tuple[str, int, int], str],
        declared_draft_seasons: tuple[int, ...], scope_source_ref: str,
        source_revision: str, source_observed_at: datetime,
        transfer_ledger_complete: bool = False, use_ledger_complete: bool = False,
        allotment_complete: bool = False) -> HistoricalPickInventory:
    """Normalize already collected source rows; no API reads, writes or valuation.

    Every selection in a declared draft year must be bound or explicitly remains
    a coverage issue. Per-selection timestamps are not fabricated from draft order.
    """
    if not source_revision.strip() or source_observed_at.tzinfo is None or source_observed_at.utcoffset() is None:
        raise ValueError("source revision and aware source observation time are required")
    source_hash = sha256(json.dumps(season_data, sort_keys=True, default=str).encode()).hexdigest()
    source = f"{source_revision}:sha256:{source_hash}"
    team_ids = tuple(str(r["roster_id"]) for r in season_data.get("rosters", ()))
    by_id = {p.pick_id: p for p in rights}
    events = []
    uses = []
    issues: set[str] = set()
    uncertain: set[str] = set()
    seen: set[str] = set()
    for tx in season_data.get("transactions", ()):
        if tx.get("status") != "complete":
            continue
        moves = []
        for row in tx.get("draft_picks") or ():
            try:
                if int(row["season"]) not in declared_draft_seasons:
                    continue
                pid = _pick_id(row)
                if pid not in by_id:
                    issues.add("transferred_pick_missing_from_declared_inventory")
                    continue
                moves.append(DraftPickTransfer(pid, str(row["previous_owner_id"]), str(row["owner_id"])))
            except (KeyError, TypeError, ValueError):
                issues.add("malformed_pick_transfer")
        if not moves:
            continue
        tid = str(tx.get("transaction_id") or "")
        at = _ms(tx.get("status_updated"))
        created = _ms(tx.get("created"))
        if not tid or tid in seen or at is None or created is None or created > at or at > source_observed_at:
            issues.add("missing_or_conflicting_pick_transfer_identity_clock")
            continue
        seen.add(tid)
        events.append(HistoricalPickTransferEvent(tid, at, tuple(moves), source))
    used: set[str] = set()
    transfer_issues = set(issues)
    seen_drafts: set[str] = set()
    for entry in season_data.get("drafts", ()):
        draft = entry.get("draft") or {}
        try:
            if int(draft["season"]) not in declared_draft_seasons:
                continue
        except (KeyError, TypeError, ValueError):
            issues.add("draft_season_unavailable")
            continue
        did = str(draft.get("draft_id") or "")
        if not did or did in seen_drafts:
            issues.add("missing_or_duplicate_draft_identity")
            continue
        seen_drafts.add(did)
        lower = _ms(draft.get("start_time"))
        # last_picked bounds all retained selections, not each individual pick.
        upper = _ms(draft.get("last_picked")) or source_observed_at
        if upper > source_observed_at or (lower is not None and lower > upper):
            issues.add("conflicting_draft_use_window")
            uncertain.update(pid for key, pid in draft_pick_bindings.items() if key[0] == did)
            continue
        seen_keys: set[tuple[str, int, int]] = set()
        for pick in entry.get("picks") or ():
            try:
                key = (did, int(pick["round"]), int(pick["draft_slot"]))
                pid = draft_pick_bindings.get(key)
                owner = str(pick["roster_id"])
                if pid is None or pid not in by_id:
                    issues.add("draft_selection_missing_original_pick_binding")
                    continue
                if pid in used or owner not in team_ids:
                    issues.add("duplicate_selection_or_unknown_drafting_roster")
                    uncertain.add(pid)
                    continue
                uses.append(HistoricalPickUse(pid, owner, source, lower, upper))
                used.add(pid)
                seen_keys.add(key)
            except (KeyError, TypeError, ValueError):
                issues.add("malformed_draft_selection")
        if draft.get("status") == "complete":
            missing = {pid for key, pid in draft_pick_bindings.items() if key[0] == did and key not in seen_keys}
            if missing:
                issues.add("completed_draft_selection_coverage_incomplete")
                uncertain.update(missing)
    return build_historical_pick_inventory(team_ids=team_ids, rights=rights, events=tuple(events), uses=tuple(uses),
        declared_draft_seasons=declared_draft_seasons, scope_source_ref=f"{scope_source_ref};{source}",
        coverage_through=source_observed_at,
        transfer_ledger_complete=transfer_ledger_complete and not transfer_issues, issues=tuple(sorted(issues)),
        uncertain_pick_ids=tuple(sorted(uncertain)),
        use_ledger_complete=use_ledger_complete and not (issues-transfer_issues), allotment_complete=allotment_complete)


def inspect_sleeper_draft_pick_coverage(season_data: Mapping[str, Any]) -> dict[str, int]:
    """Sanitized source inventory only; no manager/player/pick identities or values."""
    drafts = season_data.get("drafts") or ()
    selections = [p for e in drafts for p in (e.get("picks") or ())]
    return {"draft_records": len(drafts), "selection_records": len(selections),
        "linear_draft_records": sum((e.get("draft") or {}).get("type") == "linear" for e in drafts),
        "complete_draft_records": sum((e.get("draft") or {}).get("status") == "complete" for e in drafts),
        "drafts_with_selection_records": sum(bool(e.get("picks")) for e in drafts),
        "drafts_with_start_and_last_pick": sum(_ms((e.get("draft") or {}).get("start_time")) is not None
            and _ms((e.get("draft") or {}).get("last_picked")) is not None for e in drafts),
        "selections_with_round_slot_roster": sum(all(p.get(k) is not None for k in ("round", "draft_slot", "roster_id"))
            for p in selections)}
