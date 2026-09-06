from datetime import UTC, datetime, timedelta

import pytest

from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_challenger import (
    CardinalCalibrationPair,
    CardinalTransformKind,
    benchmark_cardinal_transform,
    build_chronological_overlap_pairs,
    fit_cardinal_transform,
)


BASE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _native(source: str, scale: str, asset: str, value: float, when: datetime) -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset,
        source_id=source,
        native_scale_id=scale,
        value=value,
        observed_at=when,
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def _pair(native: float, target: float, when: datetime, asset: str) -> CardinalCalibrationPair:
    return CardinalCalibrationPair(
        asset_id=asset,
        source_id="source-a",
        native_scale_id="a-scale",
        native_value=native,
        target_source_id="source-b",
        target_scale_id="b-scale",
        target_value=target,
        source_observed_at=when,
        target_observed_at=when,
        market_context_id=CONTEXT,
    )


def test_overlap_pairing_uses_only_target_evidence_available_at_source_time() -> None:
    source = (
        _native("source-a", "a-scale", "p1", 50, BASE + timedelta(days=2)),
    )
    target = (
        _native("source-b", "b-scale", "p1", 90, BASE + timedelta(days=1)),
        _native("source-b", "b-scale", "p1", 999, BASE + timedelta(days=3)),
    )

    pairs = build_chronological_overlap_pairs(source, target)

    assert len(pairs) == 1
    assert pairs[0].target_value == 90
    assert pairs[0].target_observed_at == BASE + timedelta(days=1)


def test_affine_challenger_recovers_cardinal_spacing_and_scores_later_holdout() -> None:
    training = (
        _pair(10, 25, BASE + timedelta(days=1), "p1"),
        _pair(20, 45, BASE + timedelta(days=2), "p2"),
        _pair(30, 65, BASE + timedelta(days=3), "p3"),
        _pair(40, 85, BASE + timedelta(days=4), "p4"),
    )
    transform = fit_cardinal_transform(
        training,
        kind=CardinalTransformKind.AFFINE,
        fitted_at=BASE + timedelta(days=5),
        model_version="challenger-test-v1",
    )

    assert transform.slope == pytest.approx(2.0)
    assert transform.intercept == pytest.approx(5.0)
    assert transform.apply(50) == pytest.approx(105.0)

    holdout = (
        _pair(50, 105, BASE + timedelta(days=6), "p5"),
        _pair(60, 125, BASE + timedelta(days=7), "p6"),
    )
    result = benchmark_cardinal_transform(transform, holdout)
    assert result.mean_absolute_error == pytest.approx(0.0)
    assert result.root_mean_squared_error == pytest.approx(0.0)


def test_piecewise_challenger_preserves_non_linear_spacing_better_than_affine() -> None:
    training = tuple(
        _pair(
            float((index % 10) + 1),
            float(((index % 10) + 1) ** 2),
            BASE + timedelta(days=index + 1),
            f"train-{index}",
        )
        for index in range(30)
    )
    holdout = tuple(
        _pair(
            float((index % 10) + 1),
            float(((index % 10) + 1) ** 2),
            BASE + timedelta(days=31 + index),
            f"holdout-{index}",
        )
        for index in range(10)
    )
    fitted_at = BASE + timedelta(days=31)
    piecewise = fit_cardinal_transform(
        training,
        kind=CardinalTransformKind.PIECEWISE_QUANTILE,
        fitted_at=fitted_at,
        model_version="piecewise-test-v1",
    )
    affine = fit_cardinal_transform(
        training,
        kind=CardinalTransformKind.AFFINE,
        fitted_at=fitted_at,
        model_version="affine-test-v1",
    )

    piecewise_result = benchmark_cardinal_transform(piecewise, holdout)
    affine_result = benchmark_cardinal_transform(affine, holdout)

    assert len(piecewise.anchors) >= 3
    assert piecewise_result.mean_absolute_error < affine_result.mean_absolute_error


def test_benchmark_rejects_training_period_rows_as_holdout() -> None:
    training = (
        _pair(10, 25, BASE + timedelta(days=1), "p1"),
        _pair(20, 45, BASE + timedelta(days=2), "p2"),
        _pair(30, 65, BASE + timedelta(days=3), "p3"),
    )
    transform = fit_cardinal_transform(
        training,
        kind=CardinalTransformKind.AFFINE,
        fitted_at=BASE + timedelta(days=4),
        model_version="challenger-test-v1",
    )

    with pytest.raises(ValueError, match="later than transform training evidence"):
        benchmark_cardinal_transform(
            transform,
            (_pair(25, 55, BASE + timedelta(days=2), "p4"),),
        )


def test_fit_rejects_non_monotone_mapping() -> None:
    pairs = (
        _pair(10, 100, BASE + timedelta(days=1), "p1"),
        _pair(20, 80, BASE + timedelta(days=2), "p2"),
        _pair(30, 60, BASE + timedelta(days=3), "p3"),
    )
    with pytest.raises(ValueError, match="not monotone increasing"):
        fit_cardinal_transform(
            pairs,
            kind=CardinalTransformKind.AFFINE,
            fitted_at=BASE + timedelta(days=4),
            model_version="challenger-test-v1",
        )
