from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator

from fsffl.state.draft_order_policy import (
    DraftOrderPolicyEvidence,
    resolve_draft_order_policy,
)
from fsffl.state.models import FrozenModel, LeagueRules
from fsffl.team_utility.draft_order import (
    DraftOrderScenario,
    DraftOrderSimulationResult,
)
from fsffl.team_utility.draft_order_metric import (
    DraftMetricDirection,
    DraftMetricScenarioSet,
    rank_metric_scenarios_to_draft_order,
)


class HistoricalDraftOrderStatus(StrEnum):
    PRODUCED = "PRODUCED"
    MISSING_POLICY_EVIDENCE = "MISSING_POLICY_EVIDENCE"
    UNSUPPORTED_POLICY_MECHANISM = "UNSUPPORTED_POLICY_MECHANISM"
    MISSING_SCENARIO_EVIDENCE = "MISSING_SCENARIO_EVIDENCE"
    INVALID_POLICY_PARAMETERS = "INVALID_POLICY_PARAMETERS"


class HistoricalDraftOrderScenarioEvidence(FrozenModel):
    """Complete point-in-time draft-order scenarios supplied to orchestration."""

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
    league_rules: LeagueRules,
    scenario_evidence: HistoricalDraftOrderScenarioEvidence | None = None,
    metric_evidence: DraftMetricScenarioSet | None = None,
) -> HistoricalDraftOrderProductionResult:
    """Resolve historical rule evidence and produce only evidence-backed scenarios.

    Supported mechanisms are explicit and generic:
    - ``explicit_scenarios`` accepts complete scenarios produced elsewhere.
    - ``ranked_metric`` ranks a supplied point-in-time metric using the policy's
      explicit ``metric_id`` and ``direction`` parameters.

    Other mechanisms remain unsupported until an evidence-backed producer exists.
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

    if policy.mechanism == "explicit_scenarios":
        if scenario_evidence is None:
            return HistoricalDraftOrderProductionResult(
                status=HistoricalDraftOrderStatus.MISSING_SCENARIO_EVIDENCE,
                policy=policy,
                reason="explicit_scenarios policy requires complete point-in-time scenario evidence",
            )
        _validate_scenario_identity(
            league_id=league_id,
            draft_season=draft_season,
            as_of=as_of,
            evidence_league_id=scenario_evidence.league_id,
            evidence_draft_season=scenario_evidence.draft_season,
            evidence_as_of=scenario_evidence.as_of,
        )
        scenarios = scenario_evidence.scenarios
        if not scenarios:
            return HistoricalDraftOrderProductionResult(
                status=HistoricalDraftOrderStatus.MISSING_SCENARIO_EVIDENCE,
                policy=policy,
                reason="scenario evidence is empty",
            )
        model_version = scenario_evidence.model_version
        evidence_provenance = scenario_evidence.provenance
        evidence_as_of = scenario_evidence.as_of

    elif policy.mechanism == "ranked_metric":
        if metric_evidence is None:
            return HistoricalDraftOrderProductionResult(
                status=HistoricalDraftOrderStatus.MISSING_SCENARIO_EVIDENCE,
                policy=policy,
                reason="ranked_metric policy requires point-in-time metric scenarios",
            )
        _validate_scenario_identity(
            league_id=league_id,
            draft_season=draft_season,
            as_of=as_of,
            evidence_league_id=metric_evidence.league_id,
            evidence_draft_season=metric_evidence.draft_season,
            evidence_as_of=metric_evidence.as_of,
        )
        params = {item.name: item.value for item in policy.parameters}
        metric_id = params.get("metric_id")
        direction_raw = params.get("direction")
        if not isinstance(metric_id, str) or metric_id != metric_evidence.metric_id:
            return HistoricalDraftOrderProductionResult(
                status=HistoricalDraftOrderStatus.INVALID_POLICY_PARAMETERS,
                policy=policy,
                reason="ranked_metric policy metric_id must match supplied metric evidence",
            )
        try:
            direction = DraftMetricDirection(str(direction_raw))
        except ValueError:
            return HistoricalDraftOrderProductionResult(
                status=HistoricalDraftOrderStatus.INVALID_POLICY_PARAMETERS,
                policy=policy,
                reason="ranked_metric policy requires a valid explicit direction parameter",
            )
        scenarios = rank_metric_scenarios_to_draft_order(
            metric_evidence,
            league_rules=league_rules,
            direction=direction,
        )
        model_version = metric_evidence.model_version
        evidence_provenance = metric_evidence.provenance
        evidence_as_of = metric_evidence.as_of

    else:
        return HistoricalDraftOrderProductionResult(
            status=HistoricalDraftOrderStatus.UNSUPPORTED_POLICY_MECHANISM,
            policy=policy,
            reason=f"draft-order mechanism is not implemented: {policy.mechanism}",
        )

    result = DraftOrderSimulationResult(
        league_id=league_id,
        draft_season=draft_season,
        as_of=evidence_as_of,
        scenarios=scenarios,
        model_version=model_version,
        rule_policy_version=f"{policy.policy_id}:{policy.version}",
        provenance=(
            f"{evidence_provenance}; policy={policy.provenance.source}; "
            f"policy_version={policy.policy_id}:{policy.version}"
        ),
    )
    return HistoricalDraftOrderProductionResult(
        status=HistoricalDraftOrderStatus.PRODUCED,
        result=result,
        policy=policy,
        reason="historical draft-order scenarios produced under resolved point-in-time policy",
    )


def _validate_scenario_identity(
    *,
    league_id: str,
    draft_season: int,
    as_of: datetime,
    evidence_league_id: str,
    evidence_draft_season: int,
    evidence_as_of: datetime,
) -> None:
    if evidence_league_id != league_id:
        raise ValueError("scenario evidence must describe the requested league")
    if evidence_draft_season != draft_season:
        raise ValueError("scenario evidence must describe the requested draft season")
    if evidence_as_of > as_of:
        raise ValueError("scenario evidence cannot postdate historical as_of")
