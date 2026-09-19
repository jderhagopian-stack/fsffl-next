from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path("artifacts/next2-benchmark")
PANEL = ROOT / "modern_projection_panel.csv"
RESULTS = ROOT / "benchmark_results.json"
REPORT = ROOT / "benchmark_report.md"
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 20260905


def load_panel() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with PANEL.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "season": int(row["season"]),
                    "player_id": row["mfl_id_key"],
                    "player": row["player"],
                    "position": row["position"],
                    "source": row["source"],
                    "projected": float(row["projected"]),
                    "actual": float(row["actual"]),
                }
            )
    return rows


def metric_summary(rows: list[dict[str, object]]) -> dict[str, float | int]:
    errors = [float(row["projected"]) - float(row["actual"]) for row in rows]
    if not errors:
        return {"n": 0, "mae": math.nan, "rmse": math.nan, "bias": math.nan}
    n = len(errors)
    return {
        "n": n,
        "mae": sum(abs(x) for x in errors) / n,
        "rmse": math.sqrt(sum(x * x for x in errors) / n),
        "bias": sum(errors) / n,
    }


def performance(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["position"]), str(row["source"]))].append(row)
    result: list[dict[str, object]] = []
    for (position, source), items in sorted(grouped.items()):
        result.append({"position": position, "source": source, **metric_summary(items)})
    return result


def overall_performance(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["source"])].append(row)
    return [{"source": source, **metric_summary(items)} for source, items in sorted(grouped.items())]


def learn_inverse_rmse(train_perf: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    by_pos: dict[str, dict[str, float]] = defaultdict(dict)
    for item in train_perf:
        rmse = float(item["rmse"])
        if rmse > 0:
            by_pos[str(item["position"])][str(item["source"])] = 1.0 / rmse
    normalized: dict[str, dict[str, float]] = {}
    for pos, values in by_pos.items():
        total = sum(values.values())
        normalized[pos] = {source: value / total for source, value in sorted(values.items())}
    return normalized


def training_source_sets(weights: dict[str, dict[str, float]]) -> dict[str, set[str]]:
    return {position: set(source_weights) for position, source_weights in weights.items()}


def ensemble_rows(
    rows: list[dict[str, object]],
    *,
    source_name: str,
    weights: dict[str, dict[str, float]] | None,
    allowed_sources: dict[str, set[str]] | None = None,
    require_min_sources: int = 2,
) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["season"]), str(row["position"]), str(row["player_id"]), str(row["player"]))].append(row)
    output: list[dict[str, object]] = []
    for (season, position, player_id, player), items in grouped.items():
        eligible = items
        if allowed_sources is not None:
            permitted = allowed_sources.get(position, set())
            eligible = [item for item in items if str(item["source"]) in permitted]
        if len(eligible) < require_min_sources:
            continue
        if weights is None:
            active_weights = {str(item["source"]): 1.0 for item in eligible}
        else:
            available = weights.get(position, {})
            active_weights = {
                str(item["source"]): available[str(item["source"])]
                for item in eligible
                if str(item["source"]) in available
            }
        if len(active_weights) < require_min_sources:
            continue
        total = sum(active_weights.values())
        if total <= 0:
            continue
        projected = sum(
            float(item["projected"]) * active_weights[str(item["source"])]
            for item in eligible
            if str(item["source"]) in active_weights
        ) / total
        output.append(
            {
                "season": season,
                "player_id": player_id,
                "player": player,
                "position": position,
                "source": source_name,
                "projected": projected,
                "actual": float(eligible[0]["actual"]),
                "component_count": len(active_weights),
            }
        )
    return output


def row_key(row: dict[str, object]) -> tuple[int, str, str]:
    return (int(row["season"]), str(row["position"]), str(row["player_id"]))


def paired_rows(
    baseline: list[dict[str, object]], challenger: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    left = {row_key(row): row for row in baseline}
    right = {row_key(row): row for row in challenger}
    keys = sorted(set(left) & set(right))
    return [left[key] for key in keys], [right[key] for key in keys]


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    index = (len(ordered) - 1) * q
    lo = math.floor(index)
    hi = math.ceil(index)
    if lo == hi:
        return ordered[lo]
    fraction = index - lo
    return ordered[lo] * (1 - fraction) + ordered[hi] * fraction


def paired_bootstrap(
    baseline: list[dict[str, object]],
    challenger: list[dict[str, object]],
    *,
    reps: int = BOOTSTRAP_REPS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, object]:
    if len(baseline) != len(challenger):
        raise ValueError("Paired bootstrap requires equal-length aligned rows")
    n = len(baseline)
    if n < 2:
        return {"n": n, "reps": 0, "mae_diff": None, "rmse_diff": None}
    base_errors = [float(row["projected"]) - float(row["actual"]) for row in baseline]
    challenger_errors = [float(row["projected"]) - float(row["actual"]) for row in challenger]
    rng = random.Random(seed)
    mae_diffs: list[float] = []
    rmse_diffs: list[float] = []
    for _ in range(reps):
        sample = [rng.randrange(n) for _ in range(n)]
        base_mae = sum(abs(base_errors[i]) for i in sample) / n
        challenger_mae = sum(abs(challenger_errors[i]) for i in sample) / n
        base_rmse = math.sqrt(sum(base_errors[i] ** 2 for i in sample) / n)
        challenger_rmse = math.sqrt(sum(challenger_errors[i] ** 2 for i in sample) / n)
        mae_diffs.append(challenger_mae - base_mae)
        rmse_diffs.append(challenger_rmse - base_rmse)

    def summarize(values: list[float]) -> dict[str, float]:
        return {
            "mean": sum(values) / len(values),
            "ci95_low": percentile(values, 0.025),
            "ci95_high": percentile(values, 0.975),
            "prob_challenger_better": sum(value < 0 for value in values) / len(values),
        }

    return {"n": n, "reps": reps, "mae_diff": summarize(mae_diffs), "rmse_diff": summarize(rmse_diffs)}


def paired_comparison(
    baseline: list[dict[str, object]], challenger: list[dict[str, object]]
) -> dict[str, object]:
    paired_baseline, paired_challenger = paired_rows(baseline, challenger)
    by_position: dict[str, object] = {}
    for position in sorted({str(row["position"]) for row in paired_baseline}):
        base_pos = [row for row in paired_baseline if str(row["position"]) == position]
        chal_pos = [row for row in paired_challenger if str(row["position"]) == position]
        by_position[position] = {
            "baseline": metric_summary(base_pos),
            "challenger": metric_summary(chal_pos),
            "bootstrap_challenger_minus_baseline": paired_bootstrap(
                base_pos, chal_pos, seed=BOOTSTRAP_SEED + sum(ord(c) for c in position)
            ),
        }
    return {
        "overall": {
            "baseline": metric_summary(paired_baseline),
            "challenger": metric_summary(paired_challenger),
            "bootstrap_challenger_minus_baseline": paired_bootstrap(paired_baseline, paired_challenger),
        },
        "by_position": by_position,
    }


def common_source_set(rows: list[dict[str, object]], season: int) -> dict[str, list[str]]:
    by_pos_source_players: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        if int(row["season"]) == season:
            by_pos_source_players[(str(row["position"]), str(row["source"]))].add(str(row["player_id"]))
    positions = sorted({position for position, _ in by_pos_source_players})
    return {
        pos: sorted(source for p, source in by_pos_source_players if p == pos)
        for pos in positions
    }


def fmt(value: float) -> str:
    return f"{value:.2f}"


def ci_text(item: dict[str, float]) -> str:
    return f"{fmt(item['mean'])} [{fmt(item['ci95_low'])}, {fmt(item['ci95_high'])}]"


def main() -> None:
    rows = load_panel()
    if not rows:
        raise SystemExit("No benchmark rows were extracted")
    train = [row for row in rows if int(row["season"]) == 2024]
    test = [row for row in rows if int(row["season"]) == 2025]
    if not train or not test:
        raise SystemExit(f"Need both 2024 training and 2025 held-out rows; got {len(train)} and {len(test)}")

    train_perf = performance(train)
    test_perf = performance(test)
    weights = learn_inverse_rmse(train_perf)
    seen_sources = training_source_sets(weights)

    equal_all_test = ensemble_rows(
        test,
        source_name="fsffl_equal_weight_all_available",
        weights=None,
    )
    equal_comparable_test = ensemble_rows(
        test,
        source_name="fsffl_equal_weight_training_sources",
        weights=None,
        allowed_sources=seen_sources,
    )
    challenger_test = ensemble_rows(
        test,
        source_name="fsffl_inverse_rmse_challenger",
        weights=weights,
        allowed_sources=seen_sources,
    )
    fair_comparison = paired_comparison(equal_comparable_test, challenger_test)

    sources_by_season_position = {
        "2024": common_source_set(rows, 2024),
        "2025": common_source_set(rows, 2025),
    }

    result = {
        "study": "NEXT-2 modern multi-source historical projection benchmark",
        "design": {
            "training_season": 2024,
            "held_out_season": 2025,
            "target": "season fantasy points as carried by the public Fantasy Football Analytics research panel",
            "weight_learning": "inverse RMSE by position, learned on 2024 only",
            "exploratory_equal_weight": "equal blend of all 2025 sources available for each player with at least two projections",
            "fair_equal_weight_baseline": "equal blend restricted to providers observed in 2024, so it uses the same eligible source family as the challenger",
            "challenger": "2024 inverse-RMSE weights, renormalized over the same training-observed sources available for each 2025 player",
            "uncertainty": f"paired player-level bootstrap, {BOOTSTRAP_REPS} replicates with fixed seed; reported differences are challenger minus equal baseline",
        },
        "row_counts": {"all": len(rows), "training_2024": len(train), "held_out_2025": len(test)},
        "sources_by_season_position": sources_by_season_position,
        "training_source_performance": train_perf,
        "held_out_source_performance": test_perf,
        "held_out_source_performance_overall_observed_cohorts": overall_performance(test),
        "learned_weights": weights,
        "held_out_exploratory_equal_weight_performance": performance(equal_all_test),
        "held_out_fair_equal_weight_performance": performance(equal_comparable_test),
        "held_out_challenger_performance": performance(challenger_test),
        "held_out_fair_paired_comparison": fair_comparison,
        "held_out_ensemble_rows": {
            "equal_all_available": len(equal_all_test),
            "equal_training_sources": len(equal_comparable_test),
            "challenger": len(challenger_test),
        },
    }
    RESULTS.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# NEXT-2 Modern Historical Projection Benchmark",
        "",
        "## Study design",
        "",
        "This is a chronological out-of-sample study: **2024 trains the source weighting and 2025 is held out for evaluation**. No 2025 outcome is used to choose the challenger weights.",
        "",
        f"The extracted panel contains **{len(rows):,} matched provider/player observations**: {len(train):,} in 2024 and {len(test):,} in 2025.",
        "",
        "The source carrier is the public Fantasy Football Analytics historical projection dataset. The provider named in `data_src` is treated as the forecast source; the carrier itself is **not** counted as an independent projection vote.",
        "",
        "The primary ensemble test is deliberately fair: equal weighting and the challenger use the **same source eligibility and the same held-out players**. A separate all-available equal blend is retained only as an exploratory result because 2025 adds a source that did not exist in the 2024 training set.",
        "",
        "## Held-out 2025 provider results",
        "",
        "Provider rows below are observed-cohort diagnostics; providers cover different player sets, so small RMSE differences should not be read as a clean head-to-head ranking without a common cohort.",
        "",
        "| Position | Source | Players | MAE | RMSE | Bias |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in sorted(test_perf, key=lambda x: (str(x["position"]), float(x["rmse"]))):
        lines.append(
            f"| {item['position']} | {item['source']} | {item['n']} | {fmt(float(item['mae']))} | {fmt(float(item['rmse']))} | {fmt(float(item['bias']))} |"
        )

    lines.extend([
        "",
        "## Fair held-out 2025 ensemble test",
        "",
        "Negative differences favor the challenger; positive differences favor equal weighting. Confidence intervals come from paired player-level bootstrap resampling.",
        "",
        "| Position | Players | Equal MAE | Challenger MAE | MAE diff (95% CI) | Equal RMSE | Challenger RMSE | RMSE diff (95% CI) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    by_position = fair_comparison["by_position"]
    for position in sorted(by_position):
        item = by_position[position]
        base = item["baseline"]
        challenger = item["challenger"]
        boot = item["bootstrap_challenger_minus_baseline"]
        lines.append(
            f"| {position} | {base['n']} | {fmt(float(base['mae']))} | {fmt(float(challenger['mae']))} | {ci_text(boot['mae_diff'])} | {fmt(float(base['rmse']))} | {fmt(float(challenger['rmse']))} | {ci_text(boot['rmse_diff'])} |"
        )

    overall = fair_comparison["overall"]
    overall_boot = overall["bootstrap_challenger_minus_baseline"]
    lines.extend([
        "",
        "### Overall paired result",
        "",
        f"Across the common held-out cohort of **{overall['baseline']['n']} players**, equal weighting produced MAE **{fmt(float(overall['baseline']['mae']))}** and RMSE **{fmt(float(overall['baseline']['rmse']))}**; the challenger produced MAE **{fmt(float(overall['challenger']['mae']))}** and RMSE **{fmt(float(overall['challenger']['rmse']))}**.",
        "",
        f"Challenger-minus-equal MAE difference: **{ci_text(overall_boot['mae_diff'])}**. Challenger-minus-equal RMSE difference: **{ci_text(overall_boot['rmse_diff'])}**.",
        "",
        "## Exploratory all-available equal blend",
        "",
        "This version may use a 2025-only source and therefore is useful operationally, but it is not the clean test of weighting strategy.",
        "",
        "| Position | Players | MAE | RMSE | Bias |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for item in sorted(performance(equal_all_test), key=lambda x: str(x["position"])):
        lines.append(
            f"| {item['position']} | {item['n']} | {fmt(float(item['mae']))} | {fmt(float(item['rmse']))} | {fmt(float(item['bias']))} |"
        )

    lines.extend(["", "## Weights learned from 2024 only", ""])
    for position in sorted(weights):
        rendered = ", ".join(f"{source}={value:.3f}" for source, value in weights[position].items())
        lines.append(f"- **{position}:** {rendered}")

    lines.extend([
        "",
        "## Interpretation guardrails",
        "",
        "- One train/test split is enough to reject a clearly weak challenger, but not enough to establish a permanent production weighting rule. More chronological seasons are required for promotion.",
        "- Provider observed-cohort results are not automatically comparable because coverage differs. The equal-vs-challenger conclusion is based on the paired common cohort instead.",
        "- The bootstrap quantifies player-sample uncertainty within the 2025 held-out season; it does not replace year-to-year stability testing.",
        "- The first challenger is deliberately simple. It remains research-only unless it demonstrates repeatable held-out improvement.",
        "- Provider rights and redistribution are separate from predictive skill. Raw upstream data stays in the workflow artifact rather than the public FSFFL NEXT repository.",
        "- Exact point-in-time acquisition metadata for each underlying source still must be checked before any provider-specific production weight is formally promoted.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
