from datetime import UTC, datetime

import pytest

from fsffl.forecast.ingestion import HistoricalProjectionSnapshot, normalize_historical_snapshots
from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.state.models import Position


def _snapshot(*, external_id: str = "row-1", issued_at: datetime | None = None) -> HistoricalProjectionSnapshot:
    issued = issued_at or datetime(2024, 8, 15, 12, tzinfo=UTC)
    return HistoricalProjectionSnapshot(
        provider="provider:test",
        external_id=external_id,
        player_id="player-1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2024, 9, 5, tzinfo=UTC),
        period_end=datetime(2025, 1, 6, tzinfo=UTC),
        mean=240.0,
        stddev=30.0,
        p10=200.0,
        p50=240.0,
        p90=280.0,
        issued_at=issued,
        retrieved_at=datetime(2026, 9, 4, tzinfo=UTC),
        source_version="archive-2024",
    )


def test_historical_ingestion_preserves_issue_and_retrieval_time() -> None:
    observation = normalize_historical_snapshots((_snapshot(),))[0]

    assert observation.as_of == datetime(2024, 8, 15, 12, tzinfo=UTC)
    assert observation.provenance.effective_at == observation.as_of
    assert observation.provenance.retrieved_at == datetime(2026, 9, 4, tzinfo=UTC)
    assert observation.provenance.provider_ref is not None
    assert observation.provenance.provider_ref.external_id == "row-1"


def test_historical_ingestion_rejects_exact_duplicate_revision() -> None:
    snapshot = _snapshot()
    with pytest.raises(ValueError, match="duplicate historical projection snapshot"):
        normalize_historical_snapshots((snapshot, snapshot))


def test_historical_ingestion_requires_timezone_aware_issue_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _snapshot(issued_at=datetime(2024, 8, 15, 12))
