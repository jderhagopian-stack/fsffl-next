"""Exact 2026-09-09 pre-kickoff fantasy roster reconstruction (FSFFL research).

Factual layers:
- August-vintage Sleeper provider roster from immutable pre-kickoff Git blob.
- Complete *historically dated* week-1 Sleeper transaction receipts, obtained
  from the public Sleeper transaction endpoint, filtered at archive cutoff.
- An explicitly named *unexplained* Travis Hunter reconciliation against the
  independently retained 2026-09-09 FSFFL NEXT original-vintage artifact.
- Thirty archived lineup/IR/taxi placement facts from that same pre-kickoff
  artifact, needed because a trade log does not record lineup edits.
- SHA256 hashes from original Sept 9 Analytics over exact player/team/slot and
  pick-owner identities; no private archived roster payload is stored in Git.

A transaction receipt cannot explain an unrecorded loss of membership.
We use the archived Sept 9 state to establish the fact of absence and call
the historical *reason* unknown. No future scores or November projections.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from urllib.request import Request, urlopen
import json

LEAGUE_ID = "1312071960615731200"
AS_OF = datetime(2026, 9, 9, 23, 23, 55, tzinfo=UTC)
JOURNAL_FLOOR = datetime(2026, 8, 27, tzinfo=UTC)
API = f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/transactions/1"
EXACT_EXPECTED_TRANSACTIONS = frozenset("""
1398811923553808384 1399045591664754688 1399825324354637824
1399867188692709376 1399915431354990592 1399915791595384832
1399916640014991360 1399916671858118656 1399976634357948416
1399983169490411520 1400393559751864320 1400663945601155072
1400665664796041216 1400678270420176896 1400990098173988864
1400990256601305088 1401088130517356544 1401265332118630400
1401297624019038208 1402021946123640832 1403066556992241664
""".split())
EXPECTED_MEMBERSHIP_SHA = "f1c0016ba592de8fa558ebc8b4f6624b762cf763a7380f48b368466d3f25f62c"
EXPECTED_PLAYER_SLOT_SHA = "adf4c8c5190f01f1ae059c2e36f6f266439332ce2ab99293171751f27b20b52e"
EXPECTED_PICK_SHA = "e791bf936248061583c34fad3da50431f3865652d9374357fc22498e7740497a"

# These are *not invented waiver transactions*. They were archived in the
# original 2026-09-09 23:26 UTC FIRST-PARTY analytics artifact #65.
# This exact list contains ONLY roster-slot differences from older Sleeper
# provider data after replay, not a raw dump of private tenant state.
PREKICKOFF_SLOT_OVERRIDES = {
    "12467": "SUPERFLEX", "13421": "FLEX",
    "12469": "BENCH", "12524": "BENCH", "13276": "TAXI",
    "13305": "BENCH", "8142": "WR", "8205": "IR",
    "9480": "FLEX", "11603": "TE", "8110": "BENCH",
    "11566": "SUPERFLEX", "11628": "WR", "13281": "BENCH",
    "6770": "QB", "8121": "FLEX",
    "12490": "BENCH", "13414": "BENCH", "8167": "FLEX",
    "11581": "RB", "13293": "BENCH", "13413": "TAXI",
    "5850": "BENCH", "11604": "BENCH", "12502": "TE",
    "13286": "BENCH", "13411": "TAXI", "9502": "IR",
    "13425": "TAXI", "6768": "SUPERFLEX",
}
# Explicit reconciliation exception: archived 09/09 original-vintage source
# proves this asset was no longer rostered; no completed Sleeper drop was found.
# Do NOT pretend that this records a transaction or establishes its timing.
ARCHIVE_MEMBERSHIP_ABSENCES = {"12530": "Travis Hunter"}
# Pre-kickoff player identity from original 9/9 archived Analytics: not present
# in the older Sept 4 Git source's Sleeper player dictionary.
ARCHIVE_IDENTITY_ADDITIONS = {"13425": {
    "player_id": "13425", "full_name": "Jalon Daniels", "position": "QB",
    "team": None, "status": "Unknown", "active": False,
}}


class HistoricalRosterMismatch(ValueError):
    pass


def _sha(s: str) -> str:
    return sha256(s.encode("utf-8")).hexdigest()


def _iso_ms(ms: object) -> datetime:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError) as e:
        raise HistoricalRosterMismatch("Sleeper transaction missing valid completion clock") from e


def load_provider_transactions() -> list[dict]:
    request = Request(API, headers={"User-Agent": "FSFFL-NEXT-historical-replay-research/1"})
    with urlopen(request, timeout=35) as response:
        data = response.read(4_000_001)
    if len(data) > 4_000_000:
        raise HistoricalRosterMismatch("Sleeper public transaction journal size guard")
    obj = json.loads(data)
    if not isinstance(obj, list):
        raise HistoricalRosterMismatch("Sleeper week-one transaction journal did not return a list")
    return obj


def _sleeper_slot_base(roster: dict, positions: list[str]) -> dict[str, str]:
    result = {}
    players = [str(p) for p in (roster.get("players") or ())]
    starters = [str(p) for p in (roster.get("starters") or ())]
    taxi = set(str(p) for p in (roster.get("taxi") or ()))
    reserve = set(str(p) for p in (roster.get("reserve") or ()))
    for id in players:
        if id in taxi:
            result[id] = "TAXI"
        elif id in reserve:
            result[id] = "IR"
        elif id in starters:
            idx = starters.index(id)
            result[id] = positions[idx].replace("SUPER_FLEX", "SUPERFLEX")
        else:
            result[id] = "BENCH"
    return result


def _hash_map(rows: dict[str, int], *, suffix: dict[str, str] | None = None,
              canonical_player: bool = True) -> str:
    prefix = "sleeper:player:" if canonical_player else ""
    encoded = []
    for id, rid in sorted(rows.items(), key=lambda v: prefix + v[0]):
        pid = f"{prefix}{id}"
        if suffix is None:
            encoded.append(f"{pid}={rid}")
        else:
            encoded.append(f"{pid}={rid}:{suffix[id]}")
    return _sha(";".join(encoded))


def _picks_from_base(raw: list[dict]) -> dict[str, int]:
    p = {f"sleeper:{LEAGUE_ID}:pick:{y}:{rnd}:{orig}": orig
         for y in (2027, 2028, 2029) for rnd in (1, 2, 3) for orig in range(1, 13)}
    for v in raw:
        y, rnd, orig = int(v["season"]), int(v["round"]), int(v["roster_id"])
        if y not in (2027, 2028, 2029):
            continue
        p[f"sleeper:{LEAGUE_ID}:pick:{y}:{rnd}:{orig}"] = int(v["owner_id"])
    return p


def reconstruct_sept9_sources(source: dict, *, transactions: list[dict] | None = None):
    """Return frozen source payload with exact 9/9 roster and pick ownership.

    The data input is the untouched pinned archive from Sept 4. Only the
    replayer's local *copy* is changed, never the pinned source or the DB.
    """
    league = source["data/league.json"]
    if str(league.get("league_id")) != LEAGUE_ID or int(league.get("season")) != 2026:
        raise HistoricalRosterMismatch("unexpected archived fantasy league identity")
    positions = [str(slot) for slot in league["roster_positions"]][:9]
    if len(positions) != 9:
        raise HistoricalRosterMismatch("9 required lineup slots are missing")
    rosters = json.loads(json.dumps(source["data/rosters.json"]))
    owner, slot = {}, {}
    old_order: dict[int, dict[str, int]] = {}
    for row in rosters:
        rid = int(row["roster_id"])
        old_order[rid] = {str(pid): i for i, pid in enumerate(row.get("starters") or ())}
        initial = _sleeper_slot_base(row, positions)
        for pid, status in initial.items():
            if pid in owner:
                raise HistoricalRosterMismatch("duplicate owned Sleeper asset in initial provider file")
            owner[pid], slot[pid] = rid, status
    picks = _picks_from_base(source["data/traded_picks.json"])

    raw = load_provider_transactions() if transactions is None else transactions
    applied = []
    for tx in raw:
        if tx.get("status") != "complete":
            continue
        stamp = _iso_ms(tx.get("status_updated"))
        initiated_at = _iso_ms(tx.get("created"))
        # Sleeper batches older waivers and can change their status_updated
        # timestamp several days later. This base roster already reflects
        # those older claims. Partition by CREATED, not last update.
        if not JOURNAL_FLOOR <= initiated_at <= stamp <= AS_OF:
            continue
        applied.append((stamp, tx))
    tx_ids = {str(t["transaction_id"]) for _, t in applied}
    if tx_ids != EXACT_EXPECTED_TRANSACTIONS:
        raise HistoricalRosterMismatch(
            f"transaction history incomplete or changed: missing={sorted(EXACT_EXPECTED_TRANSACTIONS-tx_ids)} "
            f"extra={sorted(tx_ids-EXACT_EXPECTED_TRANSACTIONS)}"
        )
    applied.sort(key=lambda x: (x[0], str(x[1]["transaction_id"])))
    no_op_prior_drop = []
    transaction_trace = []
    for stamp, tx in applied:
        gains, losses = tx.get("adds") or {}, tx.get("drops") or {}
        transfers = tx.get("draft_picks") or []
        tx_id = str(tx["transaction_id"])
        for pid_raw, rid_raw in losses.items():
            pid, rid = str(pid_raw), int(rid_raw)
            current = owner.get(pid)
            if current is None:
                no_op_prior_drop.append({"transaction_id": tx_id, "player_id":pid})
                continue
            if current != rid:
                raise HistoricalRosterMismatch(f"drop owner conflict: tx={tx_id} player={pid}")
        for pid_raw, rid_raw in gains.items():
            pid, new_owner = str(pid_raw), int(rid_raw)
            old_owner = owner.get(pid)
            if old_owner is not None and old_owner != new_owner:
                # A trade can move from a disposing owner listed in the same
                # transaction; an ordinary waiver cannot steal an owned asset.
                if (tx.get("type") != "trade" or int(losses.get(pid, -1)) != old_owner):
                    raise HistoricalRosterMismatch(f"unexpected existing owner for add tx={tx_id}: {pid}")
        # Atomic transaction: ALL drops precede ALL adds, not each roster side.
        for pid in losses:
            owner.pop(str(pid), None)
            slot.pop(str(pid), None)
        for pid_raw, rid_raw in gains.items():
            pid, rid = str(pid_raw), int(rid_raw)
            owner[pid] = rid
            slot[pid] = "BENCH"
        for pick in transfers:
            year, rnd, original = int(pick["season"]), int(pick["round"]), int(pick["roster_id"])
            if year not in (2027, 2028, 2029):
                continue
            pick_key = f"sleeper:{LEAGUE_ID}:pick:{year}:{rnd}:{original}"
            before = picks.get(pick_key)
            previous_owner = int(pick["previous_owner_id"])
            new_owner = int(pick["owner_id"])
            if before != previous_owner:
                raise HistoricalRosterMismatch(f"draft-pick transfer provenance mismatch tx={tx_id}: {pick_key}")
            picks[pick_key] = new_owner
        transaction_trace.append({"transaction_id": tx_id, "type": tx.get("type"),
                                  "completed_at": stamp.isoformat(),
                                  "player_additions": len(gains), "player_drops": len(losses),
                                  "pick_movements": len(transfers)})
    for pid in ARCHIVE_MEMBERSHIP_ABSENCES:
        if pid not in owner:
            raise HistoricalRosterMismatch(f"documented 9/9 unexplained absence was not in baseline: {pid}")
        owner.pop(pid)
        slot.pop(pid)

    for pid, value in PREKICKOFF_SLOT_OVERRIDES.items():
        if pid not in owner:
            raise HistoricalRosterMismatch(f"original-vintage lineup override has no reconstructed owner: {pid}")
        slot[pid] = value

    mm = _hash_map(owner)
    if mm != EXPECTED_MEMBERSHIP_SHA:
        raise HistoricalRosterMismatch(f"September 9 recovered player roster does not match archived digest: {mm}")
    ss = _hash_map(owner, suffix=slot)
    if ss != EXPECTED_PLAYER_SLOT_SHA:
        raise HistoricalRosterMismatch(f"September 9 recovered roster slots do not match archived digest: {ss}")
    ps = _hash_map(picks, canonical_player=False)
    if ps != EXPECTED_PICK_SHA:
        raise HistoricalRosterMismatch(f"September 9 future pick owners do not match archived digest: {ps}")
    if len(owner) != 237 or len(picks) != 108:
        raise HistoricalRosterMismatch("archive source-cohort player/pick counts disagree")

    by_rid: dict[int, list[str]] = defaultdict(list)
    for pid, rid in owner.items():
        by_rid[rid].append(pid)
    starters = [p.replace("SUPER_FLEX", "SUPERFLEX") for p in positions]
    for row in rosters:
        rid = int(row["roster_id"])
        members = sorted(by_rid[rid], key=lambda x: (int(x) if x.isdigit() else x))
        row["players"] = members
        row["taxi"] = sorted((p for p in members if slot[p] == "TAXI"))
        row["reserve"] = sorted((p for p in members if slot[p] == "IR"))
        lineup = []
        for position in starters:
            # RB/WR are repeated required slots; consume exactly one player per
            # slot occurrence, never append an entire positional group twice.
            match = [p for p in members if slot[p] == position and p not in lineup]
            match.sort(key=lambda p: (old_order.get(rid, {}).get(p, 100), p))
            if not match:
                raise HistoricalRosterMismatch(f"missing pre-kickoff starter for {position}: team {rid}")
            lineup.append(match[0])
        if len(lineup) != 9:
            raise HistoricalRosterMismatch(f"2026 Sept 9 starter count !=9 for team {rid}: {len(lineup)}")
        ordered_positions = [slot[p] for p in lineup]
        if sorted(ordered_positions) != sorted(starters):
            raise HistoricalRosterMismatch(f"lineup slot requirements invalid for team {rid}")
        row["starters"] = lineup
    players = json.loads(json.dumps(source["data/players.json"]))
    for pid, identity in ARCHIVE_IDENTITY_ADDITIONS.items():
        if pid in players:
            raise HistoricalRosterMismatch(f"archive-only identity no longer needed: {pid}")
        players[pid] = identity
    # Apply historical pick transfers into provider-shaped traded_picks.
    picks_existing = {
        (int(row["season"]), int(row["round"]), int(row["roster_id"])): dict(row)
        for row in source["data/traded_picks.json"]
    }
    for key, rid in picks.items():
        _, _, _, year, rnd, orig = key.split(":")
        iy, ir, io = int(year), int(rnd), int(orig)
        prev = picks_existing.get((iy, ir, io))
        if prev is None and rid == io:
            continue
        if prev is None:
            prev = {"season": year, "round": ir, "roster_id": io,
                    "previous_owner_id": io, "owner_id": rid}
        else:
            prev = {**prev, "owner_id": rid}
        picks_existing[(iy, ir, io)] = prev
    final = dict(source)
    final.update({
        "data/rosters.json": rosters,
        "data/traded_picks.json": list(picks_existing.values()),
        "data/players.json": players,
    })
    receipt = {
        "status": "source_replayed_to_original_pre_kickoff_archive_digest",
        "as_of": AS_OF.isoformat(),
        "transaction_ids": sorted(tx_ids),
        "transactions_applied": len(applied),
        "lineup_slot_corrections_from_archived_analytics": len(PREKICKOFF_SLOT_OVERRIDES),
        "source_frozen_player_count": len(owner),
        "source_frozen_pick_count": len(picks),
        "sha256_player_ownership": mm, "sha256_player_roster_slots": ss,
        "sha256_future_picks": ps,
        "unmatched_prior_drop_receipts": no_op_prior_drop,
        "unexplained_archived_membership_absence": [
            {"player_id": k, "full_name": v, "reason": "not established by completed transaction history"}
            for k, v in ARCHIVE_MEMBERSHIP_ABSENCES.items()
        ],
        "player_identity_recovered_from_original_vintage": list(ARCHIVE_IDENTITY_ADDITIONS),
        "transaction_trace": transaction_trace,
    }
    return final, receipt
