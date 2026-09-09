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


class BehavioralProbabilityBasis(StrEnum):
    INFERRED = "inferred"
    CALIBRATED = "calibrated"


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
    """Governed owner-response estimate with explicit uncertainty and provenance.

    Observed evidence reports what an owner actually did. Inferred estimates may
    combine observed owner history with current competitive state, roster
    construction, package shape and other governed context to produce a numeric
    probability when the inferential method and uncertainty are exposed.

    Calibrated estimates are a stronger evidence class: they additionally require
    predictive calibration provenance. Lack of full calibration does not force a
    useful estimate to zero; it requires the product to label the estimate as
    inferred and expose its uncertainty.

    This contract never owns universal market Value or recommendation authority.
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
    probability_basis: BehavioralProbabilityBasis | None = None
    probability_method: str | None = None
    confidence_score: Annotated[float | None, Field(ge=0.0, le=1.0)] = None
    inference_model_version: str | None = None
    calibration_model_version: str | None = None
    model_version: str = "behavioral-likelihood-contract-v2"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral likelihood timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def enforce_probability_provenance(self) -> "BehavioralLikelihoodEstimate":
        probability_fields = (
            self.acceptance_probability,
            self.probability_interval_low,
            self.probability_interval_high,
        )
        has_any_probability = any(value is not None for value in probability_fields)
        has_all_probability = all(value is not None for value in probability_fields)

        if not has_any_probability:
            if self.probability_basis is not None or self.probability_method is not None:
                raise ValueError("probability provenance requires a numeric behavioral probability")
            if self.confidence_score is not None:
                raise ValueError("probability confidence requires a numeric behavioral probability")
            if self.inference_model_version is not None or self.calibration_model_version is not None:
                raise ValueError("probability model provenance requires a numeric behavioral probability")
            return self

        if not has_all_probability:
            raise ValueError("behavioral probabilities require a complete uncertainty interval")
        if self.probability_interval_low > self.acceptance_probability:
            raise ValueError("probability interval low cannot exceed acceptance_probability")
        if self.probability_interval_high < self.acceptance_probability:
            raise ValueError("probability interval high cannot be below acceptance_probability")
        if self.probability_basis is None:
            raise ValueError("behavioral probabilities require an explicit probability_basis")
        if not self.probability_method or not self.probability_method.strip():
            raise ValueError("behavioral probabilities require method provenance")
        if self.confidence_score is None:
            raise ValueError("behavioral probabilities require an explicit confidence_score")

        if self.probability_basis == BehavioralProbabilityBasis.INFERRED:
            if self.evidence_level != BehavioralEvidenceLevel.INFERRED:
                raise ValueError("inferred probability basis requires inferred behavioral evidence")
            if not self.inference_model_version or not self.inference_model_version.strip():
                raise ValueError("inferred behavioral probabilities require inference model provenance")
            if self.calibration_model_version is not None:
                raise ValueError("inferred behavioral probabilities cannot claim calibration provenance")

        if self.probability_basis == BehavioralProbabilityBasis.CALIBRATED:
            if self.evidence_level != BehavioralEvidenceLevel.CALIBRATED:
                raise ValueError("calibrated probability basis requires calibrated behavioral evidence")
            if not self.calibration_model_version or not self.calibration_model_version.strip():
                raise ValueError("calibrated behavioral probabilities require calibration provenance")

        return self
