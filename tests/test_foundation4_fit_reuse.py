from pathlib import Path
import gc
import importlib.util
from types import SimpleNamespace
import weakref

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits

from fsffl.product import foundation4_fit_reuse as reuse


def oracle():
    path = Path(__file__).parent / 'fixtures/career_coverage/frozen_foundation4_fit.py'
    spec = importlib.util.spec_from_file_location('fit_oracle', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def isolated_memory_guard(monkeypatch):
    # Identity/transport tests must not depend on unrelated suite fixture RSS.
    monkeypatch.setattr(reuse, 'reclaim_before_heavy_allocation', lambda **kwargs: None)


@pytest.fixture
def cache(monkeypatch):
    result = reuse.ExactTrainingFitCache()
    monkeypatch.setattr(reuse, '_shared_cache', result)
    yield result
    result.close()


def data():
    rng = np.random.default_rng(405)
    value = rng.normal(size=280)
    train = pd.DataFrame(dict(value=value, other=rng.normal(size=280),
        trajectory_state=['stable', 'changing'] * 140,
        position=['QB', 'RB', 'WR', 'TE'] * 70,
        actual=np.maximum(0, 80 * value + 60), horizon=[4, 5, 6, 7] * 70,
        horizon_sq=[16, 25, 36, 49] * 70))
    first = train.iloc[:13].copy()
    second = first.copy()
    second['value'] += 0.5
    return train, first, second


@pytest.mark.parametrize('model', [
    'ridge_direct', 'two_part_ridge', 'histgb_direct', 'two_part_histgb',
    'state_histgb', 'extra_trees', 'carry_y3',
])
def test_accepted_fit_predictions_remain_exact_for_fresh_evaluation(cache, monkeypatch, model):
    dev = oracle()
    train, first, second = data()
    for frame in (train, first, second):
        frame['y3'] = 90 + frame.value
    with threadpool_limits(limits=1):
        expected_first = dev.fit_predict(train, first, 'fixture', model, 'global_continuous')
        expected_second = dev.fit_predict(train, second, 'fixture', model, 'global_continuous')
        fits = []
        # Count actual native fits, including the two-part/state learners.
        for name in reuse._CLASSES:
            cls = getattr(dev, name)
            original = cls.fit
            def counted(self, *args, _fit=original, **kwargs):
                fits.append(type(self).__name__)
                return _fit(self, *args, **kwargs)
            monkeypatch.setattr(cls, 'fit', counted)
        reuse.install_exact_training_fit_reuse(dev, scope='accepted-test-oracle')
        actual_first = dev.fit_predict(train, first, 'fixture', model, 'global_continuous')
        cold_count = len(fits)
        actual_second = dev.fit_predict(train, second, 'fixture', model, 'global_continuous')
    for actual, expected in zip(actual_first + actual_second, expected_first + expected_second):
        if model == 'extra_trees':
            # Native parallel tree summation can itself differ by a few ULPs.
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)
        else:
            np.testing.assert_array_equal(actual, expected)
    assert len(fits) == cold_count
    assert cold_count > 0 if model != 'carry_y3' else cold_count == 0
    assert not np.array_equal(actual_first[0], actual_second[0])


@pytest.mark.parametrize('change', ['x', 'target', 'order', 'params', 'scope', 'dtype'])
def test_every_consumed_training_coordinate_invalidates_reuse(cache, monkeypatch, change):
    rng = np.random.default_rng(7)
    x = rng.normal(size=(100, 4))
    y = rng.normal(size=100)
    fits = []
    original = Ridge.fit
    def counted(self, *args, **kwargs):
        fits.append(1)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Ridge, 'fit', counted)
    cache.fit(Ridge(alpha=10), x, y, scope='a')
    alpha, scope = 10, 'a'
    if change == 'x':
        x = x.copy(); x[0, 0] += 0.01
    elif change == 'target':
        y = y.copy(); y[0] += 0.01
    elif change == 'order':
        x, y = x[::-1].copy(), y[::-1].copy()
    elif change == 'params':
        alpha = 11
    elif change == 'scope':
        scope = 'b'
    else:
        x = x.astype(np.float32)
    cache.fit(Ridge(alpha=alpha), x, y, scope=scope)
    assert len(fits) == 2


def test_private_cache_holds_no_model_and_never_loads_modified_file(cache, monkeypatch):
    x, y = np.ones((100, 2)), np.ones(100)
    fitted = cache.fit(Ridge(), x, y, scope='a')
    reference = weakref.ref(fitted)
    del fitted
    gc.collect()
    assert reference() is None
    path = next(iter(cache._entries.values()))[0]
    path.write_bytes(b'not a trusted process-created pickle')
    def forbidden(*args):
        pytest.fail('Digest mismatch must be rejected before unpickling')
    monkeypatch.setattr(reuse.pickle, 'load', forbidden)
    result = cache.fit(Ridge(), x, y, scope='a')
    np.testing.assert_array_equal(result.predict(x), np.ones(100))


def test_cache_bounds_and_oversized_model_do_not_change_fit_result(tmp_path):
    x, y = np.ones((100, 2)), np.ones(100)
    cache = reuse.ExactTrainingFitCache(max_entries=2, max_bytes=2048)
    try:
        for alpha in range(8):
            cache.fit(Ridge(alpha=alpha), x, y, scope='a')
        assert len(cache._entries) <= 2
        assert cache._bytes <= 2048
        assert len(list(Path(cache._directory.name).iterdir())) <= 2
    finally:
        cache.close()
    tiny = reuse.ExactTrainingFitCache(max_bytes=1)
    try:
        fitted = tiny.fit(Ridge(), x, y, scope='a')
        np.testing.assert_array_equal(fitted.predict(x), np.ones(100))
        assert tiny._bytes == 0
        assert list(Path(tiny._directory.name).iterdir()) == []
    finally:
        tiny.close()


def test_install_failure_preserves_original_constructors(monkeypatch):
    dev = SimpleNamespace(Ridge=Ridge)
    monkeypatch.setattr(reuse, '_shared_cache', None)
    def unavailable(**kwargs):
        raise OSError('no temporary directory')
    monkeypatch.setattr(reuse.tempfile, 'TemporaryDirectory', unavailable)
    reuse.install_exact_training_fit_reuse(dev, scope='a')
    assert dev.Ridge is Ridge


def test_cache_write_failure_returns_real_fit(cache, monkeypatch):
    x, y = np.ones((100, 2)), np.ones(100)
    def unavailable(**kwargs):
        raise OSError('unavailable')
    monkeypatch.setattr(reuse.tempfile, 'NamedTemporaryFile', unavailable)
    result = cache.fit(Ridge(), x, y, scope='a')
    np.testing.assert_array_equal(result.predict(x), np.ones(100))
    assert cache._bytes == 0


def test_concurrent_identical_requests_fit_once(cache, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    fits = []
    original = Ridge.fit
    def counted(self, *args, **kwargs):
        fits.append(1)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Ridge, 'fit', counted)
    x, y = np.ones((100, 2)), np.ones(100)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: cache.fit(Ridge(), x, y, scope='a'), range(2)))
    assert len(fits) == 1
    for result in results:
        np.testing.assert_array_equal(result.predict(x), np.ones(100))


def test_unseeded_or_unsupported_fits_take_the_native_path(cache, monkeypatch):
    from sklearn.ensemble import HistGradientBoostingRegressor
    fits = []
    original = HistGradientBoostingRegressor.fit
    def counted(self, *args, **kwargs):
        fits.append(1)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(HistGradientBoostingRegressor, 'fit', counted)
    x, y = np.ones((100, 2)), np.ones(100)
    with threadpool_limits(limits=1):
        for _ in range(2):
            cache.fit(HistGradientBoostingRegressor(max_iter=2), x, y, scope='a')
    assert len(fits) == 2
    assert not cache._entries


def test_memory_guard_refusal_skips_optional_serialization(cache, monkeypatch):
    def reject(**kwargs):
        assert kwargs['label'] == 'foundation4-before-fit-cache-write'
        raise MemoryError('no headroom')
    monkeypatch.setattr(reuse, 'reclaim_before_heavy_allocation', reject)
    x, y = np.ones((100, 2)), np.ones(100)
    result = cache.fit(Ridge(), x, y, scope='a')
    np.testing.assert_array_equal(result.predict(x), np.ones(100))
    assert not cache._entries


def test_constructor_adapter_releases_completed_model_without_gc(cache):
    dev = SimpleNamespace(Ridge=Ridge)
    reuse.install_exact_training_fit_reuse(dev, scope='a')
    x, y = np.ones((100, 2)), np.ones(100)
    result = dev.Ridge().fit(x, y)
    reference = weakref.ref(result)
    del result
    assert reference() is None
