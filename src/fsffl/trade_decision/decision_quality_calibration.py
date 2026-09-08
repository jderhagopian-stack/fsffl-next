from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.calibration import DataRightsClass

from .decision_quality import DecisionQualityPolicy, DecisionQualityPolicyAuthority


class DecisionQualityCalibrationTargetKind(StrEnum):
    CONTEMPORANEOUS_BLINDED_REVIEW = "contemporaneous_blinded_review"
    POINT_IN_TIME_EXPERT_REVIEW = "point_in_time_expert_review"
    POINT_IN_TIME_GOVERNANCE_LABEL = "point_in_time_governance_label"


class DecisionQualityCalibrationObservation(FrozenModel):
    """One leakage-safe target row for comparing Decision-quality policies.

    The target must be explicitly point-in-time. Retrospective outcomes are not a
    valid target kind for calibrating the at-the-time Decision grade. Raw league
    data may remain private/runtime-only; provenance and data rights travel with
    every calibration row.
    """

    observation_id: str
    transaction_id: str
    team_id: str
    observed_at: datetime
    target_score: Annotated[float, Field(ge=0, le=100)]
    component_scores: dict[str, Annotated[float, Field(ge=0, le=100)]]
    source_id: str
    target_kind: DecisionQualityCalibrationTargetKind
    target_definition: str
    rights_class: DataRightsClass
    provenance: str
    source_version: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality calibration observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_row(self) -> "DecisionQualityCalibrationObservation":
        required = (
            self.observation_id,
            self.transaction_id,
            self.team_id,
            self.source_id,
            self.target_definition,
            self.provenance,
        )
        if any(not value.strip() for value in required):
            raise ValueError("decision-quality calibration metadata cannot be blank")
        if not self.component_scores:
            raise ValueError("decision-quality calibration row requires component scores")
        if any(not key.strip() for key in self.component_scores):
            raise ValueError("decision-quality calibration component ids cannot be blank")
        if self.source_version is not None and not self.source_version.strip():
            raise ValueError("source_version cannot be blank when supplied")
        return self


class DecisionQualityCalibrationPanel(FrozenModel):
    observations: tuple[DecisionQualityCalibrationObservation, ...]
    as_of: datetime
    panel_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality calibration as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_panel(self) -> "DecisionQualityCalibrationPanel":
        if not self.panel_version.strip():
            raise ValueError("decision-quality calibration panel_version cannot be blank")
        if not self.observations:
            raise ValueError("decision-quality calibration panel cannot be empty")
        if any(row.observed_at > self.as_of for row in self.observations):
            raise ValueError("decision-quality calibration panel contains future evidence")
        ids = [row.observation_id for row in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("decision-quality calibration observation ids must be unique")
        return self


class DecisionQualityCandidateScore(FrozenModel):
    policy_id: str
    policy_version: str
    sample_size: Annotated[int, Field(ge=1)]
    mean_absolute_error: Annotated[float, Field(ge=0)]
    root_mean_squared_error: Annotated[float, Field(ge=0)]


class DecisionQualityCalibrationResult(FrozenModel):
    training_scores: tuple[DecisionQualityCandidateScore, ...]
    holdout_scores: tuple[DecisionQualityCandidateScore, ...]
    best_training_policy_id: str
    best_training_policy_version: str
    panel_version: str
    evidence_through: datetime
    model_version: str = "decision-quality-policy-backtest-v1"

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality calibration evidence_through must be timezone-aware")
        return value


def _predict(row: DecisionQualityCalibrationObservation, policy: DecisionQualityPolicy) -> float:
    missing = [item.component_id for item in policy.weights if item.component_id not in row.component_scores]
    if missing:
        raise ValueError(f"calibration row is missing policy components: {tuple(sorted(missing))}")
    return sum(row.component_scores[item.component_id] * item.weight for item in policy.weights)


def _score(
    rows: tuple[DecisionQualityCalibrationObservation, ...],
    policy: DecisionQualityPolicy,
) -> DecisionQualityCandidateScore:
    if not rows:
        raise ValueError("cannot score a decision-quality policy on an empty sample")
    errors = [_predict(row, policy) - row.target_score for row in rows]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = (sum(error * error for error in errors) / len(errors)) ** 0.5
    return DecisionQualityCandidateScore(
        policy_id=policy.policy_id,
        policy_version=policy.model_version,
        sample_size=len(rows),
        mean_absolute_error=mae,
        root_mean_squared_error=rmse,
    )


def backtest_decision_quality_policies(
    *,
    panel: DecisionQualityCalibrationPanel,
    candidate_policies: tuple[DecisionQualityPolicy, ...],
    holdout_start: datetime,
    model_version: str = "decision-quality-policy-backtest-v1",
) -> DecisionQualityCalibrationResult:
    """Compare explicit candidate policies without inventing or promoting weights.

    Policies are ranked on the pre-holdout training window. Holdout performance is
    reported separately. The function does not convert the winning candidate to a
    CALIBRATED production policy; promotion remains an explicit governance action.
    """

    if holdout_start.tzinfo is None:
        raise ValueError("holdout_start must be timezone-aware")
    if holdout_start > panel.as_of:
        raise ValueError("holdout_start cannot be after panel as_of")
    if not candidate_policies:
        raise ValueError("at least one decision-quality candidate policy is required")
    identities = [(item.policy_id, item.model_version) for item in candidate_policies]
    if len(identities) != len(set(identities)):
        raise ValueError("decision-quality candidate policies must have unique identities")
    if any(item.evidence_through > panel.as_of for item in candidate_policies):
        raise ValueError("candidate policy uses evidence beyond calibration panel as_of")

    training = tuple(row for row in panel.observations if row.observed_at < holdout_start)
    holdout = tuple(row for row in panel.observations if row.observed_at >= holdout_start)
    if not training or not holdout:
        raise ValueError("decision-quality calibration requires nonempty training and holdout samples")

    training_scores = tuple(_score(training, policy) for policy in candidate_policies)
    holdout_scores = tuple(_score(holdout, policy) for policy in candidate_policies)
    winner = min(
        training_scores,
        key=lambda item: (item.mean_absolute_error, item.root_mean_squared_error, item.policy_id, item.policy_version),
    )
    return DecisionQualityCalibrationResult(
        training_scores=training_scores,
        holdout_scores=holdout_scores,
        best_training_policy_id=winner.policy_id,
        best_training_policy_version=winner.policy_version,
        panel_version=panel.panel_version,
        evidence_through=panel.as_of,
        model_version=model_version,
    )


def promote_calibrated_policy(
    candidate: DecisionQualityPolicy,
    *,
    calibration: DecisionQualityCalibrationResult,
    provenance: str,
    model_version: str,
) -> DecisionQualityPolicy:
    """Create a calibrated policy only from the backtest winner.

    This is still an explicit governance operation. No accuracy threshold is
    hidden here; a caller must decide whether the recorded training/holdout
    evidence is strong enough for promotion.
    """

    if (candidate.policy_id, candidate.model_version) != (
        calibration.best_training_policy_id,
        calibration.best_training_policy_version,
    ):
        raise ValueError("only the recorded training winner can be promoted")
    if not provenance.strip() or not model_version.strip():
        raise ValueError("calibrated policy promotion requires provenance and model_version")
    return DecisionQualityPolicy(
        policy_id=candidate.policy_id,
        model_version=model_version,
        provenance=provenance,
        evidence_through=calibration.evidence_through,
        weights=candidate.weights,
        authority=DecisionQualityPolicyAuthority.CALIBRATED,
    )
