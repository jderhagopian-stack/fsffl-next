from pathlib import Path

from fsffl.product.opportunity_search import _multi_lane_search_order


ROOT = Path(__file__).resolve().parents[1]


def _row(name: str, *, gap: float, target_value: float, focal: float, counterparty: float, send_count: int) -> dict[str, object]:
    return {
        "name": name,
        "market_gap_ratio": gap,
        "search_distance": gap * 100.0,
        "target_fsffl_value": target_value,
        "focal_position_strength_index": focal,
        "counterparty_receive_position_strength_index": counterparty,
        "send": [{"asset_ref": f"player:{name}:{index}"} for index in range(send_count)],
    }


def test_multi_lane_search_keeps_closest_market_match_first_but_admits_premium_target_early() -> None:
    rows = [
        _row("closest", gap=0.01, target_value=45.0, focal=95.0, counterparty=95.0, send_count=1),
        _row("market-two", gap=0.02, target_value=50.0, focal=90.0, counterparty=90.0, send_count=1),
        _row("premium", gap=0.30, target_value=99.0, focal=75.0, counterparty=80.0, send_count=3),
        _row("focal-need", gap=0.15, target_value=65.0, focal=40.0, counterparty=85.0, send_count=2),
        _row("counterparty-fit", gap=0.18, target_value=60.0, focal=80.0, counterparty=35.0, send_count=2),
    ]

    ordered = _multi_lane_search_order(rows)

    assert ordered[0]["name"] == "closest"
    assert [row["name"] for row in ordered[:5]].index("premium") < 4
    assert {row["name"] for row in ordered} == {row["name"] for row in rows}


def test_trade_search_supports_three_asset_premium_target_structures_without_consolidation_score() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()

    assert "_MAX_DISCOVERY_PACKAGE_SIZE = 3" in source
    assert '3: "three_for_one"' in source
    assert "for size in range(1, max_size + 1)" in source
    assert "the best single asset to veto all package complexity" in source
    assert "consolidation coefficient" in source
    assert "composite_score" not in source
    assert "opportunity_score" not in source


def test_both_trade_finder_spotlights_can_seed_nearby_package_frontier() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunity_spotlights.js").read_text()

    assert "opp-explore-market" in ui
    assert "opp-explore-promising" in ui
    assert "runSpotlightFrontier('market')" in ui
    assert "runSpotlightFrontier('decision')" in ui
    assert "spotlightFrontierKind" in ui
    assert "oppSpotlightSeedKey(kind)===requestKey" in ui
