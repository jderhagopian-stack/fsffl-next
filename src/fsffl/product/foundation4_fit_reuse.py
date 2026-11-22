"""Bounded reuse of exact accepted training fits, never player predictions.

Only process-created models in a private temporary directory may be restored.
The process index owns their digests; no external pickle/path is accepted.
"""
from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
import logging
from pathlib import Path
import pickle
import sys
import tempfile
from threading import RLock
from time import perf_counter

import numpy as np
import sklearn

from .resource_coordinator import reclaim_before_heavy_allocation

_logger = logging.getLogger("uvicorn.error")
_CLASSES = (
    "Ridge", "LogisticRegression", "HistGradientBoostingRegressor",
    "HistGradientBoostingClassifier", "ExtraTreesRegressor",
)


class _BudgetExceeded(Exception):
    pass


class _Writer:
    def __init__(self, handle, limit):
        self.handle, self.limit = handle, limit
        self.size = 0
        self.digest = hashlib.sha256()

    def write(self, value):
        if self.size + len(value) > self.limit:
            raise _BudgetExceeded()
        count = self.handle.write(value)
        self.digest.update(value)
        self.size += count
        return count


class _FitHandle:
    __slots__ = ("estimator", "cache", "scope")

    def __init__(self, estimator, cache, scope):
        self.estimator, self.cache, self.scope = estimator, cache, scope

    def fit(self, *args, **kwargs):
        if len(args) != 2 or kwargs:
            return self.estimator.fit(*args, **kwargs)
        return self.cache.fit(self.estimator, *args, scope=self.scope)


class ExactTrainingFitCache:
    """One bounded, process-private disk cache; no fitted models held in RAM."""

    def __init__(self, *, max_entries=64, max_bytes=32 * 1024 * 1024):
        if max_entries < 1 or max_bytes < 1:
            raise ValueError("fit cache bounds must be positive")
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._directory = tempfile.TemporaryDirectory(prefix="fsffl-exact-fits-")
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = RLock()

    def _key(self, estimator, x, y, scope):
        if type(estimator).__name__ not in _CLASSES or not type(estimator).__module__.startswith("sklearn."):
            return None
        params = estimator.get_params(deep=False)
        # All accepted stochastic learners have an explicit integer seed.
        if type(estimator).__name__ != "Ridge" and not isinstance(params.get("random_state"), int):
            return None
        # Accepted Ridge uses its deterministic default solver.
        if type(estimator).__name__ == "Ridge" and params.get("solver") not in ("auto", "svd", "cholesky", "lsqr"):
            return None
        digest = hashlib.sha256(json.dumps({
            "format": "exact-training-fit-v1", "scope": scope,
            "class": type(estimator).__module__ + "." + type(estimator).__qualname__,
            "params": params, "numpy": np.__version__, "sklearn": sklearn.__version__,
            "python": list(sys.version_info[:2]),
        }, sort_keys=True, allow_nan=False).encode())
        for array in (x, y):
            if (not isinstance(array, np.ndarray) or array.dtype.kind not in "biuf"
                    or not array.flags.c_contiguous):
                return None  # No copying/casting a training matrix just for reuse.
            digest.update(json.dumps([array.dtype.str, array.shape]).encode())
            digest.update(memoryview(array).cast("B"))
        return digest.hexdigest()

    def _remove(self, key):
        entry = self._entries.get(key)
        if entry is not None:
            path, _digest, size = entry
            path.unlink(missing_ok=True)
            self._entries.pop(key)
            self._bytes -= size

    def fit(self, estimator, x, y, *, scope):
        started = perf_counter()
        try:
            key = self._key(estimator, x, y, scope)
        except Exception:
            key = None
        if key is None:
            return estimator.fit(x, y)
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                path, expected_digest, _size = entry
                restored = None
                try:
                    with path.open("rb") as handle:
                        digest = hashlib.sha256()
                        for block in iter(lambda: handle.read(65536), b""):
                            digest.update(block)
                        if digest.hexdigest() != expected_digest:
                            raise ValueError("fit cache digest mismatch")
                        handle.seek(0)
                        restored = pickle.load(handle)
                    if type(restored) is not type(estimator) or restored.get_params(deep=False) != estimator.get_params(deep=False):
                        raise ValueError("fit cache estimator mismatch")
                    self._entries.move_to_end(key)
                    _logger.info("FSFFL Foundation4 exact fit reuse=hit model=%s elapsed=%.3fs",
                                 type(estimator).__name__, perf_counter() - started)
                    return restored
                except Exception:
                    restored = None  # Release rejected model before a native refit.
                    try:
                        self._remove(key)
                    except OSError:
                        return estimator.fit(x, y)
            # Model fitting errors remain real errors, never cache misses.
            fitted = estimator.fit(x, y)
            temporary = None
            try:
                reclaim_before_heavy_allocation(label="foundation4-before-fit-cache-write")
                with tempfile.NamedTemporaryFile(dir=self._directory.name, delete=False) as handle:
                    temporary = Path(handle.name)
                    writer = _Writer(handle, self.max_bytes)
                    pickle.dump(fitted, writer, protocol=pickle.HIGHEST_PROTOCOL)
                while self._entries and (
                    len(self._entries) >= self.max_entries or self._bytes + writer.size > self.max_bytes
                ):
                    self._remove(next(iter(self._entries)))
                path = Path(self._directory.name) / (key + ".pickle")
                temporary.replace(path)
                temporary = None
                self._entries[key] = (path, writer.digest.hexdigest(), writer.size)
                self._bytes += writer.size
            except Exception as exc:
                _logger.info("FSFFL Foundation4 exact fit save=skipped type=%s", type(exc).__name__)
            finally:
                if temporary is not None:
                    try:
                        temporary.unlink(missing_ok=True)
                    except OSError:
                        pass
            _logger.info("FSFFL Foundation4 exact fit reuse=miss model=%s elapsed=%.3fs",
                         type(estimator).__name__, perf_counter() - started)
            return fitted

    def close(self):
        with self._lock:
            self._entries.clear()
            self._bytes = 0
            self._directory.cleanup()


_shared_cache = None
_shared_lock = RLock()


def install_exact_training_fit_reuse(dev, *, scope):
    """Wrap only this loaded accepted module's constructors, not sklearn globals."""
    global _shared_cache
    with _shared_lock:
        if _shared_cache is None:
            try:
                _shared_cache = ExactTrainingFitCache()
            except OSError:
                _logger.info("FSFFL Foundation4 exact fit cache unavailable")
                return
        cache = _shared_cache
    for name in _CLASSES:
        original = getattr(dev, name, None)
        if original is None:
            continue
        def factory(*args, _original=original, **kwargs):
            return _FitHandle(_original(*args, **kwargs), cache, scope)
        setattr(dev, name, factory)
