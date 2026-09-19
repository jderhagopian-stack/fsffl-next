from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.models import ValueScale


class MaterialityDirection(StrEnum):
    MATERIAL_GAIN = "material_gain"
    MATERIAL_LOSS = "material_loss"
    IMMATERIAL = "immaterial"
    UNAVAILABLE = "unavailable"


class CompetitiveMaterialityPolicy(FrozenModel):
    """Explicit tolerances for interpreting NEXT-4 competitive/resilience deltas.

    Thresholds require empirical or explicitly provisional policy justification;
    callers may not hide operational defaults in decision code. Championship is
    the postseason title outcome. ``first_place_probability_abs`` remains only as
    a backwards-compatible diagnostic tolerance while existing callers migrate.
    """

    expected_wins_abs: Annotated[float, Field(ge=0.0)]
    playoff_probability_abs: Annotated[float, Field(ge=0.0, le=1.0)]
    first_place_probability_abs: Annotated[float, Field(ge=0.0, le=1.0)]
    lineup_drop_abs: Annotated[float, Field(ge=0.0)]
    model_version: str
    evidence_through: datetime
    provenance: str
    championship_probability_abs: Annotated[float, Field(ge=0.0, le=1.0)] | None = None

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("materiality evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "CompetitiveMaterialityPolicy":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("materiality policy metadata cannot be blank")
        return self


class EconomicMaterialityPolicy(FrozenModel):
    """Economic materiality tied to one explicit NEXT-3 value scale/version."""

    scale: ValueScale
    mean_value_abs: Annotated[float, Field(ge=0.0)]
    model_version: str
    evidence_through: datetime
    provenance: str

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("materiality evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "EconomicMaterialityPolicy":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("materiality policy metadata cannot be blank")
        return self


def classify_positive_delta(
    value: float | int | None,
    *,
    absolute_threshold: float,
) -> MaterialityDirection:
    """Classify a metric where positive is favorable using an explicit threshold."""

    if absolute_threshold < 0:
        raise ValueError("materiality threshold cannot be negative")
    if value is None:
        return MaterialityDirection.UNAVAILABLE
    if value > absolute_threshold:
        return MaterialityDirection.MATERIAL_GAIN
    if value < -absolute_threshold:
        return MaterialityDirection.MATERIAL_LOSS
    return MaterialityDirection.IMMATERIAL


def classify_negative_delta(
    value: float | int | None,
    *,
    absolute_threshold: float,
) -> MaterialityDirection:
    """Classify a metric where negative is favorable using an explicit threshold."""

    result = classify_positive_delta(value, absolute_threshold=absolute_threshold)
    if result == MaterialityDirection.MATERIAL_GAIN:
        return MaterialityDirection.MATERIAL_LOSS
    if result == MaterialityDirection.MATERIAL_LOSS:
        return MaterialityDirection.MATERIAL_GAIN
    return result
