from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import FrozenModel, Position


class ReplacementPolicy(StrEnum):
    """Predeclared league-level replacement candidates for research comparison."""

    MARGINAL_STARTER = "marginal_starter"
    FIRST_BENCH_REPLACEMENT = "first_bench_replacement"
    REPLACEMENT_QUANTILE = "replacement_quantile"


class IntrinsicSeasonEvidence(FrozenModel):
    """Point-in-time annual evidence used by intrinsic-value research.

    Forecast distributions must already be unconditional when Forecast owns
    survival/attrition treatment. Value research must never apply survival again.
    """

    season_offset: Annotated[int, Field(ge=0)]
    player_forecast: ForecastDistribution
    replacement_forecast: ForecastDistribution
    realized_player_points: float | None = None
    realized_replacement_points: float | None = None


class IntrinsicCalibrationRow(FrozenModel):
    """Research-only historical row with explicit chronological evidence cutoff."""

    as_of: datetime
    evidence_cutoff: datetime
    asset_id: str
    position: Position
    league_context_id: str
    forecast_model_version: str
    seasons: tuple[IntrinsicSeasonEvidence, ...]
    auxiliary_transaction_refs: tuple[str, ...] = ()
    auxiliary_market_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    fold_id: str

    @field_validator("as_of", "evidence_cutoff")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("intrinsic calibration timestamps must be timezone-aware")
        return value

    @field_validator(
        "asset_id", "league_context_id", "forecast_model_version", "fold_id"
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("intrinsic calibration identifiers cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_point_in_time_contract(self) -> "IntrinsicCalibrationRow":
        if self.evidence_cutoff > self.as_of:
            raise ValueError("calibration evidence cannot postdate row as_of")
        offsets = [season.season_offset for season in self.seasons]
        if not offsets:
            raise ValueError("intrinsic calibration row requires annual forecast evidence")
        if offsets != sorted(set(offsets)):
            raise ValueError("season offsets must be unique and increasing")
        return self


class ReplacementPolicyBenchmark(FrozenModel):
    """Chronological holdout result for one league-level replacement policy."""

    policy: ReplacementPolicy
    fold_id: str
    training_through: datetime
    holdout_start: datetime
    holdout_end: datetime
    sample_size: Annotated[int, Field(ge=1)]
    realized_surplus_mae: Annotated[float, Field(ge=0)]
    realized_surplus_bias: float
    interval_coverage: Annotated[float | None, Field(ge=0, le=1)] = None

    @model_validator(mode="after")
    def validate_chronology(self) -> "ReplacementPolicyBenchmark":
        for value in (self.training_through, self.holdout_start, self.holdout_end):
            if value.tzinfo is None:
                raise ValueError("replacement benchmark timestamps must be timezone-aware")
        if self.training_through >= self.holdout_start:
            raise ValueError("training evidence must precede chronological holdout")
        if self.holdout_end <= self.holdout_start:
            raise ValueError("holdout_end must follow holdout_start")
        return self


def expected_replacement_adjusted_surplus(
    season: IntrinsicSeasonEvidence,
) -> float:
    """Transparent Model-A building block; no market or team-specific information."""

    return max(0.0, season.player_forecast.mean - season.replacement_forecast.mean)


def discounted_surplus_mean(
    row: IntrinsicCalibrationRow,
    *,
    annual_weights: tuple[float, ...],
) -> float:
    """Research-only Model A mean under explicit predeclared annual weights."""

    if len(annual_weights) < len(row.seasons):
        raise ValueError("annual weights must cover every forecast season")
    if any(weight < 0 for weight in annual_weights):
        raise ValueError("annual weights cannot be negative")
    return sum(
        annual_weights[season.season_offset]
        * expected_replacement_adjusted_surplus(season)
        for season in row.seasons
    )
