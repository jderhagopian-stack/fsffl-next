from types import SimpleNamespace
from threading import Event, Lock
from concurrent.futures import ThreadPoolExecutor
import time

from fsffl.product.market_economics_cache import make_cached_candidate_economics


def _runtime(*, state_id="state-1", value=None):
    state = SimpleNamespace(state_id=state_id)
    return SimpleNamespace(
        league_state=state,
        selected_team_id="team-me",
        value_evidence=value if value is not None else SimpleNamespace(model_version="value-v1"),
    )


def _row(*, label="Target", gap=0.1):
    return {
        "counterparty_team_id": "team-them",
        "send": [{"asset_ref": "player:mine", "label": "Mine"}],
        "receive": [{"asset_ref": "player:theirs", "label": label}],
        "market_gap_ratio": gap,
    }


def test_exact_package_economics_reuse_preserves_current_search_metadata() -> None:
    calls = 0

    def evaluator(runtime, row, **kwargs):
        nonlocal calls
        calls += 1
        return {
            **row,
            "economics": {"proposal_id": "same"},
            "economic_net": {"proposal_id": "same"},
            "package_concentration": {"proposal_id": "same"},
            "package_economics": {"proposal_id": "same"},
            "cheap_economic_screen_complete": True,
            "cheap_economic_screen_authority": "decision",
            "preliminary_economic_band": "robust_or_ordinary",
        }

    cached = make_cached_candidate_economics(evaluator)
    runtime = _runtime()
    first = cached(runtime, _row(label="First", gap=0.10))
    second = cached(runtime, _row(label="Second", gap=0.02))

    assert calls == 1
    assert first["receive"][0]["label"] == "First"
    assert second["receive"][0]["label"] == "Second"
    assert second["market_gap_ratio"] == 0.02
    assert second["economic_net"] == first["economic_net"]


def test_package_economics_cache_invalidates_on_state_or_value_identity() -> None:
    calls = 0

    def evaluator(runtime, row, **kwargs):
        nonlocal calls
        calls += 1
        return {**row, "preliminary_economic_band": f"call-{calls}"}

    cached = make_cached_candidate_economics(evaluator)
    value_a = SimpleNamespace(model_version="value-v1")
    value_b = SimpleNamespace(model_version="value-v1")
    runtime_a = _runtime(value=value_a)
    runtime_b = _runtime(value=value_b)
    runtime_c = _runtime(state_id="state-2", value=value_a)

    assert cached(runtime_a, _row())["preliminary_economic_band"] == "call-1"
    assert cached(runtime_a, _row())["preliminary_economic_band"] == "call-1"
    assert cached(runtime_b, _row())["preliminary_economic_band"] == "call-2"
    assert cached(runtime_c, _row())["preliminary_economic_band"] == "call-3"
    assert calls == 3


def test_identical_concurrent_package_economics_are_single_flight() -> None:
    calls = 0
    count_lock = Lock()
    started = Event()
    release = Event()

    def evaluator(runtime, row, **kwargs):
        nonlocal calls
        with count_lock:
            calls += 1
        started.set()
        assert release.wait(2)
        return {**row, "preliminary_economic_band": "robust_or_ordinary"}

    cached = make_cached_candidate_economics(evaluator)
    runtime = _runtime()
    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(cached, runtime, _row(label="Leader"))
        assert started.wait(1)
        follower = pool.submit(cached, runtime, _row(label="Follower"))
        time.sleep(0.05)
        release.set()
        first = leader.result(timeout=2)
        second = follower.result(timeout=2)

    assert calls == 1
    assert first["receive"][0]["label"] == "Leader"
    assert second["receive"][0]["label"] == "Follower"
