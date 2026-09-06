from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from .calibration import CalibrationEvidenceKind, CalibrationObservation, CalibrationPanel, DataRightsClass
from .cardinal import NativeMarketMagnitudeObservation
from .cardinal_challenger import (
    CardinalCalibrationPair,
    CardinalTransformBenchmark,
    CardinalTransformKind,
    build_chronological_overlap_pairs,
    benchmark_cardinal_transform,
    fit_cardinal_transform,
)


def native_history_from_panel(
    panel: CalibrationPanel,
    *,
    source_id: str,
    native_scale_id: str,
    market_context_id: str,
) -> tuple[NativeMarketMagnitudeObservation, ...]:
    """Convert one historical market source into typed cardinal research evidence.

    This adapter preserves provider-native magnitude and point-in-time provenance.
    It is research-only and cannot create an authoritative FSFFL Value scale.
    """

    if not source_id.strip() or not native_scale_id.strip() or not market_context_id.strip():
        raise ValueError("historical cardinal identifiers cannot be blank")

    rows = []
    for row in panel.observations:
        if (
            row.source_id != source_id
            or row.evidence_kind != CalibrationEvidenceKind.MARKET_VALUE
            or row.metric != "market_value"
            or row.asset_id is None
            or row.format_context_id != market_context_id
        ):
            continue
        rows.append(
            NativeMarketMagnitudeObservation(
                asset_id=row.asset_id,
                source_id=row.source_id,
                native_scale_id=native_scale_id,
                value=row.value,
                observed_at=row.observed_at,
                market_context_id=market_context_id,
                rights_class=row.rights_class,
                source_version=row.source_version,
                provenance_uri=row.provenance_uri,
            )
        )
    return tuple(sorted(rows, key=lambda item: (item.observed_at, item.asset_id)))


def build_fresh_historical_pairs(
    source: tuple[NativeMarketMagnitudeObservation, ...],
    target: tuple[NativeMarketMagnitudeObservation, ...],
    *,
    max_target_age_days: int = 14,
) -> tuple[CardinalCalibrationPair, ...]:
    """Build chronological overlap pairs while rejecting stale target snapshots."""

    if max_target_age_days < 0:
        raise ValueError("max_target_age_days must be non-negative")
    pairs = build_chronological_overlap_pairs(source, target)
    max_age = timedelta(days=max_target_age_days)
    return tuple(
        pair
        for pair in pairs
        if pair.source_observed_at - pair.target_observed_at <= max_age
    )


def split_cardinal_pairs(
    pairs: tuple[CardinalCalibrationPair, ...],
    *,
    holdout_start: datetime,
) -> tuple[tuple[CardinalCalibrationPair, ...], tuple[CardinalCalibrationPair, ...]]:
    """Chronologically split paired evidence into training and later holdout rows."""

    if holdout_start.tzinfo is None:
        raise ValueError("holdout_start must be timezone-aware")
    training = tuple(row for row in pairs if row.source_observed_at < holdout_start)
    holdout = tuple(row for row in pairs if row.source_observed_at >= holdout_start)
    if len(training) < 3:
        raise ValueError("cardinal historical training split requires at least 3 pairs")
    if not holdout:
        raise ValueError("cardinal historical split requires later holdout pairs")
    return training, holdout


def benchmark_historical_cardinal_kinds(
    pairs: tuple[CardinalCalibrationPair, ...],
    *,
    holdout_start: datetime,
    model_version_prefix: str,
    kinds: tuple[CardinalTransformKind, ...] = (
        CardinalTransformKind.AFFINE,
        CardinalTransformKind.LOG_AFFINE,
    ),
) -> tuple[CardinalTransformBenchmark, ...]:
    """Fit frozen cardinal challengers and score them only on later evidence."""

    if not model_version_prefix.strip():
        raise ValueError("model_version_prefix cannot be blank")
    training, holdout = split_cardinal_pairs(pairs, holdout_start=holdout_start)
    results = []
    for kind in kinds:
        transform = fit_cardinal_transform(
            training,
            kind=kind,
            fitted_at=holdout_start,
            model_version=f"{model_version_prefix}-{kind.value}",
        )
        results.append(benchmark_cardinal_transform(transform, holdout))
    return tuple(results)
