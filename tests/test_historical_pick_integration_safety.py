from datetime import UTC, datetime

import pytest

from fsffl.state.models import DraftPick, LeagueRules
from fsffl.value.historical_pick import (
    HistoricalDraftSlotObservation,
    HistoricalPickCoordinateEvidence,
    HistoricalSlotProbability,
    reconstruct_historical_pick_coordinate,
)
from fsffl.value.models import ValueDistribution, ValueScale


SCALE = ValueScale(scale_id="test-dynasty", version="1", unit_label="test units")
OTHER_SCALE = ValueScale(scale_id="other", version="1", unit_label="other units")
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def _rules(team_count: int = 10) -> LeagueRules:
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=4,
        lineup=(),
        scoring=(),
    )


def _pick() -> DraftPick:
    return DraftPick(
        pick_id="pick-2027-2",
        league_id="league-generic",
        season=2027,
        round=2,
        original_team_id="team-a",
    )


def _obs(*, season: int, round: int = 2, slot: int = 1, mean: float = 100.0, scale=SCALE, source=None):
    label = source or f"source-{season}-{round}-{slot}-{scale.scale_id}"
    return HistoricalDraftSlotObservation(
        draft_season=season,
        round=round,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=5),
        scale=scale,
        available_at=datetime(2025, 6, 1, tzinfo=UTC),
        model_version=f"model-{label}",
        provenance=f"provenance-{label}",
    )


def test_exact_historical_slot_cannot_exceed_league_size() -> None:
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=AS_OF,
        observations=(_obs(season=2024, slot=1),),
        slot_probabilities=(),
        exact_slot_in_round=11,
        exact_slot_known_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="exact slot exceeds league team count"):
        reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(10), scale=SCALE)


def test_unrelated_observations_do_not_inflate_pick_evidence_metadata() -> None:
    contributing = _obs(season=2025, slot=1, mean=100, source="contributing")
    wrong_scale = _obs(season=2024, slot=1, mean=999, scale=OTHER_SCALE, source="wrong-scale")
    other_round = _obs(season=2023, round=3, slot=1, mean=999, source="other-round")
    separate_slot = _obs(season=2022, slot=8, mean=10, source="separate-slot")
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=AS_OF,
        observations=(contributing, wrong_scale, other_round, separate_slot),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=1,
                probability=1.0,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-prob-v1",
                provenance="probability-source",
            ),
        ),
    )

    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(), scale=SCALE)

    assert result.status == "RECONSTRUCTED"
    assert result.evidence_quality == "LOW"
    assert result.used_draft_seasons == (2025,)
    assert "provenance-contributing" in result.provenance
    assert "provenance-wrong-scale" not in result.provenance
    assert "provenance-other-round" not in result.provenance
    assert "provenance-separate-slot" not in result.provenance
    assert result.estimate is not None
    assert "model-contributing" in result.estimate.class_strength_model_version
    assert "wrong-scale" not in result.estimate.class_strength_model_version
    assert "other-round" not in result.estimate.class_strength_model_version
    assert "separate-slot" not in result.estimate.class_strength_model_version


def test_dominance_pool_metadata_includes_only_rows_that_shape_used_slot() -> None:
    # Slot 1 is pulled into a PAVA block with slot 2, so slot 2 genuinely contributes
    # to the reconstructed slot-1 coordinate. Slot 8 remains a separate block and must
    # not inflate the slot-1 evidence metadata.
    slot1 = _obs(season=2025, slot=1, mean=80, source="slot1")
    slot2 = _obs(season=2024, slot=2, mean=100, source="slot2-pooled")
    slot8 = _obs(season=2023, slot=8, mean=10, source="slot8-unrelated")
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=AS_OF,
        observations=(slot1, slot2, slot8),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=1,
                probability=1.0,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-prob-v1",
                provenance="probability-source",
            ),
        ),
    )

    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(), scale=SCALE)

    assert result.used_draft_seasons == (2024, 2025)
    assert result.evidence_quality == "MEDIUM"
    assert "provenance-slot1" in result.provenance
    assert "provenance-slot2-pooled" in result.provenance
    assert "provenance-slot8-unrelated" not in result.provenance
    assert "structural draft-position dominance projection" in result.provenance
