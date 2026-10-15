"""Shared bounded selection path for exact-State Career coverage.

This module only chooses canonical subjects and batches them to the accepted
Career materializer. It owns no model math and never manufactures evidence.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from threading import RLock
from typing import Callable, Iterable, Mapping, Sequence


POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


@dataclass(frozen=True)
class CareerCoverageSubject:
    player_id: str
    position: str
    team_id: str | None
    roster_slot: str | None
    source: str


@dataclass(frozen=True)
class CareerCoverageBatch:
    subjects: tuple[CareerCoverageSubject, ...]
    authority: Mapping[str, object]
    missing: Mapping[str, str]
    state_hash: str


def build_career_position_depth_refresh(
    *, state_hash: str, roster_rows: Iterable[Mapping[str, object]],
    subjects: Sequence[CareerCoverageSubject], authority: Mapping[str, object],
    failures: Mapping[str, str], partial_authority: Mapping[str, object] | None = None,
) -> tuple[Mapping[str, object], ...]:
    """Create one Position & Depth status row for every roster identity.

    Missing canonical player evidence is represented on that player's roster
    row. It must not cause the whole matching-State payload to disappear.
    Position/team/slot are copied from the exact roster record when no canonical
    Career subject exists; no Career value or player identity is inferred.
    """
    selected = {subject.player_id: subject for subject in subjects}
    output = []
    for row in roster_rows:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            continue
        if str(row.get("state_hash", state_hash)) != state_hash:
            raise ValueError("Career Position & Depth row belongs to another State")
        subject = selected.get(player_id)
        position = subject.position if subject is not None else str(row.get("position") or "")
        team_id = subject.team_id if subject is not None else row.get("team_id")
        roster_slot = subject.roster_slot if subject is not None else row.get("roster_slot")
        if subject is not None:
            if str(row.get("position", subject.position)).upper() != subject.position.upper():
                raise ValueError(f"Career Position & Depth position differs from exact roster for {player_id}")
            if str(row.get("team_id") or "") != str(subject.team_id or ""):
                raise ValueError(f"Career Position & Depth team differs from exact roster for {player_id}")
            if str(row.get("roster_slot") or "") != str(subject.roster_slot or ""):
                raise ValueError(f"Career Position & Depth slot differs from exact roster for {player_id}")
        if player_id in authority:
            status, reason = "career_authority_available", ""
        elif player_id in (partial_authority or {}):
            status, reason = "career_authority_partial", str(
                failures.get(player_id, "required_career_component_unavailable")
            )
        else:
            status, reason = "career_authority_failure", failures.get(
                player_id,
                "canonical_player_absent_from_exact_state_identity_universe"
                if subject is None
                else "player_specific_career_authority_unavailable",
            )
        output.append({
            "state_hash": state_hash, "player_id": player_id,
            "position": position, "team_id": team_id,
            "roster_slot": roster_slot, "career_coverage_status": status,
            "career_failure_reason": reason,
        })
    return tuple(sorted(output, key=lambda row: str(row["player_id"])))


def select_career_coverage(
    *,
    state_players: Iterable[Mapping[str, object]],
    roster_rows: Iterable[Mapping[str, object]],
    state_hash: str,
    precomputed_player_ids: Iterable[str] = (),
    on_demand_player_ids: Iterable[str] = (),
) -> tuple[CareerCoverageSubject, ...]:
    """Select roster subjects, an explicitly bounded cohort, and requests.

    Roster rows always take precedence. Unrostered players are included only
    when named in the caller's already-ranked/precomputed cohort or explicitly
    requested on demand; NFL attachment alone never expands Career work to the
    full free-agent pool. A player outside the State universe is deliberately
    left to the canonical identity/acquisition layer and is not fabricated.
    """
    if not state_hash or not str(state_hash).strip():
        raise ValueError("exact State hash is required")
    universe: dict[str, Mapping[str, object]] = {}
    for row in state_players:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            continue
        if player_id in universe:
            raise ValueError(f"duplicate canonical State player {player_id}")
        universe[player_id] = row

    roster: dict[str, Mapping[str, object]] = {}
    for row in roster_rows:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            continue
        if player_id in roster:
            raise ValueError(f"duplicate roster player {player_id}")
        if str(row.get("state_hash", state_hash)) != state_hash:
            raise ValueError("roster row belongs to a different exact State")
        roster[player_id] = row

    selected: dict[str, CareerCoverageSubject] = {}
    requested = {str(x).strip() for x in on_demand_player_ids if str(x).strip()}
    precomputed = {str(x).strip() for x in precomputed_player_ids if str(x).strip()}
    for player_id, row in universe.items():
        position = str(row.get("position", "")).upper()
        if position not in POSITIONS:
            continue
        roster_row = roster.get(player_id)
        if roster_row:
            roster_position = str(roster_row.get("position", position)).upper()
            if roster_position != position:
                raise ValueError(f"roster/State position mismatch for {player_id}")
            selected[player_id] = CareerCoverageSubject(
                player_id, position, str(roster_row.get("team_id") or "") or None,
                str(roster_row.get("roster_slot") or "") or None, "exact_state_roster",
            )
        elif player_id in requested:
            selected[player_id] = CareerCoverageSubject(player_id, position, None, None, "on_demand")
        elif player_id in precomputed:
            # Callers provide only the bounded cohort selected for Explore.
            selected[player_id] = CareerCoverageSubject(player_id, position, None, None, "waiver_pool")
    return tuple(selected[k] for k in sorted(selected))


def resolve_career_coverage(
    *,
    state_players: Iterable[Mapping[str, object]],
    roster_rows: Iterable[Mapping[str, object]],
    state_hash: str,
    evidence_by_player: Mapping[str, object],
    materialize_batch: Callable[[Sequence[CareerCoverageSubject], Mapping[str, object]], Mapping[str, object]],
    precomputed_player_ids: Iterable[str] = (),
    on_demand_player_ids: Iterable[str] = (),
) -> CareerCoverageBatch:
    """Make one shared batch call; preserve missing-input failures per player."""
    state_players = tuple(state_players)
    roster_rows = tuple(roster_rows)
    precomputed_player_ids = tuple(precomputed_player_ids)
    on_demand_player_ids = tuple(on_demand_player_ids)
    subjects = select_career_coverage(
        state_players=state_players, roster_rows=roster_rows, state_hash=state_hash,
        precomputed_player_ids=precomputed_player_ids,
        on_demand_player_ids=on_demand_player_ids,
    )
    missing: dict[str, str] = {}
    selected_ids = {subject.player_id for subject in subjects}
    state_ids = {str(row.get("player_id", "")).strip() for row in state_players}
    roster_ids = {str(row.get("player_id", "")).strip() for row in roster_rows}
    requested_ids = {str(x).strip() for x in on_demand_player_ids if str(x).strip()}
    for player_id in sorted((roster_ids | requested_ids) - state_ids):
        missing[player_id] = "canonical_player_absent_from_exact_state_identity_universe"
    for player_id in sorted(roster_ids - selected_ids - set(missing)):
        missing[player_id] = "rostered_player_has_no_supported_qb_rb_wr_te_position"
    usable: list[CareerCoverageSubject] = []
    packets: dict[str, object] = {}
    for subject in subjects:
        packet = evidence_by_player.get(subject.player_id)
        if packet is None:
            missing[subject.player_id] = "governed_player_evidence_packet_unavailable"
        else:
            usable.append(subject)
            packets[subject.player_id] = packet
    # The accepted model/materializer owns missing-feature semantics and
    # authority failures. This callback is intentionally invoked once per State.
    authority = materialize_batch(tuple(usable), packets) if usable else {}
    for subject in usable:
        if subject.player_id not in authority:
            missing[subject.player_id] = "materializer_returned_no_player_authority"
    return CareerCoverageBatch(tuple(subjects), authority, missing, state_hash)


def evidence_fingerprint(*, model_digest: str, scoring_digest: str,
                          evidence_packet: Mapping[str, object]) -> str:
    """League-neutral reusable key for one subject's governed Career evidence."""
    payload = {"model": model_digest, "scoring": scoring_digest, "evidence": evidence_packet}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


class BoundedCareerEvidenceCache:
    """Small process-local LRU; State/tenant artifacts are never cached here."""

    def __init__(self, max_entries: int = 512) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self._limit = int(max_entries)
        self._values: OrderedDict[str, object] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> object | None:
        with self._lock:
            value = self._values.get(key)
            if value is not None:
                self._values.move_to_end(key)
            return value

    def put(self, key: str, value: object) -> None:
        with self._lock:
            self._values[key] = value
            self._values.move_to_end(key)
            while len(self._values) > self._limit:
                self._values.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._values)


DEFAULT_EXPLORE_CAREER_COHORT_SIZE = 50
MAX_EXPLORE_CAREER_COHORT_SIZE = 100


def select_explore_career_cohort(
    *,
    candidate_rows: Iterable[Mapping[str, object]],
    max_candidates: int = DEFAULT_EXPLORE_CAREER_COHORT_SIZE,
) -> tuple[Mapping[str, object], ...]:
    """Select a bounded Explore cohort from already-supported waiver evidence.

    The broad State selector remains a cheap discovery index. Career precompute
    is limited to supported waiver rows explicitly carrying a governed
    opportunity_score; unsupported or unscored rows are not silently promoted.
    Highest opportunity scores rank first, with canonical player ID as a stable
    tie-break. The default is 50 and callers cannot exceed 100 in one cohort.
    """
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("Explore cohort size must be an integer")
    if not 1 <= max_candidates <= MAX_EXPLORE_CAREER_COHORT_SIZE:
        raise ValueError(
            f"Explore cohort size must be between 1 and {MAX_EXPLORE_CAREER_COHORT_SIZE}"
        )

    ranked: list[tuple[float, str, Mapping[str, object]]] = []
    seen: set[str] = set()
    for row in candidate_rows:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            raise ValueError("Explore candidate requires canonical player_id")
        if player_id in seen:
            raise ValueError(f"duplicate Explore candidate {player_id}")
        seen.add(player_id)
        if row.get("source") != "waiver_pool":
            continue
        if row.get("career_supported") is not True:
            continue
        try:
            score = float(row["opportunity_score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"supported Explore candidate {player_id} requires governed opportunity_score"
            ) from exc
        if not math.isfinite(score):
            raise ValueError(f"invalid opportunity_score for {player_id}")
        ranked.append((score, player_id, row))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in ranked[:max_candidates])
