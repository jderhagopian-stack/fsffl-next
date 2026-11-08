"""Fixed magnitude benchmarks for Intrinsic display; never economic authority.

PR #464's linear family. References are versioned units, not forecasts of an
absolute maximum. Percentiles and native signed raw contributions stay separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from math import isfinite

from fsffl.state.models import LeagueRules

INTRINSIC_MAGNITUDE_VERSION = "intrinsic-magnitude-v1:linear-fixed-20261108"


@dataclass(frozen=True)
class IntrinsicMagnitudeCoordinate:
    horizon: str
    anchor: float
    configuration_id: str

    @property
    def fingerprint(self) -> str:
        return sha256(json.dumps(
            [INTRINSIC_MAGNITUDE_VERSION, self.horizon, self.anchor, self.configuration_id],
            separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()

    def index(self, raw: float | None) -> float | None:
        if raw is None or not isfinite(raw):
            return None
        return 10_000.0 * max(0.0, min(1.0, raw / self.anchor))

    def overflow(self, raw: float | None) -> bool:
        return raw is not None and isfinite(raw) and raw > self.anchor

    def summary(self) -> dict[str, object]:
        return {
            "version": INTRINSIC_MAGNITUDE_VERSION,
            "input_fingerprint": self.fingerprint,
            "configuration_id": self.configuration_id,
            "horizon": self.horizon, "reference_raw": self.anchor,
            "formula": "10000 * clamp(raw / reference_raw, 0, 1)",
            "reference_policy": "fixed versioned benchmark; not an absolute maximum",
            "negative_policy": "display zero; preserve signed raw",
            "overflow_policy": "display 10000; expose raw and overflow flag",
            "percentiles": "separate descriptive ranks",
            "presentation_only": True, "market_inputs_used": False,
            "economic_gap_subtraction_allowed": False,
            "minimum_index": 0, "maximum_index": 10_000,
        }


@lru_cache(maxsize=32)
def intrinsic_magnitude_coordinate(
    rules: LeagueRules | None, horizon: str,
) -> IntrinsicMagnitudeCoordinate | None:
    if horizon not in {"three_year", "career"}:
        raise ValueError("unsupported Intrinsic display horizon")
    if rules is None:
        return None
    from fsffl.value.career_tail import (
        CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE, lineup_capacity_signature,
    )
    from .foundation4_shadow_inputs import foundation4_fsffl_scoring_is_compatible
    # Do not transplant reference magnitudes into unvalidated league economies.
    if (lineup_capacity_signature(rules) != CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE
            or not foundation4_fsffl_scoring_is_compatible(rules)):
        return None
    return IntrinsicMagnitudeCoordinate(
        horizon, 750.0 if horizon == "three_year" else 2200.0,
        "fsffl-half-ppr:" + CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE,
    )


def reproject_published_intrinsic(payload: dict, rules: LeagueRules) -> dict:
    """Versioned read projection of saved raw lenses; no historical writes/builds.

    Only lens surfaces carry both accepted raw horizon fields. Never derive raw
    values from an old index or reinterpret an unavailable row as a zero.
    """
    three = intrinsic_magnitude_coordinate(rules, "three_year")
    career = intrinsic_magnitude_coordinate(rules, "career")
    if (three is None or career is None or "players" not in payload
            or not any("three_year_raw_intrinsic_value" in row or "raw_career_forward_reference" in row
                       for row in payload["players"])):
        return payload
    rows = []
    for row in payload["players"]:
        updated = dict(row)
        for coordinate, raw_key, index_key, flag in (
            (three, "three_year_raw_intrinsic_value", "intrinsic_value_index", "intrinsic_index_overflow"),
            (career, "raw_career_forward_reference", "career_intrinsic_index", "career_index_overflow"),
        ):
            if raw_key in row:
                updated[index_key] = coordinate.index(row[raw_key])
                updated[flag] = coordinate.overflow(row[raw_key])
        if "three_year_raw_intrinsic_value" in row:
            updated["value_index_gap"] = None
        rows.append(updated)
    result = {**payload, "players": rows, "intrinsic_display": {
        "three_year": three.summary(), "career": career.summary(),
    }}
    if "fsffl_intrinsic" in result:
        result["fsffl_intrinsic"] = {
            **result["fsffl_intrinsic"], "display_coordinate": INTRINSIC_MAGNITUDE_VERSION,
            "presentation": three.summary(),
        }
    if "career_intrinsic" in result:
        result["career_intrinsic"] = {**result["career_intrinsic"], "presentation": career.summary()}
    return result
