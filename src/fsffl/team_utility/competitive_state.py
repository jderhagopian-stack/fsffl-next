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


def _linear_quantile(values: tuple[float, ...], quantile: float) -> float:
    """Return a deterministic linear-interpolated quantile for a small league panel."""

    if not values:
        raise ValueError("competitive-state policy requires league simulation outcomes")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    ordered = tuple(sorted(values))
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def derive_league_relative_competitive_state_policy(
    outcomes: tuple[TeamCompetitiveOutcome, ...],
    *,
    as_of: datetime,
) -> CompetitiveStatePolicy:
    """Build a transparent provisional policy from the current league distribution.

    This avoids arbitrary absolute win/probability cutoffs while historical state
    calibration is still being reconstructed. The quartile boundaries are purely
    descriptive partitions of the current authoritative Simulation distribution:
    lower quartile -> rebuilding, middle-lower -> developing, middle-upper ->
    competitive, and upper quartile with upper-quartile first-place odds ->
    contender. This policy does not change Simulation outcomes, Value, or owner
    strategic posture and is explicitly replaceable by future empirical calibration.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not outcomes:
        raise ValueError("competitive-state policy requires league simulation outcomes")
    playoff = tuple(item.playoff_probability for item in outcomes)
    first_place = tuple(item.first_place_probability for item in outcomes)
    return CompetitiveStatePolicy(
        developing_playoff_min=_linear_quantile(playoff, 0.25),
        competitive_playoff_min=_linear_quantile(playoff, 0.50),
        contender_playoff_min=_linear_quantile(playoff, 0.75),
        contender_first_place_min=_linear_quantile(first_place, 0.75),
        model_version="next4-competitive-state-policy-v1:league-relative-quartiles",
        evidence_through=as_of,
        provenance=(
            "Structurally derived from the current authoritative league Simulation "
            "distribution using 25th/50th/75th percentile playoff boundaries and "
            "75th-percentile first-place odds; provisional until historical "
            "competitive-state calibration is promoted."
        ),
    )


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
