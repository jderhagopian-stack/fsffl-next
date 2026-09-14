from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import FrozenModel, Position, Provenance


class CareerStateProbability(FrozenModel):
    state: str
    probability: Annotated[float, Field(ge=0.0, le=1.0)]
    production: ForecastDistribution | None = None
    sample_size: int | None = Field(default=None, ge=0)

    @field_validator("state")
    @classmethod
    def require_state_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("career-state name cannot be empty")
        return value


class CareerStateForecast(FrozenModel):
    """Forecast-owned player/horizon career-state distribution.

    Intrinsic may consume this contract but must not infer or reweight football
    transition probabilities. Taxonomies are versioned and may differ by position.
    """

    player_id: str
    position: Position
    horizon_year: Annotated[int, Field(ge=1)]
    current_state: str
    taxonomy_version: str
    states: tuple[CareerStateProbability, ...]
    upward_transition_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    downward_transition_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    survival_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence_quality: Annotated[float, Field(ge=0.0, le=1.0)]
    model_version: str
    as_of: datetime
    provenance: Provenance

    @field_validator("player_id", "current_state", "taxonomy_version", "model_version")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("career-state identifiers cannot be empty")
        return value

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("career-state as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_probability_coherence(self) -> "CareerStateForecast":
        if not self.states:
            raise ValueError("career-state forecast requires at least one state")
        names = [state.state for state in self.states]
        if len(set(names)) != len(names):
            raise ValueError("career-state names must be unique")
        total = sum(state.probability for state in self.states)
        if abs(total - 1.0) > 1e-6:
            raise ValueError("career-state probabilities must sum to 1")
        if self.current_state not in names:
            raise ValueError("current_state must exist in the taxonomy")
        if self.upward_transition_probability + self.downward_transition_probability > 1.0 + 1e-6:
            raise ValueError("upward and downward transition probabilities cannot exceed 1 in aggregate")
        if self.provenance.effective_at > self.as_of:
            raise ValueError("career-state evidence cannot postdate forecast as_of")
        return self
