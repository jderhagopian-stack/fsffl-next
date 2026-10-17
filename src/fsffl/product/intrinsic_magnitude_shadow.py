"""Shadow-only magnitude-sensitive Intrinsic presentation experiments.

This module is intentionally not imported by production presentation, routing,
forecasting, valuation, or trade calculation. Anchors must be externally frozen
from governed historical calibration evidence; no defaults are supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite, sqrt
from typing import Literal, Mapping


Horizon = Literal["three_year", "career"]
Curve = Literal["linear", "sqrt"]


@dataclass(frozen=True)
class MagnitudeRuler:
    horizon: Horizon
    anchor: float
    curve: Curve
    reference_version: str

    def __post_init__(self) -> None:
        if self.horizon not in ("three_year", "career"):
            raise ValueError("unsupported Intrinsic horizon")
        if not isfinite(self.anchor) or self.anchor <= 0:
            raise ValueError("anchor must be finite and positive")
        if self.curve not in ("linear", "sqrt"):
            raise ValueError("unsupported magnitude curve")
        if not self.reference_version.strip():
            raise ValueError("frozen reference provenance is required")

    @property
    def fingerprint(self) -> str:
        payload = (self.horizon, self.anchor, self.curve, self.reference_version)
        return sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()

    def score(self, raw: float | None) -> float | None:
        if raw is None:
            return None
        if not isfinite(raw):
            raise ValueError("raw Intrinsic must be finite")
        # Negative marginal contributions do not create negative presentation
        # scores. The original raw quantity is retained outside this module.
        fraction = max(0.0, min(1.0, raw / self.anchor))
        transformed = sqrt(fraction) if self.curve == "sqrt" else fraction
        return 10000.0 * transformed


def shadow_compare(
    raw_by_player: Mapping[str, float | None],
    *,
    ruler: MagnitudeRuler,
) -> dict[str, float | None]:
    """Read-only comparison, independent of reference player membership."""
    return {player_id: ruler.score(raw) for player_id, raw in raw_by_player.items()}
