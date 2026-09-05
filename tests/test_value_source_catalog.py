from datetime import UTC, datetime

from fsffl.value import (
    MarketEvidenceKind,
    MarketObservation,
    ValueAssetKind,
    ValueScale,
    estimate_market_price,
    next3_market_source_registry_v1,
)


AS_OF = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="market units")


def observation(source: str, value: float) -> MarketObservation:
    return MarketObservation(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        source=source,
        evidence_kind=MarketEvidenceKind.MARKET_INDEX,
        observed_at=AS_OF,
        value=value,
        scale=SCALE,
    )


def test_next3_market_catalog_groups_trade_derived_sources_conservatively() -> None:
    registry = next3_market_source_registry_v1()

    assert registry.independent_roots("dynastyprocess_market_values") == (
        "fantasypros_dynasty_consensus_root",
    )
    transaction_root = ("revealed_dynasty_transactions_root",)
    assert registry.independent_roots("dynastydealer_market_values") == transaction_root
    assert registry.independent_roots("fantasycalc_market_values") == transaction_root
    assert registry.independent_roots("statsguy_market_values") == transaction_root


def test_four_provider_panel_counts_as_two_independent_evidence_family_votes() -> None:
    registry = next3_market_source_registry_v1()
    result = estimate_market_price(
        (
            observation("dynastyprocess_market_values", 100.0),
            observation("dynastydealer_market_values", 80.0),
            observation("fantasycalc_market_values", 90.0),
            observation("statsguy_market_values", 110.0),
        ),
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        scale=SCALE,
        as_of=AS_OF,
        market_context_id="dynasty:sf",
        model_version="market-baseline-v1",
        minimum_sources=2,
        source_registry=registry,
    )

    # Transaction-family providers collapse to their median (90), while the
    # independent consensus-family observation contributes 100. The two evidence
    # families then receive equal authority in the robust baseline.
    assert result.distribution.mean == 95.0


def test_four_provider_panel_cannot_claim_four_independent_votes() -> None:
    registry = next3_market_source_registry_v1()
    try:
        estimate_market_price(
            (
                observation("dynastyprocess_market_values", 100.0),
                observation("dynastydealer_market_values", 80.0),
                observation("fantasycalc_market_values", 90.0),
                observation("statsguy_market_values", 110.0),
            ),
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="dynasty:sf",
            model_version="market-baseline-v1",
            minimum_sources=4,
            source_registry=registry,
        )
    except ValueError as exc:
        assert "2 independent sources; requires 4" in str(exc)
    else:
        raise AssertionError("shared transaction evidence roots must not count as four votes")
