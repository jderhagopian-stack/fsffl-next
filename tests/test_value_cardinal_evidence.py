from datetime import UTC, datetime

from fsffl.value.calibration import CalibrationEvidenceKind, CalibrationObservation, DataRightsClass
from fsffl.value.cardinal import characterize_native_magnitudes, preserve_native_market_magnitudes


NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def _row(source: str, asset: str, value: float, *, minute: int = 0) -> CalibrationObservation:
    return CalibrationObservation(
        source_id=source,
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        observed_at=NOW.replace(minute=minute),
        asset_id=asset,
        format_context_id="dynasty:12t:sf:0.5ppr",
        metric="market_value",
        value=value,
        rights_class=DataRightsClass.RUNTIME_ONLY,
        provenance_uri=f"https://example.test/{source}",
    )


def test_native_market_magnitude_is_preserved_without_percentile_conversion() -> None:
    rows = (
        _row("dynastydealer_market_values", "p1", 9000),
        _row("fantasycalc_market_values", "p1", 7350),
        _row("statsguy_market_values", "p1", 91),
    )

    preserved = preserve_native_market_magnitudes(rows)
    by_source = {row.source_id: row for row in preserved}

    assert by_source["dynastydealer_market_values"].value == 9000
    assert by_source["fantasycalc_market_values"].value == 7350
    assert by_source["statsguy_market_values"].value == 91
    assert by_source["dynastydealer_market_values"].native_scale_id == "dynastydealer-current-value"
    assert all(row.market_context_id == "dynasty:12t:sf:0.5ppr" for row in preserved)


def test_latest_native_snapshot_wins_per_source_asset() -> None:
    preserved = preserve_native_market_magnitudes(
        (
            _row("fantasycalc_market_values", "p1", 7000, minute=0),
            _row("fantasycalc_market_values", "p1", 7600, minute=1),
        )
    )
    assert len(preserved) == 1
    assert preserved[0].value == 7600


def test_native_scale_characterization_preserves_magnitude_shape() -> None:
    preserved = preserve_native_market_magnitudes(
        (
            _row("dynastydealer_market_values", "p1", 10000),
            _row("dynastydealer_market_values", "p2", 5000),
            _row("dynastydealer_market_values", "p3", 1000),
        )
    )
    summary = characterize_native_magnitudes(preserved)[0]

    assert summary.sample_size == 3
    assert summary.minimum == 1000
    assert summary.median == 5000
    assert summary.maximum == 10000
    assert summary.top_to_median_ratio == 2.0
