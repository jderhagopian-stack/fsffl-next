from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules


class DraftSlotAssignment(FrozenModel):
    """One team's rookie-draft slot inside one simulated/observed scenario."""

    team_id: str
    slot_in_round: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def validate_identity(self) -> "DraftSlotAssignment":
        if not self.team_id.strip():
            raise ValueError("draft-slot team_id cannot be blank")
        return self


class DraftOrderScenario(FrozenModel):
    """One possible draft-order realization supplied by Simulation/rules authority.

    The scenario does not assume reverse standings, Max PF, playoff finish, lottery,
    or any other draft-order rule. Upstream league-rule logic must produce the
    assignments that are valid for that league.
    """

    probability: Annotated[float, Field(gt=0, le=1)]
    assignments: tuple[DraftSlotAssignment, ...]

    @model_validator(mode="after")
    def validate_assignments(self) -> "DraftOrderScenario":
        if not self.assignments:
            raise ValueError("draft-order scenario requires assignments")
        team_ids = [row.team_id for row in self.assignments]
        slots = [row.slot_in_round for row in self.assignments]
        if len(team_ids) != len(set(team_ids)):
            raise ValueError("draft-order scenario team ids must be unique")
        if len(slots) != len(set(slots)):
            raise ValueError("draft-order scenario slots must be unique")
        return self


class DraftOrderSimulationResult(FrozenModel):
    """Point-in-time distribution of complete rookie-draft order scenarios."""

    league_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    as_of: datetime
    scenarios: tuple[DraftOrderScenario, ...]
    model_version: str
    rule_policy_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("draft-order as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "DraftOrderSimulationResult":
        if any(not value.strip() for value in (
            self.league_id,
            self.model_version,
            self.rule_policy_version,
            self.provenance,
        )):
            raise ValueError("draft-order identifiers/provenance cannot be blank")
        if not self.scenarios:
            raise ValueError("draft-order result requires scenarios")
        if abs(sum(row.probability for row in self.scenarios) - 1.0) > 1e-9:
            raise ValueError("draft-order scenario probabilities must sum to 1")
        return self

    def slot_distribution_for_team(
        self,
        team_id: str,
        *,
        league_rules: LeagueRules,
    ) -> tuple[tuple[int, float], ...]:
        """Marginalize complete scenarios to one team's slot probabilities."""

        if not team_id.strip():
            raise ValueError("team_id cannot be blank")
        probabilities: dict[int, float] = {}
        for scenario in self.scenarios:
            matching = [row for row in scenario.assignments if row.team_id == team_id]
            if len(matching) != 1:
                raise ValueError("every draft-order scenario must assign the requested team exactly once")
            slot = matching[0].slot_in_round
            if slot > league_rules.team_count:
                raise ValueError("draft-order scenario slot exceeds league team count")
            probabilities[slot] = probabilities.get(slot, 0.0) + scenario.probability
        return tuple(sorted(probabilities.items()))
