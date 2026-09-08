from fsffl.runtime.historical_trade_composition import (
    HistoricalTradeComposition,
    HistoricalTradeCompositionClass,
)
from fsffl.runtime.historical_trade_research_priority import (
    HistoricalEvidenceAlignment,
    HistoricalEvidenceDirection,
    HistoricalResearchEvidenceProfile,
    classify_historical_evidence_alignment,
    prioritize_historical_trade_evidence_cases,
)


def composition(transaction_id: str, kind: HistoricalTradeCompositionClass) -> HistoricalTradeComposition:
    counts = {
        HistoricalTradeCompositionClass.PLAYER_ONLY: (2, 0, 0),
        HistoricalTradeCompositionClass.PLAYERS_AND_PICKS: (2, 2, 0),
    }[kind]
    return HistoricalTradeComposition(
        transaction_id=transaction_id,
        team_count=2,
        player_count=counts[0],
        pick_count=counts[1],
        faab_transfer_count=counts[2],
        composition_class=kind,
    )


def profile(
    transaction_id: str,
    current: HistoricalEvidenceDirection,
    future: HistoricalEvidenceDirection,
    current_confidence: float = 0.8,
    future_confidence: float = 0.8,
) -> HistoricalResearchEvidenceProfile:
    return HistoricalResearchEvidenceProfile(
        transaction_id=transaction_id,
        current_impact_direction=current,
        future_value_direction=future,
        current_impact_confidence=current_confidence,
        future_value_confidence=future_confidence,
        provenance=("point-in-time research fixture",),
    )


def test_alignment_distinguishes_agreement_conflict_and_unknown() -> None:
    assert classify_historical_evidence_alignment(
        profile("aligned", HistoricalEvidenceDirection.FAVORS_TEAM_A, HistoricalEvidenceDirection.FAVORS_TEAM_A)
    ) == HistoricalEvidenceAlignment.ALIGNED
    assert classify_historical_evidence_alignment(
        profile("conflicted", HistoricalEvidenceDirection.FAVORS_TEAM_A, HistoricalEvidenceDirection.FAVORS_TEAM_B)
    ) == HistoricalEvidenceAlignment.CONFLICTED
    assert classify_historical_evidence_alignment(
        profile("unknown", HistoricalEvidenceDirection.UNKNOWN, HistoricalEvidenceDirection.FAVORS_TEAM_B)
    ) == HistoricalEvidenceAlignment.NEUTRAL_OR_UNKNOWN


def test_research_priority_prefers_aligned_clean_high_confidence_cases() -> None:
    compositions = (
        composition("conflicted-player", HistoricalTradeCompositionClass.PLAYER_ONLY),
        composition("aligned-mixed", HistoricalTradeCompositionClass.PLAYERS_AND_PICKS),
        composition("aligned-player-low", HistoricalTradeCompositionClass.PLAYER_ONLY),
        composition("aligned-player-high", HistoricalTradeCompositionClass.PLAYER_ONLY),
    )
    profiles = (
        profile(
            "conflicted-player",
            HistoricalEvidenceDirection.FAVORS_TEAM_A,
            HistoricalEvidenceDirection.FAVORS_TEAM_B,
            0.95,
            0.95,
        ),
        profile(
            "aligned-mixed",
            HistoricalEvidenceDirection.FAVORS_TEAM_A,
            HistoricalEvidenceDirection.FAVORS_TEAM_A,
            0.95,
            0.95,
        ),
        profile(
            "aligned-player-low",
            HistoricalEvidenceDirection.FAVORS_TEAM_B,
            HistoricalEvidenceDirection.FAVORS_TEAM_B,
            0.55,
            0.55,
        ),
        profile(
            "aligned-player-high",
            HistoricalEvidenceDirection.FAVORS_TEAM_A,
            HistoricalEvidenceDirection.FAVORS_TEAM_A,
            0.9,
            0.85,
        ),
    )

    ranked = prioritize_historical_trade_evidence_cases(
        compositions=compositions,
        evidence_profiles=profiles,
    )

    assert [row.transaction_id for row in ranked] == [
        "aligned-player-high",
        "aligned-player-low",
        "aligned-mixed",
        "conflicted-player",
    ]
    assert ranked[0].evidence_strength == 0.85


def test_real_kirk_freiermuth_case_is_research_conflicted_not_forced() -> None:
    kirk_freiermuth = profile(
        "862758969872125952",
        HistoricalEvidenceDirection.FAVORS_TEAM_A,
        HistoricalEvidenceDirection.FAVORS_TEAM_B,
        current_confidence=0.8,
        future_confidence=0.8,
    )
    assert classify_historical_evidence_alignment(kirk_freiermuth) == HistoricalEvidenceAlignment.CONFLICTED
