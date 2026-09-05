from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("historical observations must be timezone-aware")
    return parsed


def _percentile_ranks(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    if not ordered:
        return {}
    raw: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            raw[ordered[k][0]] = rank
        i = j
    n = len(raw)
    if n == 1:
        return {asset: 0.5 for asset in raw}
    return {asset: (rank - 1.0) / (n - 1.0) for asset, rank in raw.items()}


def _snapshots(panel: dict) -> tuple[list[datetime], dict[datetime, dict[str, float]]]:
    grouped: dict[datetime, dict[str, float]] = defaultdict(dict)
    for row in panel.get("observations", []):
        if row.get("evidence_kind") != "market_value" or row.get("metric") != "market_value":
            continue
        asset_id = row.get("asset_id")
        if not asset_id:
            continue
        grouped[_dt(row["observed_at"])][asset_id] = float(row["value"])
    dates = sorted(grouped)
    return dates, dict(grouped)


def _latest_snapshot(
    dates: list[datetime],
    snapshots: dict[datetime, dict[str, float]],
    target: datetime,
    *,
    max_age_days: int,
) -> tuple[datetime, dict[str, float]] | None:
    idx = bisect_right(dates, target) - 1
    if idx < 0:
        return None
    snapshot_date = dates[idx]
    if target - snapshot_date > timedelta(days=max_age_days):
        return None
    return snapshot_date, snapshots[snapshot_date]


def benchmark(
    panel_a: dict,
    panel_b: dict,
    *,
    horizon_days: int = 28,
    max_snapshot_age_days: int = 14,
    min_overlap: int = 100,
) -> dict:
    dates_a, snapshots_a = _snapshots(panel_a)
    dates_b, snapshots_b = _snapshots(panel_b)
    if not dates_a or not dates_b:
        raise ValueError("both historical panels must contain market snapshots")

    evaluation_rows: list[dict] = []
    error_a: list[float] = []
    error_b: list[float] = []
    error_ensemble: list[float] = []

    for anchor in dates_a:
        current_b = _latest_snapshot(
            dates_b, snapshots_b, anchor, max_age_days=max_snapshot_age_days
        )
        if current_b is None:
            continue
        future_target = anchor + timedelta(days=horizon_days)
        future_a = _latest_snapshot(
            dates_a, snapshots_a, future_target, max_age_days=max_snapshot_age_days
        )
        future_b = _latest_snapshot(
            dates_b, snapshots_b, future_target, max_age_days=max_snapshot_age_days
        )
        if future_a is None or future_b is None:
            continue

        current_a_values = snapshots_a[anchor]
        _, current_b_values = current_b
        future_a_date, future_a_values = future_a
        future_b_date, future_b_values = future_b
        overlap = sorted(
            set(current_a_values)
            & set(current_b_values)
            & set(future_a_values)
            & set(future_b_values)
        )
        if len(overlap) < min_overlap:
            continue

        current_a_rank = _percentile_ranks({a: current_a_values[a] for a in overlap})
        current_b_rank = _percentile_ranks({a: current_b_values[a] for a in overlap})
        future_a_rank = _percentile_ranks({a: future_a_values[a] for a in overlap})
        future_b_rank = _percentile_ranks({a: future_b_values[a] for a in overlap})

        a_errors: list[float] = []
        b_errors: list[float] = []
        ensemble_errors: list[float] = []
        for asset_id in overlap:
            target = median((future_a_rank[asset_id], future_b_rank[asset_id]))
            current_ensemble = median((current_a_rank[asset_id], current_b_rank[asset_id]))
            a_errors.append(abs(current_a_rank[asset_id] - target))
            b_errors.append(abs(current_b_rank[asset_id] - target))
            ensemble_errors.append(abs(current_ensemble - target))

        error_a.extend(a_errors)
        error_b.extend(b_errors)
        error_ensemble.extend(ensemble_errors)
        evaluation_rows.append(
            {
                "anchor": anchor.isoformat(),
                "source_b_snapshot": current_b[0].isoformat(),
                "future_source_a_snapshot": future_a_date.isoformat(),
                "future_source_b_snapshot": future_b_date.isoformat(),
                "overlap": len(overlap),
                "source_a_mae": mean(a_errors),
                "source_b_mae": mean(b_errors),
                "equal_median_ensemble_mae": mean(ensemble_errors),
            }
        )

    if not evaluation_rows:
        raise RuntimeError("no chronological evaluation windows satisfied overlap/freshness rules")

    pooled = {
        "source_a_mae": mean(error_a),
        "source_b_mae": mean(error_b),
        "equal_median_ensemble_mae": mean(error_ensemble),
        "asset_evaluations": len(error_ensemble),
        "evaluation_windows": len(evaluation_rows),
    }
    best = min(
        (
            ("source_a", pooled["source_a_mae"]),
            ("source_b", pooled["source_b_mae"]),
            ("equal_median_ensemble", pooled["equal_median_ensemble_mae"]),
        ),
        key=lambda item: item[1],
    )[0]
    return {
        "horizon_days": horizon_days,
        "max_snapshot_age_days": max_snapshot_age_days,
        "min_overlap": min_overlap,
        "pooled": pooled,
        "best_diagnostic_candidate": best,
        "windows": evaluation_rows,
        "notes": (
            "Diagnostic chronological stability benchmark only. The target is the future median "
            "percentile rank of the two historical market sources, not completed transaction truth. "
            "This result cannot by itself promote production authority."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chronologically benchmark a two-source NEXT-3 market ensemble challenger."
    )
    parser.add_argument("--history-a", type=Path, required=True)
    parser.add_argument("--history-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--horizon-days", type=int, default=28)
    parser.add_argument("--max-snapshot-age-days", type=int, default=14)
    parser.add_argument("--min-overlap", type=int, default=100)
    args = parser.parse_args()

    result = benchmark(
        json.loads(args.history_a.read_text(encoding="utf-8")),
        json.loads(args.history_b.read_text(encoding="utf-8")),
        horizon_days=args.horizon_days,
        max_snapshot_age_days=args.max_snapshot_age_days,
        min_overlap=args.min_overlap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print("NEXT-3 chronological ensemble diagnostic")
    print("pooled=", result["pooled"])
    print("best_diagnostic_candidate=", result["best_diagnostic_candidate"])


if __name__ == "__main__":
    main()
