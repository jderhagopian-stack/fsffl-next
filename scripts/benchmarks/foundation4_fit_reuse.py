"""Synthetic exact-fit cold/hit cost, not a hosted refresh benchmark."""
import json
from time import perf_counter

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from fsffl.product.foundation4_fit_reuse import ExactTrainingFitCache


def main():
    rng = np.random.default_rng(405)
    x = rng.normal(size=(5000, 32))
    y = np.maximum(0, 80 + x[:, 0] * 40 + rng.normal(size=5000) * 10)
    evaluation = rng.normal(size=(40, 32))
    params = dict(loss='squared_error', learning_rate=.05, max_iter=100,
                  max_leaf_nodes=15, min_samples_leaf=20,
                  l2_regularization=10.0, random_state=20260926)
    cache = ExactTrainingFitCache()
    try:
        with threadpool_limits(limits=1):
            start = perf_counter()
            first = cache.fit(HistGradientBoostingRegressor(**params), x, y, scope='synthetic-v1')
            cold = perf_counter() - start
            expected = first.predict(evaluation)
            del first
            start = perf_counter()
            second = cache.fit(HistGradientBoostingRegressor(**params), x, y, scope='synthetic-v1')
            hit = perf_counter() - start
            np.testing.assert_array_equal(second.predict(evaluation), expected)
        print(json.dumps(dict(kind='synthetic 5000x32, not hosted', cold_seconds=cold,
                              hit_seconds=hit, cached_bytes=cache._bytes,
                              entries=len(cache._entries), exact_prediction_parity=True)))
    finally:
        cache.close()


if __name__ == '__main__':
    main()
