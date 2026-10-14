#!/usr/bin/env python3
"""Offline exact-GSIS historical coverage audit; no network or production writes.

A third-party stats CSV requires an explicit approved-rights record matching
the file SHA256. This is a source-readiness tool, NOT commercial legal approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(manifest_path: Path | None, file_path: Path) -> dict:
    if manifest_path is None:
        raise ValueError("Historical data not loaded: --rights-manifest is required for --stats")
    meta = json.loads(manifest_path.read_text(encoding="utf-8"))
    if meta.get("decision") != "GO" or meta.get("allow_offline_research") is not True:
        raise ValueError("Historical data not loaded: manifest must expressly permit research (GO)")
    if not meta.get("license_evidence_url") or not meta.get("origin"):
        raise ValueError("Historical data not loaded: license evidence and source origin required")
    if meta.get("file_sha256") != sha256(file_path):
        raise ValueError("Historical data not loaded: SHA256 does not match approved manifest")
    return meta


def load_reference(file_path: Path) -> list[dict]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"player_id", "historical_gsis_id", "position", "player_name"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Reference CSV missing required columns")
        subjects = list(reader)
    if len({r["player_id"] for r in subjects}) != len(subjects):
        raise ValueError("Duplicate FSFFL player_id")
    gsis_ids = [r["historical_gsis_id"].strip() for r in subjects if r["historical_gsis_id"].strip()]
    if len(gsis_ids) != len(set(gsis_ids)):
        raise ValueError("Duplicate nonempty GSIS identifier")
    return subjects


def load_stats(file_path: Path, start: int, end: int) -> tuple[dict, dict]:
    """Streaming source row coverage. Missing source rows are NEVER scored as zero."""
    panel = {}
    totals = Counter()
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"player_id", "season"}.issubset(set(reader.fieldnames or [])):
            raise ValueError("Stats CSV must have player_id (GSIS) and season")
        metrics = [key for key in (
            "passing_yards", "passing_tds", "interceptions", "carries",
            "rushing_yards", "rushing_tds", "targets", "receptions",
            "receiving_yards", "receiving_tds"
        ) if key in (reader.fieldnames or [])]
        for row in reader:
            totals["rows_read"] += 1
            season = int(row["season"]) if row.get("season") else None
            gsis = row.get("player_id", "").strip()
            if season is None or not start <= season <= end or not gsis:
                totals["rows_skipped_outside_window_or_id"] += 1
                continue
            key = gsis, season
            slot = panel.setdefault(key, {"rows": 0, "weeks": set(), "present": Counter()})
            slot["rows"] += 1
            if row.get("week", "").strip():
                slot["weeks"].add(row["week"].strip())
            for metric in metrics:
                if row.get(metric, "").strip() not in ("", "NA", "NaN", "null", "None"):
                    slot["present"][metric] += 1
            totals["rows_accepted"] += 1
    return panel, {"columns_checked": metrics, "counts": dict(totals)}


def audit(reference: Path, stats: Path | None, rights_manifest: Path | None,
          output: Path, start: int, end: int) -> dict:
    if end < start or start < 1990 or end > 2100:
        raise ValueError("Invalid season range")
    if stats is not None:
        rights = validate_manifest(rights_manifest, stats)
        panel, source = load_stats(stats, start, end)
    else:
        if rights_manifest is not None:
            raise ValueError("--rights-manifest provided without --stats")
        rights, panel, source = None, {}, None
    subjects = load_reference(reference)
    if not subjects:
        raise ValueError("Empty reference cohort")
    output.mkdir(parents=True, exist_ok=True)
    by_position = defaultdict(Counter)
    detailed = []
    for subject in subjects:
        pos = subject["position"]
        gsis = subject["historical_gsis_id"].strip()
        by_position[pos]["subjects"] += 1
        by_position[pos]["with_gsis"] += bool(gsis)
        seen_years = sorted(year for (pid, year) in panel if pid == gsis) if gsis and stats else []
        if stats is not None and gsis:
            by_position[pos]["any_stats_year_match"] += bool(seen_years)
        detailed.append({
            "player_id": subject["player_id"],
            "name": subject["player_name"],
            "position": pos,
            "historical_gsis_id": gsis,
            "identity": "HAS_GSIS" if gsis else "NO_GSIS",
            "stats_status": ("NOT_TESTED" if stats is None else
                             "NO_GSIS" if not gsis else
                             "MATCHED_YEAR" if seen_years else "NO_SOURCE_ROW"),
            "matched_seasons": ";".join(map(str, seen_years)),
            "matched_season_count": len(seen_years),
        })
    with (output / "subject_coverage.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detailed[0]))
        writer.writeheader()
        writer.writerows(detailed)
    result = {
        "mode": "EXTERNAL_RIGHTS_APPROVED" if stats else "INTERNAL_ONLY",
        "reference_sha256": sha256(reference),
        "subject_count": len(subjects),
        "subjects_with_gsis": sum(bool(s["historical_gsis_id"].strip()) for s in subjects),
        "subjects_without_gsis": sum(not bool(s["historical_gsis_id"].strip()) for s in subjects),
        "season_window": [start, end],
        "by_position": {p: dict(c) for p, c in sorted(by_position.items())},
        "stats_sha256": sha256(stats) if stats else None,
        "stats_observations": source,
        "source_rights": {
            "decision": rights["decision"],
            "evidence_url": rights["license_evidence_url"],
            "origin": rights["origin"],
        } if rights else "NOT_USED",
        "limitations": [
            "An absent row is not evidence of a score of zero, injury, or retirement.",
            "Matched source IDs do not establish full field completeness or forecast authority.",
            "Historical data must satisfy source-specific commercial and point-in-time rules.",
            "This tool does not authorize product use or ingestion and performs no ML training."
        ],
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--stats", type=Path)
    parser.add_argument("--rights-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=2019)
    parser.add_argument("--end", type=int, default=2025)
    args = parser.parse_args()
    result = audit(args.reference, args.stats, args.rights_manifest,
                   args.output, args.start, args.end)
    print(json.dumps({key: result[key] for key in (
        "mode", "subject_count", "subjects_with_gsis",
        "subjects_without_gsis", "by_position"
    )}, indent=2))


if __name__ == "__main__":
    main()
