from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_pick import build_slot_forecast_from_draft_order
from fsffl.state.models import DraftPick, LeagueRules
from fsffl.team_utility.draft_order import (
    DraftOrderScenario,
    DraftOrderSimulationResult,
    DraftSlotAssignment,
)


def _rules(team_count=4, rounds=3):
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=rounds,
        lineup=(),
        scoring=(),
    )


def _pick(league_id="league-generic", season=2027, round=2):
    return DraftPick(
        pick_id="pick-2027-r2-a",
        league_id=league_id,
        season=season,
        round=round,
        original_team_id="a",
    )


def _result(league_id="league-generic", season=2027):
    return DraftOrderSimulationResult(
        league_id=league_id,
        draft_season=season,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        scenarios=(
            DraftOrderScenario(
                probability=0.25,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=1),
                    DraftSlotAssignment(team_id="b", slot_in_round=2),
                ),
            ),
            DraftOrderScenario(
                probability=0.75,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=2),
                    DraftSlotAssignment(team_id="b", slot_in_round=1),
                ),
            ),
        ),
        model_version="draft-order-sim-v2",
        rule_policy_version="explicit-league-policy-v3",
        provenance="point-in-time simulation plus explicit league draft-order policy",
    )


def test_bridge_preserves_simulation_distribution_and_provenance():
    forecast = build_slot_forecast_from_draft_order(
        pick=_pick(),
        result=_result(),
        league_rules=_rules(),
    )

    assert forecast.pick_id == "pick-2027-r2-a"
    assert [(row.slot_in_round, row.probability) for row in forecast.probabilities] == [
        (1, 0.25),
        (2, 0.75),
    ]
    assert all(row.evidence_as_of == datetime(2026, 9, 1, tzinfo=UTC) for row in forecast.probabilities)
    assert all(row.model_version == "draft-order-sim-v2+explicit-league-policy-v3" for row in forecast.probabilities)
    assert all("explicit league draft-order policy" in row.provenance for row in forecast.probabilities)


def test_bridge_rejects_cross_league_or_wrong_season_evidence():
    with pytest.raises(ValueError, match="pick league"):
        build_slot_forecast_from_draft_order(
            pick=_pick(league_id="league-a"),
            result=_result(league_id="league-b"),
            league_rules=_rules(),
        )

    with pytest.raises(ValueError, match="pick draft season"):
        build_slot_forecast_from_draft_order(
            pick=_pick(season=2028),
            result=_result(season=2027),
            league_rules=_rules(),
        )


def test_bridge_rejects_pick_outside_configured_rookie_rounds():
    with pytest.raises(ValueError, match="outside the configured rookie draft"):
        build_slot_forecast_from_draft_order(
            pick=_pick(round=4),
            result=_result(),
            league_rules=_rules(rounds=3),
        )
