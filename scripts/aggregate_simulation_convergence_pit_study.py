from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


PRODUCTION_COUNT = 50_000
REFERENCE_COUNT = 100_000


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _aggregate(rows: list[dict[str, float | bool | None]]) -> dict[str, Any]:
    keys = sorted({key for row in rows for key in row})
    out: dict[str, Any] = {}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        if not values:
            out[key] = None
        elif all(isinstance(value, bool) for value in values):
            out[key] = {
                "agreement_rate": sum(1 for value in values if value) / len(values),
                "n": len(values),
            }
        else:
            numeric = [float(value) for value in values]
            out[key] = {
                "median": statistics.median(numeric),
                "p90": _percentile(numeric, 0.90),
                "max": max(numeric),
                "n": len(numeric),
            }
    return out


def _sign(value: float, *, eps: float = 1e-12) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _seed_stability(rows: list[dict[str, float | None]]) -> dict[str, Any]:
    keys = sorted({key for row in rows for key in row})
    out: dict[str, Any] = {}
    for key in keys:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        if not values:
            out[key] = None
            continue
        cell: dict[str, Any] = {
            "mean": statistics.mean(values),
            "stddev_across_independent_roots": statistics.pstdev(values),
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "n": len(values),
        }
        if key.endswith("_delta"):
            signs = [_sign(value) for value in values]
            sign_counts = {sign: signs.count(sign) for sign in set(signs)}
            cell["sign_consensus_rate"] = max(sign_counts.values()) / len(signs)
            cell["signs"] = {
                str(sign): count
                for sign, count in sorted(sign_counts.items())
            }
        out[key] = cell
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/research/simulation_convergence_pit_20261002"),
    )
    args = parser.parse_args()

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.parts]
    if not reports:
        raise SystemExit("at least one part is required")

    study_ids = {report["study_id"] for report in reports}
    if study_ids != {"simulation-convergence-pit-20261002-v1"}:
        raise SystemExit(f"unexpected study ids: {sorted(study_ids)}")
    counts = tuple(reports[0]["counts"])
    if any(tuple(report["counts"]) != counts for report in reports[1:]):
        raise SystemExit("study parts disagree on trial counts")

    seeds = []
    raw_by_count: dict[int, list[dict[str, Any]]] = {count: [] for count in counts}
    absolute_raw_by_count: dict[int, list[dict[str, Any]]] = {
        count: [] for count in counts
    }
    runtime_seconds: dict[str, float] = {}
    for report in reports:
        seeds.extend(report["root_seeds"])
        for count in counts:
            raw_by_count[count].extend(report["raw_by_count"][str(count)])
            absolute_raw_by_count[count].extend(
                report["absolute_raw_by_count"][str(count)]
            )
        runtime_seconds.update(
            {str(key): float(value) for key, value in report["seed_runtime_seconds"].items()}
        )
    if len(seeds) != len(set(seeds)):
        raise SystemExit("study parts overlap root seeds")
    if sorted(seeds) != list(range(20261201, 20261209)):
        raise SystemExit(f"expected the pre-registered eight roots, got {sorted(seeds)}")

    summary = {count: _aggregate(raw_by_count[count]) for count in counts}
    independent_seed_stability = {
        count: _seed_stability(absolute_raw_by_count[count]) for count in counts
    }
    production = summary[PRODUCTION_COUNT]
    sign_rates = [
        cell["agreement_rate"]
        for key, cell in production.items()
        if key.endswith("_delta_sign_matches_100k") and isinstance(cell, dict)
    ]

    final = {
        **{
            key: value
            for key, value in reports[0].items()
            if key not in {
                "convergence_summary",
                "root_seeds",
                "seed_runtime_seconds",
                "seed_start",
                "raw_by_count",
                "absolute_raw_by_count",
                "independent_seed_stability",
                "authority_recommendation_guard",
            }
        },
        "root_seeds": sorted(seeds),
        "convergence_summary": {str(key): value for key, value in summary.items()},
        "independent_seed_stability": {
            str(key): value for key, value in independent_seed_stability.items()
        },
        "seed_runtime_seconds": runtime_seconds,
        "authority_recommendation_guard": {
            "production_count": PRODUCTION_COUNT,
            "reference_count": REFERENCE_COUNT,
            "production_sign_agreement_min": min(sign_rates) if sign_rates else None,
            "authority_change_applied": False,
            "management_approval_required_for_any_change": True,
            "interpretation": (
                "Use the measured 50k-vs-100k error envelope and sign stability "
                "to decide whether a different production count is worth considering. "
                "Do not infer a new adaptive authority rule from preview-stage counts."
            ),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "RESULTS.json").write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Simulation 2.0 item 8 — convergence + PIT calibration study",
        "",
        "**Status:** research evidence only; production authority remains 50,000.",
        "",
        f"- Seeds: {len(seeds)} ({min(seeds)}-{max(seeds)})",
        f"- Counts executed: {', '.join(f'{value:,}' for value in counts)}",
        "- 1,000 is item-7 screening context only, not an authority candidate.",
        f"- Reference: {REFERENCE_COUNT:,} (research reference only)",
        "",
        "## Convergence by trial count",
        "",
        "| runs | wins max abs p90 | playoff max abs p90 | title max abs p90 | finish TV p90 | pick-slot TV p90 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for count in counts:
        row = summary[count]
        lines.append(
            f"| {count:,} | "
            f"{row['expected_wins_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['playoff_probability_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['championship_probability_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['finish_rank_max_tv_vs_100k']['p90']:.6f} | "
            f"{row['future_pick_slot_max_tv_vs_100k']['p90']:.6f} |"
        )
    lines += ["", "## Scenario delta sign stability at 50,000", ""]
    for key, cell in production.items():
        if key.endswith("_delta_sign_matches_100k") and isinstance(cell, dict):
            lines.append(f"- {key}: {cell['agreement_rate']:.1%} ({cell['n']} seeds)")
    lines.append(
        "- Stability/sensitivity only; alternate-world outcomes are not observed "
        "causal historical targets."
    )
    lines += ["", "## Independent-root stability at 50,000", ""]
    for key, cell in independent_seed_stability[PRODUCTION_COUNT].items():
        if isinstance(cell, dict):
            line = (
                f"- {key}: mean={cell['mean']:.6f}, "
                f"root_stddev={cell['stddev_across_independent_roots']:.6f}, "
                f"range={cell['range']:.6f}, n={cell['n']}"
            )
            if "sign_consensus_rate" in cell:
                line += f", sign_consensus={cell['sign_consensus_rate']:.1%}"
            lines.append(line)
    pit = final["pit_calibration"]
    lines += [
        "",
        "## PIT calibration",
        "",
        f"- Status: {pit['status']}",
        f"- Authentic canonical State snapshots: {pit['state_snapshot_count']}",
        f"- Authentic provider projection snapshots: {pit['projection_snapshot_count']}",
        f"- Normalized projection observations: {pit['projection_observation_count']}",
        (
            "- Finalized full-season Simulation calibration cases: "
            f"{pit['eligible_full_simulation_cases']}"
        ),
        f"- Scored probability observations: {pit['scored_probability_observations']}",
        f"- Scored continuous observations: {pit['scored_continuous_observations']}",
        f"- Reason: {pit['reason']}",
        "- Limitations:",
        *[f"  - {item}" for item in pit["limitations"]],
        "",
        "No production-count or adaptive-authority change is made by this study.",
        "Any proposed change must be returned to Management for sanity check and explicit approval.",
    ]
    (args.output_dir / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("FSFFL_ITEM8_FINAL_JSON_BEGIN")
    print(json.dumps(final, sort_keys=True))
    print("FSFFL_ITEM8_FINAL_JSON_END")


if __name__ == "__main__":
    main()
