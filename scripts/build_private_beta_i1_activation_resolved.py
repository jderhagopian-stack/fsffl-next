from __future__ import annotations

import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import pandas as pd

POSITIONS = {"QB", "RB", "WR", "TE"}
_SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}


def _load_builder():
    path = Path(__file__).with_name("build_private_beta_i1_activation.py")
    spec = importlib.util.spec_from_file_location("private_beta_i1_activation_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load activation builder: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _pandas(frame: Any) -> pd.DataFrame:
    if hasattr(frame, "to_pandas"):
        return frame.to_pandas()
    if isinstance(frame, pd.DataFrame):
        return frame
    return pd.DataFrame(frame)


def _first_column(frame: pd.DataFrame, *names: str) -> str | None:
    for name in names:
        if name in frame.columns:
            return name
    return None


def _normalize_name(value: object) -> str:
    """Provider-neutral identity normalization for a unique fallback only.

    Punctuation/spacing differences and ordinary generational suffixes are ignored.
    The compact form also makes `D.J.` and `DJ` equivalent. Uniqueness is enforced
    before this normalization is ever allowed to recover a stable id.
    """

    tokens = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split()
    while tokens and tokens[-1] in _SUFFIX_TOKENS:
        tokens.pop()
    return "".join(tokens)


def _row_names(row: pd.Series, name_columns: tuple[str, ...]) -> set[str]:
    names: set[str] = set()
    for column in name_columns:
        value = row.get(column)
        if value is not None and not pd.isna(value):
            text = str(value).strip()
            if text:
                names.add(text)
    first = row.get("first_name") if "first_name" in row.index else None
    last = row.get("last_name") if "last_name" in row.index else None
    if first is not None and last is not None and not pd.isna(first) and not pd.isna(last):
        combined = f"{str(first).strip()} {str(last).strip()}".strip()
        if combined:
            names.add(combined)
    return names


def _roster_identity_index(source_season: int) -> tuple[dict[tuple[str, str], set[str]], set[str]]:
    """Build a completed-source-roster-limited name/position -> GSIS index.

    The bridge never invents a player id. It recovers an nflverse stable id only
    when the completed-source roster contains exactly one matching player after
    normalization. Restricting the index to the completed source season avoids
    historical same-name collisions from the all-player identity table.
    """

    players = _pandas(nfl.load_players())
    rosters = _pandas(nfl.load_rosters([source_season]))

    player_id_col = _first_column(players, "gsis_id", "player_id")
    player_position_col = _first_column(players, "position_group", "position")
    roster_id_col = _first_column(rosters, "gsis_id", "gsis_it", "player_id")
    if player_id_col is None or player_position_col is None or roster_id_col is None:
        raise RuntimeError(
            "identity bridge cannot locate nflverse player/roster identity columns; "
            f"players={list(players.columns)} rosters={list(rosters.columns)}"
        )

    roster_ids = {
        str(value).strip()
        for value in rosters[roster_id_col].dropna().tolist()
        if str(value).strip()
    }
    name_columns = tuple(
        column
        for column in (
            "display_name",
            "full_name",
            "football_name",
            "common_name",
            "short_name",
        )
        if column in players.columns
    )
    if not name_columns and not {"first_name", "last_name"}.issubset(players.columns):
        raise RuntimeError(
            "identity bridge cannot locate nflverse player name columns; "
            f"available={list(players.columns)}"
        )

    index: dict[tuple[str, str], set[str]] = {}
    known_ids: set[str] = set()
    for _, row in players.iterrows():
        raw_id = row[player_id_col]
        if pd.isna(raw_id):
            continue
        gsis = str(raw_id).strip()
        if not gsis or gsis not in roster_ids:
            continue
        raw_position = row[player_position_col]
        if pd.isna(raw_position):
            continue
        position = str(raw_position).upper()
        if position not in POSITIONS:
            continue
        known_ids.add(gsis)
        for name in _row_names(row, name_columns):
            normalized = _normalize_name(name)
            if normalized:
                index.setdefault((normalized, position), set()).add(gsis)
    return index, known_ids


def _recover_sleeper_stable_ids(
    sleeper: dict[str, dict],
    *,
    source_season: int,
) -> tuple[dict[str, dict], dict[str, int | str]]:
    index, roster_ids = _roster_identity_index(source_season)

    current_name_counts: Counter[tuple[str, str]] = Counter()
    occupied_gsis: Counter[str] = Counter()
    for sleeper_id, raw in sleeper.items():
        position = str(raw.get("position") or "").upper()
        if position not in POSITIONS or not raw.get("team"):
            continue
        name = str(
            raw.get("full_name")
            or " ".join(filter(None, (raw.get("first_name"), raw.get("last_name"))))
            or sleeper_id
        ).strip()
        normalized = _normalize_name(name)
        if normalized:
            current_name_counts[(normalized, position)] += 1
        existing = str(raw.get("gsis_id") or "").strip()
        if existing:
            occupied_gsis[existing] += 1

    proposals: dict[str, str] = {}
    ambiguous_name = 0
    duplicate_current_name = 0
    no_roster_match = 0
    existing_stable_id = 0
    for sleeper_id, raw in sleeper.items():
        position = str(raw.get("position") or "").upper()
        if position not in POSITIONS or not raw.get("team"):
            continue
        existing = str(raw.get("gsis_id") or "").strip()
        if existing:
            existing_stable_id += 1
            continue
        name = str(
            raw.get("full_name")
            or " ".join(filter(None, (raw.get("first_name"), raw.get("last_name"))))
            or sleeper_id
        ).strip()
        normalized = _normalize_name(name)
        key = (normalized, position)
        if not normalized:
            no_roster_match += 1
            continue
        if current_name_counts.get(key, 0) != 1:
            duplicate_current_name += 1
            continue
        candidates = index.get(key, set())
        if len(candidates) == 1:
            proposals[sleeper_id] = next(iter(candidates))
        elif len(candidates) > 1:
            ambiguous_name += 1
        else:
            no_roster_match += 1

    proposed_gsis_counts = Counter(proposals.values())
    recovered = 0
    occupied_collision = 0
    proposal_collision = 0
    output = {key: dict(value) for key, value in sleeper.items()}
    for sleeper_id, gsis in proposals.items():
        if occupied_gsis.get(gsis, 0) > 0:
            occupied_collision += 1
            continue
        if proposed_gsis_counts[gsis] != 1:
            proposal_collision += 1
            continue
        output[sleeper_id]["gsis_id"] = gsis
        recovered += 1

    return output, {
        "version": "completed-source-roster-unique-name-position-v1",
        "source_season": source_season,
        "completed_source_roster_skill_ids": len(roster_ids),
        "existing_current_stable_ids": existing_stable_id,
        "recovered_stable_ids": recovered,
        "ambiguous_roster_name_position": ambiguous_name,
        "duplicate_current_name_position": duplicate_current_name,
        "occupied_stable_id_collision": occupied_collision,
        "proposal_stable_id_collision": proposal_collision,
        "no_completed_source_roster_match": no_roster_match,
    }


def main() -> None:
    builder = _load_builder()
    original_sleepers = builder._sleepers
    original_build_current_facts = builder._build_current_facts
    bridge_audit: dict[str, int | str] = {}

    # The base builder already treats normalized-name matching as a unique,
    # fail-closed fallback. Strengthen only the normalization semantics here.
    builder._normalize_name = _normalize_name

    def bridged_sleepers() -> dict[str, dict]:
        nonlocal bridge_audit
        raw = original_sleepers()
        resolved, bridge_audit = _recover_sleeper_stable_ids(raw, source_season=2025)
        return resolved

    def build_current_facts_with_audit(**kwargs):
        artifact = original_build_current_facts(**kwargs)
        metadata = artifact.get("metadata", {})
        identity = metadata.get("identity_resolution", {})
        if isinstance(identity, dict):
            identity["stable_id_bridge"] = dict(bridge_audit)
        old_version = str(artifact.get("source_version") or "")
        if old_version:
            new_version = old_version.replace(
                "frozen-coordinate-v3",
                "frozen-coordinate-v4-identity-bridge",
            )
            artifact["source_version"] = new_version
            for row in artifact.get("rows", []):
                if isinstance(row, dict):
                    row["source_version"] = new_version
        return artifact

    builder._sleepers = bridged_sleepers
    builder._build_current_facts = build_current_facts_with_audit
    builder.main()


if __name__ == "__main__":
    main()
