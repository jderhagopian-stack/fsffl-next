from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class I1RegularizationPolicy:
    """Versioned regularization metadata for the frozen I1 architecture.

    This is a governance seam, not a user/runtime tuning surface. Production I1
    imports the single governed policy below. A later management-authorized
    calibration can replace the policy values without changing model plumbing or
    the Forecast/Intrinsic architecture.
    """

    version: str = "i1-regularization-v1-c0.25"
    default_c: float = 0.25
    component_c: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("I1 regularization policy version cannot be blank")
        values = (self.default_c, *self.component_c.values())
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("all governed I1 regularization C values must be finite and positive")

    def c_for(self, component: str) -> float:
        if not component.strip():
            raise ValueError("I1 regularization component cannot be blank")
        return float(self.component_c.get(component, self.default_c))


# Provisional research-selected production candidate. This value may change only
# through a separately authorized model-version/configuration update.
FROZEN_I1_REGULARIZATION = I1RegularizationPolicy()
