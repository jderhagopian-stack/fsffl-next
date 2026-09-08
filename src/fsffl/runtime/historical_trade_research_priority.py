from __future__ import annotations

from collections import Counter
from enum import StrEnum

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .historical_trade_composition import HistoricalTradeComposition


class HistoricalEvidenceDirection(StrEnum):
    FAVORS_TEAM_A = "favors_team_a"
    EVEN = "even"
    FAVORS_TEAM_B = "favors_team_b"
    UNKNOWN = "unknown"


class HistoricalEvidenceAlignment(StrEnum):
    ALIGNED = "aligned"
    CONFLICTED = "conflicted"
    NEUTRAL_OR_UNKNOWN = "neutral_or_unknown"


class HistoricalResearchEvidenceProfile(FrozenModel):
    """Research-order metadata; never a Decision or grade shortcut.

    Directions describe independent point-in-time evidence families supplied by
    upstream research. They intentionally carry no value magnitude and cannot be
    consumed as authoritative trade utility.
    """

    transaction_id: str
    current_impact_direction: HistoricalEvidenceDirection
    future_value_direction: HistoricalEvidenceDirection
    current_impact_confidence: float = Field(ge=0, le=1)
    future_value_confidence: float = Field(ge=0, le=1)
    provenance: tuple[str, ...]

    @model_validator(mode="after")
    def validate_profile(self) -> "HistoricalResearchEvidenceProfile":
        if not self.transaction_id.strip():
            raise ValueError("historical research profile transaction_id cannot be blank")
        if not self.provenance:
            raise ValueError("historical research profile requires provenance")
        return self


class HistoricalResearchPriority(FrozenModel):
    transaction_id: str
    alignment: HistoricalEvidenceAlignment
    evidence_strength: float = Field(ge=0, le=1)
    composition: HistoricalTradeComposition


class HistoricalResearchEvidenceInventory(FrozenModel):
    """Batch research summary with no valuation or grading authority."""

    profiled_trade_count: int = Field(ge=0)
    alignment_counts: dict[str, int]
    aligned_transaction_ids: tuple[str, ...]
    conflicted_transaction_ids: tuple[str, ...]
    neutral_or_unknown_transaction_ids: tuple[str, ...]
    minimum_evidence_strength: float | None = Field(default=None, ge=0, le=1)
    maximum_evidence_strength: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_inventory(self) -> "HistoricalResearchEvidenceInventory":
        ids = (
            self.aligned_transaction_ids
            + self.conflicted_transaction_ids
            + self.neutral_or_unknown_transaction_ids
        )
        if len(ids) != self.profiled_trade_count or len(ids) != len(set(ids)):
            raise ValueError("historical research inventory transaction ids must be unique and complete")
        if sum(self.alignment_counts.values()) != self.profiled_trade_count:
            raise ValueError("historical research inventory alignment counts must sum to profiled trades")
        if self.profiled_trade_count == 0:
            if self.minimum_evidence_strength is not None or self.maximum_evidence_strength is not None:
                raise ValueError("empty research inventory cannot carry evidence strength extrema")
        elif self.minimum_evidence_strength is None or self.maximum_evidence_strength is None:
            raise ValueError("nonempty research inventory requires evidence strength extrema")
        return self


def classify_historical_evidence_alignment(
    profile: HistoricalResearchEvidenceProfile,
) -> HistoricalEvidenceAlignment:
    current = profile.current_impact_direction
    future = profile.future_value_direction
    directional = {
        HistoricalEvidenceDirection.FAVORS_TEAM_A,
        HistoricalEvidenceDirection.FAVORS_TEAM_B,
    }
    if current in directional and future in directional:
        if current == future:
            return HistoricalEvidenceAlignment.ALIGNED
        return HistoricalEvidenceAlignment.CONFLICTED
    return HistoricalEvidenceAlignment.NEUTRAL_OR_UNKNOWN


def prioritize_historical_trade_evidence_cases(
    *,
    compositions: tuple[HistoricalTradeComposition, ...],
    evidence_profiles: tuple[HistoricalResearchEvidenceProfile, ...],
) -> tuple[HistoricalResearchPriority, ...]:
    """Order cases for research efficiency without changing model authority.

    Clean, independently aligned PIT evidence is examined first because it is the
    most informative place to test robustness under broad coefficient uncertainty.
    Conflicted and incomplete cases remain in the queue and are never excluded.
    """

    composition_by_id = {row.transaction_id: row for row in compositions}
    if len(composition_by_id) != len(compositions):
        raise ValueError("historical trade compositions must have unique transaction ids")

    profile_ids = [profile.transaction_id for profile in evidence_profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("historical research profiles must have unique transaction ids")

    rows: list[HistoricalResearchPriority] = []
    for profile in evidence_profiles:
        composition = composition_by_id.get(profile.transaction_id)
        if composition is None:
            raise ValueError(f"missing composition for transaction {profile.transaction_id}")
        alignment = classify_historical_evidence_alignment(profile)
        strength = min(profile.current_impact_confidence, profile.future_value_confidence)
        rows.append(
            HistoricalResearchPriority(
                transaction_id=profile.transaction_id,
                alignment=alignment,
                evidence_strength=strength,
                composition=composition,
            )
        )

    alignment_priority = {
        HistoricalEvidenceAlignment.ALIGNED: 0,
        HistoricalEvidenceAlignment.CONFLICTED: 1,
        HistoricalEvidenceAlignment.NEUTRAL_OR_UNKNOWN: 2,
    }
    composition_priority = {
        "player_only": 0,
        "pick_only": 1,
        "players_and_picks": 2,
        "players_and_faab": 3,
        "picks_and_faab": 4,
        "faab_only": 5,
        "mixed": 6,
    }
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                alignment_priority[row.alignment],
                composition_priority[row.composition.composition_class.value],
                -row.evidence_strength,
                row.transaction_id,
            ),
        )
    )


def summarize_historical_research_evidence(
    *,
    priorities: tuple[HistoricalResearchPriority, ...],
) -> HistoricalResearchEvidenceInventory:
    """Summarize evidence alignment for batch orchestration only.

    The inventory identifies which PIT-researched cases are ready to *attempt*
    robustness envelopes. It does not infer missing evidence, value assets, select a
    winner, or establish grade eligibility.
    """

    ids = [row.transaction_id for row in priorities]
    if len(ids) != len(set(ids)):
        raise ValueError("historical research priorities must have unique transaction ids")

    counts = Counter(row.alignment.value for row in priorities)
    aligned = tuple(sorted(row.transaction_id for row in priorities if row.alignment == HistoricalEvidenceAlignment.ALIGNED))
    conflicted = tuple(sorted(row.transaction_id for row in priorities if row.alignment == HistoricalEvidenceAlignment.CONFLICTED))
    unknown = tuple(
        sorted(
            row.transaction_id
            for row in priorities
            if row.alignment == HistoricalEvidenceAlignment.NEUTRAL_OR_UNKNOWN
        )
    )
    strengths = [row.evidence_strength for row in priorities]
    return HistoricalResearchEvidenceInventory(
        profiled_trade_count=len(priorities),
        alignment_counts={alignment.value: counts.get(alignment.value, 0) for alignment in HistoricalEvidenceAlignment},
        aligned_transaction_ids=aligned,
        conflicted_transaction_ids=conflicted,
        neutral_or_unknown_transaction_ids=unknown,
        minimum_evidence_strength=min(strengths) if strengths else None,
        maximum_evidence_strength=max(strengths) if strengths else None,
    )
