"""Bound transient matrix construction while calling the accepted transforms."""
from __future__ import annotations

import numpy as np


def bounded_candidate_fit(original, dev, long, candidate, origin, horizon, position, evaluation):
    """Let the accepted route select rows, copying only its model's columns.

    The route still owns every training-row predicate. Its Boolean selection
    is applied directly to the feature projection, avoiding the transient
    all-feature training table. No serialization or dtype conversion occurs.
    """
    architecture, feature_set, model = candidate.split("|")
    columns = {"position", "actual", "horizon", "horizon_sq"}
    columns.update(dev.FEATURE_SETS[feature_set])
    selected = [name for name in long.columns if name in columns]

    class TrainingProjection:
        def __getattr__(self, name):
            return getattr(long, name)

        def __getitem__(self, predicate):
            # Accepted fit_candidate selects its training frame exactly once
            # with a Boolean Series; reject any changed source contract.
            if getattr(predicate, "dtype", None) != bool:
                raise TypeError("accepted Foundation 4 training selection must be Boolean")
            return long.loc[predicate, selected]

    return original(dev, TrainingProjection(), candidate, origin, horizon, position, evaluation)


def bounded_feature_matrix(original, categorical, train, evaluation, features, architecture):
    """Apply the unchanged column-independent transform without wide temporaries.

    The original implementation supplies medians, clipping, normalization and
    categorical levels. Float64 precision and feature ordering stay unchanged.
    """
    names = list(features)
    if architecture in {"shared_horizon", "global_continuous"} and "position_cat" not in names:
        names.append("position_cat")
    if architecture in {"position_continuous", "global_continuous"}:
        for name in ("horizon", "horizon_sq"):
            if name not in names:
                names.append(name)
    cats = [name for name in names if name in categorical or name == "position_cat"]
    nums = [name for name in names if name not in cats]

    def scoped(frame, selected):
        return frame.loc[:, [name for name in dict.fromkeys(["position", *selected]) if name in frame]]

    cat_train, cat_eval, cat_names = original(scoped(train, cats), scoped(evaluation, cats), tuple(cats), "specialist")
    output_names = nums + cat_names
    train_matrix = np.empty((len(train), len(output_names)), dtype=float)
    eval_matrix = np.empty((len(evaluation), len(output_names)), dtype=float)
    train_matrix[:, len(nums):] = cat_train
    eval_matrix[:, len(nums):] = cat_eval
    del cat_train, cat_eval
    for index, name in enumerate(nums):
        column_train, column_eval, _ = original(scoped(train, [name]), scoped(evaluation, [name]), (name,), "specialist")
        train_matrix[:, index] = column_train[:, 0]
        eval_matrix[:, index] = column_eval[:, 0]
    return train_matrix, eval_matrix, output_names
