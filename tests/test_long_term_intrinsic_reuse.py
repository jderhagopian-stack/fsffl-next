"""Pure Value reuse cannot hide fresh inputs or create a competing authority."""
from dataclasses import replace

import pytest

from fsffl.product import long_term_intrinsic_reuse as reuse
from fsffl.persistence.contracts import utc_now
from tests.test_long_term_intrinsic_shadow import _contract, _rules


@pytest.fixture(autouse=True)
def isolated_memory_guard(monkeypatch):
    # Deterministic transport/identity tests must not inherit RSS from unrelated
    # full-suite fixtures. Guard refusal is exercised explicitly below.
    monkeypatch.setattr(reuse, 'reclaim_before_heavy_allocation', lambda **kwargs: None)


class Store:
    def __init__(self):
        self.rows = {}
        self.reads = self.writes = 0

    def get_reusable_artifact(self, key):
        self.reads += 1
        return self.rows.get(key)

    def put_artifact(self, record):
        self.writes += 1
        self.rows[record.key] = record


def traced_builder(monkeypatch):
    calls = []
    original = reuse.build_long_term_intrinsic_shadow
    def build(forecast, *, rules):
        calls.append(forecast)
        return original(forecast, rules=rules)
    monkeypatch.setattr(reuse, 'build_long_term_intrinsic_shadow', build)
    return calls


def test_restart_and_provenance_only_refresh_reuse_identical_numeric_result(monkeypatch):
    store = Store()
    calls = traced_builder(monkeypatch)
    original = reuse.LongTermIntrinsicReuse(store)(_contract(), rules=_rules())
    # A different producer instance has no process-local hint to trust.
    restored = reuse.LongTermIntrinsicReuse(store)(
        _contract(provenance_marker='new-capture', reverse=True), rules=_rules())
    assert restored == original
    assert len(calls) == 1
    assert (store.reads, store.writes, len(store.rows)) == (2, 1, 1)


@pytest.mark.parametrize('change', ['mean', 'uncertainty', 'cohort', 'rules', 'model'])
def test_consumed_input_changes_force_recalculation(monkeypatch, change):
    store = Store()
    calls = traced_builder(monkeypatch)
    resolver = reuse.LongTermIntrinsicReuse(store)
    forecast, rules = _contract(), _rules()
    original = resolver(forecast, rules=rules)
    if change == 'mean':
        forecast = _contract(boost_qb1_y4=20)
    elif change == 'uncertainty':
        rows = list(forecast.forecasts)
        rows[0] = rows[0].model_copy(update={'absolute_error_80': 15})
        forecast = forecast.model_copy(update={'forecasts': tuple(rows)})
    elif change == 'cohort':
        forecast = forecast.model_copy(update={
            'forecasts': tuple(r for r in forecast.forecasts if r.player_id != 'qb3')})
    elif change == 'rules':
        rules = rules.model_copy(update={'team_count': 3})
    else:
        forecast = forecast.model_copy(update={'forecast_model_version': 'new-model'})
    changed = resolver(forecast, rules=rules)
    assert len(calls) == 2
    assert changed.input_fingerprint != original.input_fingerprint
    assert changed == reuse.build_long_term_intrinsic_shadow(forecast, rules=rules)
    if change in ('mean', 'uncertainty', 'model'):
        assert len(store.rows) == 1, 'New numerical revisions must replace the slot'
    else:
        assert len(store.rows) == 2, 'Different rules/cohort must not share a slot'


@pytest.mark.parametrize('corruption', ['fingerprint', 'seed', 'cohort', 'shape', 'invalidated'])
def test_untrusted_or_incompatible_payload_is_rebuilt(monkeypatch, corruption):
    store = Store()
    resolver = reuse.LongTermIntrinsicReuse(store)
    original = resolver(_contract(), rules=_rules())
    key, record = next(iter(store.rows.items()))
    payload = dict(record.payload)
    if corruption == 'fingerprint':
        payload['input_fingerprint'] = 'wrong'
    elif corruption == 'seed':
        payload['base_seed'] += 1
    elif corruption == 'cohort':
        payload['estimates'] = payload['estimates'][:-1]
    elif corruption == 'shape':
        payload = {'broken': True}
    store.rows[key] = replace(record, payload=payload,
                             invalidated_at=utc_now() if corruption == 'invalidated' else None)
    calls = traced_builder(monkeypatch)
    assert resolver(_contract(), rules=_rules()) == original
    assert len(calls) == 1
    assert store.writes == 2


@pytest.mark.parametrize('operation', ['read', 'write'])
def test_cache_transport_failure_preserves_owned_calculation(monkeypatch, operation):
    store = Store()
    def broken(*args):
        raise RuntimeError('unavailable')
    setattr(store, 'get_reusable_artifact' if operation == 'read' else 'put_artifact', broken)
    expected = reuse.build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    calls = traced_builder(monkeypatch)
    assert reuse.LongTermIntrinsicReuse(store)(_contract(), rules=_rules()) == expected
    assert len(calls) == 1


def test_memory_guard_skips_optional_cache_write_without_losing_result(monkeypatch):
    store = Store()
    expected = reuse.build_long_term_intrinsic_shadow(_contract(), rules=_rules())
    def reject(**kwargs):
        assert kwargs['label'] == 'career-before-expanded-component-serialization'
        raise MemoryError('no serialization headroom')
    monkeypatch.setattr(reuse, 'reclaim_before_heavy_allocation', reject)
    assert reuse.LongTermIntrinsicReuse(store)(_contract(), rules=_rules()) == expected
    assert store.writes == 0
