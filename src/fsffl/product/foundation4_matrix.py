"""Bound transient matrix construction while calling the accepted transforms."""
from __future__ import annotations

import numpy as np


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
