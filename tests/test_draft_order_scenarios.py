from datetime import UTC, datetime

import pytest

from fsffl.state.models import LeagueRules
from fsffl.team_utility.draft_order import (
    DraftOrderScenario,
    DraftOrderSimulationResult,
    DraftSlotAssignment,
)


def _rules(team_count=4):
    return LeagueRules(
        team_count=team_count,
        roster_size=20,
        rookie_draft_rounds=3,
        lineup=(),
        scoring=(),
    )


def test_scenarios_marginalize_to_team_slot_distribution_without_rule_assumption():
    result = DraftOrderSimulationResult(
        league_id="league-generic",
        draft_season=2027,
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
        model_version="draft-order-sim-v1",
        rule_policy_version="league-rule-policy-v1",
        provenance="point-in-time simulation plus explicit league draft-order rules",
    )

    assert result.slot_distribution_for_team("a", league_rules=_rules()) == (
        (1, 0.25),
        (2, 0.75),
    )


def test_scenario_does_not_allow_two_teams_to_share_one_slot():
    with pytest.raises(ValueError, match="slots must be unique"):
        DraftOrderScenario(
            probability=1.0,
            assignments=(
                DraftSlotAssignment(team_id="a", slot_in_round=1),
                DraftSlotAssignment(team_id="b", slot_in_round=1),
            ),
        )


def test_distribution_fails_if_requested_team_is_missing_from_any_scenario():
    result = DraftOrderSimulationResult(
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        scenarios=(
            DraftOrderScenario(
                probability=1.0,
                assignments=(DraftSlotAssignment(team_id="b", slot_in_round=1),),
            ),
        ),
        model_version="draft-order-sim-v1",
        rule_policy_version="league-rule-policy-v1",
        provenance="explicit scenario",
    )
    with pytest.raises(ValueError, match="assign the requested team exactly once"):
        result.slot_distribution_for_team("a", league_rules=_rules())


def test_distribution_uses_league_team_count_not_hardcoded_slot_limit():
    result = DraftOrderSimulationResult(
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        scenarios=(
            DraftOrderScenario(
                probability=1.0,
                assignments=(DraftSlotAssignment(team_id="a", slot_in_round=5),),
            ),
        ),
        model_version="draft-order-sim-v1",
        rule_policy_version="league-rule-policy-v1",
        provenance="explicit scenario",
    )
    with pytest.raises(ValueError, match="exceeds league team count"):
        result.slot_distribution_for_team("a", league_rules=_rules(team_count=4))
