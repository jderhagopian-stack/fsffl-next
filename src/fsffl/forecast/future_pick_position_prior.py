"""Explicit provisional draft-position evidence when no forecast is available.

Exchangeability is a neutral assumption, not a simulated finish distribution.
It carries no league, owner, class-strength or acceptance prediction.
"""
from datetime import UTC, datetime

from fsffl.state.models import FrozenModel
from typing import Literal
from pydantic import Field

FUTURE_PICK_POSITION_POLICY = "exchangeable-later-draft-slot-prior-v1"
FUTURE_PICK_POSITION_AVAILABLE_AT = datetime(2026, 11, 14, 20, 33, 53, tzinfo=UTC)


class FuturePickPositionPrior(FrozenModel):
    draft_season: int = Field(ge=1900, le=2300)
    team_count: int = Field(ge=1)
    model_version: Literal[FUTURE_PICK_POSITION_POLICY] = FUTURE_PICK_POSITION_POLICY
    evidence_kind: Literal["bounded_provisional_exchangeability"] = "bounded_provisional_exchangeability"

    def probabilities(self) -> tuple[tuple[int, float], ...]:
        if self.team_count < 1 or not 1900 <= self.draft_season <= 2300:
            raise ValueError("valid future draft season and capacity required")
        return tuple((slot, 1 / self.team_count) for slot in range(1, self.team_count + 1))
