from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import isclose
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.models import MarketPriceEstimate, ValueDistribution, ValueScale


class ContextualValueAdjustmentKind(StrEnum):
    TEAM_NEED = "team_need"
    COMPETITIVE_STATE = "competitive_state"
    ROSTER_CONSTRUCTION = "roster_construction"
    ASSET_MIX = "asset_mix"
    REPLACEMENT_OPTIONS = "replacement_options"
    OWNER_BEHAVIOR = "owner_behavior"
    COUNTERPARTY_HISTORY = "counterparty_history"
    PACKAGE_CONTEXT = "package_context"
    OTHER_GOVERNED = "other_governed"


class ContextualValueEvidenceLevel(StrEnum):
    INFERRED = "inferred"
    CALIBRATED = "calibrated"


class ContextualValueAdjustment(FrozenModel):
    """One bounded additive contribution to team/owner-adjusted value.

    `authority_id`, `overlap_group`, and `evidence_ids` are explicit so the
    aggregate contract can fail closed when the same causal evidence is counted
    twice. Contributions are additive deltas on the baseline ValueScale; there is
    intentionally no multiplier field.
    """

    kind: ContextualValueAdjustmentKind
    authority_id: str
    overlap_group: str
    delta_mean: float
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence_level: ContextualValueEvidenceLevel
    evidence_ids: tuple[str, ...]
    source_model_version: str
    residualized_against: tuple[str, ...] = ()
    explanation: str = ""

    @model_validator(mode="after")
    def validate_adjustment(self) -> "ContextualValueAdjustment":
        for field_name, value in (
            ("authority_id", self.authority_id),
            ("overlap_group", self.overlap_group),
            ("source_model_version", self.source_model_version),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} cannot be blank")
        if not self.evidence_ids:
            raise ValueError("contextual value adjustment requires evidence_ids")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("contextual value adjustment evidence_ids must be unique")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("contextual value adjustment evidence_ids cannot be blank")
        if len(self.residualized_against) != len(set(self.residualized_against)):
            raise ValueError("residualized_against authorities must be unique")
        if self.authority_id in self.residualized_against:
            raise ValueError("an adjustment cannot residualize against itself")
        return self


class TeamOwnerAdjustedValueEstimate(FrozenModel):
    """Contextual willingness-to-pay/clearing-value estimate for one asset.

    Universal FSFFL Market Value remains embedded as the immutable baseline.
    Contextual adjustments may move the expected value for a specific team and
    owner, but only through bounded additive contributions with non-overlapping
    authority/evidence ownership. This contract does not mutate or replace the
    universal MarketPriceEstimate.
    """

    team_id: str
    owner_id: str | None = None
    market_baseline: MarketPriceEstimate
    adjusted_distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    adjustments: tuple[ContextualValueAdjustment, ...]
    adjustment_bound_abs: Annotated[float, Field(ge=0.0)]
    model_version: str = "team-owner-adjusted-value-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("team/owner-adjusted value timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_adjusted_value(self) -> "TeamOwnerAdjustedValueEstimate":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("team/owner-adjusted value identifiers cannot be blank")
        if self.owner_id is not None and not self.owner_id.strip():
            raise ValueError("owner_id cannot be blank when provided")
        if self.market_baseline.as_of > self.as_of:
            raise ValueError("contextual value cannot use a future market baseline")
        if self.market_baseline.scale != self.scale:
            raise ValueError("contextual value must remain on the market baseline ValueScale")

        authority_ids = [item.authority_id for item in self.adjustments]
        if len(authority_ids) != len(set(authority_ids)):
            raise ValueError("team/owner-adjusted value cannot count the same authority twice")
        overlap_groups = [item.overlap_group for item in self.adjustments]
        if len(overlap_groups) != len(set(overlap_groups)):
            raise ValueError("team/owner-adjusted value cannot contain overlapping adjustments")

        seen_evidence: set[str] = set()
        for item in self.adjustments:
            duplicate_evidence = seen_evidence.intersection(item.evidence_ids)
            if duplicate_evidence:
                raise ValueError(
                    "team/owner-adjusted value cannot reuse evidence across adjustments: "
                    + ", ".join(sorted(duplicate_evidence))
                )
            seen_evidence.update(item.evidence_ids)

        total_delta = sum(item.delta_mean for item in self.adjustments)
        if abs(total_delta) > self.adjustment_bound_abs + 1e-9:
            raise ValueError("contextual value adjustment exceeds governed absolute bound")
        expected_mean = self.market_baseline.distribution.mean + total_delta
        if not isclose(
            self.adjusted_distribution.mean,
            expected_mean,
            rel_tol=1e-9,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "adjusted mean must equal market baseline plus additive non-overlapping deltas"
            )
        return self

    @property
    def total_adjustment(self) -> float:
        return sum(item.delta_mean for item in self.adjustments)
