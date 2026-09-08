from datetime import UTC, datetime, timedelta

from fsffl.value.calibration import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    CalibrationPanel,
    DataRightsClass,
)
from fsffl.value.cardinal_challenger import CardinalTransformKind
from fsffl.value.cardinal_history import (
    benchmark_historical_cardinal_kinds,
    build_fresh_historical_pairs,
    native_history_from_panel,
)


BASE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _row(source: str, asset: str, value: float, when: datetime) -> CalibrationObservation:
    return CalibrationObservation(
        source_id=source,
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        observed_at=when,
        asset_id=asset,
        format_context_id=CONTEXT,
        metric="market_value",
        value=value,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def test_historical_bridge_preserves_native_magnitude_and_filters_stale_pairs() -> None:
    source_panel = CalibrationPanel(
        observations=(
            _row("source-a", "p1", 10, BASE + timedelta(days=20)),
            _row("source-a", "p2", 20, BASE + timedelta(days=20)),
        ),
        as_of=BASE + timedelta(days=20),
        panel_version="a-v1",
    )
    target_panel = CalibrationPanel(
        observations=(
            _row("source-b", "p1", 25, BASE + timedelta(days=19)),
            _row("source-b", "p2", 45, BASE + timedelta(days=1)),
        ),
        as_of=BASE + timedelta(days=20),
        panel_version="b-v1",
    )
    source = native_history_from_panel(
        source_panel, source_id="source-a", native_scale_id="a-scale", market_context_id=CONTEXT
    )
    target = native_history_from_panel(
        target_panel, source_id="source-b", native_scale_id="b-scale", market_context_id=CONTEXT
    )
    pairs = build_fresh_historical_pairs(source, target, max_target_age_days=14)

    assert source[0].value == 10
    assert len(pairs) == 1
    assert pairs[0].asset_id == "p1"
    assert pairs[0].target_value == 25


def test_historical_benchmark_compares_affine_and_log_on_later_holdout() -> None:
    source_rows = []
    target_rows = []
    for day, native in enumerate((10, 20, 30, 40, 50, 60), start=1):
        when = BASE + timedelta(days=day)
        source_rows.append(_row("source-a", f"p{day}", native, when))
        target_rows.append(_row("source-b", f"p{day}", 2 * native + 5, when))

    source_panel = CalibrationPanel(
        observations=tuple(source_rows),
        as_of=BASE + timedelta(days=6),
        panel_version="a-v1",
    )
    target_panel = CalibrationPanel(
        observations=tuple(target_rows),
        as_of=BASE + timedelta(days=6),
        panel_version="b-v1",
    )
    source = native_history_from_panel(
        source_panel, source_id="source-a", native_scale_id="a-scale", market_context_id=CONTEXT
    )
    target = native_history_from_panel(
        target_panel, source_id="source-b", native_scale_id="b-scale", market_context_id=CONTEXT
    )
    pairs = build_fresh_historical_pairs(source, target)
    results = benchmark_historical_cardinal_kinds(
        pairs,
        holdout_start=BASE + timedelta(days=5),
        model_version_prefix="historical-test-v1",
    )
    by_kind = {result.kind: result for result in results}

    assert by_kind[CardinalTransformKind.AFFINE].sample_size == 2
    assert by_kind[CardinalTransformKind.AFFINE].mean_absolute_error < 1e-9
    assert (
        by_kind[CardinalTransformKind.AFFINE].mean_absolute_error
        < by_kind[CardinalTransformKind.LOG_AFFINE].mean_absolute_error
    )
