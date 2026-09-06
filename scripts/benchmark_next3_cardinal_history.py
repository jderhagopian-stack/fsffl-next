from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from fsffl.value.calibration import CalibrationPanel
from fsffl.value.cardinal_history import (
    benchmark_historical_cardinal_kinds,
    build_fresh_historical_pairs,
    native_history_from_panel,
)


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("holdout-start must be timezone-aware")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark provider-native dynasty magnitude mappings on chronological "
            "holdout evidence. Research/challenger output only."
        )
    )
    parser.add_argument("--source-panel", type=Path, required=True)
    parser.add_argument("--target-panel", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-scale-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-scale-id", required=True)
    parser.add_argument("--market-context-id", required=True)
    parser.add_argument("--holdout-start", required=True)
    parser.add_argument("--max-target-age-days", type=int, default=14)
    parser.add_argument("--model-version-prefix", default="next3-cardinal-history-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_panel = CalibrationPanel.model_validate_json(args.source_panel.read_text(encoding="utf-8"))
    target_panel = CalibrationPanel.model_validate_json(args.target_panel.read_text(encoding="utf-8"))

    source = native_history_from_panel(
        source_panel,
        source_id=args.source_id,
        native_scale_id=args.source_scale_id,
        market_context_id=args.market_context_id,
    )
    target = native_history_from_panel(
        target_panel,
        source_id=args.target_id,
        native_scale_id=args.target_scale_id,
        market_context_id=args.market_context_id,
    )
    if not source or not target:
        raise RuntimeError("requested source/context produced no native historical evidence")

    pairs = build_fresh_historical_pairs(
        source,
        target,
        max_target_age_days=args.max_target_age_days,
    )
    if not pairs:
        raise RuntimeError("historical sources produced no fresh point-in-time overlap pairs")

    holdout_start = _dt(args.holdout_start)
    benchmarks = benchmark_historical_cardinal_kinds(
        pairs,
        holdout_start=holdout_start,
        model_version_prefix=args.model_version_prefix,
    )
    ranked = sorted(benchmarks, key=lambda row: (row.mean_absolute_error, row.root_mean_squared_error))

    output = {
        "authority_status": "challenger_research_only",
        "source": {"source_id": args.source_id, "scale_id": args.source_scale_id},
        "target": {"source_id": args.target_id, "scale_id": args.target_scale_id},
        "market_context_id": args.market_context_id,
        "holdout_start": holdout_start.isoformat(),
        "max_target_age_days": args.max_target_age_days,
        "source_observations": len(source),
        "target_observations": len(target),
        "fresh_overlap_pairs": len(pairs),
        "benchmarks": [row.model_dump(mode="json") for row in ranked],
        "best_holdout_candidate": ranked[0].kind.value,
        "notes": (
            "This compares provider-native cardinal mappings on later holdout evidence. "
            "It does not promote an FSFFL Value scale and does not authorize Decision/Search use."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")

    print("NEXT-3 cardinal historical challenger benchmark")
    print(f"pairs={len(pairs)} holdout_start={holdout_start.isoformat()}")
    for row in ranked:
        print(
            f"{row.kind.value}: n={row.sample_size} "
            f"mae={row.mean_absolute_error:.6f} rmse={row.root_mean_squared_error:.6f} "
            f"bias={row.mean_signed_error:.6f}"
        )
    print(f"best_holdout_candidate={ranked[0].kind.value}")


if __name__ == "__main__":
    main()
