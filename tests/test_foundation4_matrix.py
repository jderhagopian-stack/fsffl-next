from pathlib import Path
import runpy
import numpy as np
import pandas as pd
import pytest

from fsffl.product.foundation4_matrix import bounded_feature_matrix, bounded_candidate_fit
from types import SimpleNamespace


@pytest.mark.parametrize('architecture', ['specialist', 'shared_horizon', 'position_continuous', 'global_continuous'])
def test_bounded_matrix_matches_accepted_frozen_transform(architecture):
    oracle = runpy.run_path(str(Path(__file__).parent/'fixtures/career_coverage/frozen_foundation4_matrix.py'))
    rng = np.random.default_rng(405)
    train = pd.DataFrame({'position': ['QB','RB','WR','TE']*50,
        'value': rng.normal(size=200), 'constant': np.ones(200),
        'horizon': [4,5,6,7]*50, 'horizon_sq': [16,25,36,49]*50,
        'trajectory_state': ['stable', None, 'change', 'stable']*50})
    train.loc[3:17, 'value'] = np.nan
    train.loc[199, 'value'] = 10000
    evaluation = train.iloc[:9].copy()
    features = ('value','absent_numeric','constant','trajectory_state')
    expected = oracle['matrix'](train, evaluation, features, architecture)
    actual = bounded_feature_matrix(oracle['matrix'], oracle['CATEGORICAL'], train, evaluation, features, architecture)
    assert actual[2] == expected[2]
    np.testing.assert_allclose(actual[0], expected[0], rtol=0, atol=1e-14)
    np.testing.assert_allclose(actual[1], expected[1], rtol=0, atol=1e-14)


@pytest.mark.parametrize('architecture', ['specialist', 'shared_horizon', 'position_continuous', 'global_continuous'])
def test_training_projection_preserves_accepted_rows_and_dtypes(architecture):
    train = pd.DataFrame({'position': ['QB', 'RB', 'WR', 'TE'] * 8,
        'horizon': [4, 5, 6, 7] * 8, 'target_season': list(range(2000, 2032)),
        'horizon_sq': [16, 25, 36, 49] * 8, 'actual': np.arange(32.),
        'value': np.arange(32.) / 3, 'unrelated': ['wide unused column'] * 32})
    train['position'] = train.position.astype('category')
    train.loc[9, 'value'] = np.nan
    # Verbatim accepted route predicates (be2541a496227b33c12c755f576843dc4ab5a0bb).
    def accepted_fit(dev, long, candidate, T, h, pos, ev):
        arch, fs, model = candidate.split('|')
        if arch == 'specialist':
            tr = long[(long.horizon == h) & (long.position == pos) & (long.target_season < T)]
        elif arch == 'global_continuous':
            tr = long[long.target_season < T]
        elif arch == 'position_continuous':
            tr = long[(long.position == pos) & (long.target_season < T)]
        elif arch == 'shared_horizon':
            tr = long[(long.horizon == h) & (long.target_season < T)]
        else:
            raise KeyError(candidate)
        return dev.fit_predict(tr, ev, fs, model, arch), len(tr)
    dev = SimpleNamespace(FEATURE_SETS={'test': ('value',)},
        fit_predict=lambda tr, *args: tr)
    candidate = architecture + '|test|ridge_direct'
    expected, count = accepted_fit(dev, train, candidate, 2026, 4, 'QB', train.iloc[:2])
    actual, actual_count = bounded_candidate_fit(accepted_fit, dev, train, candidate, 2026, 4, 'QB', train.iloc[:2])
    assert actual_count == count
    assert 'unrelated' not in actual
    pd.testing.assert_frame_equal(actual, expected[actual.columns])
