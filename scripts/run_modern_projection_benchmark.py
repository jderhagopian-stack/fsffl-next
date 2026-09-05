from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path("artifacts/next2-benchmark")
PANEL = ROOT / "modern_projection_panel.csv"
RESULTS = ROOT / "benchmark_results.json"
REPORT = ROOT / "benchmark_report.md"


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


def performance(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["position"]), str(row["source"]))].append(
            float(row["projected"]) - float(row["actual"])
        )
    result = []
    for (position, source), errors in sorted(grouped.items()):
        n = len(errors)
        result.append(
            {
                "position": position,
                "source": source,
                "n": n,
                "mae": sum(abs(x) for x in errors) / n,
                "rmse": math.sqrt(sum(x * x for x in errors) / n),
                "bias": sum(errors) / n,
            }
        )
    return result


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


def ensemble_rows(
    rows: list[dict[str, object]],
    *,
    source_name: str,
    weights: dict[str, dict[str, float]] | None,
    require_min_sources: int = 2,
) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["season"]), str(row["position"]), str(row["player_id"]), str(row["player"]))].append(row)
    output: list[dict[str, object]] = []
    for (season, position, player_id, player), items in grouped.items():
        # One observation per underlying source is guaranteed by extraction.
        if len(items) < require_min_sources:
            continue
        if weights is None:
            active_weights = {str(item["source"]): 1.0 for item in items}
        else:
            available = weights.get(position, {})
            active_weights = {
                str(item["source"]): available[str(item["source"])]
                for item in items
                if str(item["source"]) in available
            }
        if len(active_weights) < require_min_sources:
            continue
        total = sum(active_weights.values())
        if total <= 0:
            continue
        projected = sum(
            float(item["projected"]) * active_weights[str(item["source"])]
            for item in items
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
                "actual": float(items[0]["actual"]),
                "component_count": len(active_weights),
            }
        )
    return output


def common_source_set(rows: list[dict[str, object]], season: int) -> dict[str, list[str]]:
    by_pos_source_players: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        if int(row["season"]) == season:
            by_pos_source_players[(str(row["position"]), str(row["source"]))].add(str(row["player_id"]))
    positions = sorted({position for position, _ in by_pos_source_players})
    result: dict[str, list[str]] = {}
    for pos in positions:
        sources = sorted(source for p, source in by_pos_source_players if p == pos)
        result[pos] = sources
    return result


def fmt(value: float) -> str:
    return f"{value:.2f}"


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

    equal_test = ensemble_rows(test, source_name="fsffl_equal_weight", weights=None)
    challenger_test = ensemble_rows(
        test,
        source_name="fsffl_inverse_rmse_challenger",
        weights=weights,
    )
    equal_perf = performance(equal_test)
    challenger_perf = performance(challenger_test)

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
            "equal_weight": "equal blend of available sources for each player with at least two source projections",
            "challenger": "2024 inverse-RMSE weights, renormalized over sources available for each 2025 player",
        },
        "row_counts": {"all": len(rows), "training_2024": len(train), "held_out_2025": len(test)},
        "sources_by_season_position": sources_by_season_position,
        "training_source_performance": train_perf,
        "held_out_source_performance": test_perf,
        "learned_weights": weights,
        "held_out_equal_weight_performance": equal_perf,
        "held_out_challenger_performance": challenger_perf,
        "held_out_ensemble_rows": {
            "equal_weight": len(equal_test),
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
        "## Held-out 2025 provider results",
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
        "## Held-out 2025 ensemble results",
        "",
        "| Position | Method | Players | MAE | RMSE | Bias |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ])
    ensemble_perf = equal_perf + challenger_perf
    for item in sorted(ensemble_perf, key=lambda x: (str(x["position"]), str(x["source"]))):
        lines.append(
            f"| {item['position']} | {item['source']} | {item['n']} | {fmt(float(item['mae']))} | {fmt(float(item['rmse']))} | {fmt(float(item['bias']))} |"
        )

    lines.extend([
        "",
        "## Weights learned from 2024 only",
        "",
    ])
    for position in sorted(weights):
        rendered = ", ".join(f"{source}={value:.3f}" for source, value in weights[position].items())
        lines.append(f"- **{position}:** {rendered}")

    lines.extend([
        "",
        "## Interpretation guardrails",
        "",
        "- These results compare the historical provider projections actually present in the recovered panel; missing source/player rows are reported through sample size rather than fabricated.",
        "- The first challenger is deliberately simple. It is a research baseline, not automatic production authority.",
        "- Provider rights and redistribution are separate from predictive skill. Raw upstream data is kept in the workflow artifact rather than committed to the public FSFFL NEXT repository.",
        "- Exact point-in-time acquisition metadata for each underlying source still must be checked before any provider-specific production weight is formally promoted.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
