from pathlib import Path

from fsffl.product.opportunity_search import _multi_lane_search_order, _relative_market_gap


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


def test_trade_finder_broadens_package_complexity_without_inventing_consolidation_economics() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert "_MAX_DISCOVERY_PACKAGE_SIZE = 3" in source
    assert "for size in range(1, max_size + 1)" in source
    assert "best single asset to veto all package complexity" in source
    assert "consolidation coefficient" in source
    assert "Decision owns whether the structure is actually good" in source
    assert "award a consolidation premium" in source
    assert "if pair_distance < single_distance:" not in source


def test_trade_finder_package_shape_is_an_exploration_lane_not_a_value_score() -> None:
    rows = [
        _row("closest", gap=0.01, target_value=40.0, focal=95.0, counterparty=95.0, send_count=1),
        _row("package", gap=0.20, target_value=80.0, focal=80.0, counterparty=80.0, send_count=3),
    ]

    ordered = _multi_lane_search_order(rows)

    assert ordered[0]["name"] == "closest"
    assert {row["name"] for row in ordered} == {"closest", "package"}
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")
    assert "No metrics are blended into a score" in source
    assert "composite_score" not in source
    assert "opportunity_score" not in source


def test_trade_finder_market_gap_is_scale_relative_without_a_fitted_cutoff() -> None:
    assert _relative_market_gap(100.0, 90.0) == _relative_market_gap(1000.0, 900.0)
    assert _relative_market_gap(0.0, 0.0) == 0.0

    search_source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")
    workspace_source = Path("src/fsffl/product/opportunity_workspace.py").read_text(encoding="utf-8")

    assert '"market_gap_ratio": _relative_market_gap(receive_value, send_total)' in search_source
    assert "market_gap_ratio" in search_source
    assert "_multi_lane_search_order" in search_source
    assert "closest market match" in search_source
    assert "search_market_fit_has_no_fixed_acceptability_cutoff" in workspace_source


def test_trade_finder_asset_payload_preserves_canonical_player_context() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert '"detail": option.detail' in source
    assert '"age_years": option.age_years' in source
    assert '"roster_slot": option.roster_slot.value if option.roster_slot is not None else None' in source
    assert "def _asset_payload" in source
    assert "fsffl_value" in source
