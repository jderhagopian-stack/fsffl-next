from pathlib import Path


NAV = Path("src/fsffl/product/static/product_navigation.js")
MARKET = Path("src/fsffl/product/static/north_star_market.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_route_is_not_navigation_locked_before_team_context() -> None:
    source = _source(NAV)
    market = "{route:'opportunities',label:'Market',short:'Market',question:'What should I do?',icon:'market'}"
    assert market in source
    assert "{route:'opportunities',label:'Market',short:'Market',question:'What should I do?',icon:'market',teamScoped:true}" not in source


def test_north_star_market_does_not_shadow_global_route_state() -> None:
    source = _source(MARKET)
    assert "function opportunityState()" in source
    assert "function state()" not in source
    assert "state?.route==='opportunities'" in source
