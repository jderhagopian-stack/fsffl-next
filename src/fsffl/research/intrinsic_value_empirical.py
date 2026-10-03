from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, Position


class ReplacementCandidate(StrEnum):
    """Competing league-level opportunity baselines; none is presumed correct."""

    STARTER_THRESHOLD = "starter_threshold"
    MARGINAL_LINEUP_OPPORTUNITY = "marginal_lineup_opportunity"
    FIRST_ROSTERED_REPLACEMENT = "first_rostered_replacement"
    REPLACEMENT_POOL_QUANTILE = "replacement_pool_quantile"


class TimePreferenceConfounder(StrEnum):
    """Observable effects that must not be misidentified as pure time preference."""

    CURRENT_MARKET_CONSENSUS = "current_market_consensus"
    AGE_CAREER_STAGE = "age_career_stage"
    POSITION_SCARCITY = "position_scarcity"
    LIQUIDITY = "liquidity"
    DRAFT_CLASS_STRENGTH = "draft_class_strength"
    PICK_SLOT_UNCERTAINTY = "pick_slot_uncertainty"
    CURRENT_PRODUCTION = "current_production"
    FORECAST_UNCERTAINTY = "forecast_uncertainty"


class EconomicBehaviorScenario(StrEnum):
    AGING_RB_VS_YOUNG_RB = "aging_rb_vs_young_rb"
    ELITE_QB_LONGEVITY = "elite_qb_longevity"
    DEVELOPING_WR = "developing_wr"
    DEVELOPING_TE = "developing_te"
    POSITION_SCARCITY_SHIFT = "position_scarcity_shift"
    EXPECTED_APPRECIATION_DECLINE = "expected_appreciation_decline"


class ChronologicalFold(FrozenModel):
    fold_id: str
    training_through: datetime
    holdout_start: datetime
    holdout_end: datetime

    @model_validator(mode="after")
    def validate_chronology(self) -> "ChronologicalFold":
        for value in (self.training_through, self.holdout_start, self.holdout_end):
            if value.tzinfo is None:
                raise ValueError("chronological fold timestamps must be timezone-aware")
        if self.training_through >= self.holdout_start:
            raise ValueError("training evidence must precede holdout")
        if self.holdout_end <= self.holdout_start:
            raise ValueError("holdout_end must follow holdout_start")
        if not self.fold_id.strip():
            raise ValueError("fold_id cannot be blank")
        return self


class ReplacementBenchmarkResult(FrozenModel):
    candidate: ReplacementCandidate
    fold_id: str
    league_context_id: str
    position: Position
    sample_size: Annotated[int, Field(ge=1)]
    realized_surplus_mae: Annotated[float, Field(ge=0)]
    realized_surplus_bias: float
    lineup_opportunity_error: Annotated[float | None, Field(default=None, ge=0)] = None
    interval_coverage: Annotated[float | None, Field(default=None, ge=0, le=1)] = None


class TimePreferenceIdentificationResult(FrozenModel):
    """Research result; discounting is unidentified until confounders are addressed."""

    fold_id: str
    estimate: float | None = None
    standard_error: Annotated[float | None, Field(default=None, ge=0)] = None
    confounders_controlled: tuple[TimePreferenceConfounder, ...] = ()
    residual_market_dependence: float | None = None
    identified: bool = False

    @model_validator(mode="after")
    def require_controls_for_identification(self) -> "TimePreferenceIdentificationResult":
        required = {
            TimePreferenceConfounder.AGE_CAREER_STAGE,
            TimePreferenceConfounder.POSITION_SCARCITY,
            TimePreferenceConfounder.LIQUIDITY,
            TimePreferenceConfounder.DRAFT_CLASS_STRENGTH,
            TimePreferenceConfounder.CURRENT_PRODUCTION,
            TimePreferenceConfounder.FORECAST_UNCERTAINTY,
        }
        controlled = set(self.confounders_controlled)
        if self.identified and not required.issubset(controlled):
            raise ValueError("time preference cannot be identified before required confounders are controlled")
        if self.identified and self.estimate is None:
            raise ValueError("identified time preference requires an estimate")
        return self


class MarketIndependenceDiagnostic(FrozenModel):
    """Out-of-time diagnostic; correlation alone cannot define success or failure."""

    fold_id: str
    sample_size: Annotated[int, Field(ge=2)]
    pearson_correlation: Annotated[float, Field(ge=-1, le=1)]
    rank_correlation: Annotated[float, Field(ge=-1, le=1)]
    mean_absolute_standardized_residual: Annotated[float, Field(ge=0)]
    material_disagreement_rate: Annotated[float, Field(ge=0, le=1)]
    market_adds_incremental_downstream_information: bool


class EconomicUsefulnessCheck(FrozenModel):
    scenario: EconomicBehaviorScenario
    fold_id: str
    passed: bool
    explanation: str

    @model_validator(mode="after")
    def require_explanation(self) -> "EconomicUsefulnessCheck":
        if not self.explanation.strip():
            raise ValueError("economic usefulness checks require an explanation")
        return self


class ModelComparisonResult(FrozenModel):
    """Promotion comparison that allows the transparent model to win."""

    model_name: str
    fold_id: str
    football_economic_error: Annotated[float, Field(ge=0)]
    intertemporal_error: Annotated[float, Field(ge=0)]
    uncertainty_coverage_error: Annotated[float, Field(ge=0)]
    complexity_parameter_count: Annotated[int, Field(ge=0)]
    interpretable: bool

    @model_validator(mode="after")
    def require_name(self) -> "ModelComparisonResult":
        if not self.model_name.strip():
            raise ValueError("model_name cannot be blank")
        return self
