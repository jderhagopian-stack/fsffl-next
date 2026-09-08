from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


class BehavioralEvidenceLevel(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CALIBRATED = "calibrated"


class BehavioralLikelihoodDirection(StrEnum):
    UNKNOWN = "unknown"
    REDUCED = "reduced"
    NEUTRAL = "neutral"
    ELEVATED = "elevated"


class BehavioralDriverKind(StrEnum):
    OWNER_HISTORY = "owner_history"
    COMPETITIVE_STATE = "competitive_state"
    ROSTER_CONSTRUCTION = "roster_construction"
    PACKAGE_SHAPE = "package_shape"
    COUNTERPARTY_HISTORY = "counterparty_history"


class BehavioralLikelihoodDriver(FrozenModel):
    kind: BehavioralDriverKind
    direction: BehavioralLikelihoodDirection
    description: str
    evidence_level: BehavioralEvidenceLevel

    @field_validator("description")
    @classmethod
    def require_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("behavioral likelihood drivers require a description")
        return value


class BehavioralLikelihoodEstimate(FrozenModel):
    """Governed owner-response estimate without pretending inference is fact.

    Observed evidence reports what an owner actually did. Inferred estimates may
    combine observed owner history with current competitive state, roster
    construction and package shape to provide a directional likelihood judgment.
    Numeric acceptance probabilities are reserved for historically calibrated
    models whose predictive calibration has been validated separately.

    This contract never owns market Value or recommendation authority.
    """

    owner_id: str
    as_of: datetime
    evidence_level: BehavioralEvidenceLevel
    direction: BehavioralLikelihoodDirection = BehavioralLikelihoodDirection.UNKNOWN
    drivers: tuple[BehavioralLikelihoodDriver, ...] = ()
    observed_trade_count: Annotated[int, Field(ge=0)] = 0
    acceptance_probability: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    probability_interval_low: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    probability_interval_high: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    calibration_model_version: str | None = None
    model_version: str = "behavioral-likelihood-contract-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral likelihood timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def enforce_calibration_boundary(self) -> "BehavioralLikelihoodEstimate":
        probability_fields = (
            self.acceptance_probability,
            self.probability_interval_low,
            self.probability_interval_high,
        )
        has_probability = any(value is not None for value in probability_fields)
        if self.evidence_level != BehavioralEvidenceLevel.CALIBRATED and has_probability:
            raise ValueError("numeric acceptance probability requires calibrated behavioral evidence")
        if self.evidence_level != BehavioralEvidenceLevel.CALIBRATED and self.calibration_model_version is not None:
            raise ValueError("calibration_model_version is only valid for calibrated estimates")
        if self.evidence_level == BehavioralEvidenceLevel.CALIBRATED:
            if self.acceptance_probability is None:
                raise ValueError("calibrated behavioral estimates require acceptance_probability")
            if self.probability_interval_low is None or self.probability_interval_high is None:
                raise ValueError("calibrated behavioral estimates require a probability interval")
            if self.probability_interval_low > self.acceptance_probability:
                raise ValueError("probability interval low cannot exceed acceptance_probability")
            if self.probability_interval_high < self.acceptance_probability:
                raise ValueError("probability interval high cannot be below acceptance_probability")
            if not self.calibration_model_version or not self.calibration_model_version.strip():
                raise ValueError("calibrated behavioral estimates require calibration provenance")
        return self
