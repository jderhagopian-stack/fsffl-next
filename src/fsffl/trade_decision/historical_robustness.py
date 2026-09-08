from __future__ import annotations

from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    SideDecisionShape,
)


class HistoricalDecisionRobustnessStatus(StrEnum):
    ROBUST = "robust"
    SENSITIVE = "sensitive"
    INCOMPLETE = "incomplete"


class HistoricalDecisionScenario(FrozenModel):
    """One governed PIT uncertainty scenario evaluated by Decision authority.

    Runtime/Value may construct lower/central/upper or other explicitly governed
    scenarios, but this object contains only the resulting Decision output. It
    does not create asset values, scenario probabilities, or utility weights.
    """

    scenario_id: str
    decision: BilateralTradeDecision

    @field_validator("scenario_id")
    @classmethod
    def require_scenario_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("historical decision scenario_id cannot be blank")
        return value.strip()


class HistoricalDecisionRobustness(FrozenModel):
    """Whether Decision's qualitative conclusion survives PIT uncertainty."""

    proposal_id: str
    status: HistoricalDecisionRobustnessStatus
    scenario_ids: tuple[str, ...]
    side_a_team_id: str
    side_b_team_id: str
    side_a_shapes: tuple[SideDecisionShape, ...]
    side_b_shapes: tuple[SideDecisionShape, ...]
    bilateral_shapes: tuple[BilateralDecisionShape, ...]
    model_versions: tuple[str, ...]
    reason: str
    model_version: str = "historical-decision-robustness-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "HistoricalDecisionRobustness":
        text = (self.proposal_id, self.side_a_team_id, self.side_b_team_id, self.reason, self.model_version)
        if any(not value.strip() for value in text):
            raise ValueError("historical decision robustness identifiers/reason cannot be blank")
        if not self.scenario_ids:
            raise ValueError("historical decision robustness requires scenarios")
        if len(self.scenario_ids) != len(set(self.scenario_ids)):
            raise ValueError("historical decision robustness scenario ids must be unique")
        if not self.model_versions:
            raise ValueError("historical decision robustness requires Decision model lineage")
        return self


def assess_historical_decision_robustness(
    scenarios: tuple[HistoricalDecisionScenario, ...],
    *,
    model_version: str = "historical-decision-robustness-v1",
) -> HistoricalDecisionRobustness:
    """Test whether the Decision conclusion changes across governed PIT scenarios.

    No magnitude threshold is invented here. The test asks a narrower question:
    did Decision authority classify the trade differently anywhere inside the
    supplied plausible evidence range? If yes, historical grading should surface
    that sensitivity rather than manufacture confidence. If all qualitative
    Decision shapes agree, uncertainty alone is not a reason to withhold a grade.
    """

    if not scenarios:
        raise ValueError("historical decision robustness requires at least one scenario")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    proposal_ids = {item.decision.proposal_id for item in scenarios}
    if len(proposal_ids) != 1:
        raise ValueError("historical decision scenarios must describe one proposal")
    side_a_ids = {item.decision.side_a.team_id for item in scenarios}
    side_b_ids = {item.decision.side_b.team_id for item in scenarios}
    if len(side_a_ids) != 1 or len(side_b_ids) != 1:
        raise ValueError("historical decision scenarios must preserve team identity")

    scenario_ids = tuple(item.scenario_id for item in scenarios)
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("historical decision scenario ids must be unique")

    a_shapes = tuple(item.decision.side_a.shape for item in scenarios)
    b_shapes = tuple(item.decision.side_b.shape for item in scenarios)
    bilateral_shapes = tuple(item.decision.shape for item in scenarios)
    versions = tuple(sorted({item.decision.model_version for item in scenarios}))

    contains_incomplete = (
        SideDecisionShape.INCOMPLETE in a_shapes
        or SideDecisionShape.INCOMPLETE in b_shapes
        or BilateralDecisionShape.MIXED_OR_INCOMPLETE in bilateral_shapes
    )
    stable = len(set(a_shapes)) == 1 and len(set(b_shapes)) == 1 and len(set(bilateral_shapes)) == 1

    if contains_incomplete:
        status = HistoricalDecisionRobustnessStatus.INCOMPLETE
        reason = "one or more PIT scenarios contains incomplete Decision evidence"
    elif stable:
        status = HistoricalDecisionRobustnessStatus.ROBUST
        reason = "Decision shape is unchanged across all supplied PIT uncertainty scenarios"
    else:
        status = HistoricalDecisionRobustnessStatus.SENSITIVE
        reason = "Decision shape changes across the supplied PIT uncertainty scenarios"

    return HistoricalDecisionRobustness(
        proposal_id=next(iter(proposal_ids)),
        status=status,
        scenario_ids=scenario_ids,
        side_a_team_id=next(iter(side_a_ids)),
        side_b_team_id=next(iter(side_b_ids)),
        side_a_shapes=a_shapes,
        side_b_shapes=b_shapes,
        bilateral_shapes=bilateral_shapes,
        model_versions=versions,
        reason=reason,
        model_version=model_version,
    )
