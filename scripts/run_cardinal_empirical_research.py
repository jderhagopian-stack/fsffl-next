from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from fsffl.value.calibration import CalibrationPanel
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_challenger import (
    CardinalTransformKind,
    benchmark_cardinal_transform,
    fit_cardinal_transform,
)
from fsffl.value.cardinal_history import (
    build_fresh_historical_pairs,
    native_history_from_panel,
    split_cardinal_pairs,
)
from fsffl.value.cardinal_transaction_benchmark import (
    benchmark_cardinal_sources_against_one_for_one_trades,
)
from fsffl.value.transaction_evidence import (
    OneForOneTradeObservation,
    normalize_sleeper_one_for_one_trades,
)

USER_AGENT = "fsffl-next-cardinal-research/0.1"
SLEEPER_BASE = "https://api.sleeper.app/v1"


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed fixed research endpoints
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def _load_panel(path: Path) -> CalibrationPanel:
    return CalibrationPanel.model_validate_json(path.read_text(encoding="utf-8"))


def _load_sleeper_crosswalk(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"sleeper_id", "asset_id"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("crosswalk must contain sleeper_id and asset_id")
        return {
            (row.get("sleeper_id") or "").strip(): (row.get("asset_id") or "").strip()
            for row in reader
            if (row.get("sleeper_id") or "").strip() and (row.get("asset_id") or "").strip()
        }


def _league_chain(current_league_id: str, *, minimum_season: int) -> tuple[tuple[str, int], ...]:
    result: list[tuple[str, int]] = []
    seen: set[str] = set()
    league_id = current_league_id
    while league_id and league_id not in seen:
        seen.add(league_id)
        payload = json.loads(_download_text(f"{SLEEPER_BASE}/league/{league_id}"))
        season = int(payload["season"])
        if season >= minimum_season:
            result.append((league_id, season))
        previous = str(payload.get("previous_league_id") or "").strip()
        if not previous or season <= minimum_season:
            break
        league_id = previous
    result.sort(key=lambda item: item[1])
    return tuple(result)


def _sleeper_one_for_one_history(
    current_league_id: str,
    *,
    crosswalk: dict[str, str],
    minimum_season: int,
    format_context_id: str,
    as_of: datetime,
) -> tuple[OneForOneTradeObservation, ...]:
    observations: list[OneForOneTradeObservation] = []
    seen_transactions: set[str] = set()
    for league_id, season in _league_chain(current_league_id, minimum_season=minimum_season):
        rows_by_id: dict[str, dict] = {}
        for round_number in range(0, 19):
            try:
                payload = json.loads(
                    _download_text(
                        f"{SLEEPER_BASE}/league/{league_id}/transactions/{round_number}"
                    )
                )
            except Exception:
                continue
            if not isinstance(payload, list):
                continue
            for row in payload:
                if not isinstance(row, dict):
                    continue
                transaction_id = str(row.get("transaction_id") or "").strip()
                if transaction_id:
                    rows_by_id[transaction_id] = row
        normalized = normalize_sleeper_one_for_one_trades(
            json.dumps(list(rows_by_id.values())),
            league_id=f"sleeper:{league_id}",
            format_context_id=format_context_id,
            asset_id_by_sleeper_id=crosswalk,
            as_of=as_of,
            provenance_uri=f"sleeper:league:{league_id}:season:{season}",
        )
        for trade in normalized.observations:
            if trade.transaction_id not in seen_transactions:
                seen_transactions.add(trade.transaction_id)
                observations.append(trade)
    observations.sort(key=lambda item: (item.completed_at, item.transaction_id))
    return tuple(observations)


def _holdout_start(pairs, fraction: float) -> datetime:
    if not 0.5 <= fraction < 1.0:
        raise ValueError("holdout fraction boundary must be in [0.5, 1.0)")
    dates = sorted({pair.source_observed_at for pair in pairs})
    if len(dates) < 4:
        raise ValueError("cardinal empirical benchmark requires at least four distinct dates")
    index = min(len(dates) - 1, max(1, int(len(dates) * fraction)))
    return dates[index]


def _benchmark_mapping(pairs, *, label: str, holdout_fraction: float) -> dict[str, object]:
    holdout_start = _holdout_start(pairs, holdout_fraction)
    training, holdout = split_cardinal_pairs(pairs, holdout_start=holdout_start)
    rows = []
    for kind in (
        CardinalTransformKind.AFFINE,
        CardinalTransformKind.LOG_AFFINE,
        CardinalTransformKind.PIECEWISE_QUANTILE,
    ):
        transform = fit_cardinal_transform(
            training,
            kind=kind,
            fitted_at=holdout_start,
            model_version=f"next3-cardinal-empirical-{label}-{kind.value}-v1",
        )
        benchmark = benchmark_cardinal_transform(transform, holdout)
        rows.append(
            {
                "kind": kind.value,
                "training_pairs": len(training),
                "holdout_pairs": benchmark.sample_size,
                "mae": benchmark.mean_absolute_error,
                "rmse": benchmark.root_mean_squared_error,
                "mean_signed_error": benchmark.mean_signed_error,
                "intercept": transform.intercept,
                "slope": transform.slope,
                "anchors": [list(anchor) for anchor in transform.anchors],
            }
        )
    rows.sort(key=lambda item: (item["mae"], item["rmse"]))
    return {
        "label": label,
        "holdout_start": holdout_start.isoformat(),
        "candidate_results": rows,
        "best_kind": rows[0]["kind"],
    }


def _latest_snapshot_summary(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
) -> dict[str, object]:
    if not observations:
        return {}
    latest_at = max(row.observed_at for row in observations)
    latest_day = latest_at.date()
    values = sorted(row.value for row in observations if row.observed_at.date() == latest_day)
    if not values:
        return {}

    def quantile(q: float) -> float:
        idx = round((len(values) - 1) * q)
        return float(values[idx])

    q25 = quantile(0.25)
    q50 = quantile(0.50)
    q75 = quantile(0.75)
    q90 = quantile(0.90)
    q99 = quantile(0.99)
    return {
        "snapshot_date": latest_day.isoformat(),
        "assets": len(values),
        "minimum": values[0],
        "q25": q25,
        "median": q50,
        "q75": q75,
        "q90": q90,
        "q99": q99,
        "maximum": values[-1],
        "q99_to_median_ratio": None if q50 == 0 else q99 / q50,
        "q90_to_median_ratio": None if q50 == 0 else q90 / q50,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run end-to-end empirical research for the FSFFL cardinal Value challenger."
    )
    parser.add_argument("--statsguy-history", type=Path, required=True)
    parser.add_argument("--dynastyprocess-history", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--sleeper-league-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--market-context-id", default="dynasty:2qb")
    parser.add_argument("--minimum-season", type=int, default=2023)
    parser.add_argument("--max-target-age-days", type=int, default=14)
    parser.add_argument("--holdout-fraction", type=float, default=0.75)
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args()

    as_of = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(UTC)
    )
    if as_of.tzinfo is None:
        raise ValueError("as-of must be timezone-aware")

    statsguy_panel = _load_panel(args.statsguy_history)
    dynastyprocess_panel = _load_panel(args.dynastyprocess_history)
    crosswalk = _load_sleeper_crosswalk(args.crosswalk)

    statsguy = native_history_from_panel(
        statsguy_panel,
        source_id="statsguy_market_values",
        native_scale_id="statsguy-dynasty-value",
        market_context_id=args.market_context_id,
    )
    dynastyprocess = native_history_from_panel(
        dynastyprocess_panel,
        source_id="dynastyprocess_market_values",
        native_scale_id="dynastyprocess-2qb-value",
        market_context_id=args.market_context_id,
    )
    if not statsguy or not dynastyprocess:
        raise RuntimeError("both historical sources must contain cardinal observations")

    sg_to_dp_pairs = build_fresh_historical_pairs(
        statsguy,
        dynastyprocess,
        max_target_age_days=args.max_target_age_days,
    )
    dp_to_sg_pairs = build_fresh_historical_pairs(
        dynastyprocess,
        statsguy,
        max_target_age_days=args.max_target_age_days,
    )
    if len(sg_to_dp_pairs) < 20 or len(dp_to_sg_pairs) < 20:
        raise RuntimeError(
            "insufficient fresh historical overlap for empirical cardinal mapping: "
            f"statsguy_to_dynastyprocess={len(sg_to_dp_pairs)} "
            f"dynastyprocess_to_statsguy={len(dp_to_sg_pairs)}"
        )

    trades = _sleeper_one_for_one_history(
        args.sleeper_league_id,
        crosswalk=crosswalk,
        minimum_season=args.minimum_season,
        format_context_id=args.market_context_id,
        as_of=as_of,
    )
    native_trade_benchmark = benchmark_cardinal_sources_against_one_for_one_trades(
        statsguy + dynastyprocess,
        trades,
        market_context_id=args.market_context_id,
        max_snapshot_age_days=args.max_target_age_days,
    )

    trade_dates = [trade.completed_at.isoformat() for trade in trades]
    report = {
        "status": "challenger_research_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "as_of": as_of.isoformat(),
        "market_context_id": args.market_context_id,
        "minimum_sleeper_season": args.minimum_season,
        "startup_2022_excluded": args.minimum_season > 2022,
        "source_history": {
            "statsguy": {
                "observations": len(statsguy),
                "first": min(row.observed_at for row in statsguy).isoformat(),
                "last": max(row.observed_at for row in statsguy).isoformat(),
                "latest_snapshot": _latest_snapshot_summary(statsguy),
            },
            "dynastyprocess": {
                "observations": len(dynastyprocess),
                "first": min(row.observed_at for row in dynastyprocess).isoformat(),
                "last": max(row.observed_at for row in dynastyprocess).isoformat(),
                "latest_snapshot": _latest_snapshot_summary(dynastyprocess),
            },
        },
        "mapping_benchmarks": [
            _benchmark_mapping(
                sg_to_dp_pairs,
                label="statsguy-to-dynastyprocess",
                holdout_fraction=args.holdout_fraction,
            ),
            _benchmark_mapping(
                dp_to_sg_pairs,
                label="dynastyprocess-to-statsguy",
                holdout_fraction=args.holdout_fraction,
            ),
        ],
        "one_for_one_trade_benchmark": native_trade_benchmark.model_dump(mode="json"),
        "one_for_one_trade_count": len(trades),
        "one_for_one_trade_dates": trade_dates,
        "notes": [
            "All scale mappings are challenger research only; no production Value authority is changed.",
            "Chronological holdout is used for transformation comparison; future market evidence is excluded.",
            "Completed one-for-one Sleeper trades are pairwise revealed-preference evidence, not exact scalar clearing prices.",
            "The 2022 startup season is excluded from transaction calibration by construction.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print("FSFFL NEXT cardinal empirical research")
    print(f"statsguy observations={len(statsguy)}")
    print(f"dynastyprocess observations={len(dynastyprocess)}")
    print(f"fresh overlap sg->dp={len(sg_to_dp_pairs)} dp->sg={len(dp_to_sg_pairs)}")
    print(f"clean one-for-one trades={len(trades)} dates={trade_dates}")
    for mapping in report["mapping_benchmarks"]:
        best = mapping["candidate_results"][0]
        print(
            f"{mapping['label']} best={best['kind']} "
            f"mae={best['mae']:.4f} rmse={best['rmse']:.4f} "
            f"holdout={best['holdout_pairs']}"
        )
    for row in native_trade_benchmark.source_results:
        print(
            f"trade benchmark {row.source_id}/{row.native_scale_id}: "
            f"n={row.evaluated_trades} mean_relative_gap={row.mean_abs_relative_gap:.4f} "
            f"median_relative_gap={row.median_abs_relative_gap:.4f}"
        )
    print("RESULT_JSON_BEGIN")
    print(json.dumps(report, sort_keys=True))
    print("RESULT_JSON_END")


if __name__ == "__main__":
    main()
