"""Presentation-only Career ruler; never an input to economic calculations."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from typing import Mapping

CAREER_PRESENTATION_VERSION = "career-index-v1:active-reference-empirical-midrank"


@dataclass(frozen=True)
class CareerPresentationCoordinate:
    """Exact publication's accepted reference game, independent of roster expansion.

    Equal raw values share their average rank. Distinct anchors interpolate
    linearly between their midranks. Values outside the reference range clamp
    to 0/10,000; a completely tied reference maps to its midpoint. A new
    reference/rules calculation creates a new fingerprint, never a hidden
    moving roster/query-based universe. Raw economic quantities stay unchanged.
    """

    reference: tuple[tuple[str, float], ...]

    def __post_init__(self):
        if len(self.reference) < 2:
            raise ValueError("Career display requires a complete reference game of at least two players")
        if len({key for key, _ in self.reference}) != len(self.reference):
            raise ValueError("Career display reference identities must be unique")
        if not all(isfinite(value) for _, value in self.reference):
            raise ValueError("Career display reference values must be finite")

    @classmethod
    def from_reference(cls, raw_values: Mapping[str, float], *, reference_ids: frozenset[str]):
        if not reference_ids.issubset(raw_values):
            raise ValueError("Career display reference is incomplete")
        return cls(tuple((key, float(raw_values[key])) for key in sorted(reference_ids)))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            [CAREER_PRESENTATION_VERSION, self.reference], separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()

    def index(self, raw: float | None) -> float | None:
        if raw is None or not isfinite(raw):
            return None
        values = sorted(value for _, value in self.reference)
        if raw < values[0]:
            return 0.0
        if raw > values[-1]:
            return 10_000.0
        left, right = bisect_left(values, raw), bisect_right(values, raw)
        denominator = len(values) - 1
        if left != right:
            return 10_000.0 * (left + right - 1) / (2 * denominator)
        low, high = values[left - 1], values[left]
        low_rank = (bisect_left(values, low) + bisect_right(values, low) - 1) / 2
        high_rank = (bisect_left(values, high) + bisect_right(values, high) - 1) / 2
        return 10_000.0 * (low_rank + (raw - low) / (high - low) * (high_rank - low_rank)) / denominator

    def summary(self) -> dict[str, object]:
        values = [value for _, value in self.reference]
        return {
            "version": CAREER_PRESENTATION_VERSION,
            "input_fingerprint": self.fingerprint,
            "reference_universe": "Current-owned active accepted Foundation 4 reference game",
            "reference_player_ids": [key for key, _ in self.reference],
            "reference_count": len(self.reference),
            "raw_minimum": min(values), "raw_maximum": max(values),
            "tie_policy": "average rank; linear interpolation between distinct raw anchors",
            "outside_reference_policy": "clamp to 0 or 10000",
            "presentation_only": True, "market_inputs_used": False,
            "economic_gap_subtraction_allowed": False,
            "minimum_index": 0, "maximum_index": 10_000,
        }
