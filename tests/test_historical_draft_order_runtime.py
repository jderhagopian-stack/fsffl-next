from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_draft_order import (
    HistoricalDraftOrderScenarioEvidence,
    HistoricalDraftOrderStatus,
    produce_historical_draft_order,
)
from fsffl.state.draft_order_policy import DraftOrderPolicyEvidence
from fsffl.state.models import Provenance, ProviderRef
from fsffl.team_utility.draft_order import DraftOrderScenario, DraftSlotAssignment


AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def _policy(*, mechanism="explicit_scenarios", available_at=AS_OF):
    return DraftOrderPolicyEvidence(
        league_id="league-generic",
        draft_season=2027,
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=available_at,
        policy_id="rookie-order",
        version="3",
        mechanism=mechanism,
        description="verified league-specific rookie draft ordering rule",
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


def test_producer_accepts_complete_explicit_scenarios_under_resolved_policy():
    produced = produce_historical_draft_order(
        policies=(_policy(),),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        scenario_evidence=_scenarios(),
    )
    assert produced.status == HistoricalDraftOrderStatus.PRODUCED
    assert produced.result is not None
    assert produced.result.rule_policy_version == "rookie-order:3"
    assert produced.result.slot_distribution_for_team(
        "a",
        league_rules=type("Rules", (), {"team_count": 2})(),
    ) == ((1, 0.4), (2, 0.6))


def test_producer_fails_closed_when_policy_was_not_knowable():
    result = produce_historical_draft_order(
        policies=(_policy(available_at=datetime(2026, 10, 1, tzinfo=UTC)),),
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
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
            scenario_evidence=future,
        )

    wrong_league = _scenarios().model_copy(update={"league_id": "other"})
    with pytest.raises(ValueError, match="requested league"):
        produce_historical_draft_order(
            policies=(_policy(),),
            league_id="league-generic",
            draft_season=2027,
            as_of=AS_OF,
            scenario_evidence=wrong_league,
        )
