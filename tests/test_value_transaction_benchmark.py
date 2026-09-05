from datetime import UTC, datetime, timedelta

from fsffl.value import CalibrationEvidenceKind, CalibrationObservation, DataRightsClass
from fsffl.value.transaction_benchmark import benchmark_market_sources_against_one_for_one_trades
from fsffl.value.transaction_evidence import OneForOneTradeObservation


TRADE_TIME = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
SNAPSHOT_TIME = TRADE_TIME - timedelta(days=3)


def market(source: str, asset: str, value: float, *, observed_at: datetime = SNAPSHOT_TIME):
    return CalibrationObservation(
        source_id=source,
        evidence_kind=CalibrationEvidenceKind.MARKET_VALUE,
        observed_at=observed_at,
        asset_id=asset,
        format_context_id="dynasty:sf",
        metric="market_value",
        value=value,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def trade() -> OneForOneTradeObservation:
    return OneForOneTradeObservation(
        transaction_id="trade-1",
        league_id="league-1",
        format_context_id="dynasty:sf",
        completed_at=TRADE_TIME,
        roster_a_id=1,
        roster_b_id=2,
        asset_a_id="player:a",
        asset_b_id="player:b",
    )


def test_scores_sources_and_median_ensemble_without_future_leakage() -> None:
    rows = (
        market("source-a", "player:a", 90.0),
        market("source-a", "player:b", 80.0),
        market("source-a", "player:c", 10.0),
        market("source-b", "player:a", 100.0),
        market("source-b", "player:b", 20.0),
        market("source-b", "player:c", 10.0),
        # This future snapshot would make source-a look very different if leaked.
        market("source-a", "player:a", 100.0, observed_at=TRADE_TIME + timedelta(days=1)),
        market("source-a", "player:b", 0.0, observed_at=TRADE_TIME + timedelta(days=1)),
        market("source-a", "player:c", 50.0, observed_at=TRADE_TIME + timedelta(days=1)),
    )
    result = benchmark_market_sources_against_one_for_one_trades(
        rows,
        (trade(),),
        compatible_context_ids=("dynasty:sf",),
        max_snapshot_age_days=7,
        ensemble_minimum_sources=2,
    )

    by_source = {row.source_id: row for row in result.source_results}
    assert by_source["source-a"].evaluated_trades == 1
    assert by_source["source-a"].mean_abs_percentile_gap == 0.5
    assert by_source["source-b"].mean_abs_percentile_gap == 0.5
    assert result.ensemble_result is not None
    assert result.ensemble_result.evaluated_trades == 1
    assert result.ensemble_result.mean_abs_percentile_gap == 0.5


def test_excludes_stale_market_snapshot() -> None:
    rows = (
        market("stale", "player:a", 100.0, observed_at=TRADE_TIME - timedelta(days=30)),
        market("stale", "player:b", 90.0, observed_at=TRADE_TIME - timedelta(days=30)),
    )
    result = benchmark_market_sources_against_one_for_one_trades(
        rows,
        (trade(),),
        compatible_context_ids=("dynasty:sf",),
        max_snapshot_age_days=14,
    )
    assert result.source_results == ()
    assert result.ensemble_result is None
