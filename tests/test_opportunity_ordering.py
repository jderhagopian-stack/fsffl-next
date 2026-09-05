from datetime import UTC, datetime

from fsffl.opportunity.models import (
    ActionAuthority,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)
from fsffl.opportunity.ordering import (
    ObjectiveDirection,
    OpportunityObjective,
    OrderedOpportunityPoint,
    authority_tier,
    dominates,
    pareto_front,
)


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _candidate(
    candidate_id: str,
    *,
    authority: ActionAuthority = ActionAuthority.MARKET_TEST_ONLY,
    evidence: EvidenceCompleteness = EvidenceCompleteness.COMPLETE,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id=candidate_id,
        kind=OpportunityKind.TRADE,
        focal_team_id="a",
        league_state_id="state-1",
        as_of=AS_OF,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=authority,
        evidence_completeness=evidence,
        search_model_version="test",
    )


def _point(candidate_id: str, wins: float, economics: float) -> OrderedOpportunityPoint:
    return OrderedOpportunityPoint(
        candidate=_candidate(candidate_id),
        objectives=(
            OpportunityObjective(
                name="expected_wins_delta",
                value=wins,
                direction=ObjectiveDirection.MAXIMIZE,
            ),
            OpportunityObjective(
                name="economic_net_delta",
                value=economics,
                direction=ObjectiveDirection.MAXIMIZE,
            ),
        ),
    )


def test_pareto_front_preserves_mixed_tradeoffs() -> None:
    win_now = _point("win-now", 0.8, -100.0)
    long_term = _point("long-term", 0.2, 300.0)

    assert not dominates(win_now, long_term)
    assert not dominates(long_term, win_now)
    assert pareto_front((win_now, long_term)) == (long_term, win_now)


def test_strictly_better_point_dominates() -> None:
    strong = _point("strong", 0.8, 100.0)
    weak = _point("weak", 0.4, 50.0)

    assert dominates(strong, weak)
    assert pareto_front((weak, strong)) == (strong,)


def test_pareto_comparison_requires_same_objectives_and_directions() -> None:
    left = _point("left", 0.5, 100.0)
    right = OrderedOpportunityPoint(
        candidate=_candidate("right"),
        objectives=(
            OpportunityObjective(
                name="expected_wins_delta",
                value=0.4,
                direction=ObjectiveDirection.MINIMIZE,
            ),
            OpportunityObjective(
                name="economic_net_delta",
                value=50.0,
                direction=ObjectiveDirection.MAXIMIZE,
            ),
        ),
    )

    try:
        dominates(left, right)
    except ValueError as exc:
        assert "directions" in str(exc)
    else:
        raise AssertionError("expected objective-direction mismatch")


def test_authority_tier_is_categorical_not_substantive_score() -> None:
    actionable = _candidate("a", authority=ActionAuthority.ACTIONABLE)
    market_test = _candidate("b", authority=ActionAuthority.MARKET_TEST_ONLY)
    diagnostic = _candidate(
        "c",
        authority=ActionAuthority.DIAGNOSTIC_ONLY,
        evidence=EvidenceCompleteness.PARTIAL,
    )

    assert authority_tier(actionable) > authority_tier(market_test) > authority_tier(diagnostic)
