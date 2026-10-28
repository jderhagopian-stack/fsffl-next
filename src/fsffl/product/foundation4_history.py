"""Exact accepted horizon rows without duplicating every historical feature."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


class _Locator:
    def __init__(self, frame, *, materialize):
        self.frame, self.materialize = frame, materialize

    def __getitem__(self, key):
        rows, columns = key
        positions = self.frame.positions
        if not isinstance(rows, slice):
            positions = positions[np.asarray(rows, dtype=bool)]
        view = _TrainingView(self.frame.panel, positions, tuple(columns))
        return view.materialize() if self.materialize else view


class _ILocator:
    def __init__(self, frame):
        self.frame = frame

    def __getitem__(self, rows):
        return _TrainingView(self.frame.panel, self.frame.positions[rows], self.frame.columns)


class _TrainingView:
    def __init__(self, panel, positions, columns):
        self.panel, self.positions = panel, positions
        self.columns = pd.Index(columns)

    def __len__(self):
        return len(self.positions)

    def __contains__(self, name):
        return name in self.columns

    def __getattr__(self, name):
        if name in self.columns:
            return self.panel.column(name, self.positions)
        raise AttributeError(name)

    @property
    def loc(self):
        # The accepted matrix sees ordinary DataFrames of only its requested
        # columns; accepted fit/state-label code sees lazy training rows.
        return _Locator(self, materialize=True)

    @property
    def iloc(self):
        return _ILocator(self)

    def materialize(self):
        return pd.DataFrame({name: self.panel.column(name, self.positions) for name in self.columns})


class BoundedHorizonHistory:
    """Keep accepted row coordinates in RAM, unexpanded feature columns on disk.

    Files are private, temporary Series pickles written here and read only by
    this object. Native pandas dtypes/categories and float64 bits round-trip;
    no CSV inference, missing-token substitution or feature redefinition occurs.
    """

    def __init__(self, dev, base, raw, directory: Path, *, columns=None):
        staged = self.stage_base(base, directory)
        self._expand_staged(dev, staged, raw, columns=columns)

    @staticmethod
    def stage_base(base, directory: Path):
        """Stage feature columns before expanding the much taller horizon panel.

        The caller can drop its wide base DataFrame after this returns and before
        ``from_staged`` allocates horizon metadata. This avoids holding both the
        wide base and its expanded row metadata at the same time.
        """
        directory.mkdir(parents=True, exist_ok=True)
        keys = base.loc[:, ['player_id', 'base_season', 'position']].copy()
        keys['_career_base_row'] = np.arange(len(base))
        paths = {}
        base_columns = tuple(base.columns)
        for number, name in enumerate(base_columns):
            path = directory / f'{number}.pkl'
            base[name].to_pickle(path)
            paths[name] = path
        return keys, paths, base_columns

    @classmethod
    def from_staged(cls, dev, staged, raw, *, columns=None):
        """Expand staged feature sources after the caller releases the base."""
        instance = cls.__new__(cls)
        instance._expand_staged(dev, staged, raw, columns=columns)
        return instance

    def _expand_staged(self, dev, staged, raw, *, columns=None):
        keys, paths, base_columns = staged
        # The accepted implementation still owns horizon order, eligibility,
        # target seasons, actual lookup and absent-actual semantics.
        metadata = dev.build_long(keys, raw)
        self.source_rows = metadata.pop('_career_base_row').to_numpy(dtype=int)
        self.paths = paths
        metadata_columns = [name for name in metadata.columns if name not in base_columns]
        self.columns = pd.Index(list(base_columns) + metadata_columns)
        if columns is not None:
            self.columns = self.columns[self.columns.isin(columns)]
        retained_metadata = [name for name in metadata.columns if name in self.columns]
        metadata.drop(columns=[name for name in metadata.columns if name not in retained_metadata], inplace=True)
        self.metadata = metadata
        self.panel = self
        self.positions = np.arange(len(self.source_rows))

    def __len__(self):
        return len(self.positions)

    def __contains__(self, name):
        return name in self.columns

    def __getattr__(self, name):
        if name in self.columns:
            return self.column(name, self.positions)
        raise AttributeError(name)

    @property
    def loc(self):
        return _Locator(self, materialize=False)

    def column(self, name, positions):
        if name in self.metadata:
            result = self.metadata[name].iloc[positions].copy()
        else:
            source = pd.read_pickle(self.paths[name])
            result = source.iloc[self.source_rows[positions]].copy()
        result.index = pd.Index(positions)
        return result
