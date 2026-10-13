"""Bind accepted Foundation 4 components to the active Current subject set."""
from __future__ import annotations

import json
from typing import Mapping

from fsffl.forecast.long_horizon_contract import LongHorizonForecastAuthorityContract


def align_foundation4_cohort(
    *, player_ids: set[str], long_forecast: LongHorizonForecastAuthorityContract,
    terminal_features: Mapping,
):
    """Keep the frozen baseline intact; explicitly scope the active calculation.

    Current owns the active reference-game IDs. All requested IDs must have both
    accepted later-horizon components. Extra frozen reference IDs are recorded
    as inactive instead of becoming fabricated Current/State observations.
    """
    long_ids = {row.player_id for row in long_forecast.forecasts}
    tail_ids = set(terminal_features)
    if not player_ids or not player_ids.issubset(long_ids & tail_ids):
        raise ValueError(
            "Foundation 4 active cohort lacks accepted component authority: "
            f"Y4-Y7={sorted(player_ids - long_ids)}; terminal={sorted(player_ids - tail_ids)}"
        )
    if long_ids != tail_ids:
        raise ValueError("Foundation 4 reference Y4-Y7 and terminal cohorts differ")
    excluded = long_ids - player_ids
    if not excluded:
        return long_forecast, dict(terminal_features)
    aligned = LongHorizonForecastAuthorityContract.model_validate({
        **long_forecast.model_dump(exclude={"forecasts", "provenance"}),
        "forecasts": tuple(row for row in long_forecast.forecasts if row.player_id in player_ids),
        "provenance": {**{key: value if value is None or isinstance(value, (str, bool, int, float))
            else json.dumps(value, sort_keys=True, separators=(",", ":"))
            for key, value in long_forecast.provenance.items()},
            "active_cohort_ids": json.dumps(sorted(player_ids), separators=(",", ":")),
            "inactive_reference_ids": json.dumps(sorted(excluded), separators=(",", ":")),
            "cohort_policy": "Current-owned-active-subjects-v1"},
    })
    return aligned, {key: terminal_features[key] for key in sorted(player_ids)}
