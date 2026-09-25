from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from math import sqrt
from statistics import fmean
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, RosterSlot

from .models import ForecastMetric


class CalibrationScoringFingerprint(FrozenModel):
    """Exact scoring coordinate represented by one empirical calibration."""

    fingerprint_id: str
    subject_family: Literal["K", "DST"]
    formula: str
    rule_weights: tuple[tuple[str, float], ...]
    metric_weights: tuple[tuple[ForecastMetric, float], ...]

    @field_validator("fingerprint_id", "formula")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("calibration fingerprint text cannot be blank")
        return value

    @model_validator(mode="after")
    def unique_coordinates(self) -> "CalibrationScoringFingerprint":
        rules = [key for key, _value in self.rule_weights]
        metrics = [key for key, _value in self.metric_weights]
        if not rules or len(rules) != len(set(rules)):
            raise ValueError("fingerprint rule coordinates must be unique and non-empty")
        if not metrics or len(metrics) != len(set(metrics)):
            raise ValueError("fingerprint metric coordinates must be unique and non-empty")
        return self


class CalibrationFingerprintCompatibility(FrozenModel):
    fingerprint_id: str
    compatible: bool
    active_rule_weights: tuple[tuple[str, float], ...]
    missing_from_fingerprint: tuple[str, ...]
    coefficient_mismatches: tuple[str, ...]


K_REDUCED_2024_FINGERPRINT = CalibrationScoringFingerprint(
    fingerprint_id="k-2024-reduced-fgm-fgmiss-xpm-v1",
    subject_family="K",
    formula="3*FGM - (FGA-FGM) + XPM",
    rule_weights=(("fgm", 3.0), ("fgmiss", -1.0), ("xpm", 1.0)),
    metric_weights=(
        (ForecastMetric.FG_MADE, 4.0),
        (ForecastMetric.FG_ATTEMPT, -1.0),
        (ForecastMetric.XP_MADE, 1.0),
    ),
)

DST_REDUCED_2024_FINGERPRINT = CalibrationScoringFingerprint(
    fingerprint_id="dst-2024-reduced-sack-int-v1",
    subject_family="DST",
    formula="1*DST_SACK + 2*DST_INTERCEPTION",
    rule_weights=(("sack", 1.0), ("int", 2.0)),
    metric_weights=(
        (ForecastMetric.DST_SACK, 1.0),
        (ForecastMetric.DST_INTERCEPTION, 2.0),
    ),
)


def evaluate_calibration_fingerprint_compatibility(
    fingerprint: CalibrationScoringFingerprint,
    rules: LeagueRules,
) -> CalibrationFingerprintCompatibility:
    """Require exact family scoring identity before a relative error floor can promote."""

    slot = RosterSlot.K if fingerprint.subject_family == "K" else RosterSlot.DST
    has_slot = any(item.slot == slot and item.count > 0 for item in rules.lineup)
    if not has_slot:
        return CalibrationFingerprintCompatibility(
            fingerprint_id=fingerprint.fingerprint_id,
            compatible=False,
            active_rule_weights=(),
            missing_from_fingerprint=("required_lineup_slot_missing",),
            coefficient_mismatches=(),
        )

    if fingerprint.subject_family == "K":
        prefixes = ("fg", "xp")
        active = tuple(
            sorted(
                (item.stat, float(item.points))
                for item in rules.scoring
                if item.points != 0 and item.stat.startswith(prefixes)
            )
        )
    else:
        dst_prefixes = (
            "blk_kick", "def_", "def_st_", "ff", "fum_rec", "int",
            "pts_allow_", "safe", "sack", "tkl", "qb_hit", "pass_def",
            "yds_allow_", "three_and_out", "fourth_down_stop", "forced_punt",
        )
        active = tuple(
            sorted(
                (item.stat, float(item.points))
                for item in rules.scoring
                if item.points != 0 and item.stat.startswith(dst_prefixes)
            )
        )

    expected = dict(fingerprint.rule_weights)
    active_map = dict(active)
    missing = tuple(sorted(stat for stat in active_map if stat not in expected))
    mismatches = tuple(
        sorted(
            stat
            for stat, weight in active_map.items()
            if stat in expected and expected[stat] != weight
        )
    )
    omitted_expected = tuple(sorted(stat for stat in expected if stat not in active_map))
    incompatible = tuple(sorted(set(missing) | set(omitted_expected)))
    return CalibrationFingerprintCompatibility(
        fingerprint_id=fingerprint.fingerprint_id,
        compatible=not incompatible and not mismatches,
        active_rule_weights=active,
        missing_from_fingerprint=incompatible,
        coefficient_mismatches=mismatches,
    )


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


class KDstSeasonHoldoutSummary(FrozenModel):
    train_sample_size: Annotated[int, Field(ge=1)]
    holdout_sample_size: Annotated[int, Field(ge=1)]
    train_relative_rmse: Annotated[float, Field(ge=0.0)]
    holdout_relative_rmse: Annotated[float, Field(ge=0.0)]
    holdout_within_one_train_floor_rate: Annotated[float, Field(ge=0.0, le=1.0)]
    method: str = "subject_hash_holdout_v1:rmse_divided_by_subset_mean_projection"


def evaluate_k_dst_season_error_holdout(
    samples: tuple[KDstCalibrationSample, ...],
    *,
    minimum_independent_sources: int = 2,
    holdout_modulus: int = 5,
    holdout_bucket: int = 0,
) -> KDstSeasonHoldoutSummary:
    """Deterministic non-promoting holdout diagnostic for a scoring fingerprint."""

    if holdout_modulus < 2:
        raise ValueError("holdout_modulus must be at least two")
    if holdout_bucket < 0 or holdout_bucket >= holdout_modulus:
        raise ValueError("holdout_bucket must be within holdout_modulus")
    eligible = tuple(
        sample
        for sample in samples
        if sample.independent_source_count >= minimum_independent_sources
    )
    train: list[KDstCalibrationSample] = []
    holdout: list[KDstCalibrationSample] = []
    for sample in eligible:
        digest = sha256(sample.subject_key.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % holdout_modulus
        (holdout if bucket == holdout_bucket else train).append(sample)
    if not train or not holdout:
        raise ValueError("deterministic holdout split requires non-empty train and holdout")

    train_summary = fit_k_dst_season_error(
        tuple(train),
        minimum_independent_sources=minimum_independent_sources,
    )
    holdout_summary = fit_k_dst_season_error(
        tuple(holdout),
        minimum_independent_sources=minimum_independent_sources,
    )
    within = sum(
        1
        for sample in holdout
        if abs(sample.realized_points - sample.projected_points)
        <= train_summary.relative_rmse * abs(sample.projected_points)
    )
    return KDstSeasonHoldoutSummary(
        train_sample_size=len(train),
        holdout_sample_size=len(holdout),
        train_relative_rmse=train_summary.relative_rmse,
        holdout_relative_rmse=holdout_summary.relative_rmse,
        holdout_within_one_train_floor_rate=within / len(holdout),
    )


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
