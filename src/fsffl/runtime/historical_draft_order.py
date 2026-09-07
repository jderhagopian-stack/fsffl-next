from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator

from fsffl.state.draft_order_policy import (
    DraftOrderPolicyEvidence,
    resolve_draft_order_policy,
)
from fsffl.state.models import FrozenModel
from fsffl.team_utility.draft_order import (
    DraftOrderScenario,
    DraftOrderSimulationResult,
)


class HistoricalDraftOrderStatus(StrEnum):
    PRODUCED = "PRODUCED"
    MISSING_POLICY_EVIDENCE = "MISSING_POLICY_EVIDENCE"
    UNSUPPORTED_POLICY_MECHANISM = "UNSUPPORTED_POLICY_MECHANISM"
    MISSING_SCENARIO_EVIDENCE = "MISSING_SCENARIO_EVIDENCE"


class HistoricalDraftOrderScenarioEvidence(FrozenModel):
    """Complete point-in-time draft-order scenarios supplied to orchestration.

    Runtime does not infer the league rule or competitive outcomes represented by
    these scenarios. The producing research/simulation path must provide complete
    assignments and provenance before they can be accepted here.
    """

    league_id: str
    draft_season: int
    as_of: datetime
    scenarios: tuple[DraftOrderScenario, ...]
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical draft-order scenario as_of must be timezone-aware")
        return value


class HistoricalDraftOrderProductionResult(FrozenModel):
    status: HistoricalDraftOrderStatus
    result: DraftOrderSimulationResult | None = None
    policy: DraftOrderPolicyEvidence | None = None
    reason: str


def produce_historical_draft_order(
    *,
    policies: tuple[DraftOrderPolicyEvidence, ...],
    league_id: str,
    draft_season: int,
    as_of: datetime,
    scenario_evidence: HistoricalDraftOrderScenarioEvidence | None,
    supported_mechanisms: tuple[str, ...] = ("explicit_scenarios",),
) -> HistoricalDraftOrderProductionResult:
    """Resolve historical rule evidence and accept only supported scenario paths.

    This is deliberately orchestration, not a universal draft-order formula. The
    current supported mechanism accepts complete scenarios produced elsewhere.
    Max-PF, playoff, lottery, consolation, or custom mechanisms require their own
    evidence-backed producers before they may be added to ``supported_mechanisms``.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    policy = resolve_draft_order_policy(
        policies,
        league_id=league_id,
        draft_season=draft_season,
        as_of=as_of,
    )
    if policy is None:
        return HistoricalDraftOrderProductionResult(
            status=HistoricalDraftOrderStatus.MISSING_POLICY_EVIDENCE,
            reason="no draft-order policy was both effective and knowable at as_of",
        )

    if policy.mechanism not in supported_mechanisms:
        return HistoricalDraftOrderProductionResult(
            status=HistoricalDraftOrderStatus.UNSUPPORTED_POLICY_MECHANISM,
            policy=policy,
            reason=f"draft-order mechanism is not implemented: {policy.mechanism}",
        )

    if scenario_evidence is None:
        return HistoricalDraftOrderProductionResult(
            status=HistoricalDraftOrderStatus.MISSING_SCENARIO_EVIDENCE,
            policy=policy,
            reason="supported policy requires complete point-in-time scenario evidence",
        )

    if scenario_evidence.league_id != league_id:
        raise ValueError("scenario evidence must describe the requested league")
    if scenario_evidence.draft_season != draft_season:
        raise ValueError("scenario evidence must describe the requested draft season")
    if scenario_evidence.as_of > as_of:
        raise ValueError("scenario evidence cannot postdate historical as_of")
    if not scenario_evidence.scenarios:
        return HistoricalDraftOrderProductionResult(
            status=HistoricalDraftOrderStatus.MISSING_SCENARIO_EVIDENCE,
            policy=policy,
            reason="scenario evidence is empty",
        )

    result = DraftOrderSimulationResult(
        league_id=league_id,
        draft_season=draft_season,
        as_of=scenario_evidence.as_of,
        scenarios=scenario_evidence.scenarios,
        model_version=scenario_evidence.model_version,
        rule_policy_version=f"{policy.policy_id}:{policy.version}",
        provenance=(
            f"{scenario_evidence.provenance}; policy={policy.provenance.source}; "
            f"policy_version={policy.policy_id}:{policy.version}"
        ),
    )
    return HistoricalDraftOrderProductionResult(
        status=HistoricalDraftOrderStatus.PRODUCED,
        result=result,
        policy=policy,
        reason="historical draft-order scenarios accepted under resolved point-in-time policy",
    )
