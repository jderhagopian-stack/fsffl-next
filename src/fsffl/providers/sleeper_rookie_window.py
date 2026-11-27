"""FSFFL's three-class allotment, anchored to the linked Sleeper franchise history."""
from collections.abc import Mapping
from dataclasses import dataclass

from fsffl.state.models import RookiePickWindow

# Verified ordinary rookie drafts. The league's designated primary draft supplies
# the identity for subsequent renewals, within this same provider lineage only.
DRAFTS = {
    "1195205225995415552": "1195205225995415553",
    "1312071960615731200": "1312071960619941888",
}


def fsffl_pick_years(
    league_season: int, *, regular_draft_complete: bool | None
) -> range | None:
    if regular_draft_complete is None:
        return None
    first = league_season + int(regular_draft_complete)
    return range(first, first + 3)


def in_family(league, ancestors=()):
    current = league
    for parent in (*ancestors, None):
        if str(current.get("league_id")) in DRAFTS or str(current.get("previous_league_id")) in DRAFTS:
            return True
        if not parent or str(current.get("previous_league_id")) != str(parent.get("league_id")):
            break
        current = parent
    return False


def ordinary_draft(league, drafts):
    if not isinstance(drafts, list):
        return None
    registered = DRAFTS.get(str(league["league_id"]))
    identity = registered or league.get("draft_id")
    matches = [d for d in drafts if isinstance(d, Mapping) and identity
               and str(d.get("draft_id")) == str(identity)]
    if len(matches) != 1:
        return None

    def eligible(draft):
        if not isinstance(draft, Mapping):
            return False
        metadata = draft.get("metadata") or {}
        settings = draft.get("settings") or {}
        if not isinstance(metadata, Mapping) or not isinstance(settings, Mapping):
            return False
        description = f"{metadata.get('name', '')} {metadata.get('description', '')}".casefold()
        return (
            str(draft.get("league_id")) == str(league["league_id"])
            and str(draft.get("season")) == str(league["season"])
            and draft.get("type") == "linear"
            and type(settings.get("rounds")) is int and settings["rounds"] > 0
            and settings["rounds"] == (league.get("settings") or {}).get("draft_rounds")
            and not any(word in description for word in ("supplemental", "midseason", "startup"))
        )

    if not eligible(matches[0]) or (not registered and sum(eligible(d) for d in drafts) != 1):
        return None
    return matches[0]


def acquire(get, league):
    ancestors = []
    parent = league.get("previous_league_id")
    seen = {str(league.get("league_id"))}
    current_season = str(league.get("season", ""))
    while (not in_family(league, ancestors) and parent and str(parent) not in seen
           and current_season.isdigit() and int(current_season) > 2026):
        seen.add(str(parent))
        prior = get(f"/league/{parent}")
        if not isinstance(prior, Mapping) or str(prior.get("league_id")) != str(parent):
            return {"rookie_lineage_unavailable": True}
        ancestors.append({k: prior.get(k) for k in ("league_id", "previous_league_id")})
        parent = prior.get("previous_league_id")
        current_season = str(prior.get("season", ""))
    if not in_family(league, ancestors):
        return {}
    drafts = get(f"/league/{league['league_id']}/drafts")
    draft = ordinary_draft(league, drafts)
    selections = get(f"/draft/{draft['draft_id']}/picks") if draft else None
    transfers = None
    if draft and draft.get("status") in ("pre_draft", "drafting", "paused"):
        transfers = get(f"/draft/{draft['draft_id']}/traded_picks")
    # Keep only the evidence consumed by normalization and the refresh probe.
    return {"rookie_ancestors": ancestors, "rookie_drafts": [draft] if draft else [],
            "rookie_transfers": [row for row in transfers if isinstance(row, Mapping)
                                and str(row.get("draft_id")) == str(draft["draft_id"])
                                and str(row.get("season")) == str(league["season"])] if isinstance(transfers, list) and draft else [],
            "rookie_selections": [{k: p.get(k) for k in ("draft_id", "round", "draft_slot", "pick_no", "player_id")}
                                  for p in selections if isinstance(p, Mapping)]
            if isinstance(selections, list) and all(isinstance(p, Mapping) for p in selections) else None}


@dataclass
class Inventory:
    window: RookiePickWindow
    slots: dict[int, int]
    spent: set[tuple[int, int]]


def inventory(bundle, prior):
    league = bundle.league
    season = int(league["season"])
    draft = ordinary_draft(league, bundle.rookie_drafts)
    complete = None
    slots = {}
    spent = set()
    rows = bundle.rookie_selections
    previous = prior if prior and prior.draft_season == season else None
    if draft:
        by_owner = {str(r["owner_id"]): int(r["roster_id"]) for r in bundle.rosters if r.get("owner_id")}
        order = draft.get("draft_order") or {}
        team_count = len(bundle.rosters)
        round_count = draft["settings"]["rounds"]
        try:
            slots = {by_owner[str(owner)]: int(slot) for owner, slot in order.items()}
            direct = draft.get("slot_to_roster_id") or {}
            roster_ids = {int(r["roster_id"]) for r in bundle.rosters}
            for slot, roster in direct.items():
                original = int(roster)
                if original not in roster_ids or slots.get(original, int(slot)) != int(slot):
                    raise ValueError("draft order disagrees with original roster assignment")
                slots[original] = int(slot)
            if (len(slots) < len(order) or len(set(slots.values())) != len(slots)
                    or any(not 1 <= slot <= team_count for slot in slots.values())):
                raise ValueError("conflicting original draft slots")
            if previous and previous.draft_id != str(draft["draft_id"]):
                raise ValueError("ordinary draft identity changed")
            if len({r["roster_id"] for r in bundle.rosters}) != team_count or draft["settings"].get("teams") != team_count:
                raise ValueError("draft and league sizes disagree")
            if rows is None:
                raise ValueError("selection evidence missing")
            for row in rows:
                rnd, slot = int(row["round"]), int(row["draft_slot"])
                if (str(row["draft_id"]) != str(draft["draft_id"]) or not row.get("player_id")
                        or not 1 <= rnd <= round_count or not 1 <= slot <= team_count
                        or int(row["pick_no"]) != (rnd - 1) * team_count + slot or (rnd, slot) in spent):
                    raise ValueError("inconsistent draft selection")
                spent.add((rnd, slot))
            numbers = {(rnd - 1) * team_count + slot for rnd, slot in spent}
            if numbers != set(range(1, len(spent) + 1)):
                raise ValueError("incomplete selection ledger")
            if previous and not set(previous.used_slots).issubset(spent):
                raise ValueError("previously used draft choice disappeared")
            if previous and previous.used_slots and slots != dict(previous.original_slots):
                raise ValueError("original slot assignments changed after use")
            status = draft.get("status")
            if status == "complete" and len(spent) == round_count * team_count:
                complete = True
            elif status in ("drafting", "paused") or (status == "pre_draft" and not spent):
                complete = False
        except (TypeError, ValueError, KeyError, AttributeError):
            slots = {}
    years = fsffl_pick_years(season, regular_draft_complete=complete)
    if years is None or (prior and prior.first_year > years.start):
        if prior:
            window = prior.model_copy(update={"status": "retained"})
            return Inventory(window, dict(previous.original_slots) if previous else {},
                             set(previous.used_slots) if previous else set())
        return Inventory(RookiePickWindow(first_year=None, status="unresolved"), {}, set())
    window = RookiePickWindow(first_year=years.start, status="verified", draft_season=season,
                              draft_id=str(draft["draft_id"]), original_slots=tuple(sorted(slots.items())),
                              used_slots=tuple(sorted(spent)))
    return Inventory(window, slots, spent)
