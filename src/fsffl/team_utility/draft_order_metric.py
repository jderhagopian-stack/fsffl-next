from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules

from .draft_order import DraftOrderScenario, DraftSlotAssignment


class DraftMetricDirection(StrEnum):
    LOWER_VALUE_EARLIER_PICK = "lower_value_earlier_pick"
    HIGHER_VALUE_EARLIER_PICK = "higher_value_earlier_pick"


class TeamDraftMetric(FrozenModel):
    team_id: str
    value: float

    @model_validator(mode="after")
    def validate_team(self) -> "TeamDraftMetric":
        if not self.team_id.strip():
            raise ValueError("draft metric team_id cannot be blank")
        return self


class DraftMetricScenario(FrozenModel):
    """One point-in-time realization of a league-defined draft-order metric."""

    probability: float
    metrics: tuple[TeamDraftMetric, ...]

    @model_validator(mode="after")
    def validate_scenario(self) -> "DraftMetricScenario":
        if self.probability <= 0 or self.probability > 1:
            raise ValueError("draft metric scenario probability must be in (0, 1]")
        if not self.metrics:
            raise ValueError("draft metric scenario requires team metrics")
        ids = [row.team_id for row in self.metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("draft metric team ids must be unique")
        return self


class DraftMetricScenarioSet(FrozenModel):
    league_id: str
    draft_season: int
    as_of: datetime
    scenarios: tuple[DraftMetricScenario, ...]
    metric_id: str
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("draft metric as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_set(self) -> "DraftMetricScenarioSet":
        if any(not value.strip() for value in (self.league_id, self.metric_id, self.model_version, self.provenance)):
            raise ValueError("draft metric identifiers/provenance cannot be blank")
        if not self.scenarios:
            raise ValueError("draft metric scenario set cannot be empty")
        if abs(sum(row.probability for row in self.scenarios) - 1.0) > 1e-9:
            raise ValueError("draft metric scenario probabilities must sum to 1")
        team_sets = [frozenset(row.team_id for row in scenario.metrics) for scenario in self.scenarios]
        if any(team_set != team_sets[0] for team_set in team_sets[1:]):
            raise ValueError("every draft metric scenario must contain the same teams")
        return self


def rank_metric_scenarios_to_draft_order(
    evidence: DraftMetricScenarioSet,
    *,
    league_rules: LeagueRules,
    direction: DraftMetricDirection,
) -> tuple[DraftOrderScenario, ...]:
    """Convert explicit metric scenarios into complete draft-order scenarios.

    Ties fail closed because a league-specific tiebreak rule is required; this
    function does not invent team-id or other hidden tiebreakers.
    """

    expected_team_count = len(evidence.scenarios[0].metrics)
    if expected_team_count != league_rules.team_count:
        raise ValueError("draft metric evidence must contain every league team")

    output: list[DraftOrderScenario] = []
    reverse = direction == DraftMetricDirection.HIGHER_VALUE_EARLIER_PICK
    for scenario in evidence.scenarios:
        values = [row.value for row in scenario.metrics]
        if len(values) != len(set(values)):
            raise ValueError("draft metric ties require explicit league tiebreak evidence")
        ranked = sorted(scenario.metrics, key=lambda row: row.value, reverse=reverse)
        output.append(
            DraftOrderScenario(
                probability=scenario.probability,
                assignments=tuple(
                    DraftSlotAssignment(team_id=row.team_id, slot_in_round=index)
                    for index, row in enumerate(ranked, start=1)
                ),
            )
        )
    return tuple(output)
