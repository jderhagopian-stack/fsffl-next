from pathlib import Path

ROOT = Path("src/fsffl/product")
SCENARIO = ROOT / "scenario_cache.py"
PERSISTENT = ROOT / "persistent_webapp.py"
QUICK_ROUTE = ROOT / "quick_frontier_routes.py"
QUICK_JS = ROOT / "static/quick_counter_frontier.js"
INDEX = ROOT / "static/index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_exact_scenario_cache_reuses_durable_authoritative_artifacts() -> None:
    source = _read(SCENARIO)
    for phrase in (
        "configure_scenario_cache_persistence",
        "get_reusable_artifact",
        "decode_simulation",
        "simulation_artifact",
        "put_artifact",
        "tier=durable",
        "No approximation",
        '"durable_hits"',
    ):
        assert phrase in source
    assert "simulation_count" not in source


def test_hosted_runtime_enables_scenario_persistence_without_new_authority() -> None:
    source = _read(PERSISTENT)
    assert "configure_scenario_cache_persistence(_persistence_store)" in source
    assert "install_quick_frontier_routes" in source


def test_quick_frontier_is_same_governed_engine_with_bounded_first_slice() -> None:
    source = _read(QUICK_ROUTE)
    assert "build_negotiation_frontier" in source
    assert "_QUICK_FRONTIER_EVALUATIONS = 4" in source
    assert "max_evaluations=_QUICK_FRONTIER_EVALUATIONS" in source
    assert '"deeper_search_available"' in source
    assert '"full_frontier_max_evaluations": 24' in source
    assert "acceptance_probability" not in source


def test_counter_client_returns_quick_results_before_optional_full_expansion() -> None:
    source = _read(QUICK_JS)
    assert "/api/trade-center/frontier/quick" in source
    assert "/api/trade-center/frontier" in source
    assert "Search more counter packages" in source
    assert "The current quick results stay visible" in source
    assert "window.exploreTradeFrontier=quick" in source


def test_quick_counter_asset_is_loaded_with_current_static_generation() -> None:
    source = _read(INDEX)
    assert "quick_counter_frontier.js?v=20260912-market-trade5" in source
    assert source.index("trade_center.js") < source.index("quick_counter_frontier.js")
    assert source.index("quick_counter_frontier.js") < source.index("market_trade_recomposition.js")
