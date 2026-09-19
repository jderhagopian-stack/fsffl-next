from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fsffl.forecast.integrated_i1 import age_band, fit_state_boundaries, state_for_points
from fsffl.state.models import Position


POSITIONS = ("QB", "RB", "WR", "TE")
SENTINELS = (
    "Aaron Rodgers",
    "Sam Darnold",
    "Bijan Robinson",
    "Jahmyr Gibbs",
    "Puka Nacua",
    "Christian McCaffrey",
    "Brock Bowers",
    "Trey McBride",
)
SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}
PROVIDER_NAME_COLUMNS = ("display_name", "full_name", "football_name", "common_name", "short_name")
SCHEMA_VERSION = "fsffl-replacement-identity-materialization-coordinate-v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def normalize_name(value: object) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split()
    while tokens and tokens[-1] in SUFFIX_TOKENS:
        tokens.pop()
    return "".join(tokens)


def position_value(value: object) -> str:
    return str(value or "").strip().upper()


def text_value(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def identifier_value(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip() or None


def player_aliases(row: pd.Series) -> list[str]:
    aliases: set[str] = set()
    for column in PROVIDER_NAME_COLUMNS:
        if column in row.index:
            value = text_value(row.get(column))
            if value:
                aliases.add(value)
    first = text_value(row.get("first_name")) if "first_name" in row.index else None
    last = text_value(row.get("last_name")) if "last_name" in row.index else None
    if first and last:
        aliases.add(f"{first} {last}")
    return sorted(aliases)


def load_provider_snapshot(players_path: Path, roster_path: Path) -> tuple[dict[str, dict], dict[tuple[str, str], set[str]], dict[str, Any]]:
    players = pd.read_csv(players_path, low_memory=False)
    roster = pd.read_csv(roster_path, low_memory=False)
    required_players = {"gsis_id", "position_group"}
    required_roster = {"gsis_id", "season"}
    if not required_players.issubset(players.columns) or not required_roster.issubset(roster.columns):
        raise ValueError("provider snapshots do not contain required identity columns")

    roster = roster[roster["season"].astype(int) == 2025].copy()
    roster_ids = {str(value).strip() for value in roster["gsis_id"].dropna() if str(value).strip()}
    roster_by_gsis: dict[str, dict] = {}
    for _, row in roster.iterrows():
        gsis = text_value(row.get("gsis_id"))
        if not gsis:
            continue
        candidate = {
            "team": text_value(row.get("team")),
            "position": position_value(row.get("position")),
            "sleeper_id": identifier_value(row.get("sleeper_id")),
            "status": text_value(row.get("status")),
        }
        prior = roster_by_gsis.get(gsis)
        if prior is None or canonical_bytes(candidate) < canonical_bytes(prior):
            roster_by_gsis[gsis] = candidate

    provider: dict[str, dict] = {}
    name_index: dict[tuple[str, str], set[str]] = {}
    for _, row in players.iterrows():
        gsis = text_value(row.get("gsis_id"))
        position = position_value(row.get("position_group") or row.get("position"))
        if not gsis or position not in POSITIONS:
            continue
        aliases = player_aliases(row)
        normalized_aliases = sorted({normalize_name(name) for name in aliases if normalize_name(name)})
        record = {
            "gsis_id": gsis,
            "position": position,
            "aliases": aliases,
            "normalized_aliases": normalized_aliases,
            "on_2025_roster": gsis in roster_ids,
            "roster": roster_by_gsis.get(gsis),
        }
        provider[gsis] = record
        if gsis in roster_ids:
            for normalized in normalized_aliases:
                name_index.setdefault((normalized, position), set()).add(gsis)

    governed_rows = [provider[key] for key in sorted(provider) if provider[key]["on_2025_roster"]]
    snapshot = {
        "schema_version": "fsffl-nflverse-identity-snapshot-v1",
        "source_season": 2025,
        "rule": "players restricted to roster_2025 GSIS ids; skill positions only; aliases use the activation-path normalization fields",
        "skill_player_count": len(governed_rows),
        "rows": governed_rows,
    }
    return provider, name_index, snapshot


def direct_gsis(row: dict) -> str | None:
    refs = row.get("provider_refs") or []
    values = sorted({str(ref.get("external_id") or "").strip() for ref in refs if ref.get("provider") == "gsis" and str(ref.get("external_id") or "").strip()})
    return values[0] if len(values) == 1 else None


def point_in_time_residuals(panel: pd.DataFrame, season: int) -> tuple[dict[str, dict], dict[str, Any]]:
    panel = panel.copy()
    prior = panel[panel["season"] < season].copy()
    current = panel[panel["season"] == season].copy()
    result: dict[str, dict] = {}
    position_audit: dict[str, Any] = {}
    for position in POSITIONS:
        values = prior.loc[(prior["position"] == position) & (prior["fantasy_points"] > 0), "fantasy_points"].tolist()
        if len(values) < 20:
            raise ValueError(f"insufficient PIT boundary rows for {position} {season}")
        boundaries = fit_state_boundaries(values)
        pp = prior[prior["position"] == position].copy()
        pp["state"] = [state_for_points(float(value), boundaries) for value in pp["fantasy_points"]]
        pp["age_band"] = [age_band(Position[position], float(value) if np.isfinite(value) else None) for value in pp["age_years"]]
        state_stats: dict[str, tuple[int, float, float]] = {}
        age_state_stats: dict[tuple[str, str], tuple[int, float, float]] = {}
        for state, group in pp.groupby("state"):
            data = group["fantasy_points"].to_numpy(dtype=float)
            mean = float(data.mean())
            std = float(data.std(ddof=1)) if len(data) > 1 else 0.0
            if std < 1e-6:
                std = max(1.0, abs(mean) * 0.25)
            state_stats[str(state)] = (len(data), mean, std)
        for (band, state), group in pp.groupby(["age_band", "state"]):
            data = group["fantasy_points"].to_numpy(dtype=float)
            mean = float(data.mean())
            std = float(data.std(ddof=1)) if len(data) > 1 else 0.0
            if std < 1e-6:
                std = max(1.0, abs(mean) * 0.25)
            age_state_stats[(str(band), str(state))] = (len(data), mean, std)
        position_audit[position] = {
            "positive_prior_rows": len(values),
            "boundaries": [list(group) for group in boundaries],
        }
        for _, row in current[current["position"] == position].iterrows():
            gsis = str(row["player_id"])
            points = float(row["fantasy_points"])
            player_state = str(state_for_points(points, boundaries))
            band = str(age_band(Position[position], float(row["age_years"]) if np.isfinite(row["age_years"]) else None))
            fallback = state_stats.get(player_state)
            if fallback is None or fallback[0] < 10:
                continue
            primary = age_state_stats.get((band, player_state))
            if primary is not None and primary[0] >= 10:
                n, mean, std = primary
                scope = "position_age_band_state"
            else:
                n, mean, std = fallback
                scope = "position_state_fallback"
            result[gsis] = {
                "season": season,
                "source_key": f"{gsis}:{season}",
                "fantasy_points": points,
                "age_years": None if not np.isfinite(row["age_years"]) else float(row["age_years"]),
                "experience_years": int(row["experience_years"]),
                "state": player_state,
                "age_band": band,
                "age_state_residual_z": float((points - mean) / std),
                "residual_scope": scope,
                "reference_n": int(n),
                "reference_mean": float(mean),
                "reference_sd": float(std),
            }
    return result, position_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year1-universe", type=Path, required=True)
    parser.add_argument("--phase2-panel", type=Path, required=True)
    parser.add_argument("--phase2-q3-rows", type=Path, required=True)
    parser.add_argument("--players-snapshot", type=Path, required=True)
    parser.add_argument("--roster-snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--coordinate-as-of", required=True)
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=False)
    year1 = json.loads(args.year1_universe.read_text())
    current_rows = year1["rows"]
    if len(current_rows) != 335:
        raise ValueError(f"expected 335 frozen Year-1 rows, found {len(current_rows)}")
    provider, name_index, provider_snapshot = load_provider_snapshot(args.players_snapshot, args.roster_snapshot)
    panel = pd.read_csv(args.phase2_panel, low_memory=False)
    panel = panel[panel["position"].isin(POSITIONS)].copy()
    panel["season"] = panel["season"].astype(int)
    panel["fantasy_points"] = pd.to_numeric(panel["fantasy_points"], errors="coerce").fillna(0.0)
    panel["age_years"] = pd.to_numeric(panel["age_years"], errors="coerce")
    panel["experience_years"] = pd.to_numeric(panel["experience_years"], errors="coerce").fillna(0).astype(int)
    pit_2023, pit_audit_2023 = point_in_time_residuals(panel, 2023)
    pit_2024, pit_audit_2024 = point_in_time_residuals(panel, 2024)
    pit_2022, _pit_audit_2022 = point_in_time_residuals(panel, 2022)
    q3_rows = pd.read_csv(args.phase2_q3_rows, low_memory=False)
    frozen_2022 = q3_rows[(q3_rows["source_season"] == 2022) & (q3_rows["horizon"] == 1)].copy()
    parity_diffs = []
    parity_scope_mismatches = []
    parity_missing = []
    for row in frozen_2022.itertuples(index=False):
        gsis = str(row.player_id)
        rebuilt = pit_2022.get(gsis)
        if rebuilt is None:
            parity_missing.append(gsis)
            continue
        parity_diffs.append(abs(float(rebuilt["age_state_residual_z"]) - float(row.current_age_state_resid_z)))
        if str(rebuilt["residual_scope"]) != str(row.age_state_residual_scope):
            parity_scope_mismatches.append(gsis)
    frozen_method_parity = {
        "season": 2022,
        "frozen_rows": len(frozen_2022),
        "rebuilt_rows_compared": len(parity_diffs),
        "max_abs_residual_z_diff": max(parity_diffs) if parity_diffs else None,
        "scope_mismatches": len(parity_scope_mismatches),
        "missing_rebuilt_rows": len(parity_missing),
        "status": "PASS" if parity_diffs and max(parity_diffs) <= 1e-12 and not parity_scope_mismatches and not parity_missing else "FAIL",
    }
    if frozen_method_parity["status"] != "PASS":
        raise RuntimeError(f"frozen PIT method parity failed: {frozen_method_parity}")

    current_name_counts: Counter[tuple[str, str]] = Counter()
    for row in current_rows:
        current_name_counts[(normalize_name(row["full_name"]), position_value(row["position"]))] += 1

    provisional: list[dict] = []
    for row in current_rows:
        row_key = str(row["player_id"])
        sleeper_id = str(row["completed_source_player_id"])
        name = str(row["full_name"])
        position = position_value(row["position"])
        normalized = normalize_name(name)
        supplied_gsis = direct_gsis(row)
        gsis: str | None = None
        status = "UNMATCHED"
        method = "UNMATCHED"
        reason = "NO_EXACT_NAME_POSITION_MATCH"
        direct_validation = "NOT_PRESENT"
        candidates: list[str] = []

        if supplied_gsis:
            record = provider.get(supplied_gsis)
            if record is None:
                direct_validation = "GSIS_NOT_IN_PROVIDER_SNAPSHOT"
            elif record["position"] != position:
                direct_validation = "POSITION_MISMATCH"
            elif normalized not in record["normalized_aliases"]:
                direct_validation = "NAME_MISMATCH"
            else:
                direct_validation = "VALID"
                gsis = supplied_gsis
                status = "DIRECT_ID"
                method = "DIRECT_ID"
                reason = None

        if gsis is None:
            key = (normalized, position)
            candidates = sorted(name_index.get(key, set()))
            if not normalized:
                reason = "EMPTY_NORMALIZED_NAME"
            elif current_name_counts[key] != 1:
                reason = "CURRENT_NAME_POSITION_NOT_REVERSE_UNIQUE"
                status = "AMBIGUOUS"
                method = "AMBIGUOUS"
            elif len(candidates) == 1:
                gsis = candidates[0]
                status = "EXACT_NAME_POSITION"
                method = "EXACT_NAME_POSITION"
                reason = None
            elif len(candidates) > 1:
                reason = "MULTIPLE_PROVIDER_NAME_POSITION_CANDIDATES"
                status = "AMBIGUOUS"
                method = "AMBIGUOUS"

        provisional.append({
            "year1_row_key": row_key,
            "current_player_id": sleeper_id,
            "player_name": name,
            "normalized_name": normalized,
            "position": position,
            "historical_gsis_id": gsis,
            "mapping_status": status,
            "mapping_method": method,
            "mapping_reason_code": reason,
            "direct_gsis_in_year1": supplied_gsis,
            "direct_id_validation": direct_validation,
            "exact_name_position_candidates": candidates,
        })

    accepted_counts = Counter(row["historical_gsis_id"] for row in provisional if row["historical_gsis_id"])
    for row in provisional:
        gsis = row["historical_gsis_id"]
        if gsis and accepted_counts[gsis] > 1:
            row["historical_gsis_id"] = None
            row["mapping_status"] = "AMBIGUOUS"
            row["mapping_method"] = "AMBIGUOUS"
            row["mapping_reason_code"] = "HISTORICAL_ID_COLLISION"

    coordinate_rows: list[dict] = []
    for row in provisional:
        gsis = row["historical_gsis_id"]
        season_2024 = pit_2024.get(gsis) if gsis else None
        season_2023 = pit_2023.get(gsis) if gsis else None
        if row["mapping_status"] in {"UNMATCHED", "AMBIGUOUS"}:
            coverage_reason = f"IDENTITY_{row['mapping_status']}"
            coverage = 0
        elif season_2024 is None and season_2023 is None:
            coverage_reason = "NO_2024_OR_2023_HISTORY"
            coverage = 0
        elif season_2024 is None:
            coverage_reason = "MISSING_2024_HISTORY"
            coverage = 0
        elif season_2023 is None:
            coverage_reason = "MISSING_2023_HISTORY"
            coverage = 0
        else:
            coverage_reason = "TWO_GENUINE_PRIOR_SEASONS"
            coverage = 1
        if coverage:
            z_2024 = float(season_2024["age_state_residual_z"])
            z_2023 = float(season_2023["age_state_residual_z"])
            mean_z = (z_2024 + z_2023) / 2.0
            gap_z = abs(z_2024 - z_2023)
        else:
            mean_z = 0.0
            gap_z = 0.0
        provider_record = provider.get(gsis) if gsis else None
        coordinate_rows.append({
            **row,
            "identity_snapshot_coordinate": "nflverse-players-20260918T123430Z+roster-2025-20260314",
            "identity_provider_record": None if provider_record is None else {
                "position": provider_record["position"],
                "aliases": provider_record["aliases"],
                "on_2025_roster": provider_record["on_2025_roster"],
            },
            "pit_2024_available": season_2024 is not None,
            "pit_2024": season_2024,
            "pit_2023_available": season_2023 is not None,
            "pit_2023": season_2023,
            "pit_source_coordinate": "phase2-player-season-panel-c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7",
            "prior2_mean_age_state_z": mean_z,
            "prior2_abs_gap_age_state_z": gap_z,
            "prior2_coverage": coverage,
            "prior2_coverage_reason": coverage_reason,
        })
    coordinate_rows.sort(key=lambda item: item["year1_row_key"])

    coordinate_id = f"replacement-identity-materialization-v1:{args.coordinate_as_of}"
    rows_sha256 = sha256_bytes(canonical_bytes(coordinate_rows))
    population_sha256 = sha256_bytes(canonical_bytes(sorted(row["year1_row_key"] for row in coordinate_rows)))
    coordinate = {
        "schema_version": SCHEMA_VERSION,
        "coordinate_id": coordinate_id,
        "coordinate_kind": "NEW replacement identity/materialization evidence coordinate; not recovery of original bridge",
        "as_of": args.coordinate_as_of,
        "frozen_year1_coordinate_id": year1["coordinate_id"],
        "row_count": len(coordinate_rows),
        "rows_sha256": rows_sha256,
        "population_sha256": population_sha256,
        "independence": {
            "downstream_y2_y3_materialized": False,
            "sentinel_forecast_parity_run": False,
            "intrinsic_or_shapley_run": False,
            "ranking_output_inspected": False,
        },
        "rows": coordinate_rows,
    }

    mapping_counts = Counter(row["mapping_status"] for row in coordinate_rows)
    reason_counts = Counter(row["mapping_reason_code"] for row in coordinate_rows if row["mapping_reason_code"])
    coverage_counts = Counter(row["prior2_coverage_reason"] for row in coordinate_rows)
    collision_rows = [row for row in coordinate_rows if row["mapping_status"] in {"UNMATCHED", "AMBIGUOUS"}]
    crossid_checks = []
    for row in coordinate_rows:
        gsis = row["historical_gsis_id"]
        provider_record = provider.get(gsis) or {} if gsis else {}
        roster_sleeper = (provider_record.get("roster") or {}).get("sleeper_id")
        if roster_sleeper:
            current_sleeper = row["current_player_id"].split(":", 1)[-1]
            crossid_checks.append({
                "year1_row_key": row["year1_row_key"],
                "gsis_id": gsis,
                "current_sleeper_id": current_sleeper,
                "provider_sleeper_id": roster_sleeper,
                "agrees": current_sleeper == roster_sleeper,
            })
    collision_audit = {
        "coordinate_id": coordinate_id,
        "mapping_status_counts": dict(sorted(mapping_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "by_position": {
            position: dict(sorted(Counter(row["mapping_status"] for row in coordinate_rows if row["position"] == position).items()))
            for position in POSITIONS
        },
        "posthoc_provider_crossid_validation": {
            "purpose": "independent audit only; provider Sleeper cross-ID was not an authorized mapping rule and was not used to accept a match",
            "rows_checked": len(crossid_checks),
            "agreements": sum(bool(row["agrees"]) for row in crossid_checks),
            "disagreements": sum(not bool(row["agrees"]) for row in crossid_checks),
            "disagreement_rows": [row for row in crossid_checks if not row["agrees"]],
        },
        "rows": [{key: row[key] for key in ("year1_row_key", "current_player_id", "player_name", "position", "mapping_status", "mapping_reason_code", "exact_name_position_candidates")} for row in collision_rows],
    }
    sentinel_rows = [row for row in coordinate_rows if row["player_name"] in SENTINELS]
    sentinel_audit = {
        "coordinate_id": coordinate_id,
        "expected_sentinels": list(SENTINELS),
        "found": len(sentinel_rows),
        "forecast_values_included": False,
        "rows": [{key: row[key] for key in ("player_name", "position", "current_player_id", "historical_gsis_id", "mapping_status", "pit_2024_available", "pit_2023_available", "prior2_coverage", "prior2_coverage_reason")} for row in sorted(sentinel_rows, key=lambda item: SENTINELS.index(item["player_name"]))],
    }
    pit_audit = {
        "coordinate_id": coordinate_id,
        "coverage_reason_counts": dict(sorted(coverage_counts.items())),
        "prior2_covered": sum(row["prior2_coverage"] for row in coordinate_rows),
        "pit_2024_available": sum(bool(row["pit_2024_available"]) for row in coordinate_rows),
        "pit_2023_available": sum(bool(row["pit_2023_available"]) for row in coordinate_rows),
        "by_position": {
            position: {
                "rows": sum(row["position"] == position for row in coordinate_rows),
                "prior2_covered": sum(row["prior2_coverage"] for row in coordinate_rows if row["position"] == position),
            }
            for position in POSITIONS
        },
        "pit_method_audit": {"2023": pit_audit_2023, "2024": pit_audit_2024},
        "frozen_method_parity": frozen_method_parity,
    }

    provider_snapshot.update({
        "coordinate_id": "nflverse-players-20260918T123430Z+roster-2025-20260314",
        "retrieved_at": args.coordinate_as_of,
        "raw_sources": {
            "players": {
                "url": "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv",
                "release_asset_id": 572597132,
                "asset_updated_at": "2026-09-18T12:34:30Z",
                "sha256": sha256_file(args.players_snapshot),
            },
            "roster_2025": {
                "url": "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2025.csv",
                "release_asset_id": 373640814,
                "asset_updated_at": "2026-03-14T07:33:08Z",
                "sha256": sha256_file(args.roster_snapshot),
            },
        },
        "raw_snapshot_persistence": "Raw provider files are not redistributed; exact governed identity fields used by the deterministic matcher are persisted below with upstream asset ids, timestamps, URLs, and raw hashes.",
    })

    paths = {
        "coordinate": output_dir / "replacement_identity_materialization_coordinate.json",
        "provider_snapshot": output_dir / "provider_identity_snapshot.json",
        "collision_audit": output_dir / "collision_unmatched_audit.json",
        "sentinel_audit": output_dir / "sentinel_identity_audit.json",
        "pit_audit": output_dir / "pit_coverage_audit.json",
    }
    write_json(paths["coordinate"], coordinate)
    write_json(paths["provider_snapshot"], provider_snapshot)
    write_json(paths["collision_audit"], collision_audit)
    write_json(paths["sentinel_audit"], sentinel_audit)
    write_json(paths["pit_audit"], pit_audit)

    manifest = {
        "schema_version": "fsffl-replacement-identity-materialization-manifest-v1",
        "coordinate_id": coordinate_id,
        "as_of": args.coordinate_as_of,
        "inputs": {
            "builder_script": {"path": str(Path(__file__).resolve().relative_to(Path.cwd())), "sha256": sha256_file(Path(__file__).resolve())},
            "frozen_year1_universe": {"path": str(args.year1_universe), "sha256": sha256_file(args.year1_universe)},
            "phase2_player_season_panel": {"path": "external recovered Phase2 archive/future-state-phase2/phase2_player_season_panel.csv", "sha256": sha256_file(args.phase2_panel)},
            "phase2_q3_age_state_rows": {"path": "external recovered Phase2 archive/future-state-phase2/phase2_q3_age_state_rows.csv", "sha256": sha256_file(args.phase2_q3_rows)},
            "provider_players_raw": {"release_asset_id": 572597132, "sha256": sha256_file(args.players_snapshot)},
            "provider_roster_2025_raw": {"release_asset_id": 373640814, "sha256": sha256_file(args.roster_snapshot)},
        },
        "rules": {
            "priority": ["DIRECT_ID", "CANONICAL_CROSSID", "EXACT_NAME_POSITION"],
            "canonical_crossid_sources_found": [],
            "name_normalization": "lowercase; replace non-alphanumeric with spaces; split; strip trailing jr/sr/ii/iii/iv/v; concatenate",
            "name_position_acceptance": "exact normalized full name + compatible position; exactly one provider candidate; reverse-unique current name+position; no accepted GSIS collision",
            "forbidden_tie_breaks_used": [],
            "pit": "Frozen Phase2 Q3 age/state residual definition; each season uses only panel seasons strictly earlier than that season; no fitted model parameters estimated.",
        },
        "outputs": {
            name: {"file": path.name, "sha256": sha256_file(path)} for name, path in paths.items()
        },
        "row_count": len(coordinate_rows),
        "rows_sha256": rows_sha256,
        "population_sha256": population_sha256,
        "mapping_status_counts": dict(sorted(mapping_counts.items())),
        "prior2_coverage_reason_counts": dict(sorted(coverage_counts.items())),
        "posthoc_provider_crossid_validation": collision_audit["posthoc_provider_crossid_validation"],
        "frozen_method_parity": frozen_method_parity,
        "independence": coordinate["independence"],
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, manifest)

    reloaded = json.loads(paths["coordinate"].read_text())
    reloaded_rows_sha256 = sha256_bytes(canonical_bytes(reloaded["rows"]))
    reload_verification = {
        "status": "PASS" if len(reloaded["rows"]) == 335 and reloaded_rows_sha256 == rows_sha256 else "FAIL",
        "fresh_read_path": str(paths["coordinate"]),
        "row_count_expected": 335,
        "row_count_reloaded": len(reloaded["rows"]),
        "rows_sha256_expected": rows_sha256,
        "rows_sha256_reloaded": reloaded_rows_sha256,
        "population_sha256_reloaded": sha256_bytes(canonical_bytes(sorted(row["year1_row_key"] for row in reloaded["rows"]))),
    }
    write_json(output_dir / "reload_verification.json", reload_verification)
    if reload_verification["status"] != "PASS":
        raise RuntimeError("replacement coordinate reload verification failed")
    print(json.dumps({
        "coordinate_id": coordinate_id,
        "row_count": len(coordinate_rows),
        "rows_sha256": rows_sha256,
        "mapping_status_counts": dict(sorted(mapping_counts.items())),
        "coverage_reason_counts": dict(sorted(coverage_counts.items())),
        "sentinels_found": len(sentinel_rows),
        "reload_status": reload_verification["status"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
