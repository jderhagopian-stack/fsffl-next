from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_draft_order import (
    HistoricalDraftOrderScenarioEvidence,
    HistoricalDraftOrderStatus,
    produce_historical_draft_order,
)
from fsffl.state.draft_order_policy import DraftOrderPolicyEvidence, DraftOrderPolicyParameter
from fsffl.state.models import LeagueRules, Provenance, ProviderRef
from fsffl.team_utility.draft_order import DraftOrderScenario, DraftSlotAssignment
from fsffl.team_utility.draft_order_metric import DraftMetricScenario, DraftMetricScenarioSet, TeamDraftMetric


AS_OF = datetime(2026, 9, 1, tzinfo=UTC)
RULES = LeagueRules(team_count=2, roster_size=20, rookie_draft_rounds=3, lineup=(), scoring=())


def _policy(*, mechanism="explicit_scenarios", available_at=AS_OF, parameters=()):
    return DraftOrderPolicyEvidence(
        league_id="league-generic",
        draft_season=2027,
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=available_at,
        policy_id="rookie-order",
        version="3",
        mechanism=mechanism,
        description="verified league-specific rookie draft ordering rule",
        parameters=parameters,
        provenance=Provenance(
            source="verified-league-config",
            retrieved_at=available_at,
            effective_at=datetime(2026, 1, 1, tzinfo=UTC),
            provider_ref=ProviderRef(provider="config", external_id="rookie-order"),
            source_version="3",
        ),
    )


def _scenarios():
    return HistoricalDraftOrderScenarioEvidence(
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        scenarios=(
            DraftOrderScenario(
                probability=0.4,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=1),
                    DraftSlotAssignment(team_id="b", slot_in_round=2),
                ),
            ),
            DraftOrderScenario(
                probability=0.6,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=2),
                    DraftSlotAssignment(team_id="b", slot_in_round=1),
                ),
            ),
        ),
        model_version="historical-scenario-v1",
        provenance="point-in-time competitive scenario evidence",
    )


def _metric_evidence():
    return DraftMetricScenarioSet(
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        scenarios=(
            DraftMetricScenario(
                probability=1.0,
                metrics=(
                    TeamDraftMetric(team_id="a", value=95.0),
                    TeamDraftMetric(team_id="b", value=120.0),
                ),
            ),
        ),
        metric_id="max_pf",
        model_version="historical-max-pf-v1",
        provenance="point-in-time simulated max-pf evidence",
    )


def test_producer_accepts_complete_explicit_scenarios_under_resolved_policy():
    produced = produce_historical_draft_order(
        policies=(_policy(),),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        league_rules=RULES,
        scenario_evidence=_scenarios(),
    )
    assert produced.status == HistoricalDraftOrderStatus.PRODUCED
    assert produced.result is not None
    assert produced.result.rule_policy_version == "rookie-order:3"
    assert produced.result.slot_distribution_for_team("a", league_rules=RULES) == ((1, 0.4), (2, 0.6))


def test_ranked_metric_policy_uses_explicit_metric_and_direction():
    policy = _policy(
        mechanism="ranked_metric",
        parameters=(
            DraftOrderPolicyParameter(name="metric_id", value="max_pf"),
            DraftOrderPolicyParameter(name="direction", value="lower_value_earlier_pick"),
        ),
    )
    produced = produce_historical_draft_order(
        policies=(policy,),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        league_rules=RULES,
        metric_evidence=_metric_evidence(),
    )
    assert produced.status == HistoricalDraftOrderStatus.PRODUCED
    assert produced.result is not None
    assert produced.result.slot_distribution_for_team("a", league_rules=RULES) == ((1, 1.0),)


def test_ranked_metric_policy_rejects_mismatched_metric():
    policy = _policy(
        mechanism="ranked_metric",
        parameters=(
            DraftOrderPolicyParameter(name="metric_id", value="wins"),
            DraftOrderPolicyParameter(name="direction", value="lower_value_earlier_pick"),
        ),
    )
    produced = produce_historical_draft_order(
        policies=(policy,),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        league_rules=RULES,
        metric_evidence=_metric_evidence(),
    )
    assert produced.status == HistoricalDraftOrderStatus.INVALID_POLICY_PARAMETERS
    assert produced.result is None


def test_producer_fails_closed_when_policy_was_not_knowable():
    result = produce_historical_draft_order(
        policies=(_policy(available_at=datetime(2026, 10, 1, tzinfo=UTC)),),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        league_rules=RULES,
        scenario_evidence=_scenarios(),
    )
    assert result.status == HistoricalDraftOrderStatus.MISSING_POLICY_EVIDENCE
    assert result.result is None


def test_producer_does_not_guess_unsupported_custom_mechanism():
    result = produce_historical_draft_order(
        policies=(_policy(mechanism="max_pf_then_playoff_finish"),),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        league_rules=RULES,
        scenario_evidence=_scenarios(),
    )
    assert result.status == HistoricalDraftOrderStatus.UNSUPPORTED_POLICY_MECHANISM
    assert result.result is None


def test_producer_rejects_future_or_cross_league_scenario_evidence():
    future = _scenarios().model_copy(update={"as_of": datetime(2026, 9, 2, tzinfo=UTC)})
    with pytest.raises(ValueError, match="cannot postdate"):
        produce_historical_draft_order(
            policies=(_policy(),),
            league_id="league-generic",
            draft_season=2027,
            as_of=AS_OF,
            league_rules=RULES,
            scenario_evidence=future,
        )

    wrong_league = _scenarios().model_copy(update={"league_id": "other"})
    with pytest.raises(ValueError, match="requested league"):
        produce_historical_draft_order(
            policies=(_policy(),),
            league_id="league-generic",
            draft_season=2027,
            as_of=AS_OF,
            league_rules=RULES,
            scenario_evidence=wrong_league,
        )
