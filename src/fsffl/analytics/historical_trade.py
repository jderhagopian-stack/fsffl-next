from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


class GradeStatus(StrEnum):
    GRADED = "graded"
    NOT_GRADED = "not_graded"


class AttributionStatus(StrEnum):
    DIRECT = "direct"
    ATTRIBUTED = "attributed"
    AMBIGUOUS = "ambiguous"
    TERMINAL = "terminal"


class EvidenceCompleteness(FrozenModel):
    """Explicit evidence accounting for a historical reconstruction.

    The grader fails closed when any caller-declared required item is missing.
    Required items are intentionally supplied by the governed research/product
    workflow rather than being invented in presentation code.
    """

    required_items: tuple[str, ...]
    available_items: tuple[str, ...]
    gaps: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_items(self) -> "EvidenceCompleteness":
        if any(not item.strip() for item in self.required_items + self.available_items + self.gaps):
            raise ValueError("evidence item names cannot be blank")
        required = set(self.required_items)
        available = set(self.available_items)
        explicit_gaps = set(self.gaps)
        if explicit_gaps - required:
            raise ValueError("evidence gaps must be declared required items")
        if available & explicit_gaps:
            raise ValueError("an evidence item cannot be both available and missing")
        return self

    @property
    def missing_required(self) -> tuple[str, ...]:
        missing = set(self.required_items) - set(self.available_items)
        missing.update(self.gaps)
        return tuple(sorted(missing))

    @property
    def complete(self) -> bool:
        return not self.missing_required

    @property
    def ratio(self) -> float:
        if not self.required_items:
            return 1.0
        required = set(self.required_items)
        available = set(self.available_items)
        return len(required & available) / len(required)


class GradeBand(FrozenModel):
    minimum_score: Annotated[float, Field(ge=0, le=100)]
    letter: str

    @field_validator("letter")
    @classmethod
    def require_letter(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("grade letter cannot be blank")
        return value.strip()


class GovernedGradePolicy(FrozenModel):
    """Presentation policy translating an authoritative 0-100 score to a letter.

    No default bands are provided. Thresholds must come from a separately
    governed policy with provenance and a version. This prevents analytics or
    presentation code from silently inventing model truth.
    """

    policy_id: str
    model_version: str
    provenance: str
    bands: tuple[GradeBand, ...]

    @model_validator(mode="after")
    def validate_policy(self) -> "GovernedGradePolicy":
        if not self.policy_id.strip() or not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("grade policy identifiers and provenance cannot be blank")
        if not self.bands:
            raise ValueError("grade policy must define at least one band")
        minimums = [band.minimum_score for band in self.bands]
        if len(minimums) != len(set(minimums)):
            raise ValueError("grade-band minimum scores must be unique")
        if min(minimums) != 0:
            raise ValueError("grade policy must include a floor band beginning at score 0")
        return self

    def letter_for(self, score: float) -> str:
        if score < 0 or score > 100:
            raise ValueError("grade score must be between 0 and 100")
        eligible = [band for band in self.bands if score >= band.minimum_score]
        return max(eligible, key=lambda band: band.minimum_score).letter


class GradeResult(FrozenModel):
    status: GradeStatus
    letter: str | None = None
    score: Annotated[float | None, Field(default=None, ge=0, le=100)] = None
    confidence: Annotated[float, Field(ge=0, le=1)]
    reason: str
    policy_id: str | None = None
    policy_version: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "GradeResult":
        if not self.reason.strip():
            raise ValueError("grade result reason cannot be blank")
        if self.status == GradeStatus.GRADED:
            if self.letter is None or self.score is None or self.policy_id is None or self.policy_version is None:
                raise ValueError("graded results require letter, score, and governed policy identity")
        else:
            if self.letter is not None:
                raise ValueError("not-graded results cannot contain a letter grade")
        return self


class PointInTimeDecisionEvidence(FrozenModel):
    """Decision-authority output prepared for historical grading.

    ``decision_quality_score`` is deliberately not computed here. It must be
    emitted by the authoritative Decision layer or another explicitly governed
    decision-quality policy. Historical analytics only validates evidence and
    translates that authoritative score through a governed letter-grade policy.
    """

    transaction_id: str
    team_id: str
    as_of: datetime
    decision_model_version: str
    decision_quality_score: Annotated[float | None, Field(default=None, ge=0, le=100)] = None
    decision_disposition: str | None = None
    value_exchanged: float | None = None
    team_utility_delta: float | None = None
    projected_lineup_delta: float | None = None
    replacement_value_delta: float | None = None
    pick_value_delta: float | None = None
    package_economics_delta: float | None = None
    uncertainty: float | None = None
    evidence: EvidenceCompleteness
    evidence_notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "PointInTimeDecisionEvidence":
        if not self.transaction_id.strip() or not self.team_id.strip() or not self.decision_model_version.strip():
            raise ValueError("point-in-time decision identifiers cannot be blank")
        return self


class RetrospectiveOutcomeComponents(FrozenModel):
    """Measured retrospective components, normalized upstream onto 0-100 scales."""

    asset_value_score: Annotated[float | None, Field(default=None, ge=0, le=100)] = None
    production_score: Annotated[float | None, Field(default=None, ge=0, le=100)] = None
    franchise_outcome_score: Annotated[float | None, Field(default=None, ge=0, le=100)] = None
    evidence: EvidenceCompleteness


class RetrospectiveOutcomePolicy(FrozenModel):
    """Governed summary policy for measurable outcome components.

    Weights have no defaults and must sum to one. Any positively weighted
    component that is unavailable causes a NOT_GRADED result rather than silent
    redistribution of weight.
    """

    policy_id: str
    model_version: str
    provenance: str
    asset_value_weight: Annotated[float, Field(ge=0, le=1)]
    production_weight: Annotated[float, Field(ge=0, le=1)]
    franchise_outcome_weight: Annotated[float, Field(ge=0, le=1)]

    @model_validator(mode="after")
    def validate_weights(self) -> "RetrospectiveOutcomePolicy":
        if not self.policy_id.strip() or not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("retrospective policy identifiers and provenance cannot be blank")
        total = self.asset_value_weight + self.production_weight + self.franchise_outcome_weight
        if abs(total - 1.0) > 1e-9:
            raise ValueError("retrospective outcome weights must sum to 1")
        return self


class AssetAttribution(FrozenModel):
    asset_id: str
    weight: Annotated[float, Field(gt=0, le=1)]


class AssetLineageEvent(FrozenModel):
    event_id: str
    occurred_at: datetime
    from_asset_id: str
    to_assets: tuple[AssetAttribution, ...] = ()
    description: str
    provenance: str

    @field_validator("occurred_at")
    @classmethod
    def require_event_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("lineage event timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_event(self) -> "AssetLineageEvent":
        if any(not value.strip() for value in (self.event_id, self.from_asset_id, self.description, self.provenance)):
            raise ValueError("lineage identifiers, description, and provenance cannot be blank")
        if self.to_assets:
            total = sum(item.weight for item in self.to_assets)
            if abs(total - 1.0) > 1e-9:
                raise ValueError("explicit lineage attribution weights must sum to 1")
            ids = [item.asset_id for item in self.to_assets]
            if len(ids) != len(set(ids)):
                raise ValueError("lineage child assets must be unique")
        return self


class AssetLineageStep(FrozenModel):
    asset_id: str
    attribution_weight: Annotated[float, Field(gt=0, le=1)]
    status: AttributionStatus
    event_id: str | None = None
    description: str | None = None


class AssetLineageTrace(FrozenModel):
    root_asset_id: str
    terminal_assets: tuple[AssetLineageStep, ...]
    ambiguous: bool
    notes: tuple[str, ...] = ()


class HistoricalTradeReport(FrozenModel):
    transaction_id: str
    trade_date: datetime
    teams: tuple[str, ...]
    assets_by_team: dict[str, tuple[str, ...]]
    originator_team_id: str | None = None
    point_in_time_grade: GradeResult
    point_in_time_evidence: tuple[PointInTimeDecisionEvidence, ...]
    final_outcome_grade: GradeResult
    outcome_components: RetrospectiveOutcomeComponents
    lineage: tuple[AssetLineageTrace, ...] = ()
    what_changed: tuple[str, ...] = ()
    lessons: tuple[str, ...] = ()
    model_version: str = "historical-trade-report-v1"

    @field_validator("trade_date")
    @classmethod
    def require_trade_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("trade_date must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_report(self) -> "HistoricalTradeReport":
        if not self.transaction_id.strip() or not self.model_version.strip():
            raise ValueError("historical trade report identifiers cannot be blank")
        if len(self.teams) < 2:
            raise ValueError("historical trade report requires at least two teams")
        if set(self.teams) != set(self.assets_by_team):
            raise ValueError("assets_by_team must contain exactly the report teams")
        return self


def grade_authoritative_score(
    *,
    score: float | None,
    evidence: EvidenceCompleteness,
    policy: GovernedGradePolicy | None,
    missing_score_reason: str,
) -> GradeResult:
    """Fail-closed grade translation with no hidden thresholds or imputation."""

    confidence = evidence.ratio
    if not evidence.complete:
        return GradeResult(
            status=GradeStatus.NOT_GRADED,
            confidence=confidence,
            reason="NOT GRADED — insufficient point-in-time evidence: " + ", ".join(evidence.missing_required),
        )
    if score is None:
        return GradeResult(
            status=GradeStatus.NOT_GRADED,
            confidence=confidence,
            reason=missing_score_reason,
        )
    if policy is None:
        return GradeResult(
            status=GradeStatus.NOT_GRADED,
            score=score,
            confidence=confidence,
            reason="NOT GRADED — no governed letter-grade policy is available",
        )
    return GradeResult(
        status=GradeStatus.GRADED,
        letter=policy.letter_for(score),
        score=score,
        confidence=confidence,
        reason="Grade translated from authoritative score through governed policy",
        policy_id=policy.policy_id,
        policy_version=policy.model_version,
    )


def grade_point_in_time_decision(
    evidence: PointInTimeDecisionEvidence,
    *,
    policy: GovernedGradePolicy | None,
) -> GradeResult:
    return grade_authoritative_score(
        score=evidence.decision_quality_score,
        evidence=evidence.evidence,
        policy=policy,
        missing_score_reason=(
            "NOT GRADED — Decision has not emitted a governed historical decision-quality score"
        ),
    )


def score_retrospective_outcome(
    components: RetrospectiveOutcomeComponents,
    *,
    outcome_policy: RetrospectiveOutcomePolicy,
) -> float | None:
    weighted = (
        ("asset_value_score", components.asset_value_score, outcome_policy.asset_value_weight),
        ("production_score", components.production_score, outcome_policy.production_weight),
        (
            "franchise_outcome_score",
            components.franchise_outcome_score,
            outcome_policy.franchise_outcome_weight,
        ),
    )
    if any(weight > 0 and value is None for _, value, weight in weighted):
        return None
    return sum((value or 0.0) * weight for _, value, weight in weighted)


def grade_retrospective_outcome(
    components: RetrospectiveOutcomeComponents,
    *,
    outcome_policy: RetrospectiveOutcomePolicy,
    grade_policy: GovernedGradePolicy | None,
) -> GradeResult:
    score = score_retrospective_outcome(components, outcome_policy=outcome_policy)
    return grade_authoritative_score(
        score=score,
        evidence=components.evidence,
        policy=grade_policy,
        missing_score_reason=(
            "NOT GRADED — one or more governed retrospective outcome components are unavailable"
        ),
    )


def trace_asset_lineage(
    root_asset_id: str,
    events: tuple[AssetLineageEvent, ...],
) -> AssetLineageTrace:
    """Trace explicit asset lineage without inventing attribution.

    A one-child event is direct lineage. Multi-child events are followed only
    when explicit attribution weights are supplied (which this contract requires
    for every child). Cycles are rejected. Assets without a later event are
    terminal. The function never infers causal allocation from package size or
    later value.
    """

    if not root_asset_id.strip():
        raise ValueError("root_asset_id cannot be blank")
    by_source: dict[str, list[AssetLineageEvent]] = {}
    for event in sorted(events, key=lambda item: (item.occurred_at, item.event_id)):
        by_source.setdefault(event.from_asset_id, []).append(event)

    terminal: list[AssetLineageStep] = []
    notes: list[str] = []
    ambiguous = False

    def walk(asset_id: str, weight: float, path: tuple[str, ...]) -> None:
        nonlocal ambiguous
        if asset_id in path:
            raise ValueError("asset lineage contains a cycle")
        candidates = by_source.get(asset_id, [])
        if not candidates:
            terminal.append(
                AssetLineageStep(
                    asset_id=asset_id,
                    attribution_weight=weight,
                    status=AttributionStatus.TERMINAL,
                )
            )
            return
        if len(candidates) > 1:
            ambiguous = True
            notes.append(
                f"Multiple later lineage events originate from {asset_id}; causal path is ambiguous"
            )
            terminal.append(
                AssetLineageStep(
                    asset_id=asset_id,
                    attribution_weight=weight,
                    status=AttributionStatus.AMBIGUOUS,
                )
            )
            return
        event = candidates[0]
        if not event.to_assets:
            terminal.append(
                AssetLineageStep(
                    asset_id=asset_id,
                    attribution_weight=weight,
                    status=AttributionStatus.TERMINAL,
                    event_id=event.event_id,
                    description=event.description,
                )
            )
            return
        status = AttributionStatus.DIRECT if len(event.to_assets) == 1 else AttributionStatus.ATTRIBUTED
        for child in event.to_assets:
            next_weight = weight * child.weight
            if status == AttributionStatus.ATTRIBUTED:
                notes.append(
                    f"{event.event_id} uses explicit attribution for {asset_id} -> {child.asset_id}"
                )
            walk(child.asset_id, next_weight, path + (asset_id,))

    walk(root_asset_id, 1.0, ())
    return AssetLineageTrace(
        root_asset_id=root_asset_id,
        terminal_assets=tuple(terminal),
        ambiguous=ambiguous,
        notes=tuple(notes),
    )
