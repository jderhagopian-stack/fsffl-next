from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


CANDIDATE_COUNT = 35_000
PRODUCTION_COUNT = 50_000
REFERENCE_COUNT = 100_000
EXPECTED_SEEDS = tuple(range(20261301, 20261313))


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _numeric_summary(values: list[float]) -> dict[str, float | int]:
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p90": _percentile(values, 0.90),
        "max": max(values),
        "min": min(values),
        "n": len(values),
    }


def _aggregate_comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = sorted(
        {
            key
            for row in rows
            for key in row["comparison"]
            if key not in {"product_check_results", "product_equivalent_to_100k"}
        }
    )
    result: dict[str, Any] = {}
    for key in keys:
        values = [
            row["comparison"].get(key)
            for row in rows
            if row["comparison"].get(key) is not None
        ]
        if not values:
            result[key] = None
        elif all(isinstance(value, bool) for value in values):
            result[key] = {
                "agreement_rate": sum(bool(value) for value in values) / len(values),
                "matches": sum(bool(value) for value in values),
                "n": len(values),
            }
        elif all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            result[key] = _numeric_summary([float(value) for value in values])
    product_equivalent = [
        bool(row["comparison"]["product_equivalent_to_100k"]) for row in rows
    ]
    result["product_equivalent_to_100k"] = {
        "agreement_rate": sum(product_equivalent) / len(product_equivalent),
        "matches": sum(product_equivalent),
        "n": len(product_equivalent),
    }
    return result


def _seed_dispersion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = sorted(
        {
            key
            for row in rows
            for key, value in row.items()
            if key not in {"seed", "fixture_id", "count"}
            and isinstance(value, (int, float))
        }
    )
    result: dict[str, Any] = {}
    for metric in metrics:
        values = [float(row[metric]) for row in rows if row.get(metric) is not None]
        if not values:
            continue
        result[metric] = {
            "mean": statistics.mean(values),
            "stddev_across_independent_roots": statistics.pstdev(values),
            "range": max(values) - min(values),
            "min": min(values),
            "max": max(values),
            "n": len(values),
        }
        if metric.endswith("_delta"):
            signs = [1 if value > 0 else -1 if value < 0 else 0 for value in values]
            result[metric]["signs"] = {
                str(sign): signs.count(sign) for sign in sorted(set(signs))
            }
            result[metric]["sign_consensus_rate"] = max(
                signs.count(sign) for sign in set(signs)
            ) / len(signs)
    return result


def _product_divergences(
    rows_by_key: dict[tuple[int, str, int], dict[str, Any]]
) -> dict[str, Any]:
    candidate_only: list[dict[str, Any]] = []
    production_only: list[dict[str, Any]] = []
    both: list[dict[str, Any]] = []

    for seed in EXPECTED_SEEDS:
        fixture_ids = sorted(
            {
                fixture_id
                for row_seed, fixture_id, _count in rows_by_key
                if row_seed == seed
            }
        )
        for fixture_id in fixture_ids:
            candidate = rows_by_key[(seed, fixture_id, CANDIDATE_COUNT)]
            production = rows_by_key[(seed, fixture_id, PRODUCTION_COUNT)]
            candidate_checks = candidate["comparison"]["product_check_results"]
            production_checks = production["comparison"]["product_check_results"]
            keys = sorted(set(candidate_checks) | set(production_checks))
            for check in keys:
                # Visible probability rounding is evaluated at the individual
                # team/metric cell below. Treating the whole 24-cell signature as
                # one Boolean obscures whether 35k alone crosses a UI boundary.
                if check == "rounded_probabilities_matches_100k":
                    continue
                c = candidate_checks.get(check)
                p = production_checks.get(check)
                if c is None or p is None:
                    continue
                if c and p:
                    continue
                event = {
                    "seed": seed,
                    "fixture_id": fixture_id,
                    "check": check,
                    "candidate_35k_matches_100k": bool(c),
                    "production_50k_matches_100k": bool(p),
                }
                if not c and p:
                    candidate_only.append(event)
                elif c and not p:
                    production_only.append(event)
                else:
                    both.append(event)

            def rounded_cells(row: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
                return {
                    (str(item["team_id"]), str(item["metric"])): item
                    for item in row["comparison"].get(
                        "rounded_probability_differences_vs_100k", ()
                    )
                }

            candidate_cells = rounded_cells(candidate)
            production_cells = rounded_cells(production)
            for cell in sorted(set(candidate_cells) | set(production_cells)):
                candidate_diff = candidate_cells.get(cell)
                production_diff = production_cells.get(cell)
                if candidate_diff is None and production_diff is None:
                    continue
                event = {
                    "seed": seed,
                    "fixture_id": fixture_id,
                    "check": "rounded_probability_visible_cell",
                    "team_id": cell[0],
                    "metric": cell[1],
                    "candidate_35k_matches_100k": candidate_diff is None,
                    "production_50k_matches_100k": production_diff is None,
                    "candidate_difference": candidate_diff,
                    "production_difference": production_diff,
                }
                if candidate_diff is not None and production_diff is None:
                    candidate_only.append(event)
                elif candidate_diff is None and production_diff is not None:
                    production_only.append(event)
                else:
                    both.append(event)

    return {
        "candidate_35k_diverges_while_50k_matches": candidate_only,
        "production_50k_diverges_while_35k_matches": production_only,
        "both_35k_and_50k_diverge_from_100k": both,
        "candidate_only_count": len(candidate_only),
        "production_only_count": len(production_only),
        "both_count": len(both),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.parts]
    if not reports:
        raise SystemExit("at least one stress-test part is required")
    if {report["study_id"] for report in reports} != {
        "simulation-35k-stress-20261002-v1"
    }:
        raise SystemExit("stress-test parts disagree on study identity")
    if any(report["production_count"] != PRODUCTION_COUNT for report in reports):
        raise SystemExit("stress test cannot change production Simulation authority")
    if any(report["candidate_count"] != CANDIDATE_COUNT for report in reports):
        raise SystemExit("stress test must compare the governed 35k candidate")
    if any(report["reference_count"] != REFERENCE_COUNT for report in reports):
        raise SystemExit("stress test must use same-root 100k research reference")
    if any(report["guardrails"]["production_authority_changed"] for report in reports):
        raise SystemExit("stress-test part attempted a production authority change")

    seeds = sorted(
        seed
        for report in reports
        for seed in report["root_seeds"]
    )
    if seeds != list(EXPECTED_SEEDS):
        raise SystemExit(f"expected 12 unique registered roots, got {seeds}")
    if len(seeds) != len(set(seeds)):
        raise SystemExit("stress-test part roots overlap")

    fixture_payloads = reports[0]["fixtures"]
    fixture_hashes = {
        row["fixture_id"]: row["fixture_hash"] for row in fixture_payloads
    }
    required_tags = {
        "razor_thin_playoff_bubble",
        "high_parity_league",
        "tail_championship_case",
        "future_pick_boundary_case",
        "near_zero_scenario_delta",
        "material_scenario_delta",
        "postseason_no_bye",
        "postseason_with_byes",
    }
    fixture_tags = {
        tag for row in fixture_payloads for tag in row["tags"]
    }
    if not required_tags.issubset(fixture_tags):
        raise SystemExit(
            f"stress fixtures missing required tags: {sorted(required_tags - fixture_tags)}"
        )
    for report in reports[1:]:
        observed = {
            row["fixture_id"]: row["fixture_hash"] for row in report["fixtures"]
        }
        if observed != fixture_hashes:
            raise SystemExit("stress-test parts disagree on fixture identity")

    raw_rows: list[dict[str, Any]] = []
    absolute_rows: list[dict[str, Any]] = []
    runtimes_by_count: dict[int, list[float]] = {
        CANDIDATE_COUNT: [],
        PRODUCTION_COUNT: [],
        REFERENCE_COUNT: [],
    }
    seed_elapsed_seconds: dict[str, float] = {}
    for report in reports:
        for seed_result in report["seed_results"]:
            raw_rows.extend(seed_result["raw_rows"])
            absolute_rows.extend(seed_result["absolute_rows"])
            seed_elapsed_seconds[str(seed_result["seed"])] = float(
                seed_result["seed_elapsed_seconds"]
            )
            for count in runtimes_by_count:
                runtimes_by_count[count].append(
                    float(seed_result["runtime_by_count_seconds"][str(count)])
                )

    rows_by_key = {
        (row["seed"], row["fixture_id"], row["count"]): row
        for row in raw_rows
    }
    if len(rows_by_key) != len(raw_rows):
        raise SystemExit("duplicate stress-test raw row")

    expected_row_count = len(EXPECTED_SEEDS) * len(fixture_payloads) * 3
    if len(raw_rows) != expected_row_count:
        raise SystemExit(
            f"expected {expected_row_count} stress rows, got {len(raw_rows)}"
        )

    by_count: dict[int, dict[str, Any]] = {}
    by_fixture: dict[str, dict[int, dict[str, Any]]] = {}
    dispersion: dict[str, dict[int, dict[str, Any]]] = {}
    for count in (CANDIDATE_COUNT, PRODUCTION_COUNT):
        count_rows = [row for row in raw_rows if row["count"] == count]
        by_count[count] = _aggregate_comparisons(count_rows)
    for fixture in fixture_payloads:
        fixture_id = fixture["fixture_id"]
        by_fixture[fixture_id] = {}
        dispersion[fixture_id] = {}
        for count in (CANDIDATE_COUNT, PRODUCTION_COUNT):
            rows = [
                row
                for row in raw_rows
                if row["fixture_id"] == fixture_id and row["count"] == count
            ]
            by_fixture[fixture_id][count] = _aggregate_comparisons(rows)
            absolute = [
                row
                for row in absolute_rows
                if row["fixture_id"] == fixture_id and row["count"] == count
            ]
            dispersion[fixture_id][count] = _seed_dispersion(absolute)

    runtime_summary = {
        str(count): _numeric_summary(values)
        for count, values in runtimes_by_count.items()
    }
    median_35 = float(runtime_summary[str(CANDIDATE_COUNT)]["median"])
    median_50 = float(runtime_summary[str(PRODUCTION_COUNT)]["median"])
    runtime_savings = {
        "median_seconds_35k": median_35,
        "median_seconds_50k": median_50,
        "median_seconds_saved": median_50 - median_35,
        "median_percent_saved_vs_50k": (
            0.0 if median_50 == 0 else (median_50 - median_35) / median_50
        ),
    }

    divergences = _product_divergences(rows_by_key)
    candidate_equiv = by_count[CANDIDATE_COUNT]["product_equivalent_to_100k"]
    production_equiv = by_count[PRODUCTION_COUNT]["product_equivalent_to_100k"]

    if divergences["candidate_only_count"] > 0:
        management_gate = "retain_50000_candidate_failed_meaningful_boundary"
    elif (
        divergences["production_only_count"] > 0
        or divergences["both_count"] > 0
        or production_equiv["agreement_rate"] < 1.0
    ):
        management_gate = "retain_50000_mixed_boundary_evidence"
    elif candidate_equiv["agreement_rate"] == 1.0:
        management_gate = "management_proposal_eligible_35k_product_equivalent"
    else:
        management_gate = "retain_50000_mixed_boundary_evidence"

    final = {
        "study_id": "simulation-35k-stress-20261002-final",
        "authority_status": "research_only_no_production_change",
        "production_count": PRODUCTION_COUNT,
        "candidate_count": CANDIDATE_COUNT,
        "reference_count": REFERENCE_COUNT,
        "roots": len(EXPECTED_SEEDS),
        "root_seeds": list(EXPECTED_SEEDS),
        "rng_protocol": reports[0]["rng_protocol"],
        "rng_batch_size": reports[0]["rng_batch_size"],
        "fixtures": fixture_payloads,
        "raw_rows": raw_rows,
        "absolute_rows": absolute_rows,
        "summary_by_count": {
            str(key): value for key, value in by_count.items()
        },
        "summary_by_fixture": {
            fixture_id: {str(key): value for key, value in values.items()}
            for fixture_id, values in by_fixture.items()
        },
        "independent_root_dispersion": {
            fixture_id: {str(key): value for key, value in values.items()}
            for fixture_id, values in dispersion.items()
        },
        "runtime_summary": runtime_summary,
        "runtime_savings": runtime_savings,
        "product_divergences": divergences,
        "management_gate": management_gate,
        "management_interpretation": (
            "Production remains 50,000 regardless of this research result. "
            "If the gate is proposal-eligible, Management may separately consider "
            "a 35,000 authority change. If candidate-only or mixed boundary evidence "
            "exists, retain 50,000 and close count hunting per directive."
        ),
        "guardrails": {
            "production_authority_changed": False,
            "adaptive_count_rule_changed": False,
            "production_model_identity_changed": False,
            "render_deploy_required": False,
            "origin_aware_pick_value_status": "held_pending_management_gate",
            "same_root_100k_reference_only": True,
            "decision_rules_added": False,
        },
        "seed_elapsed_seconds": seed_elapsed_seconds,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "RESULTS.json"
    result_path.write_text(
        json.dumps(final, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Simulation 35k vs 50k bounded stress test",
        "",
        "**Status:** research evidence only; production authority remains 50,000.",
        "",
        f"- Independent roots: {len(EXPECTED_SEEDS)}",
        f"- Fixtures: {len(fixture_payloads)} governed deterministic stress fixtures",
        "- Counts: 35,000 candidate / 50,000 production / same-root 100,000 reference",
        f"- Management gate: **{management_gate}**",
        "",
        "## Numerical error versus same-root 100k",
        "",
        "| candidate | wins max-abs p90 | playoff max-abs p90 | title max-abs p90 | finish TV p90 | product-equivalent rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for count in (CANDIDATE_COUNT, PRODUCTION_COUNT):
        row = by_count[count]
        lines.append(
            f"| {count:,} | "
            f"{row['expected_wins_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['playoff_probability_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['championship_probability_max_abs_error_vs_100k']['p90']:.6f} | "
            f"{row['finish_rank_max_tv_vs_100k']['p90']:.6f} | "
            f"{row['product_equivalent_to_100k']['agreement_rate']:.1%} |"
        )
    lines += [
        "",
        "## Runtime",
        "",
        f"- 35k median stress bundle: {median_35:.3f}s",
        f"- 50k median stress bundle: {median_50:.3f}s",
        (
            "- Median savings: "
            f"{runtime_savings['median_seconds_saved']:.3f}s / "
            f"{runtime_savings['median_percent_saved_vs_50k']:.1%}"
        ),
        "",
        "## Product-boundary evidence",
        "",
        (
            "- 35k diverged where 50k matched 100k: "
            f"{divergences['candidate_only_count']} checks"
        ),
        (
            "- 50k diverged where 35k matched 100k: "
            f"{divergences['production_only_count']} checks"
        ),
        (
            "- Both 35k and 50k diverged from 100k: "
            f"{divergences['both_count']} checks"
        ),
        "",
        "Checks include close-team ordering, whole-percent product rounding, "
        "league-relative competitive-state labels, pick exact-slot/tier summaries, "
        "and governed competitive materiality/sign for near-zero and material scenarios.",
        "No trade/waiver disposition is fabricated because the stress fixture intentionally "
        "contains Simulation competitive evidence only and no economic/negotiation evidence.",
        "",
        "## Fixture coverage",
        "",
    ]
    for fixture in fixture_payloads:
        lines.append(
            f"- {fixture['fixture_id']} — {', '.join(fixture['tags'])}; "
            f"hash={fixture['fixture_hash'][:16]}..."
        )
    lines += [
        "",
        "## Management",
        "",
        "This study does not change production count, model identity, deployment config, "
        "adaptive rules, or Decision authority. Origin-aware pick Value remains held "
        "until Management acts on this gate.",
    ]
    report_path = args.output_dir / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("FSFFL_SIM35K_FINAL_JSON_BEGIN")
    print(json.dumps(final, sort_keys=True))
    print("FSFFL_SIM35K_FINAL_JSON_END")
    print("FSFFL_SIM35K_REPORT_BEGIN")
    print(report_path.read_text(encoding="utf-8"))
    print("FSFFL_SIM35K_REPORT_END")


if __name__ == "__main__":
    main()
