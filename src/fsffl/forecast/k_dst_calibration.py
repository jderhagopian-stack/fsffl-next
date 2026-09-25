from __future__ import annotations

from collections import defaultdict
from math import sqrt
from statistics import fmean
from typing import Annotated

from pydantic import Field, field_validator

from fsffl.state.models import FrozenModel


class KDstCalibrationSample(FrozenModel):
    subject_key: str
    season: Annotated[int, Field(ge=2000)]
    projected_points: float
    realized_points: float
    independent_source_count: Annotated[int, Field(ge=1)]

    @field_validator("subject_key")
    @classmethod
    def require_subject_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("subject_key cannot be empty")
        return value


class KDstSeasonErrorSummary(FrozenModel):
    sample_size: Annotated[int, Field(ge=1)]
    seasons: tuple[int, ...]
    relative_rmse: Annotated[float, Field(ge=0.0)]
    mean_projection: float
    method: str = "equal_weight_2plus_independent_sources:rmse_divided_by_mean_projection"


class WeeklyRealizedScore(FrozenModel):
    subject_key: str
    season: Annotated[int, Field(ge=2000)]
    week: Annotated[int, Field(ge=1, le=18)]
    points: float


class WeeklyVolatilitySummary(FrozenModel):
    observation_count: Annotated[int, Field(ge=2)]
    subject_count: Annotated[int, Field(ge=1)]
    seasons: tuple[int, ...]
    pooled_coefficient_of_variation: Annotated[float, Field(ge=0.0)]
    method: str = "direct_realized_game_scores:within_subject_centered_pooled_cv"


def fit_k_dst_season_error(
    samples: tuple[KDstCalibrationSample, ...],
    *,
    minimum_independent_sources: int = 2,
) -> KDstSeasonErrorSummary:
    """Fit a research residual scale without promoting it into production authority."""

    eligible = [
        sample
        for sample in samples
        if sample.independent_source_count >= minimum_independent_sources
    ]
    if not eligible:
        raise ValueError("no calibration samples satisfy the independent-source gate")

    mean_projection = fmean(sample.projected_points for sample in eligible)
    if mean_projection <= 0:
        raise ValueError("mean projection must be positive for relative RMSE calibration")
    rmse = sqrt(
        fmean(
            (sample.realized_points - sample.projected_points) ** 2
            for sample in eligible
        )
    )
    return KDstSeasonErrorSummary(
        sample_size=len(eligible),
        seasons=tuple(sorted({sample.season for sample in eligible})),
        relative_rmse=rmse / mean_projection,
        mean_projection=mean_projection,
    )


def fit_k_dst_weekly_volatility(
    scores: tuple[WeeklyRealizedScore, ...],
) -> WeeklyVolatilitySummary:
    """Fit weekly volatility from realized game scores, never season_mean / 17.

    Scores are centered within subject-season before pooling so differences in
    average K or D/ST strength do not masquerade as week-to-week volatility.
    """

    by_subject: dict[tuple[str, int], list[float]] = defaultdict(list)
    for score in scores:
        by_subject[(score.subject_key, score.season)].append(score.points)

    eligible = {key: values for key, values in by_subject.items() if len(values) >= 2}
    if not eligible:
        raise ValueError("weekly volatility requires at least one subject with two games")

    residuals: list[float] = []
    subject_means: list[float] = []
    for values in eligible.values():
        subject_mean = fmean(values)
        subject_means.append(subject_mean)
        residuals.extend(value - subject_mean for value in values)

    pooled_mean = fmean(abs(value) for value in subject_means)
    if pooled_mean <= 0:
        raise ValueError("weekly volatility requires positive subject scoring means")
    pooled_stddev = sqrt(fmean(value ** 2 for value in residuals))

    return WeeklyVolatilitySummary(
        observation_count=sum(len(values) for values in eligible.values()),
        subject_count=len(eligible),
        seasons=tuple(sorted({season for _, season in eligible})),
        pooled_coefficient_of_variation=pooled_stddev / pooled_mean,
    )
