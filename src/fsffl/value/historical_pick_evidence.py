from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import DraftPick, FrozenModel, LeagueRules

from .historical_pick import (
    HistoricalDraftSlotObservation,
    HistoricalPickCoordinateEvidence,
    HistoricalSlotProbability,
)
from .models import ValueDistribution, ValueScale


class FrozenDraftedAssetValue(FrozenModel):
    """Value of a drafted asset frozen at the draft evidence boundary.

    This is not the player's later career outcome. The value must be produced by
    a Value-layer model using only information available at ``available_at``.
    """

    draft_season: Annotated[int, Field(ge=1900)]
    round: Annotated[int, Field(ge=1)]
    slot_in_round: Annotated[int, Field(ge=1)]
    value: ValueDistribution
    scale: ValueScale
    available_at: datetime
    model_version: str
    provenance: str

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("frozen drafted-asset timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "FrozenDraftedAssetValue":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("frozen drafted-asset version/provenance cannot be blank")
        return self


class HistoricalTeamDraftSlotForecast(FrozenModel):
    """Point-in-time draft-slot forecast supplied by upstream State/Simulation research.

    This object deliberately contains probabilities rather than a strength score so
    Value does not own or re-derive competitive-state-to-slot coefficients.
    """

    pick_id: str
    as_of: datetime
    probabilities: tuple[HistoricalSlotProbability, ...]

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical slot forecast as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_forecast(self) -> "HistoricalTeamDraftSlotForecast":
        if not self.pick_id.strip():
            raise ValueError("pick_id cannot be blank")
        if not self.probabilities:
            raise ValueError("historical slot forecast requires probabilities")
        slots = [item.slot_in_round for item in self.probabilities]
        if len(slots) != len(set(slots)):
            raise ValueError("historical slot forecast slots must be unique")
        if abs(sum(item.probability for item in self.probabilities) - 1.0) > 1e-9:
            raise ValueError("historical slot forecast probabilities must sum to 1")
        if any(item.evidence_as_of > self.as_of for item in self.probabilities):
            raise ValueError("slot-probability evidence cannot postdate forecast as_of")
        return self


def build_draft_slot_observations(
    values: tuple[FrozenDraftedAssetValue, ...],
    *,
    league_rules: LeagueRules,
    as_of: datetime,
) -> tuple[HistoricalDraftSlotObservation, ...]:
    """Convert frozen drafted-asset values into leakage-safe slot observations.

    Duplicate observations for the same draft-season/round/slot are aggregated
    only when they are on the same ValueScale. No missing slots are imputed.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    grouped: dict[tuple[int, int, int, ValueScale], list[FrozenDraftedAssetValue]] = defaultdict(list)
    for item in values:
        if item.available_at > as_of:
            continue
        if item.round > league_rules.rookie_draft_rounds:
            continue
        if item.slot_in_round > league_rules.team_count:
            raise ValueError("frozen drafted-asset slot exceeds league team count")
        grouped[(item.draft_season, item.round, item.slot_in_round, item.scale)].append(item)

    observations: list[HistoricalDraftSlotObservation] = []
    for (season, round_number, slot, scale), rows in sorted(grouped.items(), key=lambda x: x[0][:3]):
        mean = sum(row.value.mean for row in rows) / len(rows)
        second = sum(row.value.stddev**2 + row.value.mean**2 for row in rows) / len(rows)
        provenance = "; ".join(sorted({row.provenance for row in rows}))
        versions = "+".join(sorted({row.model_version for row in rows}))
        available_at = max(row.available_at for row in rows)
        observations.append(
            HistoricalDraftSlotObservation(
                draft_season=season,
                round=round_number,
                slot_in_round=slot,
                value=ValueDistribution(mean=mean, stddev=sqrt(max(0.0, second - mean**2))),
                scale=scale,
                available_at=available_at,
                model_version=versions,
                provenance=provenance,
            )
        )
    return tuple(observations)


def build_historical_pick_evidence(
    *,
    pick: DraftPick,
    as_of: datetime,
    league_rules: LeagueRules,
    drafted_asset_values: tuple[FrozenDraftedAssetValue, ...],
    slot_forecast: HistoricalTeamDraftSlotForecast | None = None,
    exact_slot_in_round: int | None = None,
    exact_slot_known_at: datetime | None = None,
) -> HistoricalPickCoordinateEvidence:
    """Assemble Value inputs without inventing missing historical evidence."""

    observations = build_draft_slot_observations(
        drafted_asset_values,
        league_rules=league_rules,
        as_of=as_of,
    )
    probabilities: tuple[HistoricalSlotProbability, ...] = ()
    if exact_slot_in_round is None and slot_forecast is not None:
        if slot_forecast.pick_id != pick.pick_id:
            raise ValueError("slot forecast must describe the requested pick")
        if slot_forecast.as_of > as_of:
            raise ValueError("slot forecast cannot postdate historical pick as_of")
        if any(item.slot_in_round > league_rules.team_count for item in slot_forecast.probabilities):
            raise ValueError("slot forecast exceeds league team count")
        probabilities = slot_forecast.probabilities

    return HistoricalPickCoordinateEvidence(
        pick=pick,
        as_of=as_of,
        observations=observations,
        slot_probabilities=probabilities,
        exact_slot_in_round=exact_slot_in_round,
        exact_slot_known_at=exact_slot_known_at,
    )
