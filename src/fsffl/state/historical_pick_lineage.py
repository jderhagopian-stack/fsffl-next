"""Join normalized inventories through explicit season/franchise crosswalks.

This composes accepted lineage and pick replay. It does not infer continuity
from names, manager IDs or equal provider roster numbers, or certify partial
transaction scans merely because several years have been joined.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json

from .historical_coverage import HistoricalSeasonIdentity
from .historical_pick_inventory import (
    HistoricalPickInventory, HistoricalPickRight, HistoricalPickUse,
    HistoricalPickTransferEvent, build_historical_pick_inventory,
)
from .historical_roster_replay import DraftPickTransfer
from .historical_season_lineage import HistoricalSeasonLineage, HistoricalSeasonSource, build_historical_season_lineage


@dataclass(frozen=True)
class HistoricalSeasonPickInventory:
    season: HistoricalSeasonIdentity
    inventory: HistoricalPickInventory
    # Explicit provider event-ID scope: global IDs can share a namespace;
    # providers with season-local IDs use different namespaces per season.
    event_namespace: str


@dataclass(frozen=True)
class HistoricalPickLineage:
    league_family_id: str
    source_seasons: tuple[HistoricalSeasonIdentity, ...]
    inventory: HistoricalPickInventory
    season_sources: tuple[HistoricalSeasonSource, ...]


def _intersect_bounds(lowers, uppers) -> tuple[datetime | None, datetime | None]:
    lower = max((v for v in lowers if v is not None), default=None)
    upper = min((v for v in uppers if v is not None), default=None)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("conflicting lifecycle date evidence across seasons")
    return lower, upper


def reconcile_historical_pick_lineage(*, lineage: HistoricalSeasonLineage,
        seasons: tuple[HistoricalSeasonPickInventory, ...]) -> HistoricalPickLineage:
    """Canonicalize once and feed the existing inventory, preserving uncertainty.

    Canonical team IDs in the admitted season roster bindings are the explicit
    franchise crosswalk. This does not extend those bindings to manager tenure.
    """
    checked = build_historical_season_lineage(sources=lineage.sources, links=lineage.links)
    sources = {s.season: s for s in checked.sources}
    if not seasons or len({s.season for s in seasons}) != len(seasons):
        raise ValueError("distinct registered season inventories are required")
    if any(s.season not in sources or not s.event_namespace.strip() for s in seasons):
        raise ValueError("season or event identity namespace is unregistered")
    families = {s.season.league_family_id for s in seasons}
    if len(families) != 1:
        raise ValueError("cross-family inventory joins are forbidden")
    parents = {link.current: link.previous for link in checked.links}
    roots = set()
    for item in seasons:
        root = item.season
        while root in parents:
            root = parents[root]
        roots.add(root)
    if len(roots) != 1:
        raise ValueError("season continuity is unlinked")
    family = next(iter(families))
    rights: dict[str, HistoricalPickRight] = {}
    uses: dict[str, HistoricalPickUse] = {}
    events: dict[str, HistoricalPickTransferEvent] = {}
    teams: set[str] = set()
    uncertain: set[str] = set()
    issues: set[str] = set()
    complete_allotments: dict[int, set[str]] = {}
    for item in sorted(seasons, key=lambda s: s.season.season):
        source = sources[item.season]
        inventory = item.inventory
        roster_map = {r.provider_roster_id: r.canonical_team_id for r in source.roster_bindings}
        if set(inventory.team_ids) != set(roster_map):
            raise ValueError("inventory lacks an exact historical roster crosswalk")
        teams.update(roster_map.values())
        pick_map = {}
        for right in inventory.rights:
            original = roster_map[right.original_team_id]
            pid = "hpick_" + sha256(json.dumps((family, right.draft_season, right.round, original)).encode()).hexdigest()
            pick_map[right.pick_id] = pid
            mapped = replace(right, pick_id=pid, original_team_id=original)
            old = rights.get(pid)
            if old is not None:
                lo, hi = _intersect_bounds((old.issued_not_before, mapped.issued_not_before),
                                           (old.issued_by, mapped.issued_by))
                mapped = replace(mapped, issued_not_before=lo, issued_by=hi,
                                 source_ref=";".join(sorted({old.source_ref, mapped.source_ref})))
            rights[pid] = mapped
        for event in inventory.events:
            if any(m.pick_id not in pick_map for m in event.transfers):
                raise ValueError("transfer refers to an unbound pick")
            if any(m.from_team_id not in roster_map or m.to_team_id not in roster_map for m in event.transfers):
                raise ValueError("transfer lacks a historical roster binding")
            movements = tuple(sorted((DraftPickTransfer(pick_map[m.pick_id], roster_map[m.from_team_id],
                roster_map[m.to_team_id]) for m in event.transfers), key=lambda m: (m.pick_id, m.from_team_id, m.to_team_id)))
            eid = f"{item.event_namespace}:{event.event_id}"
            mapped = replace(event, event_id=eid, transfers=movements)
            old = events.get(eid)
            if old is not None:
                if (old.effective_at, old.transfers) != (mapped.effective_at, mapped.transfers):
                    raise ValueError("conflicting event identity across source inventories")
                mapped = replace(mapped, source_ref=";".join(sorted({old.source_ref, mapped.source_ref})))
            events[eid] = mapped
        for use in inventory.uses:
            mapped = replace(use, pick_id=pick_map[use.pick_id], owner_team_id=roster_map[use.owner_team_id])
            old = uses.get(mapped.pick_id)
            if old is not None:
                if (old.owner_team_id, old.kind) != (mapped.owner_team_id, mapped.kind):
                    raise ValueError("conflicting pick-use evidence across sources")
                lo, hi = _intersect_bounds((old.not_before, mapped.not_before), (old.by, mapped.by))
                mapped = replace(mapped, not_before=lo, by=hi,
                                 source_ref=";".join(sorted({old.source_ref, mapped.source_ref})))
            uses[mapped.pick_id] = mapped
        uncertain.update(pick_map[p] for p in inventory.uncertain_pick_ids)
        issues.update(inventory.issues)
        if inventory.allotment_complete:
            for year in inventory.declared_draft_seasons:
                cohort = {pick_map[p.pick_id] for p in inventory.rights if p.draft_season == year}
                old = complete_allotments.setdefault(year, cohort)
                if old != cohort:
                    raise ValueError("conflicting complete draft allotments")
    # One supported terminal use for every enumerated one-use right establishes
    # use coverage, even when no single source year held all the selections.
    terminal_uses_complete = bool(rights) and set(rights) == set(uses) and not uncertain and not issues
    cohorts = tuple(sorted({y for s in seasons for y in s.inventory.declared_draft_seasons}))
    allotment_complete = all(any(s.inventory.allotment_complete and y in s.inventory.declared_draft_seasons
                                for s in seasons) for y in cohorts)
    if any({p.pick_id for p in rights.values() if p.draft_season == year} != ids
           for year, ids in complete_allotments.items()):
        raise ValueError("source rights contradict a declared complete allotment")
    use_complete = terminal_uses_complete or all(any(s.inventory.use_ledger_complete
        and y in s.inventory.declared_draft_seasons for s in seasons) for y in cohorts)
    identity_evidence = {"family": family, "sources": [s.model_dump(mode="json") for s in checked.sources
                                                      if s.season.league_family_id == family],
        "links": [l.model_dump(mode="json") for l in checked.links if l.current.league_family_id == family],
        "inventories": sorted((s.season.league_id, s.inventory.inventory_id, s.event_namespace) for s in seasons)}
    scope = "historical-pick-lineage-v1:" + sha256(json.dumps(identity_evidence, sort_keys=True).encode()).hexdigest()
    joined = build_historical_pick_inventory(team_ids=tuple(sorted(teams)), rights=tuple(rights.values()),
        events=tuple(events.values()), uses=tuple(uses.values()), declared_draft_seasons=cohorts,
        scope_source_ref=scope, coverage_through=max(s.inventory.coverage_through for s in seasons),
        transfer_ledger_complete=(all(s.inventory.transfer_ledger_complete for s in seasons)
                                 and len({s.inventory.coverage_through for s in seasons}) == 1),
        use_ledger_complete=use_complete, allotment_complete=allotment_complete,
        issues=tuple(sorted(issues)), uncertain_pick_ids=tuple(sorted(uncertain)))
    identities = tuple(sorted((s.season for s in seasons), key=lambda s: s.season))
    return HistoricalPickLineage(family, identities, joined, tuple(sources[s] for s in identities))
