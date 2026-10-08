"""Fail-closed PR1 replay comparison for accepted FSFFL Foundation 4 evidence.

Comparison is against the untouched run 37096263982 output. New subjects never
participate in training, route selection, normalizing, or parity acceptance.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

KEYS = {
    "board": ("player_id", "position", "evaluation_season", "year_index", "target_season", "policy_id"),
    "metrics": ("position", "horizon", "policy"),
    "terminal": ("player_id", "position"),
}
BOARD_NUMBERS = {"central_expectation", "absolute_error_80", "absolute_error_90"}
METRICS_FILE = "FOUNDATION4_FSFFL_ROLLING_POLICY_CELL_METRICS.csv"
BOARD_FILE = "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv"
TERMINAL_FILE = "FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.csv"


def compare_csv(name: str, expected: Path, actual: Path, atol: float, rtol: float) -> dict:
    with expected.open(newline="") as handle:
        reference = list(csv.DictReader(handle))
    with actual.open(newline="") as handle:
        observed = list(csv.DictReader(handle))
    if not reference or not observed:
        raise AssertionError(f"{name}: empty artifact")
    if set(reference[0]) != set(observed[0]):
        raise AssertionError(f"{name}: column mismatch {set(reference[0]) ^ set(observed[0])}")
    keys = KEYS[name]
    reference_map = {tuple(row[k] for k in keys): row for row in reference}
    observed_map = {tuple(row[k] for k in keys): row for row in observed}
    if len(reference_map) != len(reference) or len(observed_map) != len(observed):
        raise AssertionError(f"{name}: duplicate compound key")
    if reference_map.keys() != observed_map.keys():
        raise AssertionError(
            f"{name}: differing keys missing={list(reference_map.keys() - observed_map.keys())[:4]}, "
            f"extra={list(observed_map.keys() - reference_map.keys())[:4]}"
        )
    failures = []
    worst_abs = 0.0
    numeric_values_checked = 0
    for key, reference_row in reference_map.items():
        actual_row = observed_map[key]
        for column, expected_value in reference_row.items():
            got = actual_row[column]
            if expected_value == got:
                continue
            # Numerical replay is checked for any finite numeric field;
            # all identities, routes, policies, units, metadata remain exact.
            try:
                e, a = float(expected_value), float(got)
            except (ValueError, TypeError):
                failures.append((key, column, expected_value, got))
                continue
            if not (math.isfinite(e) and math.isfinite(a)):
                failures.append((key, column, expected_value, got))
                continue
            numeric_values_checked += 1
            worst_abs = max(worst_abs, abs(e - a))
            if not math.isclose(e, a, abs_tol=atol, rel_tol=rtol):
                failures.append((key, column, expected_value, got))
    if failures:
        raise AssertionError(f"{name}: {len(failures)} mismatches; first={failures[:7]}; worst_abs={worst_abs}")
    return {
        "rows": len(reference),
        "keys": len(reference_map),
        "nonidentical_numeric_values_within_tolerance": numeric_values_checked,
        "max_absolute_difference": worst_abs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--replay", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    # Strict deterministic numerical tolerance, not a statistical/model acceptance band.
    ap.add_argument("--atol", type=float, default=1e-8)
    ap.add_argument("--rtol", type=float, default=1e-10)
    args = ap.parse_args()
    results = {
        "reference_run": 37096263982,
        "accepted_research_commit": "be2541a496227b33c12c755f576843dc4ab5a0bb",
        "tolerance": {"atol": args.atol, "rtol": args.rtol},
    }
    for label, filename in (
        ("board", BOARD_FILE),
        ("metrics", METRICS_FILE),
        ("terminal", TERMINAL_FILE),
    ):
        results[label] = compare_csv(
            label, args.reference / filename, args.replay / filename, args.atol, args.rtol
        )
    with (args.reference / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_SUMMARY.json").open() as f:
        frozen_summary = json.load(f)
    with (args.replay / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_SUMMARY.json").open() as f:
        replay_summary = json.load(f)
    if frozen_summary != replay_summary:
        raise AssertionError("Board summary/authority changed")
    if results["board"]["rows"] != 5360 or results["terminal"]["rows"] != 335:
        raise AssertionError("Frozen 335 population/cardinality drift")
    with (args.reference / BOARD_FILE).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len({r["player_id"] for r in rows}) != 335:
        raise AssertionError("Frozen reference no longer contains 335 unique subjects")
    expected_keys = {(r["player_id"], int(r["year_index"]), r["policy_id"]) for r in rows}
    if len(expected_keys) != 5360:
        raise AssertionError("Frozen position/horizon/policy combinations missing")
    if Counter((r["year_index"], r["policy_id"]) for r in rows) != Counter(
        {(str(h), p): 335 for h in (4, 5, 6, 7) for p in ("baseline", "hard_router", "soft_stack", "blanket_75_25")}
    ):
        raise AssertionError("Frozen policy/horizon cardinality mismatch")
    results["pass"] = True
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    main()
