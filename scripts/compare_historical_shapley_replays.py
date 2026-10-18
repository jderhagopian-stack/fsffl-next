"""Compare full historical production-engine replay against archived corrected standalone data.

Fail closed on missing, extra, changed, or non-finite contributions. This is a
research acceptance gate; the archived file is NOT accepted production authority.
Usage:
 python scripts/compare_historical_shapley_replays.py corrected_archive.json production_engine.json
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def archived_rows(document: dict) -> dict[tuple[int, str, int], float | None]:
    rows = {}
    for cohort in document["cohorts"]:
        start = int(cohort["start_season"])
        for player in cohort["players"]:
            values = player.get("annual_shapley_hindsight")
            if values is None:
                raise ValueError("missing archived annual hindsight")
            for year_offset, value in enumerate(values):
                key = (start, player["id"], year_offset)
                if key in rows:
                    raise ValueError("duplicate archived player-year")
                rows[key] = value
    return rows


def production_rows(document: dict) -> dict[tuple[int, str, int], float | None]:
    if document.get("evidence_kind") != "hindsight_production_shapley_not_career_intrinsic":
        raise ValueError("not a production-engine hindsight replay")
    rows = {}
    for cohort in document["cohorts"]:
        start = int(cohort["start_season"])
        for player in cohort["players"]:
            for offset, value in enumerate(player["annual_observed_shapley"]):
                key = (start, player["player_id"], offset)
                if key in rows:
                    raise ValueError("duplicate production player-year")
                rows[key] = value
    return rows


def compare(archived: dict, production: dict, *, tolerance: float = 1e-7) -> dict:
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("invalid tolerance")
    old = archived_rows(archived)
    new = production_rows(production)
    mismatches = []
    all_keys = sorted(set(old) | set(new))
    for key in all_keys:
        if key not in old or key not in new:
            mismatches.append({"key": key, "issue": "missing_player_year"})
            continue
        a, b = old[key], new[key]
        if a is None or b is None:
            if a is not None or b is not None:
                mismatches.append({"key": key, "issue": "different_missingness"})
        elif not all(math.isfinite(float(v)) for v in (a, b)):
            mismatches.append({"key": key, "issue": "nonfinite"})
        elif abs(float(a) - float(b)) > tolerance:
            mismatches.append({"key": key, "issue": "numerical_drift", "archive": a, "production": b})
    return {"status": "pass" if not mismatches else "fail",
            "compared": len(all_keys), "mismatch_count": len(mismatches),
            "first_mismatches": mismatches[:30], "tolerance": tolerance}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archived_json", type=Path)
    parser.add_argument("production_json", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-7)
    args = parser.parse_args()
    report = compare(json.loads(args.archived_json.read_text()),
                     json.loads(args.production_json.read_text()), tolerance=args.tolerance)
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
