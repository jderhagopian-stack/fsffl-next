from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Lock
import shutil
import subprocess
import time

import pytest

from fsffl.product import scenario_cache


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"
STATIC = PRODUCT / "static"
RELEASE = "20260913-phase3-latency1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_quick_path_uses_same_workspace_builder_without_decision_enrichment() -> None:
    routes = _text(PRODUCT / "progressive_delivery_routes.py")
    persistent = _text(PRODUCT / "persistent_webapp.py")
    assert '"/api/opportunities/workspace/quick"' in routes
    assert "workspace_builder(runtime, bilateral_evaluation_limit=0)" in routes
    assert '"completeness": "search_only"' in routes
    assert '"decision_enrichment_pending"' in routes
    assert "workspace_builder=_webapp.build_opportunity_workspace" in persistent
    assert "make_cached_opportunity_workspace" in persistent


def test_trade_quick_path_is_partial_and_does_not_create_simulation_or_decision_truth() -> None:
    routes = _text(PRODUCT / "progressive_delivery_routes.py")
    assert '"/api/trade-center/quick"' in routes
    assert "apply_bilateral_trade" in routes
    assert "summarize_bilateral_trade_economics" in routes
    assert '"completeness": "partial_package_economics"' in routes
    assert '"final_disposition_available": False' in routes
    assert '"full_simulation_pending": True' in routes
    for forbidden in (
        "run_live_simulation_analytics",
        "build_post_trade_simulation_comparison",
        "classify_bilateral_trade_decision",
        "decide_trade_disposition",
    ):
        assert forbidden not in routes


def test_browser_delivers_quick_then_deeper_authoritative_trade_evidence() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    quick = script.index("/api/trade-center/quick")
    analysis = script.index("/api/trade-center/analyze")
    simulation = script.index("/api/trade-center/simulate")
    assert quick < analysis < simulation
    assert "Quick view ready" in script
    assert "Full 50,000-run season simulation running" in script
    assert "scenario_cache_hit" in script
    assert "they are not a final trade recommendation" in script


def test_progressive_results_are_context_guarded_and_duplicate_trade_clicks_are_coalesced() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    assert "tradeGeneration+=1" in script
    assert "key===draftKey()" in script
    assert "if(!currentTrade(generation,key))return" in script
    assert script.count("if(!currentTrade(generation,key))return") >= 4
    assert "if(activeTradeKey===key)return" in script
    assert "contextStillCurrent" in script
    assert "oppPayloadMatchesCapturedContext(quick,captured)" in script
    assert "oppPayloadMatchesCapturedContext(full,captured)" in script


def test_market_quick_result_renders_before_full_decision_request_finishes() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    quick_await = script.index("const quick=await request('/api/opportunities/workspace/quick')")
    quick_render = script.index("renderOpportunityWorkspace();", quick_await)
    full_request = script.index("request('/api/opportunities/workspace').then", quick_render)
    assert quick_await < quick_render < full_request
    assert "Quick view remains available" in script
    assert "Updated analysis ready" in script


def test_progressive_assets_use_one_fresh_hosted_release_generation() -> None:
    html = _text(STATIC / "index.html")
    versions = {token.split("?v=")[1].split('"')[0] for token in html.split() if "?v=" in token}
    assert versions == {RELEASE}
    assert f"progressive_delivery.css?v={RELEASE}" in html
    assert f"progressive_delivery.js?v={RELEASE}" in html
    assert html.rfind("progressive_delivery.js") > html.rfind("market_trade_drilldown.js")


def test_progressive_mobile_layout_keeps_first_answer_compact() -> None:
    css = _text(STATIC / "progressive_delivery.css")
    assert "@media(max-width:680px)" in css
    assert ".fsffl-progressive-sides{grid-template-columns:1fr}" in css
    assert ".fsffl-market-progress" in css
    assert "flex-direction:column" in css


def test_progressive_browser_script_parses() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    result = subprocess.run(
        [node, "--check", str(STATIC / "progressive_delivery.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


class _FakeEvidence:
    model_version = "forecast-test-v1"
    successful_source_ids = ()
    league_scored_forecasts = ()


class _FakeState:
    def __init__(self, state_id: str):
        self.state_id = state_id


def _fake_result(state_id: str):
    return SimpleNamespace(league_view=SimpleNamespace(context=SimpleNamespace(league_state_id=state_id)))


def test_identical_concurrent_simulations_share_one_authoritative_run_and_near_repeat_misses() -> None:
    scenario_cache.configure_scenario_cache_persistence(None)
    scenario_cache.clear_scenario_cache()
    evidence = _FakeEvidence()
    state = _FakeState("changed-state-a")
    started = Event()
    release = Event()
    count_lock = Lock()
    calls = 0

    def loader(current_state, _evidence):
        nonlocal calls
        with count_lock:
            calls += 1
        started.set()
        assert release.wait(2)
        return _fake_result(current_state.state_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(
            scenario_cache.run_cached_scenario_simulation,
            state,
            evidence,
            simulation_loader=loader,
        )
        assert started.wait(1)
        follower = pool.submit(
            scenario_cache.run_cached_scenario_simulation,
            state,
            evidence,
            simulation_loader=loader,
        )
        time.sleep(0.05)
        release.set()
        first = leader.result(timeout=2)
        second = follower.result(timeout=2)

    assert calls == 1
    assert first[0] is second[0]
    assert sorted((first[1], second[1])) == [False, True]
    status = scenario_cache.scenario_cache_status()
    assert status["coalesced_hits"] == 1
    assert status["inflight"] == 0

    near_repeat = _FakeState("changed-state-b")
    third, cache_hit = scenario_cache.run_cached_scenario_simulation(
        near_repeat,
        evidence,
        simulation_loader=loader,
    )
    assert third.league_view.context.league_state_id == "changed-state-b"
    assert cache_hit is False
    assert calls == 2
    scenario_cache.clear_scenario_cache()
