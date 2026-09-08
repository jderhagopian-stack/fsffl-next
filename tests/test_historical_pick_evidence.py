from datetime import UTC, datetime

import pytest

from fsffl.state.models import DraftPick, LeagueRules
from fsffl.value.historical_pick import HistoricalSlotProbability
from fsffl.value.historical_pick_evidence import (
    FrozenDraftedAssetValue,
    HistoricalTeamDraftSlotForecast,
    build_draft_slot_observations,
    build_historical_pick_evidence,
)
from fsffl.value.models import ValueDistribution, ValueScale


SCALE = ValueScale(scale_id="test-dynasty", version="1", unit_label="test units")


def _rules(team_count=10, rounds=4):
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=rounds,
        lineup=(),
        scoring=(),
    )


def _pick():
    return DraftPick(
        pick_id="pick-2027-r2-team-a",
        league_id="league-generic",
        season=2027,
        round=2,
        original_team_id="team-a",
    )


def _frozen(slot, mean, *, season=2025, available_at=None):
    return FrozenDraftedAssetValue(
        draft_season=season,
        round=2,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=5),
        scale=SCALE,
        available_at=available_at or datetime(2025, 6, 1, tzinfo=UTC),
        model_version=f"frozen-{season}",
        provenance=f"frozen draft evidence {season}",
    )


def test_builder_filters_future_observations_instead_of_leaking_them():
    rows = build_draft_slot_observations(
        (
            _frozen(1, 100, season=2024),
            _frozen(1, 130, season=2026, available_at=datetime(2027, 1, 1, tzinfo=UTC)),
        ),
        league_rules=_rules(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert len(rows) == 1
    assert rows[0].draft_season == 2024


def test_builder_derives_legal_slot_range_from_league_rules():
    with pytest.raises(ValueError, match="exceeds league team count"):
        build_draft_slot_observations(
            (_frozen(11, 100),),
            league_rules=_rules(team_count=10),
            as_of=datetime(2026, 9, 1, tzinfo=UTC),
        )


def test_builder_does_not_impute_missing_slots():
    rows = build_draft_slot_observations(
        (_frozen(1, 100), _frozen(3, 80)),
        league_rules=_rules(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert [row.slot_in_round for row in rows] == [1, 3]


def test_slot_forecast_must_match_pick_and_historical_cutoff():
    probability = HistoricalSlotProbability(
        slot_in_round=1,
        probability=1.0,
        evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
        model_version="slot-v1",
        provenance="upstream historical simulation",
    )
    wrong = HistoricalTeamDraftSlotForecast(
        pick_id="other-pick",
        as_of=datetime(2026, 8, 1, tzinfo=UTC),
        probabilities=(probability,),
    )
    with pytest.raises(ValueError, match="requested pick"):
        build_historical_pick_evidence(
            pick=_pick(),
            as_of=datetime(2026, 9, 1, tzinfo=UTC),
            league_rules=_rules(),
            drafted_asset_values=(_frozen(1, 100),),
            slot_forecast=wrong,
        )


def test_exact_slot_suppresses_slot_forecast_without_replacing_value_evidence():
    probability = HistoricalSlotProbability(
        slot_in_round=2,
        probability=1.0,
        evidence_as_of=datetime(2026, 8, 1, tzinfo=UTC),
        model_version="slot-v1",
        provenance="upstream historical simulation",
    )
    forecast = HistoricalTeamDraftSlotForecast(
        pick_id=_pick().pick_id,
        as_of=datetime(2026, 8, 1, tzinfo=UTC),
        probabilities=(probability,),
    )
    evidence = build_historical_pick_evidence(
        pick=_pick(),
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        league_rules=_rules(),
        drafted_asset_values=(_frozen(1, 100),),
        slot_forecast=forecast,
        exact_slot_in_round=1,
        exact_slot_known_at=datetime(2026, 8, 15, tzinfo=UTC),
    )
    assert evidence.slot_probabilities == ()
    assert evidence.exact_slot_in_round == 1
    assert [row.slot_in_round for row in evidence.observations] == [1]
