from datetime import UTC, datetime

import pytest

from fsffl.value import (
    MarketContextCalibration,
    MarketPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
    apply_market_context,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
MARKET_SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="market units")


def _global_market() -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=100.0, stddev=8.0, p10=90.0, p50=100.0, p90=110.0),
        scale=MARKET_SCALE,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        market_context_id="dynasty-global",
        model_version="market-v1",
        evidence_sources=("source-a", "source-b"),
    )


def test_market_context_applies_shrunk_format_and_league_residuals() -> None:
    calibration = MarketContextCalibration(
        global_context_id="dynasty-global",
        format_context_id="12t-sf-half-ppr",
        league_context_id="league:abc",
        format_offset=10.0,
        league_offset=6.0,
        format_shrinkage_weight=0.8,
        league_shrinkage_weight=0.5,
        residual_stddev=0.0,
        model_version="market-context-v1",
        evidence_through=datetime(2026, 8, 31, tzinfo=UTC),
        format_sample_size=500,
        league_sample_size=30,
    )

    result = apply_market_context(
        _global_market(),
        calibration,
        as_of=NOW,
        model_version="league-market-v1",
    )

    assert result.market_context_id == "league:abc"
    assert result.distribution.mean == pytest.approx(111.0)
    assert result.distribution.p10 == pytest.approx(101.0)
    assert result.distribution.p50 == pytest.approx(111.0)
    assert result.distribution.p90 == pytest.approx(121.0)


def test_league_context_can_have_zero_weight_when_evidence_is_weak() -> None:
    calibration = MarketContextCalibration(
        global_context_id="dynasty-global",
        format_context_id="12t-sf-half-ppr",
        league_context_id="league:new",
        format_offset=8.0,
        league_offset=50.0,
        format_shrinkage_weight=0.75,
        league_shrinkage_weight=0.0,
        residual_stddev=0.0,
        model_version="market-context-v1",
        evidence_through=datetime(2026, 8, 31, tzinfo=UTC),
        format_sample_size=400,
        league_sample_size=2,
    )

    result = apply_market_context(
        _global_market(),
        calibration,
        as_of=NOW,
        model_version="league-market-v1",
    )

    assert result.distribution.mean == pytest.approx(106.0)


def test_market_context_rejects_future_calibration_evidence() -> None:
    calibration = MarketContextCalibration(
        global_context_id="dynasty-global",
        model_version="market-context-v1",
        evidence_through=datetime(2026, 9, 6, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="future evidence"):
        apply_market_context(
            _global_market(),
            calibration,
            as_of=NOW,
            model_version="league-market-v1",
        )


def test_market_context_rejects_wrong_global_baseline() -> None:
    calibration = MarketContextCalibration(
        global_context_id="different-global",
        model_version="market-context-v1",
        evidence_through=datetime(2026, 8, 31, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="global context"):
        apply_market_context(
            _global_market(),
            calibration,
            as_of=NOW,
            model_version="league-market-v1",
        )


def test_context_calibration_cannot_claim_weight_without_evidence() -> None:
    with pytest.raises(ValueError, match="league shrinkage weight requires league evidence"):
        MarketContextCalibration(
            global_context_id="dynasty-global",
            league_context_id="league:abc",
            league_offset=5.0,
            league_shrinkage_weight=0.5,
            model_version="market-context-v1",
            evidence_through=datetime(2026, 8, 31, tzinfo=UTC),
            league_sample_size=0,
        )
