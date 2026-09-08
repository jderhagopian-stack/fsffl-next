from pathlib import Path

from fsffl.product.opportunity_search import _relative_market_gap


def test_trade_finder_only_adds_package_complexity_when_market_match_improves() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert "if pair_distance < single_distance:" in source
    assert "does not attempt to estimate a consolidation" in source
    assert "Decision owns package economics" in source
    assert "closer Cardinal market-value match" in source


def test_trade_finder_does_not_rank_two_for_one_packages_ahead_by_shape() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert '0 if row.get("package_shape") == "one_for_one" else 1' in source
    assert '0 if row.get("package_shape") == "two_for_one" else 1' not in source


def test_trade_finder_market_gap_is_scale_relative_without_a_fitted_cutoff() -> None:
    assert _relative_market_gap(100.0, 90.0) == _relative_market_gap(1000.0, 900.0)
    assert _relative_market_gap(0.0, 0.0) == 0.0

    search_source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")
    workspace_source = Path("src/fsffl/product/opportunity_workspace.py").read_text(encoding="utf-8")
    market_key = 'float(row["market_gap_ratio"])'
    need_key = 'float(row.get("focal_position_strength_index") or 100.0)'

    assert market_key in search_source
    assert need_key in search_source
    assert search_source.index(market_key) < search_source.index(need_key)
    assert '"market_gap_ratio": _relative_market_gap(receive_value, send_total)' in search_source
    assert '"cardinal_market_fit_then_roster_need"' in workspace_source
    assert "search_market_fit_has_no_fixed_acceptability_cutoff" in workspace_source
