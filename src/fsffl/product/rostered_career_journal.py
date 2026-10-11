"""Exact-State, roster-only durable Career result journal.

This is a nonproduction persistence boundary for output from the approved P0
adapter plus the accepted Career composer. It does not acquire provider data or
compute Career metrics. Callers must supply one complete Career result or one
explicit evidence failure for every rostered QB/RB/WR/TE subject.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Iterable, Mapping

POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    ).encode("utf-8")


def append_verified_rostered_career_records(
    *,
    journal_path: str | os.PathLike[str],
    state_hash: str,
    roster_rows: Iterable[Mapping[str, object]],
    state_players: Iterable[Mapping[str, object]],
    records_by_player: Mapping[str, Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    """Validate current-State roster identity and append one durable row/player.

    A record has either career_result (complete) or evidence_failure (explicit
    failure), plus state_hash, timezone-aware evaluation_as_of and nonempty
    provenance. This function never supplies missing metrics.
    """
    if not state_hash or not state_hash.strip():
        raise ValueError("exact State hash is required")
    canonical: dict[str, Mapping[str, object]] = {}
    for player in state_players:
        player_id = str(player.get("player_id", "")).strip()
        if not player_id:
            continue
        if player_id in canonical:
            raise ValueError(f"duplicate canonical State identity {player_id}")
        canonical[player_id] = player

    roster: dict[str, Mapping[str, object]] = {}
    for row in roster_rows:
        player_id = str(row.get("player_id", "")).strip()
        if not player_id:
            continue
        if player_id in roster:
            raise ValueError(f"duplicate roster identity {player_id}")
        if str(row.get("state_hash", state_hash)) != state_hash:
            raise ValueError(f"roster identity {player_id} belongs to another State")
        roster[player_id] = row

    unsupported = set(records_by_player) - set(roster)
    if unsupported:
        raise ValueError(
            "provider/Career records include nonrostered identities: "
            + ", ".join(sorted(unsupported))
        )

    rows: list[dict[str, object]] = []
    for player_id in sorted(roster):
        roster_row = roster[player_id]
        state_player = canonical.get(player_id)
        if state_player is None:
            raise ValueError(f"rostered identity {player_id} is absent from exact State")
        position = str(state_player.get("position", "")).upper()
        if position not in POSITIONS:
            raise ValueError(f"unsupported roster position for {player_id}: {position}")
        roster_position = str(roster_row.get("position", position)).upper()
        if roster_position != position:
            raise ValueError(f"roster/State position mismatch for {player_id}")
        source = records_by_player.get(player_id)
        if source is None:
            raise ValueError(f"missing explicit Career result/failure for {player_id}")
        if str(source.get("player_id", "")) != player_id:
            raise ValueError(f"provider identity mismatch for {player_id}")
        if str(source.get("state_hash", "")) != state_hash:
            raise ValueError(f"Career record belongs to another State for {player_id}")
        evaluation_as_of = source.get("evaluation_as_of")
        if not isinstance(evaluation_as_of, str) or not evaluation_as_of.strip():
            raise ValueError(f"evaluation timestamp missing for {player_id}")
        try:
            parsed_time = datetime.fromisoformat(evaluation_as_of.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid evaluation timestamp for {player_id}") from exc
        if parsed_time.tzinfo is None:
            raise ValueError(f"evaluation timestamp must include timezone for {player_id}")
        provenance = source.get("provenance")
        if not isinstance(provenance, Mapping) or not provenance:
            raise ValueError(f"provenance missing for {player_id}")
        has_result = "career_result" in source
        has_failure = "evidence_failure" in source
        if has_result == has_failure:
            raise ValueError(
                f"{player_id} must have exactly one complete Career result or explicit failure"
            )
        if has_result:
            result = source["career_result"]
            if not isinstance(result, Mapping) or not result:
                raise ValueError(f"complete Career result is empty for {player_id}")
            for metric, value in result.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"Career metric {metric} is not numeric for {player_id}")
                if not math.isfinite(float(value)):
                    raise ValueError(f"Career metric {metric} is non-finite for {player_id}")
            status = "complete"
        else:
            failure = source["evidence_failure"]
            if not isinstance(failure, Mapping) or not failure.get("reason"):
                raise ValueError(f"explicit evidence failure reason missing for {player_id}")
            status = "evidence_failure"
        row = {
            "state_hash": state_hash,
            "player_id": player_id,
            "position": position,
            "team_id": str(roster_row.get("team_id") or ""),
            "roster_slot": str(roster_row.get("roster_slot") or ""),
            "evaluation_as_of": evaluation_as_of,
            "provenance": provenance,
            "status": status,
            **({"career_result": source["career_result"]} if has_result else
               {"evidence_failure": source["evidence_failure"]}),
        }
        row["artifact_digest"] = sha256(_canonical_json(row)).hexdigest()
        rows.append(row)

    path = Path(journal_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.fchmod(fd, 0o600)
        for row in rows:
            payload = _canonical_json(row) + b"\n"
            written = os.write(fd, payload)
            if written != len(payload):
                raise OSError("short write while appending Career record")
            os.fsync(fd)
    finally:
        os.close(fd)
    return tuple(rows)
