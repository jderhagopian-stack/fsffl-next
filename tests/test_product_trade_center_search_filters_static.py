from pathlib import Path


TRADE_JS = Path("src/fsffl/product/static/trade_center.js").read_text(encoding="utf-8")


def test_trade_center_has_explicit_player_name_search_and_safe_filters() -> None:
    assert "Search player by name" in TRADE_JS
    assert "All assets" in TRADE_JS
    assert "Players" in TRADE_JS
    assert "Picks" in TRADE_JS
    assert "All positions" in TRADE_JS
    assert "All roster slots" in TRADE_JS


def test_trade_center_name_search_only_matches_player_labels() -> None:
    assert "option.asset_kind!=='player'||!option.label.toLowerCase().includes(query)" in TRADE_JS
    assert "option.detail!==position" in TRADE_JS
    assert "option.roster_slot!==slot" in TRADE_JS


def test_trade_center_filters_do_not_create_value_or_decision_logic() -> None:
    assert "provisionalScoreFor" in TRADE_JS
    assert "display-only" in TRADE_JS
    assert "acceptance probability" in TRADE_JS
    assert "package economics" in TRADE_JS
    assert "*10000" not in TRADE_JS
    assert "* 10000" not in TRADE_JS
