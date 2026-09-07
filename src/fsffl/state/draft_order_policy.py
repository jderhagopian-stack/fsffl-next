from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from .models import FrozenModel, Provenance


DraftOrderParameterValue = str | int | float | bool


class DraftOrderPolicyParameter(FrozenModel):
    """One explicit, serializable input to a league draft-order policy.

    Parameter names are intentionally open-ended. State records what the league
    rule says; it does not interpret Max PF, playoff finish, lottery, consolation,
    or other mechanisms as universal behavior.
    """

    name: str
    value: DraftOrderParameterValue

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("draft-order policy parameter name cannot be blank")
        return value.strip()


class DraftOrderPolicyEvidence(FrozenModel):
    """Versioned point-in-time evidence describing one league's draft-order rule.

    This is State evidence, not Simulation output. A downstream scenario producer
    may interpret a supported mechanism, while unsupported/custom mechanisms must
    remain explicit rather than being replaced with a guessed universal rule.
    """

    league_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    effective_at: datetime
    available_at: datetime
    policy_id: str
    version: str
    mechanism: str
    description: str
    parameters: tuple[DraftOrderPolicyParameter, ...] = ()
    provenance: Provenance

    @field_validator("effective_at", "available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("draft-order policy timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "DraftOrderPolicyEvidence":
        for value in (
            self.league_id,
            self.policy_id,
            self.version,
            self.mechanism,
            self.description,
        ):
            if not value.strip():
                raise ValueError("draft-order policy identifiers and description cannot be blank")
        names = [item.name for item in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("draft-order policy parameter names must be unique")
        return self


def resolve_draft_order_policy(
    policies: tuple[DraftOrderPolicyEvidence, ...],
    *,
    league_id: str,
    draft_season: int,
    as_of: datetime,
) -> DraftOrderPolicyEvidence | None:
    """Return the latest policy that was both effective and knowable at ``as_of``.

    No fallback mechanism is invented when evidence is absent.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    candidates = [
        item
        for item in policies
        if item.league_id == league_id
        and item.draft_season == draft_season
        and item.effective_at <= as_of
        and item.available_at <= as_of
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.effective_at, item.available_at, item.version))
