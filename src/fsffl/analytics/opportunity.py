from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.opportunity.models import ActionAuthority, CandidateReason, OpportunityCandidate, OpportunityKind
from fsffl.state.models import FrozenModel
from fsffl.trade_decision import (
    AcceptanceModelStatus,
    NegotiationFeasibilityShape,
    TradeNegotiationFeasibility,
)

from .models import AnalyticsContext


class TradeOpportunityAnalyticsRecord(FrozenModel):
    candidate: OpportunityCandidate
    counterparty_team_id: str
    negotiation: TradeNegotiationFeasibility | None = None
    pareto_front: bool = False

    @model_validator(mode="after")
    def validate_record(self) -> "TradeOpportunityAnalyticsRecord":
        if not self.counterparty_team_id.strip():
            raise ValueError("counterparty_team_id cannot be blank")
        if self.candidate.kind not in {
            OpportunityKind.TRADE,
            OpportunityKind.SHOP,
            OpportunityKind.PRICE_DISCOVERY,
        }:
            raise ValueError("trade opportunity analytics requires trade-like candidate")
        if self.counterparty_team_id == self.candidate.focal_team_id:
            raise ValueError("counterparty cannot equal focal team")
        if self.negotiation is not None:
            if self.negotiation.focal_team_id != self.candidate.focal_team_id:
                raise ValueError("negotiation focal team must match candidate")
            if self.negotiation.counterparty_team_id != self.counterparty_team_id:
                raise ValueError("negotiation counterparty must match analytics record")
        return self


class OpportunityAuthoritySummary(FrozenModel):
    total: int
    actionable: int
    market_test_only: int
    diagnostic_only: int
    none: int

    @model_validator(mode="after")
    def validate_counts(self) -> "OpportunityAuthoritySummary":
        values = (self.total, self.actionable, self.market_test_only, self.diagnostic_only, self.none)
        if any(value < 0 for value in values):
            raise ValueError("opportunity summary counts cannot be negative")
        if self.actionable + self.market_test_only + self.diagnostic_only + self.none != self.total:
            raise ValueError("opportunity authority counts must sum to total")
        return self


class CandidateReasonCount(FrozenModel):
    reason: CandidateReason
    count: int


class OpportunityAnalyticsView(FrozenModel):
    context: AnalyticsContext
    candidates: tuple[OpportunityCandidate, ...]
    authority_summary: OpportunityAuthoritySummary
    reason_counts: tuple[CandidateReasonCount, ...]
    view_model_version: str = "next7-opportunity-view-v1"


class TradePartnerAnalyticsRow(FrozenModel):
    counterparty_team_id: str
    evaluated_candidates: int
    actionable_candidates: int
    market_test_candidates: int
    diagnostic_candidates: int
    pareto_candidates: int
    mutual_gain_candidates: int
    counterparty_dominated_candidates: int
    acceptance_known_candidates: int
    acceptance_unknown_candidates: int

    @model_validator(mode="after")
    def validate_row(self) -> "TradePartnerAnalyticsRow":
        if not self.counterparty_team_id.strip():
            raise ValueError("trade partner team id cannot be blank")
        counts = (
            self.evaluated_candidates,
            self.actionable_candidates,
            self.market_test_candidates,
            self.diagnostic_candidates,
            self.pareto_candidates,
            self.mutual_gain_candidates,
            self.counterparty_dominated_candidates,
            self.acceptance_known_candidates,
            self.acceptance_unknown_candidates,
        )
        if any(value < 0 for value in counts):
            raise ValueError("trade partner counts cannot be negative")
        return self


class TradePartnerAnalyticsView(FrozenModel):
    context: AnalyticsContext
    focal_team_id: str
    partners: tuple[TradePartnerAnalyticsRow, ...]
    view_model_version: str = "next7-trade-partner-view-v1"


class TradePartnerMetric(StrEnum):
    EVALUATED_CANDIDATES = "evaluated_candidates"
    ACTIONABLE_CANDIDATES = "actionable_candidates"
    MARKET_TEST_CANDIDATES = "market_test_candidates"
    PARETO_CANDIDATES = "pareto_candidates"
    MUTUAL_GAIN_CANDIDATES = "mutual_gain_candidates"


class RankedTradePartner(FrozenModel):
    rank: int
    counterparty_team_id: str
    value: int


class TradePartnerRanking(FrozenModel):
    metric: TradePartnerMetric
    rows: tuple[RankedTradePartner, ...]
    ranking_model_version: str = "next7-trade-partner-named-metric-v1"


def build_opportunity_analytics_view(
    *,
    context: AnalyticsContext,
    candidates: tuple[OpportunityCandidate, ...],
    view_model_version: str = "next7-opportunity-view-v1",
) -> OpportunityAnalyticsView:
    counts = {authority: 0 for authority in ActionAuthority}
    reason_counts = {reason: 0 for reason in CandidateReason}
    for candidate in candidates:
        counts[candidate.action_authority] += 1
        for reason in candidate.reasons:
            reason_counts[reason] += 1

    summary = OpportunityAuthoritySummary(
        total=len(candidates),
        actionable=counts[ActionAuthority.ACTIONABLE],
        market_test_only=counts[ActionAuthority.MARKET_TEST_ONLY],
        diagnostic_only=counts[ActionAuthority.DIAGNOSTIC_ONLY],
        none=counts[ActionAuthority.NONE],
    )
    compact_reasons = tuple(
        CandidateReasonCount(reason=reason, count=count)
        for reason, count in sorted(reason_counts.items(), key=lambda item: item[0].value)
        if count > 0
    )
    return OpportunityAnalyticsView(
        context=context,
        candidates=tuple(sorted(candidates, key=lambda candidate: candidate.candidate_id)),
        authority_summary=summary,
        reason_counts=compact_reasons,
        view_model_version=view_model_version,
    )


def build_trade_partner_analytics_view(
    *,
    context: AnalyticsContext,
    focal_team_id: str,
    records: tuple[TradeOpportunityAnalyticsRecord, ...],
    view_model_version: str = "next7-trade-partner-view-v1",
) -> TradePartnerAnalyticsView:
    if not focal_team_id.strip():
        raise ValueError("focal_team_id cannot be blank")
    grouped: dict[str, list[TradeOpportunityAnalyticsRecord]] = {}
    for record in records:
        if record.candidate.focal_team_id != focal_team_id:
            raise ValueError("all trade partner records must match focal team")
        grouped.setdefault(record.counterparty_team_id, []).append(record)

    partner_rows: list[TradePartnerAnalyticsRow] = []
    for team_id in sorted(grouped):
        items = grouped[team_id]
        mutual_gain = 0
        dominated = 0
        acceptance_known = 0
        acceptance_unknown = 0
        for item in items:
            negotiation = item.negotiation
            if negotiation is not None:
                if negotiation.shape == NegotiationFeasibilityShape.MUTUAL_GAIN_CANDIDATE:
                    mutual_gain += 1
                if negotiation.shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED:
                    dominated += 1
                acceptance = negotiation.acceptance
                if acceptance is None or acceptance.status == AcceptanceModelStatus.NOT_ESTIMATED:
                    acceptance_unknown += 1
                else:
                    acceptance_known += 1
            else:
                acceptance_unknown += 1
        partner_rows.append(
            TradePartnerAnalyticsRow(
                counterparty_team_id=team_id,
                evaluated_candidates=len(items),
                actionable_candidates=sum(
                    item.candidate.action_authority == ActionAuthority.ACTIONABLE for item in items
                ),
                market_test_candidates=sum(
                    item.candidate.action_authority == ActionAuthority.MARKET_TEST_ONLY for item in items
                ),
                diagnostic_candidates=sum(
                    item.candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY for item in items
                ),
                pareto_candidates=sum(item.pareto_front for item in items),
                mutual_gain_candidates=mutual_gain,
                counterparty_dominated_candidates=dominated,
                acceptance_known_candidates=acceptance_known,
                acceptance_unknown_candidates=acceptance_unknown,
            )
        )

    return TradePartnerAnalyticsView(
        context=context,
        focal_team_id=focal_team_id,
        partners=tuple(partner_rows),
        view_model_version=view_model_version,
    )


def rank_trade_partners(
    view: TradePartnerAnalyticsView,
    *,
    metric: TradePartnerMetric,
    ranking_model_version: str = "next7-trade-partner-named-metric-v1",
) -> TradePartnerRanking:
    if not ranking_model_version.strip():
        raise ValueError("ranking_model_version cannot be blank")
    ordered = sorted(
        view.partners,
        key=lambda row: (-getattr(row, metric.value), row.counterparty_team_id),
    )
    return TradePartnerRanking(
        metric=metric,
        rows=tuple(
            RankedTradePartner(
                rank=index,
                counterparty_team_id=row.counterparty_team_id,
                value=getattr(row, metric.value),
            )
            for index, row in enumerate(ordered, start=1)
        ),
        ranking_model_version=ranking_model_version,
    )
