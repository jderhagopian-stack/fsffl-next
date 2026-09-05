from datetime import UTC, datetime

from fsffl.analytics.models import AnalyticsContext
from fsffl.analytics.opportunity import (
    TradeOpportunityAnalyticsRecord,
    TradePartnerMetric,
    build_opportunity_analytics_view,
    build_trade_partner_analytics_view,
    rank_trade_partners,
)
from fsffl.opportunity.models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)
from fsffl.trade_decision import (
    NegotiationFeasibilityShape,
    SideDecisionShape,
    TradeNegotiationFeasibility,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
CONTEXT = AnalyticsContext(
    schema_version="1",
    league_id="l1",
    league_state_id="state-1",
    as_of=AS_OF,
    generated_at=AS_OF,
    lineage=(),
)


def _candidate(candidate_id: str, authority: ActionAuthority, *, focal="a", reasons=()):
    return OpportunityCandidate(
        candidate_id=candidate_id,
        kind=OpportunityKind.TRADE,
        focal_team_id=focal,
        league_state_id="state-1",
        as_of=AS_OF,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=authority,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reasons=tuple(reasons),
        search_model_version="test",
    )


def _negotiation(proposal_id: str, counterparty: str, shape: NegotiationFeasibilityShape):
    return TradeNegotiationFeasibility(
        proposal_id=proposal_id,
        focal_team_id="a",
        counterparty_team_id=counterparty,
        shape=shape,
        counterparty_decision_shape=(
            SideDecisionShape.UNIFORM_LOSS
            if shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED
            else SideDecisionShape.MIXED
        ),
    )


def test_opportunity_summary_preserves_action_tiers_and_reasons() -> None:
    candidates = (
        _candidate("c1", ActionAuthority.ACTIONABLE),
        _candidate(
            "c2",
            ActionAuthority.MARKET_TEST_ONLY,
            reasons=(CandidateReason.UNKNOWN_ACCEPTANCE,),
        ),
        _candidate(
            "c3",
            ActionAuthority.DIAGNOSTIC_ONLY,
            reasons=(CandidateReason.COUNTERPARTY_DOMINATED,),
        ),
    )
    view = build_opportunity_analytics_view(context=CONTEXT, candidates=candidates)

    assert view.authority_summary.total == 3
    assert view.authority_summary.actionable == 1
    assert view.authority_summary.market_test_only == 1
    assert view.authority_summary.diagnostic_only == 1
    assert {(item.reason, item.count) for item in view.reason_counts} == {
        (CandidateReason.UNKNOWN_ACCEPTANCE, 1),
        (CandidateReason.COUNTERPARTY_DOMINATED, 1),
    }


def test_trade_partner_view_keeps_unknown_acceptance_explicit() -> None:
    records = (
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("c1", ActionAuthority.MARKET_TEST_ONLY),
            counterparty_team_id="b",
            negotiation=_negotiation("c1", "b", NegotiationFeasibilityShape.MUTUAL_GAIN_CANDIDATE),
            pareto_front=True,
        ),
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("c2", ActionAuthority.DIAGNOSTIC_ONLY),
            counterparty_team_id="b",
            negotiation=_negotiation("c2", "b", NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED),
        ),
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("c3", ActionAuthority.MARKET_TEST_ONLY),
            counterparty_team_id="c",
            negotiation=_negotiation("c3", "c", NegotiationFeasibilityShape.MIXED),
        ),
    )
    view = build_trade_partner_analytics_view(
        context=CONTEXT,
        focal_team_id="a",
        records=records,
    )

    b = next(row for row in view.partners if row.counterparty_team_id == "b")
    assert b.evaluated_candidates == 2
    assert b.pareto_candidates == 1
    assert b.mutual_gain_candidates == 1
    assert b.counterparty_dominated_candidates == 1
    assert b.acceptance_unknown_candidates == 2
    assert b.acceptance_known_candidates == 0


def test_trade_partner_ranking_uses_explicit_requested_metric() -> None:
    records = (
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("b1", ActionAuthority.MARKET_TEST_ONLY),
            counterparty_team_id="b",
        ),
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("b2", ActionAuthority.MARKET_TEST_ONLY),
            counterparty_team_id="b",
        ),
        TradeOpportunityAnalyticsRecord(
            candidate=_candidate("c1", ActionAuthority.ACTIONABLE),
            counterparty_team_id="c",
        ),
    )
    view = build_trade_partner_analytics_view(
        context=CONTEXT,
        focal_team_id="a",
        records=records,
    )

    evaluated = rank_trade_partners(view, metric=TradePartnerMetric.EVALUATED_CANDIDATES)
    actionable = rank_trade_partners(view, metric=TradePartnerMetric.ACTIONABLE_CANDIDATES)

    assert [row.counterparty_team_id for row in evaluated.rows] == ["b", "c"]
    assert [row.counterparty_team_id for row in actionable.rows] == ["c", "b"]
