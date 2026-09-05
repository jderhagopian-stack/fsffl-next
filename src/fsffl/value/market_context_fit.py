from __future__ import annotations

from datetime import datetime
from math import sqrt
from statistics import mean
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .calibration import CalibrationEvidenceKind, CalibrationPanel
from .market_context import MarketContextCalibration


class MarketContextFitPolicy(FrozenModel):
    """Versioned evidence policy for hierarchical market-context fitting.

    `format_prior_strength` and `league_prior_strength` are calibration-policy
    parameters, not hidden runtime constants. They determine how quickly observed
    cohort/league residuals earn authority relative to broader evidence and may
    themselves be challenged and recalibrated through held-out validation.
    """

    residual_metric: str
    format_prior_strength: Annotated[float, Field(gt=0)]
    league_prior_strength: Annotated[float, Field(gt=0)]
    model_version: str

    @model_validator(mode="after")
    def validate_policy(self) -> "MarketContextFitPolicy":
        if not self.residual_metric.strip() or not self.model_version.strip():
            raise ValueError("market-context fit policy identifiers cannot be blank")
        return self


def fit_market_context_calibration(
    panel: CalibrationPanel,
    *,
    global_context_id: str,
    format_context_id: str | None,
    league_context_id: str | None,
    policy: MarketContextFitPolicy,
    fitted_at: datetime,
) -> MarketContextCalibration:
    """Fit global -> format -> league residual adjustments from point-in-time evidence.

    Eligible rows must be market-value or completed-transaction evidence carrying
    `policy.residual_metric`. Format offsets are estimated against the global
    baseline. League offsets are estimated as residuals relative to the format
    cohort and are partially pooled toward zero using explicit prior strengths.

    The fitter never invents league behavior when no league evidence exists; in
    that case the league weight remains zero and the estimate stays at the broader
    context.
    """

    if fitted_at.tzinfo is None:
        raise ValueError("fitted_at must be timezone-aware")
    if panel.as_of > fitted_at:
        raise ValueError("cannot fit market context before panel as_of")
    if not global_context_id.strip():
        raise ValueError("global_context_id cannot be blank")
    for optional in (format_context_id, league_context_id):
        if optional is not None and not optional.strip():
            raise ValueError("market context identifiers cannot be blank")

    eligible = tuple(
        row
        for row in panel.observations
        if row.metric == policy.residual_metric
        and row.evidence_kind
        in (CalibrationEvidenceKind.MARKET_VALUE, CalibrationEvidenceKind.COMPLETED_TRANSACTION)
    )
    if not eligible:
        raise ValueError("no eligible market-context calibration evidence")

    format_rows = (
        tuple(row for row in eligible if row.format_context_id == format_context_id)
        if format_context_id is not None
        else ()
    )
    format_offset = mean(row.value for row in format_rows) if format_rows else 0.0
    format_weight = _shrinkage_weight(len(format_rows), policy.format_prior_strength)

    league_rows = (
        tuple(row for row in eligible if row.league_context_id == league_context_id)
        if league_context_id is not None
        else ()
    )
    # League residual is measured relative to the observed format mean, not the
    # already-shrunk format adjustment. This keeps the two hierarchical effects
    # identifiable and prevents double shrinking the same evidence.
    league_offset = (
        mean(row.value - format_offset for row in league_rows) if league_rows else 0.0
    )
    league_weight = _shrinkage_weight(len(league_rows), policy.league_prior_strength)

    fitted_residuals: list[float] = []
    for row in eligible:
        predicted = 0.0
        if format_context_id is not None and row.format_context_id == format_context_id:
            predicted += format_weight * format_offset
        if league_context_id is not None and row.league_context_id == league_context_id:
            predicted += league_weight * league_offset
        fitted_residuals.append(row.value - predicted)

    residual_stddev = _population_stddev(fitted_residuals)

    return MarketContextCalibration(
        global_context_id=global_context_id,
        format_context_id=format_context_id,
        league_context_id=league_context_id,
        format_offset=format_offset,
        league_offset=league_offset,
        format_shrinkage_weight=format_weight,
        league_shrinkage_weight=league_weight,
        residual_stddev=residual_stddev,
        model_version=policy.model_version,
        evidence_through=max(row.observed_at for row in eligible),
        format_sample_size=len(format_rows),
        league_sample_size=len(league_rows),
    )


def _shrinkage_weight(sample_size: int, prior_strength: float) -> float:
    if sample_size <= 0:
        return 0.0
    return sample_size / (sample_size + prior_strength)


def _population_stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    center = mean(values)
    variance = mean((value - center) ** 2 for value in values)
    return sqrt(variance)
