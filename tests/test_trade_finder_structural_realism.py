from pathlib import Path


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
