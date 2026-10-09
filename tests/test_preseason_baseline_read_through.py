"""Tranche 1 exact-authority immutable preseason baseline reuse.

A deterministic 11-read journey without network/production data. Replaying
the same authorized Forecast authority through real scoring/decoder logic must
be byte-for-byte identical, with <=1 full persistence payload read.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from dataclasses import replace
from datetime import timedelta
from statistics import median
from time import monotonic, perf_counter
import tracemalloc

from fsffl.persistence.contracts import ReusableArtifactMetadataRecord
from fsffl.persistence.runtime_cache import preseason_forecast_baseline_artifact
from fsffl.product.forecast_resilience import (
    _PreseasonBaselineReadThrough,
    make_preseason_baseline_authority_loader,
    make_resilient_forecast_loader,
)
from fsffl.forecast.preseason_baseline import baseline_from_runtime
# Keep existing governed test fixtures local to the test directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_preseason_forecast_baseline import _raw_qb_runtime, _runtime, _state, _evidence


class TracedPersistence:
    def __init__(self, record, *, payload_bytes=970_848):
        self.record = record
        self.full_reads = 0
        self.metadata_reads = 0
        self.serialized_bytes = 0
        self.payload_bytes = payload_bytes

    def get_latest_reusable_artifact_metadata(self, **kwargs):
        self.metadata_reads += 1
        current = self.record
        if current is None or not current.reusable:
            return None
        assert current.key.artifact_kind == kwargs["artifact_kind"]
        assert current.key.scope_id == kwargs["scope_id"]
        assert current.key.scope_kind == kwargs["scope_kind"]
        assert current.key.model_version == kwargs["model_version"]
        return ReusableArtifactMetadataRecord(
            key=current.key, computed_at=current.computed_at,
            invalidated_at=current.invalidated_at,
            invalidation_reason=current.invalidation_reason,
        )

    def get_reusable_artifact(self, key):
        self.full_reads += 1
        if self.record is None or self.record.key != key:
            return None
        self.serialized_bytes += self.payload_bytes
        return self.record

    def get_latest_reusable_artifact(self, **kwargs):
        self.full_reads += 1
        self.serialized_bytes += self.payload_bytes
        return self.record


def _contract(evidence):
    """Compare governed scored output, authority and complete runtime values."""
    return (
        evidence.evidence_basis, evidence.raw_forecasts,
        evidence.league_scored_forecasts, evidence.successful_source_ids,
        evidence.failed_sources, evidence.uncertainty_ready,
        evidence.runtime_result.model_dump(mode="json"),
    )


def _store():
    state = _state(scored=True)
    baseline = baseline_from_runtime(state, _raw_qb_runtime(), source_artifact_id="capture-1")
    artifact = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026", baseline=baseline)
    return state, TracedPersistence(artifact)


def test_eleven_real_forecast_replays_use_one_full_payload_and_preserve_outputs(monkeypatch):
    import fsffl.product.forecast_resilience as module
    cache = _PreseasonBaselineReadThrough()
    monkeypatch.setattr(module, "_preseason_baseline_read_through", cache)
    state, store = _store()
    # Original legacy semantics: eleven independent full artifact reads.
    legacy = make_preseason_baseline_authority_loader(
        type("Legacy", (), {"get_latest_reusable_artifact":
             lambda self, **kw: store.record})()
    )
    expected = _contract(legacy(state))
    loader = make_preseason_baseline_authority_loader(store)
    actual = [_contract(loader(state)) for _ in range(11)]
    assert all(x == expected for x in actual)
    assert store.full_reads == 1
    assert store.metadata_reads == 11
    assert store.serialized_bytes == 970_848
    # Original 11 x 970,848 byte log size. This is not billed wire egress.
    assert 11 * store.payload_bytes - store.serialized_bytes == 9_708_480


def test_mixed_authority_and_resilient_callers_share_only_frozen_baseline(monkeypatch):
    import fsffl.product.forecast_resilience as module
    monkeypatch.setattr(module,"_preseason_baseline_read_through", _PreseasonBaselineReadThrough())
    state, store = _store()
    first = make_preseason_baseline_authority_loader(store)
    second = make_resilient_forecast_loader(
        store, live_loader=lambda s: _evidence(_runtime()))
    for _ in range(6):
        assert first(state).evidence_basis == "preseason_baseline"
    for _ in range(5):
        assert second(state).evidence_basis == "live_full_season"
    assert (store.full_reads,store.metadata_reads) == (1,11)


def test_new_exact_fingerprint_replaces_cached_artifact(monkeypatch):
    import fsffl.product.forecast_resilience as module
    monkeypatch.setattr(module,"_preseason_baseline_read_through", _PreseasonBaselineReadThrough())
    state, store = _store()
    load = make_preseason_baseline_authority_loader(store)
    original = load(state)
    original_record = store.record
    different = baseline_from_runtime(state,_raw_qb_runtime(),source_artifact_id="capture-2")
    rec = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",baseline=different)
    # Changing source_artifact_id alone is not the accepted content fingerprint,
    # so explicitly simulate a new immutable record identity.
    store.record = replace(
        rec,
        key=replace(rec.key, input_fingerprint="different-accepted-artifact-fingerprint"),
        computed_at=original_record.computed_at+timedelta(seconds=1),
    )
    next_evidence = load(state)
    assert store.full_reads == 2
    assert next_evidence.raw_forecasts == original.raw_forecasts
    assert store.record.key.input_fingerprint != original_record.key.input_fingerprint


def test_same_fingerprint_new_computation_timestamp_invalidates(monkeypatch):
    import fsffl.product.forecast_resilience as module
    monkeypatch.setattr(module,"_preseason_baseline_read_through", _PreseasonBaselineReadThrough())
    state, store = _store()
    load = make_preseason_baseline_authority_loader(store)
    before = _contract(load(state))
    store.record = replace(store.record,computed_at=store.record.computed_at+timedelta(seconds=1))
    after = _contract(load(state))
    assert before == after and store.full_reads == 2


def test_short_ttl_enforced_without_background_timer(monkeypatch):
    import fsffl.product.forecast_resilience as module
    t = [1000.0]
    monkeypatch.setattr(module,"monotonic",lambda: t[0])
    monkeypatch.setattr(module,"_preseason_baseline_read_through",
                        _PreseasonBaselineReadThrough(max_entries=2,ttl_seconds=150))
    state, store = _store()
    load = make_preseason_baseline_authority_loader(store)
    load(state)
    t[0] += 100
    load(state)
    assert store.full_reads == 1
    t[0] += 151
    load(state)
    assert store.full_reads == 2
    assert len(module._preseason_baseline_read_through._entries) <= 2


def test_store_and_state_isolation_and_missing_metadata_fallthrough(monkeypatch):
    import fsffl.product.forecast_resilience as module
    monkeypatch.setattr(module,"_preseason_baseline_read_through",_PreseasonBaselineReadThrough())
    state, first = _store()
    _, second = _store()
    load_first = make_preseason_baseline_authority_loader(first)
    load_second = make_preseason_baseline_authority_loader(second)
    load_first(state)
    load_second(state)
    assert (first.full_reads,second.full_reads) == (1,1)
    # New State reevaluates rules/lineup: never reuse a previously scored output.
    state2 = state.model_copy(update={"as_of":state.as_of+timedelta(hours=1)})
    assert load_first(state2).runtime_result is not None
    assert first.full_reads == 2
    first.record = None
    # Missing preserved evidence must use existing annual fallback (or fail closed).
    import pytest
    with pytest.raises(ValueError,match="annual preseason"):
        load_first(state)
    # The missing-baseline path still performs its original annual lookup.
    assert first.full_reads == 3


def test_concurrent_same_exact_artifact_single_cold_fetch(monkeypatch):
    import fsffl.product.forecast_resilience as module
    monkeypatch.setattr(module,"_preseason_baseline_read_through",_PreseasonBaselineReadThrough())
    state, store = _store()
    load = make_preseason_baseline_authority_loader(store)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _:_contract(load(state)),range(11)))
    assert all(x==results[0] for x in results)
    assert store.full_reads == 1


def test_read_through_scoped_resource_fixture_metrics(monkeypatch):
    import fsffl.product.forecast_resilience as module
    import pytest
    monkeypatch.setattr(module,"_preseason_baseline_read_through",_PreseasonBaselineReadThrough())
    state, store = _store()
    traced = make_preseason_baseline_authority_loader(store)
    tracemalloc.start()
    t0=perf_counter()
    try:
        durations=[]
        for _ in range(11):
            tick=perf_counter()
            traced(state)
            durations.append((perf_counter()-tick)*1000)
        total=(perf_counter()-t0)*1000
        _,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert store.full_reads==1
    assert peak < 15*1024*1024
    p95=sorted(durations)[10]  # 11 samples, nearest-rank 95th percentile
    print(
        f"TRANCHE1_SYNTHETIC_FIXTURE: actual_wall_ms={total:.3f} "
        f"p95_ms={p95:.3f} trace_peak_bytes={peak} "
        f"full_sql_reads={store.full_reads} metadata_reads={store.metadata_reads} "
        f"logged_json_bytes={store.serialized_bytes}; NOT hosted timing/egress"
    )
