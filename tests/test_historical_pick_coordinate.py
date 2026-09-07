from datetime import UTC, datetime

import pytest

from fsffl.state.models import DraftPick, LeagueRules
from fsffl.value.historical_pick import (
    HistoricalDraftSlotObservation,
    HistoricalPickCoordinateEvidence,
    HistoricalSlotProbability,
    HorizonAdjustment,
    reconstruct_historical_pick_coordinate,
)
from fsffl.value.models import ValueDistribution, ValueScale


def _rules(team_count=10, rounds=4):
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=rounds,
        lineup=(),
        scoring=(),
    )


def _pick(round=2, season=2027):
    return DraftPick(
        pick_id=f"pick-{season}-{round}",
        league_id="league-generic",
        season=season,
        round=round,
        original_team_id="team-a",
    )


def _obs(season, slot, mean, available_at=None):
    return HistoricalDraftSlotObservation(
        draft_season=season,
        round=2,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=10),
        scale=ValueScale.FSFFL,
        available_at=available_at or datetime(2025, 6, 1, tzinfo=UTC),
        model_version=f"draft-{season}",
        provenance=f"frozen evidence {season}",
    )


def test_coordinate_derives_legal_slot_range_from_league_rules():
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(_obs(2024, 1, 100), _obs(2025, 1, 120)),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=11,
                probability=1.0,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-v1",
                provenance="generic state model",
            ),
        ),
    )
    with pytest.raises(ValueError, match="exceeds league team count"):
        reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(team_count=10), scale=ValueScale.FSFFL)


def test_future_draft_observation_is_rejected():
    with pytest.raises(ValueError, match="future draft observations"):
        HistoricalPickCoordinateEvidence(
            pick=_pick(),
            as_of=datetime(2026, 9, 1, tzinfo=UTC),
            observations=(
                _obs(2026, 1, 120, available_at=datetime(2027, 1, 1, tzinfo=UTC)),
            ),
            slot_probabilities=(),
        )


def test_exact_slot_cannot_be_used_before_it_was_known():
    with pytest.raises(ValueError, match="not knowable"):
        HistoricalPickCoordinateEvidence(
            pick=_pick(),
            as_of=datetime(2026, 5, 1, tzinfo=UTC),
            observations=(_obs(2024, 3, 100),),
            slot_probabilities=(),
            exact_slot_in_round=3,
            exact_slot_known_at=datetime(2026, 8, 1, tzinfo=UTC),
        )


def test_unresolved_pick_requires_explicit_slot_probabilities():
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(_obs(2024, 1, 100),),
        slot_probabilities=(),
    )
    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(), scale=ValueScale.FSFFL)
    assert result.estimate is None
    assert result.status == "NOT_RECONSTRUCTED_MISSING_SLOT_PROBABILITY_EVIDENCE"


def test_missing_slot_value_fails_closed_without_round_median_backfill():
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(_obs(2024, 1, 100), _obs(2025, 1, 120)),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=2,
                probability=1.0,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-v1",
                provenance="generic state model",
            ),
        ),
    )
    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(), scale=ValueScale.FSFFL)
    assert result.estimate is None
    assert result.missing_slots == (2,)


def test_coordinate_reuses_existing_pick_mixture_and_averages_prior_slot_evidence():
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(
            _obs(2024, 1, 100),
            _obs(2025, 1, 120),
            _obs(2024, 2, 80),
            _obs(2025, 2, 100),
        ),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=1,
                probability=0.25,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-v1",
                provenance="generic state model",
            ),
            HistoricalSlotProbability(
                slot_in_round=2,
                probability=0.75,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-v1",
                provenance="generic state model",
            ),
        ),
    )
    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(), scale=ValueScale.FSFFL)
    assert result.status == "RECONSTRUCTED"
    assert result.evidence_quality == "MEDIUM"
    assert result.estimate is not None
    assert result.estimate.distribution.mean == pytest.approx(95.0)


def test_horizon_adjustment_has_no_default_and_must_be_explicit():
    base = HistoricalPickCoordinateEvidence(
        pick=_pick(season=2027),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(_obs(2024, 1, 100), _obs(2025, 1, 100)),
        slot_probabilities=(
            HistoricalSlotProbability(
                slot_in_round=1,
                probability=1.0,
                evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
                model_version="slot-v1",
                provenance="generic state model",
            ),
        ),
    )
    no_adjustment = reconstruct_historical_pick_coordinate(base, league_rules=_rules(), scale=ValueScale.FSFFL)
    assert no_adjustment.estimate.distribution.mean == pytest.approx(100.0)

    explicit = base.model_copy(update={
        "horizon_adjustment": HorizonAdjustment(
            seasons_to_realization=1,
            factor=0.9,
            model_version="research-horizon-v1",
            provenance="bounded research sensitivity",
        )
    })
    adjusted = reconstruct_historical_pick_coordinate(explicit, league_rules=_rules(), scale=ValueScale.FSFFL)
    assert adjusted.estimate.distribution.mean == pytest.approx(90.0)


def test_pick_outside_configured_rookie_rounds_is_excluded():
    evidence = HistoricalPickCoordinateEvidence(
        pick=_pick(round=4),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        observations=(),
        slot_probabilities=(),
    )
    result = reconstruct_historical_pick_coordinate(evidence, league_rules=_rules(rounds=3), scale=ValueScale.FSFFL)
    assert result.status == "EXCLUDED_OUTSIDE_LEAGUE_ROOKIE_DRAFT"
