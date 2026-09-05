from datetime import UTC, datetime

from fsffl.value import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    DataRightsClass,
    build_market_calibration_panel_batch,
)


def _row(source_id: str, value: float) -> CalibrationObservation:
    return CalibrationObservation(
        source_id=source_id,
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        observed_at=datetime(2025, 8, 1, tzinfo=UTC),
        asset_id="player:1",
        format_context_id="dynasty:2qb",
        metric="market_value",
        value=value,
        rights_class=DataRightsClass.PUBLIC_REDISTRIBUTABLE,
    )


def test_batch_merges_multiple_sources_into_one_panel() -> None:
    result = build_market_calibration_panel_batch(
        {
            "source_a": lambda: (_row("source_a", 100.0),),
            "source_b": lambda: (_row("source_b", 110.0),),
        },
        as_of=datetime(2025, 9, 1, tzinfo=UTC),
        panel_version="test-v1",
    )

    assert result.completed_source_ids == ("source_a", "source_b")
    assert result.failed_source_ids == ()
    assert len(result.panel.observations) == 2
    assert result.observation_count_by_source_id == {"source_a": 1, "source_b": 1}


def test_batch_records_source_failure_without_hiding_other_source() -> None:
    def broken() -> tuple[CalibrationObservation, ...]:
        raise ValueError("provider unavailable")

    result = build_market_calibration_panel_batch(
        {
            "good": lambda: (_row("good", 100.0),),
            "bad": broken,
        },
        as_of=datetime(2025, 9, 1, tzinfo=UTC),
        panel_version="test-v1",
    )

    assert result.completed_source_ids == ("good",)
    assert result.failed_source_ids == ("bad",)
    assert len(result.panel.observations) == 1
    assert "provider unavailable" in result.errors_by_source_id["bad"]


def test_batch_rejects_loader_that_emits_wrong_source_identity() -> None:
    result = build_market_calibration_panel_batch(
        {"declared": lambda: (_row("other", 100.0),)},
        as_of=datetime(2025, 9, 1, tzinfo=UTC),
        panel_version="test-v1",
    )

    assert result.completed_source_ids == ()
    assert result.failed_source_ids == ("declared",)
    assert "other sources" in result.errors_by_source_id["declared"]
