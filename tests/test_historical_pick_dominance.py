from datetime import UTC, datetime

import pytest

from fsffl.state.models import DraftPick, LeagueRules
from fsffl.value.historical_pick import (
    HistoricalDraftSlotObservation,
    HistoricalPickCoordinateEvidence,
    reconstruct_historical_pick_coordinate,
)
from fsffl.value.models import ValueDistribution, ValueScale


SCALE = ValueScale(scale_id="test-dynasty", version="1", unit_label="units")
AS_OF = datetime(2026, 7, 11, 19, 10, 43, tzinfo=UTC)


def rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=20,
        rookie_draft_rounds=3,
        lineup=(),
        scoring=(),
    )


def obs(round_number: int, slot: int, mean: float) -> HistoricalDraftSlotObservation:
    return HistoricalDraftSlotObservation(
        draft_season=2025,
        round=round_number,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=10),
        scale=SCALE,
        available_at=datetime(2025, 6, 1, tzinfo=UTC),
        model_version="frozen-2025",
        provenance="PIT frozen draft value",
    )


def exact_pick(round_number: int, slot: int, observations: tuple[HistoricalDraftSlotObservation, ...]):
    pick = DraftPick(
        pick_id=f"2026-r{round_number}-{slot}",
        league_id="league",
        season=2026,
        round=round_number,
        original_team_id="team",
    )
    evidence = HistoricalPickCoordinateEvidence(
        pick=pick,
        as_of=AS_OF,
        observations=observations,
        slot_probabilities=(),
        exact_slot_in_round=slot,
        exact_slot_known_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    return reconstruct_historical_pick_coordinate(evidence, league_rules=rules(), scale=SCALE)


def test_later_pick_cannot_be_more_valuable_than_earlier_pick_within_round():
    observations = (
        obs(3, 4, 90),
        obs(3, 10, 110),
    )
    early = exact_pick(3, 4, observations)
    late = exact_pick(3, 10, observations)

    assert early.estimate is not None
    assert late.estimate is not None
    assert early.estimate.distribution.mean == pytest.approx(100.0)
    assert late.estimate.distribution.mean == pytest.approx(100.0)
    assert early.estimate.distribution.mean >= late.estimate.distribution.mean
    assert "structural draft-position dominance projection" in early.provenance


def test_dominance_constraint_applies_across_round_boundary():
    observations = (
        obs(2, 12, 100),
        obs(3, 4, 120),
    )
    earlier_overall = exact_pick(2, 12, observations)
    later_overall = exact_pick(3, 4, observations)

    assert earlier_overall.estimate is not None
    assert later_overall.estimate is not None
    assert earlier_overall.estimate.distribution.mean == pytest.approx(110.0)
    assert later_overall.estimate.distribution.mean == pytest.approx(110.0)
    assert earlier_overall.estimate.distribution.mean >= later_overall.estimate.distribution.mean


def test_already_monotone_evidence_is_not_modified_or_relabelled():
    observations = (
        obs(2, 12, 120),
        obs(3, 4, 100),
        obs(3, 10, 80),
    )
    result = exact_pick(3, 4, observations)

    assert result.estimate is not None
    assert result.estimate.distribution.mean == pytest.approx(100.0)
    assert "structural draft-position dominance projection" not in result.provenance
