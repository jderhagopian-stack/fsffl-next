from pathlib import Path


NAV = Path("src/fsffl/product/static/product_navigation.js")
MARKET = Path("src/fsffl/product/static/north_star_market.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_explore_route_is_not_navigation_locked_before_team_context() -> None:
    source = _source(NAV)
    explore = "{route:'opportunities',label:'Explore',short:'Explore',question:'Where is there something worth doing?',icon:'market'}"
    assert explore in source
    assert "{route:'opportunities',label:'Explore',short:'Explore',question:'Where is there something worth doing?',icon:'market',teamScoped:true}" not in source


def test_north_star_market_does_not_shadow_global_route_state() -> None:
    source = _source(MARKET)
    assert "const opp=()=>{" in source
    assert "const context=()=>{" in source
    assert "const onMarket=()=>{" in source
    assert "function state()" not in source
    assert 'state?.route==="opportunities"' in source
