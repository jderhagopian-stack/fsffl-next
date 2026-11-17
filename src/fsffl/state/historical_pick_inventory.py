"""Retrospective draft-right inventory; no valuation or canonical-State promotion.

Allotments and their scope are caller-evidenced facts. Transfers reuse the
accepted atomic replay primitive. Missing issuance/use dates remain unknown.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Literal

from .historical_roster_replay import DraftPickTransfer, reverse_draft_pick_transfer_batch


def _aware(value: datetime | None) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("pick evidence dates must be timezone-aware")


def _window(lower: datetime | None, upper: datetime | None) -> None:
    _aware(lower)
    _aware(upper)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("pick evidence date bounds are reversed")


@dataclass(frozen=True)
class HistoricalPickRight:
    pick_id: str
    draft_season: int
    round: int
    original_team_id: str
    source_ref: str
    issued_not_before: datetime | None = None
    issued_by: datetime | None = None

    def __post_init__(self) -> None:
        if not all(x.strip() for x in (self.pick_id, self.original_team_id, self.source_ref)):
            raise ValueError("pick identity, original team and allotment source are required")
        if self.round < 1 or self.draft_season < 1900:
            raise ValueError("invalid draft season/round")
        _window(self.issued_not_before, self.issued_by)


@dataclass(frozen=True)
class HistoricalPickUse:
    pick_id: str
    owner_team_id: str
    source_ref: str
    not_before: datetime | None
    by: datetime | None
    kind: Literal["selection", "expiry"] = "selection"

    def __post_init__(self) -> None:
        if not all(x.strip() for x in (self.pick_id, self.owner_team_id, self.source_ref)):
            raise ValueError("pick use needs identity, owner and source")
        if self.kind not in ("selection", "expiry"):
            raise ValueError("unsupported pick-use kind")
        _window(self.not_before, self.by)


@dataclass(frozen=True)
class HistoricalPickTransferEvent:
    event_id: str
    effective_at: datetime
    transfers: tuple[DraftPickTransfer, ...]
    source_ref: str

    def __post_init__(self) -> None:
        _aware(self.effective_at)
        if self.effective_at is None or not self.event_id.strip() or not self.source_ref.strip() or not self.transfers:
            raise ValueError("pick transfer needs identity, time, source and movements")


@dataclass(frozen=True)
class HistoricalPickAtCutoff:
    pick_id: str
    status: Literal["not_issued", "outstanding", "used", "unknown", "conflict"]
    owner_team_id: str | None


@dataclass(frozen=True)
class HistoricalPickInventorySnapshot:
    inventory_id: str
    cutoff: datetime
    boundary: Literal["before", "after"]
    picks: tuple[HistoricalPickAtCutoff, ...]
    issues: tuple[str, ...]
    complete_for_declared_seasons: bool
    declared_draft_seasons: tuple[int, ...]
    transfer_ledger_complete: bool
    use_ledger_complete: bool
    eligible_for_pit_decision_grade: Literal[False] = False

    @property
    def known_outstanding_owners(self) -> tuple[tuple[str, str], ...]:
        if not self.transfer_ledger_complete:
            return ()
        return tuple((p.pick_id, p.owner_team_id) for p in self.picks
                     if p.status == "outstanding" and p.owner_team_id is not None)


@dataclass(frozen=True)
class HistoricalPickInventory:
    inventory_id: str
    team_ids: tuple[str, ...]
    rights: tuple[HistoricalPickRight, ...]
    events: tuple[HistoricalPickTransferEvent, ...]
    uses: tuple[HistoricalPickUse, ...]
    declared_draft_seasons: tuple[int, ...]
    scope_source_ref: str
    transfer_ledger_complete: bool = False
    issues: tuple[str, ...] = ()
    uncertain_pick_ids: tuple[str, ...] = ()
    use_ledger_complete: bool = False
    eligible_for_pit_decision_grade: Literal[False] = False

    def at(self, cutoff: datetime, *, boundary: Literal["before", "after"] = "after") -> HistoricalPickInventorySnapshot:
        """Query one declared universe; unrelated future years are not certified."""
        _aware(cutoff)
        if cutoff is None or boundary not in ("before", "after"):
            raise ValueError("invalid cutoff boundary")
        reached = lambda t: t is not None and (t < cutoff or (t == cutoff and boundary == "after"))
        rights = {p.pick_id: p for p in self.rights}
        uses = {p.pick_id: p for p in self.uses}
        owners = {p.pick_id: p.original_team_id for p in self.rights}
        bad: set[str] = set()
        issues = set(self.issues)
        issued_by = {p.pick_id: p.issued_by for p in self.rights}
        # An observed transfer proves existence no later than that transfer, even
        # when the original issuance date is missing. Never infer a 3-year window.
        for event in self.events:
            for move in event.transfers:
                old = issued_by.get(move.pick_id)
                if old is None or event.effective_at < old:
                    issued_by[move.pick_id] = event.effective_at
        grouped: dict[datetime, list[DraftPickTransfer]] = {}
        for event in self.events:
            if reached(event.effective_at):
                grouped.setdefault(event.effective_at, []).extend(event.transfers)
        for at, batch in sorted(grouped.items()):
            touched = {m.pick_id for m in batch}
            for move in batch:
                right = rights.get(move.pick_id)
                use = uses.get(move.pick_id)
                if (right is None or move.pick_id in bad
                        or (right.issued_not_before is not None and at < right.issued_not_before)
                        or (use is not None and use.by is not None and at >= use.by)):
                    issues.add("transfer_outside_known_outstanding_window")
                    bad.update(touched)
            # The accepted reverse operator applied to inverse edges is the
            # forward atomic operator; its ownership and tie checks stay shared.
            inverse = tuple(DraftPickTransfer(m.pick_id, m.to_team_id, m.from_team_id) for m in batch)
            if touched & bad:
                continue
            failures = reverse_draft_pick_transfer_batch(owners, {t: set() for t in self.team_ids}, inverse)
            if failures:
                issues.update(failures)
                bad.update(touched)
        rows = []
        for right in self.rights:
            pid = right.pick_id
            use = uses.get(pid)
            status = "unknown"
            if pid in bad:
                status = "conflict"
            elif pid in self.uncertain_pick_ids:
                status = "unknown"
            elif use is not None and reached(use.by):
                status = "used"
                if self.transfer_ledger_complete and owners[pid] != use.owner_team_id:
                    status = "conflict"
                    issues.add("pick_use_owner_mismatch")
            elif right.issued_not_before is not None and not reached(right.issued_not_before):
                status = "not_issued"
            elif reached(issued_by[pid]):
                if ((use is None and self.use_ledger_complete)
                        or (use is not None and use.not_before is not None and not reached(use.not_before))):
                    status = "outstanding"
            rows.append(HistoricalPickAtCutoff(pid, status, owners[pid] if status == "outstanding" else None))
        complete = (self.transfer_ledger_complete and self.use_ledger_complete and not issues
                    and all(p.status in ("not_issued", "outstanding", "used") for p in rows))
        return HistoricalPickInventorySnapshot(self.inventory_id, cutoff, boundary, tuple(rows),
            tuple(sorted(issues)), complete, self.declared_draft_seasons, self.transfer_ledger_complete,
            self.use_ledger_complete)


def build_historical_pick_inventory(*, team_ids: tuple[str, ...], rights: tuple[HistoricalPickRight, ...],
        events: tuple[HistoricalPickTransferEvent, ...], uses: tuple[HistoricalPickUse, ...],
        declared_draft_seasons: tuple[int, ...], scope_source_ref: str,
        transfer_ledger_complete: bool = False, issues: tuple[str, ...] = (),
        uncertain_pick_ids: tuple[str, ...] = (), use_ledger_complete: bool = False) -> HistoricalPickInventory:
    """Construct once from explicitly enumerated allotments and a scoped ledger."""
    if not scope_source_ref.strip() or not declared_draft_seasons or len(team_ids) != len(set(team_ids)):
        raise ValueError("unique team identities, declared seasons and universe evidence are required")
    if len(team_ids) < 2 or any(not t.strip() for t in team_ids):
        raise ValueError("at least two nonblank team identities are required")
    if len({p.pick_id for p in rights}) != len(rights) or len({p.pick_id for p in uses}) != len(uses):
        raise ValueError("duplicate pick allotment or use")
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("duplicate pick transfer event")
    by_id = {p.pick_id: p for p in rights}
    if any(p.original_team_id not in team_ids or p.draft_season not in declared_draft_seasons for p in rights):
        raise ValueError("allotment outside declared team/season scope")
    if any(p.pick_id not in by_id or p.owner_team_id not in team_ids for p in uses):
        raise ValueError("use outside declared inventory")
    if any(pid not in by_id for pid in uncertain_pick_ids):
        raise ValueError("unknown pick uncertainty reference")
    for use in uses:
        lower = by_id[use.pick_id].issued_not_before
        if lower is not None and use.by is not None and use.by < lower:
            raise ValueError("pick consumed before issuance bounds")
    ordered = (tuple(sorted(rights, key=lambda p: p.pick_id)),
               tuple(sorted(events, key=lambda e: (e.effective_at, e.event_id))),
               tuple(sorted(uses, key=lambda p: p.pick_id)))
    payload = {"version": "historical-pick-inventory-v1", "teams": sorted(team_ids),
        "rights": [asdict(p) for p in ordered[0]], "events": [asdict(e) for e in ordered[1]],
        "uses": [asdict(p) for p in ordered[2]], "seasons": sorted(set(declared_draft_seasons)),
        "scope_source_ref": scope_source_ref, "ledger_complete": transfer_ledger_complete,
        "issues": sorted(set(issues)), "uncertain_pick_ids": sorted(set(uncertain_pick_ids)),
        "use_ledger_complete": use_ledger_complete}
    identity = "hpi_" + sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return HistoricalPickInventory(identity, tuple(sorted(team_ids)), *ordered,
        tuple(sorted(set(declared_draft_seasons))), scope_source_ref, transfer_ledger_complete,
        tuple(sorted(set(issues))), tuple(sorted(set(uncertain_pick_ids))), use_ledger_complete)


def enumerate_round_pick_allotment(*, draft_season: int, rounds: int, original_team_ids: tuple[str, ...],
        source_ref: str, issued_not_before: datetime | None = None,
        issued_by: datetime | None = None) -> tuple[HistoricalPickRight, ...]:
    """Explicit regular allotment, independent of draft order or a future-year window.

    Caller supplies evidenced season/round/team rules; exceptions or non-round
    mechanisms supply individual rights instead. This does not infer issuance.
    """
    if type(rounds) is not int or rounds < 1 or len(original_team_ids) < 2:
        raise ValueError("rounds and original team allotment are required")
    if len(set(original_team_ids)) != len(original_team_ids):
        raise ValueError("duplicate original team allotment")
    return tuple(HistoricalPickRight(f"{draft_season}:{rnd}:{team}", draft_season, rnd, team,
        source_ref, issued_not_before, issued_by)
        for rnd in range(1, rounds+1) for team in sorted(original_team_ids))
