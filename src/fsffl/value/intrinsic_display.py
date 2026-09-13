from __future__ import annotations

from math import exp, isfinite
from typing import Iterable

from .intrinsic_v1 import IntrinsicValueV1Estimate
from .models import ValueScale


INTRINSIC_DYNASTY_DISPLAY_SCALE = ValueScale(
    scale_id="fsffl-intrinsic-dynasty-value",
    version="1",
    unit_label="FSFFL Intrinsic Value points (0-10,000)",
)

# Stable, market-independent anchors on the raw Intrinsic v1 surplus coordinate.
# They were selected against the frozen v1 current-player safety span: a valid
# zero-surplus backup, ~45-point fringe positive value, ~110-point meaningful
# value, ~180-point premium non-QB value observed in the live Value Lens, and
# ~300-point elite QB value. The tail remains strictly increasing and approaches
# 10,000 asymptotically rather than clipping elite players together.
_DISPLAY_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),
    (45.0, 3000.0),
    (110.0, 6000.0),
    (180.0, 8500.0),
    (300.0, 9700.0),
)
_TAIL_RAW_SCALE = 100.0
_TAIL_DISPLAY_ROOM = 300.0


def intrinsic_dynasty_display_value(raw_intrinsic: float) -> float:
    """Map raw v1 surplus to the stable customer-facing 0-10,000 axis.

    The transform is deterministic, strictly increasing for non-negative finite
    inputs, independent of Market/Team Utility, and league-population invariant.
    Raw Intrinsic remains authoritative internally; this is a presentation
    coordinate with its own explicit scale/version.
    """

    raw = float(raw_intrinsic)
    if not isfinite(raw) or raw < 0:
        raise ValueError("raw Intrinsic value must be finite and non-negative")

    for (left_raw, left_display), (right_raw, right_display) in zip(
        _DISPLAY_ANCHORS,
        _DISPLAY_ANCHORS[1:],
        strict=True,
    ):
        if raw <= right_raw:
            if right_raw == left_raw:
                return left_display
            fraction = (raw - left_raw) / (right_raw - left_raw)
            return left_display + fraction * (right_display - left_display)

    tail_start_raw, tail_start_display = _DISPLAY_ANCHORS[-1]
    return tail_start_display + _TAIL_DISPLAY_ROOM * (
        1.0 - exp(-(raw - tail_start_raw) / _TAIL_RAW_SCALE)
    )


def intrinsic_population_percentiles(
    estimates: Iterable[IntrinsicValueV1Estimate],
) -> dict[str, float]:
    """Return tie-safe population ranks while anchoring valid zero surplus at 0.

    A zero is a valid economic result, but assigning the midpoint of a large tied
    zero block (for example 34th percentile) is misleading product language. Zero
    therefore maps to 0th percentile; positive values retain their population rank
    among the complete available estimate population. Unavailable players never
    enter this function and therefore never receive a fake rank.
    """

    rows = sorted(
        ((estimate.player_id, float(estimate.value)) for estimate in estimates),
        key=lambda item: (item[1], item[0]),
    )
    count = len(rows)
    if not rows:
        return {}
    if count == 1:
        return {rows[0][0]: 0.0 if rows[0][1] == 0 else 0.5}

    result: dict[str, float] = {}
    index = 0
    while index < count:
        end = index + 1
        while end < count and rows[end][1] == rows[index][1]:
            end += 1
        value = rows[index][1]
        if value == 0:
            percentile = 0.0
        else:
            percentile = ((index + end - 1) / 2.0) / (count - 1)
        for offset in range(index, end):
            result[rows[offset][0]] = percentile
        index = end
    return result
