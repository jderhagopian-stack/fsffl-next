from datetime import UTC, datetime

import pytest

from fsffl.state.models import LeagueRules
from fsffl.team_utility.draft_order_metric import (
    DraftMetricDirection,
    DraftMetricScenario,
    DraftMetricScenarioSet,
    TeamDraftMetric,
    rank_metric_scenarios_to_draft_order,
)


RULES = LeagueRules(
    team_count=3,
    roster_size=20,
    rookie_draft_rounds=3,
    lineup=(),
    scoring=(),
)


def _evidence(*, tie=False):
    values = (100.0, 100.0, 140.0) if tie else (90.0, 110.0, 140.0)
    return DraftMetricScenarioSet(
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        scenarios=(
            DraftMetricScenario(
                probability=1.0,
                metrics=tuple(
                    TeamDraftMetric(team_id=team, value=value)
                    for team, value in zip(("a", "b", "c"), values, strict=True)
                ),
            ),
        ),
        metric_id="league-defined-metric",
        model_version="metric-sim-v1",
        provenance="point-in-time simulated metric evidence",
    )


def test_lower_metric_can_map_to_earlier_pick_when_policy_says_so():
    scenarios = rank_metric_scenarios_to_draft_order(
        _evidence(),
        league_rules=RULES,
        direction=DraftMetricDirection.LOWER_VALUE_EARLIER_PICK,
    )
    assert [(row.team_id, row.slot_in_round) for row in scenarios[0].assignments] == [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ]


def test_direction_is_explicit_not_assumed():
    scenarios = rank_metric_scenarios_to_draft_order(
        _evidence(),
        league_rules=RULES,
        direction=DraftMetricDirection.HIGHER_VALUE_EARLIER_PICK,
    )
    assert [(row.team_id, row.slot_in_round) for row in scenarios[0].assignments] == [
        ("c", 1),
        ("b", 2),
        ("a", 3),
    ]


def test_ties_fail_closed_without_league_tiebreak_evidence():
    with pytest.raises(ValueError, match="tiebreak evidence"):
        rank_metric_scenarios_to_draft_order(
            _evidence(tie=True),
            league_rules=RULES,
            direction=DraftMetricDirection.LOWER_VALUE_EARLIER_PICK,
        )


def test_metric_evidence_must_cover_every_team():
    smaller = _evidence().model_copy(
        update={
            "scenarios": (
                DraftMetricScenario(
                    probability=1.0,
                    metrics=(
                        TeamDraftMetric(team_id="a", value=90),
                        TeamDraftMetric(team_id="b", value=110),
                    ),
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="every league team"):
        rank_metric_scenarios_to_draft_order(
            smaller,
            league_rules=RULES,
            direction=DraftMetricDirection.LOWER_VALUE_EARLIER_PICK,
        )
