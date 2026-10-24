import gc
import runpy
import weakref
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

from fsffl.product.foundation4_history import BoundedHorizonHistory
from fsffl.product.foundation4_matrix import bounded_feature_matrix


# Accepted build_long from be2541a496227b33c12c755f576843dc4ab5a0bb.
def accepted_long(base, raw):
    actual = {(str(r.player_id), int(r.season)): float(r.fantasy_target) for r in raw.itertuples()}
    rows = []
    for h in (4, 5, 6, 7, 8):
        z = base.copy()
        z['horizon'] = h
        z['target_season'] = z['base_season'] + h - 1
        z = z[z.target_season <= int(raw.season.max())].copy()
        z['actual'] = [actual.get((str(pid), int(ts)), 0.0) for pid, ts in zip(z.player_id, z.target_season)]
        z['active'] = (z.actual > 0).astype(int)
        z['horizon_sq'] = float(h*h)
        rows.append(z)
    long = pd.concat(rows, ignore_index=True)
    long['row_id'] = long['base_season'].astype(str) + '|' + long['player_id'] + '|H' + long['horizon'].astype(str)
    return long


@pytest.mark.parametrize('architecture', ['specialist', 'shared_horizon', 'position_continuous', 'global_continuous'])
def test_lazy_horizon_history_preserves_rows_dtypes_missing_values_and_matrix(tmp_path, architecture):
    base = pd.DataFrame({'player_id': ['p'+str(i) for i in range(160)],
        'base_season': pd.array([2015,2018,2021,2023]*40, dtype='Int64'),
        'position': pd.Categorical(['QB','RB','WR','TE']*40),
        'value': np.linspace(0,100,160),
        'trajectory_state': pd.Categorical(['NA',None,'MISSING','stable']*40)})
    base.loc[8:17, 'value'] = np.nan
    raw = pd.DataFrame({'player_id': ['p1','p5','p9'], 'season': [2023,2024,2025], 'fantasy_target': [70.,0.,40.]})
    expected = accepted_long(base,raw)
    original_base = base.copy()
    panel = BoundedHorizonHistory(SimpleNamespace(build_long=accepted_long),base,raw,tmp_path)
    # Caller releases base. Mutating it afterward must not change staged inputs.
    base.loc[:, 'value'] = -999
    actual = panel.loc[:, expected.columns].materialize()
    pd.testing.assert_frame_equal(actual, expected)
    predicate = (panel.target_season < 2025) & (panel.position != 'TE')
    training = panel.loc[predicate, expected.columns]
    selected = expected.loc[predicate]
    pd.testing.assert_frame_equal(training.iloc[[1,0,1]].materialize(), selected.iloc[[1,0,1]])
    oracle = runpy.run_path(str(Path(__file__).parent/'fixtures/career_coverage/frozen_foundation4_matrix.py'))
    features = ('value','absent_numeric','trajectory_state')
    evaluation = expected.iloc[:9].copy()
    wanted = oracle['matrix'](selected,evaluation,features,architecture)
    result = bounded_feature_matrix(oracle['matrix'],oracle['CATEGORICAL'],training,evaluation,features,architecture)
    assert result[2] == wanted[2]
    np.testing.assert_array_equal(result[0], wanted[0])
    np.testing.assert_array_equal(result[1], wanted[1])

    # Preserve the runtime's pre-existing column projection, including its
    # absent horizon_sq, rather than silently adding a generated predictor.
    columns = {'position','horizon','target_season','actual','value','trajectory_state'}
    projected=BoundedHorizonHistory(SimpleNamespace(build_long=accepted_long),original_base,raw,tmp_path/'projected',columns=columns)
    assert 'horizon_sq' not in projected
    wanted=bounded_feature_matrix(oracle['matrix'],oracle['CATEGORICAL'],expected.loc[predicate,expected.columns.intersection(list(columns))],evaluation,features,architecture)
    result=bounded_feature_matrix(oracle['matrix'],oracle['CATEGORICAL'],projected.loc[predicate,projected.columns],evaluation,features,architecture)
    np.testing.assert_array_equal(result[0],wanted[0]);np.testing.assert_array_equal(result[1],wanted[1])


def test_staged_history_expands_after_wide_base_is_released(tmp_path):
    base = pd.DataFrame({
        'player_id': ['p1', 'p2'],
        'base_season': pd.array([2023, 2024], dtype='Int64'),
        'position': pd.Categorical(['QB', 'RB']),
        'feature': [1.25, 2.5],
    })
    raw = pd.DataFrame({
        'player_id': ['p1', 'p2'],
        'season': [2025, 2025],
        'fantasy_target': [100.0, 80.0],
    })
    expected = accepted_long(base, raw)
    base_ref = weakref.ref(base)
    staged = BoundedHorizonHistory.stage_base(base, tmp_path)
    del base
    gc.collect()

    class Dev:
        def build_long(self, keys, history):
            assert base_ref() is None
            return accepted_long(keys, history)

    panel = BoundedHorizonHistory.from_staged(
        Dev(), staged, raw,
        columns={'player_id', 'base_season', 'position', 'feature', 'horizon', 'target_season', 'actual'},
    )
    projected = expected.loc[:, panel.columns]
    pd.testing.assert_frame_equal(panel.loc[:, panel.columns].materialize(), projected)
