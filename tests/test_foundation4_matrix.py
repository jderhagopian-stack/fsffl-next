from pathlib import Path
import runpy
import numpy as np
import pandas as pd
import pytest

from fsffl.product.foundation4_matrix import bounded_feature_matrix


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
