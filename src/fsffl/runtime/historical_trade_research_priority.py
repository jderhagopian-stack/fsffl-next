from __future__ import annotations

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
