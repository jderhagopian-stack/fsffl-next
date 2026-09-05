from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


def _rank_map(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    ranks: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        average_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = average_rank
        i = j
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom_x = sum(v * v for v in dx) ** 0.5
    denom_y = sum(v * v for v in dy) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / (denom_x * denom_y)


def _percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    ranks = _rank_map(values)
    n = len(ranks)
    if n <= 1:
        return {asset_id: 0.5 for asset_id in ranks}
    return {asset_id: (rank - 1.0) / (n - 1.0) for asset_id, rank in ranks.items()}


def benchmark(panel: dict) -> dict:
    latest: dict[tuple[str, str, str], tuple[str, float]] = {}
    source_counts: dict[str, int] = defaultdict(int)

    for row in panel.get("observations", []):
        if row.get("evidence_kind") != "market_value" or row.get("metric") != "market_value":
            continue
        source_id = row["source_id"]
        asset_id = row.get("asset_id")
        context = row.get("format_context_id") or "<none>"
        if not asset_id:
            continue
        key = (source_id, context, asset_id)
        observed_at = row["observed_at"]
        prior = latest.get(key)
        if prior is None or observed_at > prior[0]:
            latest[key] = (observed_at, float(row["value"]))

    by_source_context: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for (source_id, context, asset_id), (_, value) in latest.items():
        by_source_context[(source_id, context)][asset_id] = value
        source_counts[source_id] += 1

    pairs: list[dict] = []
    keys = sorted(by_source_context)
    for i, (source_a, context_a) in enumerate(keys):
        for source_b, context_b in keys[i + 1 :]:
            if context_a != context_b:
                continue
            values_a = by_source_context[(source_a, context_a)]
            values_b = by_source_context[(source_b, context_b)]
            overlap = sorted(set(values_a) & set(values_b))
            if not overlap:
                continue
            rank_a = _rank_map({asset: values_a[asset] for asset in overlap})
            rank_b = _rank_map({asset: values_b[asset] for asset in overlap})
            spearman = _pearson([rank_a[a] for a in overlap], [rank_b[a] for a in overlap])
            pct_a = _percentile_ranks({asset: values_a[asset] for asset in overlap})
            pct_b = _percentile_ranks({asset: values_b[asset] for asset in overlap})
            percentile_mae = mean(abs(pct_a[a] - pct_b[a]) for a in overlap)
            pairs.append(
                {
                    "source_a": source_a,
                    "source_b": source_b,
                    "format_context_id": context_a,
                    "overlap": len(overlap),
                    "spearman_rank_correlation": spearman,
                    "percentile_rank_mae": percentile_mae,
                }
            )

    consensus: list[dict] = []
    contexts = sorted({context for _, context in by_source_context})
    for context in contexts:
        percentile_by_source = {
            source: _percentile_ranks(values)
            for (source, ctx), values in by_source_context.items()
            if ctx == context
        }
        assets = sorted({asset for values in percentile_by_source.values() for asset in values})
        for asset_id in assets:
            votes = [values[asset_id] for values in percentile_by_source.values() if asset_id in values]
            if len(votes) < 2:
                continue
            consensus.append(
                {
                    "format_context_id": context,
                    "asset_id": asset_id,
                    "source_count": len(votes),
                    "median_percentile": median(votes),
                    "disagreement_range": max(votes) - min(votes),
                }
            )

    consensus.sort(key=lambda row: (-row["disagreement_range"], row["asset_id"]))
    return {
        "panel_version": panel.get("panel_version"),
        "as_of": panel.get("as_of"),
        "source_observation_counts": dict(sorted(source_counts.items())),
        "pairwise": pairs,
        "largest_consensus_disagreements": consensus[:100],
        "notes": (
            "Diagnostic only. Pairwise rank agreement and percentile differences compare source behavior; "
            "they do not establish predictive superiority or production authority."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark normalized NEXT-3 market sources.")
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    panel = json.loads(args.panel.read_text(encoding="utf-8"))
    result = benchmark(panel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    print("NEXT-3 source benchmark")
    print("source_counts=", result["source_observation_counts"])
    for pair in result["pairwise"]:
        print(
            "pair=",
            pair["source_a"],
            pair["source_b"],
            "context=",
            pair["format_context_id"],
            "overlap=",
            pair["overlap"],
            "spearman=",
            pair["spearman_rank_correlation"],
            "percentile_mae=",
            pair["percentile_rank_mae"],
        )


if __name__ == "__main__":
    main()
