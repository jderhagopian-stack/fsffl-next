from datetime import UTC, datetime

import pytest

from fsffl.value import (
    CalibrationEvidenceKind,
    CalibrationObservation,
    CalibrationPanel,
    DataRightsClass,
    benchmark_market_sources_against_transactions,
)


def _row(*, source: str, kind: CalibrationEvidenceKind, when: str, value: float) -> CalibrationObservation:
    return CalibrationObservation(
        source_id=source,
        evidence_kind=kind,
        observed_at=datetime.fromisoformat(when).replace(tzinfo=UTC),
        asset_id="player:1",
        format_context_id="dynasty:2qb",
        metric="market_value" if kind == CalibrationEvidenceKind.MARKET_VALUE else "transaction_price",
        value=value,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def test_market_benchmark_uses_latest_prior_snapshot_not_future_snapshot() -> None:
    panel = CalibrationPanel(
        observations=(
            _row(source="source-a", kind=CalibrationEvidenceKind.MARKET_VALUE, when="2025-01-01T00:00:00", value=90),
            _row(source="source-a", kind=CalibrationEvidenceKind.MARKET_VALUE, when="2025-03-01T00:00:00", value=999),
            _row(source="source-b", kind=CalibrationEvidenceKind.MARKET_VALUE, when="2025-01-15T00:00:00", value=110),
            _row(source="trades", kind=CalibrationEvidenceKind.COMPLETED_TRANSACTION, when="2025-02-01T00:00:00", value=100),
        ),
        as_of=datetime(2025, 3, 2, tzinfo=UTC),
        panel_version="panel-v1",
    )

    results = {result.source_id: result for result in benchmark_market_sources_against_transactions(panel)}

    assert results["source-a"].sample_size == 1
    assert results["source-a"].mean_absolute_error == 10
    assert results["source-a"].mean_signed_error == -10
    assert results["source-b"].mean_absolute_error == 10
    assert results["source-b"].mean_signed_error == 10


def test_market_benchmark_requires_transaction_evidence() -> None:
    panel = CalibrationPanel(
        observations=(
            _row(source="source-a", kind=CalibrationEvidenceKind.MARKET_VALUE, when="2025-01-01T00:00:00", value=90),
        ),
        as_of=datetime(2025, 1, 2, tzinfo=UTC),
        panel_version="panel-v1",
    )

    with pytest.raises(ValueError, match="completed transaction evidence"):
        benchmark_market_sources_against_transactions(panel)
