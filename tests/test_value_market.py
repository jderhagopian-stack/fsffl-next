from datetime import UTC, datetime, timedelta

import pytest

from fsffl.value import (
    MarketEvidenceKind,
    MarketObservation,
    ValueAssetKind,
    ValueScale,
    estimate_market_price,
)


AS_OF = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="market units")


def observation(
    source: str,
    value: float,
    *,
    observed_at: datetime = AS_OF,
    scale: ValueScale = SCALE,
) -> MarketObservation:
    return MarketObservation(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        source=source,
        evidence_kind=MarketEvidenceKind.MARKET_INDEX,
        observed_at=observed_at,
        value=value,
        scale=scale,
        source_version="v1",
    )


def test_market_baseline_uses_latest_point_in_time_snapshot_per_source() -> None:
    result = estimate_market_price(
        (
            observation("a", 10.0, observed_at=AS_OF - timedelta(days=7)),
            observation("a", 90.0, observed_at=AS_OF - timedelta(days=1)),
            observation("b", 100.0),
            observation("c", 110.0),
        ),
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        scale=SCALE,
        as_of=AS_OF,
        market_context_id="sf-half-ppr",
        model_version="market-baseline-v1",
        minimum_sources=3,
    )

    assert result.distribution.mean == 100.0
    assert result.evidence_sources == ("a", "b", "c")
    assert result.distribution.p50 == 100.0


def test_market_baseline_rejects_future_information() -> None:
    with pytest.raises(ValueError, match="no eligible"):
        estimate_market_price(
            (observation("future", 100.0, observed_at=AS_OF + timedelta(seconds=1)),),
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="sf-half-ppr",
            model_version="market-baseline-v1",
        )


def test_market_baseline_fails_closed_on_thin_source_coverage() -> None:
    with pytest.raises(ValueError, match="requires 2"):
        estimate_market_price(
            (observation("only-source", 100.0),),
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="sf-half-ppr",
            model_version="market-baseline-v1",
            minimum_sources=2,
        )


def test_market_baseline_rejects_implicit_scale_conversion() -> None:
    other_scale = ValueScale(scale_id="other", version="v1", unit_label="other units")
    with pytest.raises(ValueError, match="converted explicitly"):
        estimate_market_price(
            (observation("a", 100.0, scale=other_scale),),
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="sf-half-ppr",
            model_version="market-baseline-v1",
        )


def test_conflicting_duplicate_source_snapshot_is_data_quality_failure() -> None:
    with pytest.raises(ValueError, match="conflicting duplicate"):
        estimate_market_price(
            (observation("a", 100.0), observation("a", 101.0)),
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="sf-half-ppr",
            model_version="market-baseline-v1",
        )
