from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .simulation import TeamCompetitiveOutcome
from .utility import CalculatedCompetitiveState


class CompetitiveStatePolicy(FrozenModel):
    """Explicit policy for translating simulation outcomes into calculated state.

    Thresholds are evidence/policy inputs rather than hidden constants. NEXT-4
    may classify a team only when a governed policy is supplied. Owner strategic
    posture remains separate and cannot change this calculated classification.
    """

    developing_playoff_min: float = Field(ge=0, le=1)
    competitive_playoff_min: float = Field(ge=0, le=1)
    contender_playoff_min: float = Field(ge=0, le=1)
    contender_first_place_min: float = Field(ge=0, le=1)
    model_version: str
    evidence_through: datetime
    provenance: str

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "CompetitiveStatePolicy":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("competitive-state policy identifiers cannot be blank")
        if not (
            self.developing_playoff_min
            <= self.competitive_playoff_min
            <= self.contender_playoff_min
        ):
            raise ValueError("playoff thresholds must increase from developing to contender")
        return self


def classify_calculated_competitive_state(
    outcome: TeamCompetitiveOutcome,
    policy: CompetitiveStatePolicy,
    *,
    as_of: datetime,
) -> CalculatedCompetitiveState:
    """Classify simulation evidence without owner preference or trade logic."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if policy.evidence_through > as_of:
        raise ValueError("competitive-state policy cannot use evidence from the future")

    if (
        outcome.playoff_probability >= policy.contender_playoff_min
        and outcome.first_place_probability >= policy.contender_first_place_min
    ):
        return CalculatedCompetitiveState.CONTENDER
    if outcome.playoff_probability >= policy.competitive_playoff_min:
        return CalculatedCompetitiveState.COMPETITIVE
    if outcome.playoff_probability >= policy.developing_playoff_min:
        return CalculatedCompetitiveState.DEVELOPING
    return CalculatedCompetitiveState.REBUILDING
