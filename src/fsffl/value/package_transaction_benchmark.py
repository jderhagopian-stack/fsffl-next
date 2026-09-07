from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, median

from pydantic import Field

from fsffl.state.models import FrozenModel

from .cardinal import NativeMarketMagnitudeObservation
from .package_transaction_evidence import MultiAssetTradeObservation, PackageAssetKind, PackageTradeSide


class OneForManyPackageObservation(FrozenModel):
    transaction_id: str
    completed_at: datetime
    singleton_roster_id: int = Field(ge=1)
    package_roster_id: int = Field(ge=1)
    singleton_asset_id: str
    singleton_market_value: float = Field(gt=0.0)
    package_asset_count: int = Field(ge=2)
    package_market_value: float = Field(gt=0.0)
    package_largest_asset_share: float = Field(ge=0.0, le=1.0)
    package_value_premium_ratio: float


class PackageSizePremiumSummary(FrozenModel):
    package_asset_count: int = Field(ge=2)
    observations: int = Field(ge=1)
    mean_premium_ratio: float
    median_premium_ratio: float


class OneForManyPackageBenchmarkResult(FrozenModel):
    source_id: str
    market_context_id: str
    evaluated_trades: int = Field(ge=0)
    skipped_not_one_for_many: int = Field(ge=0)
    skipped_unmapped_or_stale: int = Field(ge=0)
    observations: tuple[OneForManyPackageObservation, ...]
    by_package_size: tuple[PackageSizePremiumSummary, ...]
    overall_mean_premium_ratio: float | None = None
    overall_median_premium_ratio: float | None = None
    max_snapshot_age_days: int = Field(ge=0)
    model_version: str = "next3-one-for-many-package-benchmark-v1"


def _eligible_asset_ids(side: PackageTradeSide) -> tuple[str, ...] | None:
    ids: list[str] = []
    for leg in side.received:
        if leg.asset_kind == PackageAssetKind.FAAB or leg.quantity != 1.0 or leg.canonical_asset_id is None:
            return None
        ids.append(leg.canonical_asset_id)
    return tuple(ids)


def _latest_values_before(
    history: tuple[NativeMarketMagnitudeObservation, ...],
    *,
    source_id: str,
    market_context_id: str,
    completed_at: datetime,
    max_age: timedelta,
) -> dict[str, float]:
    latest: dict[str, tuple[datetime, float]] = {}
    for row in history:
        if row.source_id != source_id or row.market_context_id != market_context_id:
            continue
        if row.observed_at > completed_at or completed_at - row.observed_at > max_age:
            continue
        prior = latest.get(row.asset_id)
        if prior is None or row.observed_at > prior[0]:
            latest[row.asset_id] = (row.observed_at, row.value)
    return {asset_id: value for asset_id, (_, value) in latest.items()}


def benchmark_one_for_many_package_premium(
    trades: tuple[MultiAssetTradeObservation, ...],
    market_history: tuple[NativeMarketMagnitudeObservation, ...],
    *,
    source_id: str,
    market_context_id: str,
    max_snapshot_age_days: int = 14,
    model_version: str = "next3-one-for-many-package-benchmark-v1",
) -> OneForManyPackageBenchmarkResult:
    """Measure observed whole-package clearing gaps for one-for-many trades.

    For a completed one-for-many transaction, the package side's point-in-time
    market total is compared with the singleton side's point-in-time market value.
    Positive premium means the multi-asset package carried more quoted market value
    than the singleton asset at the transaction date. The completed trade remains
    one package observation; no component receives a synthetic clearing price.

    This is research evidence only. It does not promote a premium into Value or
    Decision and does not infer causality from a completed trade.
    """

    if not source_id.strip() or not market_context_id.strip() or not model_version.strip():
        raise ValueError("package benchmark identifiers cannot be blank")
    if max_snapshot_age_days < 0:
        raise ValueError("max_snapshot_age_days must be non-negative")
    max_age = timedelta(days=max_snapshot_age_days)

    observations: list[OneForManyPackageObservation] = []
    skipped_shape = 0
    skipped_evidence = 0

    for trade in trades:
        if trade.format_context_id != market_context_id:
            continue
        a_count = len(trade.side_a.received)
        b_count = len(trade.side_b.received)
        if a_count == 1 and b_count >= 2:
            singleton_side, package_side = trade.side_a, trade.side_b
        elif b_count == 1 and a_count >= 2:
            singleton_side, package_side = trade.side_b, trade.side_a
        else:
            skipped_shape += 1
            continue

        singleton_ids = _eligible_asset_ids(singleton_side)
        package_ids = _eligible_asset_ids(package_side)
        if singleton_ids is None or package_ids is None:
            skipped_evidence += 1
            continue

        values = _latest_values_before(
            market_history,
            source_id=source_id,
            market_context_id=market_context_id,
            completed_at=trade.completed_at,
            max_age=max_age,
        )
        required = set(singleton_ids) | set(package_ids)
        if not required.issubset(values):
            skipped_evidence += 1
            continue

        singleton_value = values[singleton_ids[0]]
        package_values = [values[asset_id] for asset_id in package_ids]
        package_total = sum(package_values)
        if singleton_value <= 0 or package_total <= 0:
            skipped_evidence += 1
            continue
        observations.append(
            OneForManyPackageObservation(
                transaction_id=trade.transaction_id,
                completed_at=trade.completed_at,
                singleton_roster_id=singleton_side.roster_id,
                package_roster_id=package_side.roster_id,
                singleton_asset_id=singleton_ids[0],
                singleton_market_value=singleton_value,
                package_asset_count=len(package_ids),
                package_market_value=package_total,
                package_largest_asset_share=max(package_values) / package_total,
                package_value_premium_ratio=(package_total / singleton_value) - 1.0,
            )
        )

    by_size: dict[int, list[float]] = defaultdict(list)
    for row in observations:
        by_size[row.package_asset_count].append(row.package_value_premium_ratio)
    summaries = tuple(
        PackageSizePremiumSummary(
            package_asset_count=size,
            observations=len(values),
            mean_premium_ratio=mean(values),
            median_premium_ratio=median(values),
        )
        for size, values in sorted(by_size.items())
    )
    ratios = [row.package_value_premium_ratio for row in observations]
    return OneForManyPackageBenchmarkResult(
        source_id=source_id,
        market_context_id=market_context_id,
        evaluated_trades=len(observations),
        skipped_not_one_for_many=skipped_shape,
        skipped_unmapped_or_stale=skipped_evidence,
        observations=tuple(observations),
        by_package_size=summaries,
        overall_mean_premium_ratio=mean(ratios) if ratios else None,
        overall_median_premium_ratio=median(ratios) if ratios else None,
        max_snapshot_age_days=max_snapshot_age_days,
        model_version=model_version,
    )
