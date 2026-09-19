from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from random import Random
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .draft_order_metric import DraftMetricScenario, DraftMetricScenarioSet, TeamDraftMetric


class DraftMetricDistributionKind(StrEnum):
    NORMAL = "normal"


class TeamDraftMetricDistribution(FrozenModel):
    """Point-in-time distribution for one league-defined draft-order metric.

    Examples include Max PF, points for, or another explicit competitive metric.
    The producer of this evidence owns the metric semantics. Simulation samples it
    but does not reinterpret it as wins, standings, value, or team utility.
    """

    team_id: str
    mean_value: float
    stddev_value: Annotated[float, Field(ge=0)]
    distribution_kind: DraftMetricDistributionKind = DraftMetricDistributionKind.NORMAL
    model_version: str

    @model_validator(mode="after")
    def validate_identity(self) -> "TeamDraftMetricDistribution":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("draft metric distribution identifiers cannot be blank")
        return self


class DraftMetricSimulationInput(FrozenModel):
    league_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    as_of: datetime
    metric_id: str
    distributions: tuple[TeamDraftMetricDistribution, ...]
    simulation_count: Annotated[int, Field(ge=1)] = 50_000
    seed: int = 20260907
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("draft metric simulation as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_input(self) -> "DraftMetricSimulationInput":
        if any(not value.strip() for value in (self.league_id, self.metric_id, self.model_version, self.provenance)):
            raise ValueError("draft metric simulation identifiers/provenance cannot be blank")
        if not self.distributions:
            raise ValueError("draft metric simulation requires team distributions")
        ids = [item.team_id for item in self.distributions]
        if len(ids) != len(set(ids)):
            raise ValueError("draft metric distributions must have unique team ids")
        return self


def simulate_draft_metric(request: DraftMetricSimulationInput) -> DraftMetricScenarioSet:
    """Sample league-defined draft metric scenarios without ranking them.

    Ranking remains a separate rule-policy operation. This preserves the charter:
    Simulation owns stochastic competitive metric outcomes; the resolved league
    policy determines how those outcomes translate into rookie-draft slots.
    """

    rng = Random(request.seed)
    probability = 1.0 / request.simulation_count
    scenarios: list[DraftMetricScenario] = []

    for _ in range(request.simulation_count):
        metrics = tuple(
            TeamDraftMetric(team_id=item.team_id, value=_sample_metric(item, rng))
            for item in request.distributions
        )
        scenarios.append(DraftMetricScenario(probability=probability, metrics=metrics))

    versions = "+".join(sorted({item.model_version for item in request.distributions}))
    return DraftMetricScenarioSet(
        league_id=request.league_id,
        draft_season=request.draft_season,
        as_of=request.as_of,
        scenarios=tuple(scenarios),
        metric_id=request.metric_id,
        model_version=f"{request.model_version}+inputs:{versions}",
        provenance=request.provenance,
    )


def _sample_metric(distribution: TeamDraftMetricDistribution, rng: Random) -> float:
    if distribution.distribution_kind != DraftMetricDistributionKind.NORMAL:
        raise ValueError("unsupported draft metric distribution kind")
    if distribution.stddev_value == 0:
        return distribution.mean_value
    return rng.gauss(distribution.mean_value, distribution.stddev_value)
