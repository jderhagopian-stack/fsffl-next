"""Point-in-time empirical prior for players without ordinary projections.

This is an input-side prior only. It does not replace or refit the P0/Future
Forecast scorers. A caller must still apply the unchanged scoring authority and
retain this prior's provenance and uncertainty in the resulting forecast.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections import OrderedDict
import math
from statistics import mean, stdev
from typing import Iterable

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
STANDARD_COORDINATE = "standard_non_ppr"
PRIOR_VERSION = "historical_position_experience_age_empirical_v1"
CALIBRATION_VERSION = "sparse_prior_rolling_cqr_v2"


@dataclass(frozen=True)
class HistoricalOutcome:
    """One fully observed player-season outcome and its as-of feature facts."""

    player_id: str
    position: str
    season: int
    age_years: float | None
    experience_years: int | None
    fantasy_points: float
    scoring_coordinate: str
    observed_at: datetime


@dataclass(frozen=True)
class SparsePlayerProfile:
    """Canonical candidate features known at the requested evaluation time."""

    player_id: str
    position: str
    evaluation_season: int
    as_of: datetime
    age_years: float | None = None
    experience_years: int | None = None


@dataclass(frozen=True)
class SparsePriorForecast:
    player_id: str
    position: str
    evaluation_season: int
    mean: float
    stddev: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    sample_count: int
    training_season_max: int
    training_observed_through: datetime
    evidence_tier: str
    calibration_status: str = "uncalibrated"
    calibration_version: str | None = None
    calibration_sample_count: int = 0
    calibration_observed_through: datetime | None = None
    source: str = "fsffl:historical_empirical_sparse_prior"
    model_version: str = PRIOR_VERSION
    scoring_coordinate: str = STANDARD_COORDINATE


class SparsePriorAuthorityError(ValueError):
    """A stable, player-specific reason that the prior cannot be used."""

    def __init__(self, player_id: str, reason: str) -> None:
        self.player_id = player_id
        self.reason = reason
        super().__init__(f"sparse prior unavailable for {player_id}: {reason}")


@dataclass(frozen=True)
class PriorCalibrationCase:
    """One out-of-time prediction retained only for interval calibration."""

    position: str
    evidence_tier: str
    evaluation_season: int
    observed_at: datetime
    actual: float
    p10: float
    p25: float
    p75: float
    p90: float


@dataclass(frozen=True)
class PriorIntervalCalibration:
    position: str
    evidence_tier: str
    sample_count: int
    adjustment_50: float
    adjustment_80: float
    trained_through_season: int
    version: str = CALIBRATION_VERSION


def _age_band(age: float | None) -> str | None:
    if age is None or not math.isfinite(age):
        return None
    if age < 23:
        return "under_23"
    if age < 25:
        return "23_24"
    if age < 28:
        return "25_27"
    if age < 31:
        return "28_30"
    return "31_plus"


def _experience_band(experience: int | None) -> str | None:
    if experience is None:
        return None
    if experience < 0:
        return None
    if experience == 0:
        return "rookie"
    if experience <= 2:
        return "1_2"
    if experience <= 5:
        return "3_5"
    return "6_plus"


def _quantile(values: list[float], probability: float) -> float:
    """Linear empirical quantile, matching the common type-7 convention."""

    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


class HistoricalSparsePlayerPrior:
    """A frozen, no-fit-at-request-time, point-in-time empirical prior.

    The prior backs off from position × age × experience to broader position
    pools. It selects a pool only when at least ``minimum_sample`` fully observed
    historical outcomes are available, which gives at least ten observations in
    each nominal 10% tail at the default sample size. No missing season is
    converted to zero; zero is retained only when present as an observed outcome.
    """

    def __init__(
        self,
        outcomes: Iterable[HistoricalOutcome],
        *,
        minimum_sample: int = 100,
        history_window_seasons: int | None = 15,
    ) -> None:
        if minimum_sample < 20:
            raise ValueError("minimum_sample must be at least 20")
        if history_window_seasons is not None and history_window_seasons < 5:
            raise ValueError("history_window_seasons must be at least 5 or None")
        self._outcomes = tuple(outcomes)
        self.minimum_sample = minimum_sample
        self.history_window_seasons = history_window_seasons
        self._forecast_cache: OrderedDict[tuple[object, ...], tuple[object, ...]] = OrderedDict()
        self._validate_history()

    @staticmethod
    def _cached(
        cache: OrderedDict[tuple[object, ...], tuple[object, ...]],
        key: tuple[object, ...],
        value_factory,
        *,
        limit: int = 128,
    ) -> tuple[object, ...]:
        value = cache.get(key)
        if value is not None:
            cache.move_to_end(key)
            return value
        value = tuple(value_factory())
        cache[key] = value
        if len(cache) > limit:
            cache.popitem(last=False)
        return value

    def _validate_history(self) -> None:
        seen: set[tuple[str, int]] = set()
        for row in self._outcomes:
            key = (row.player_id, row.season)
            if key in seen:
                raise ValueError(f"duplicate historical player-season: {key}")
            seen.add(key)
            if not row.player_id.strip():
                raise ValueError("historical canonical player_id cannot be blank")
            if row.position not in SUPPORTED_POSITIONS:
                raise ValueError(f"unsupported historical position: {row.position}")
            if row.scoring_coordinate != STANDARD_COORDINATE:
                raise ValueError("sparse prior history must use standard_non_ppr points")
            if not math.isfinite(row.fantasy_points):
                raise ValueError("historical fantasy points must be finite")
            if row.age_years is not None and not math.isfinite(row.age_years):
                raise ValueError("historical age must be finite or missing")
            if row.age_years is not None and row.age_years < 0:
                raise ValueError("historical age cannot be negative")
            if row.experience_years is not None and row.experience_years < 0:
                raise ValueError("historical experience cannot be negative")
            if row.observed_at.tzinfo is None:
                raise ValueError("historical observed_at must be timezone-aware")

    def forecast(self, profile: SparsePlayerProfile) -> SparsePriorForecast:
        if not profile.player_id.strip():
            raise SparsePriorAuthorityError("<blank>", "canonical_identity_missing")
        if profile.position not in SUPPORTED_POSITIONS:
            raise SparsePriorAuthorityError(profile.player_id, "unsupported_position")
        if profile.as_of.tzinfo is None:
            raise SparsePriorAuthorityError(profile.player_id, "as_of_not_timezone_aware")
        if profile.age_years is not None and not math.isfinite(profile.age_years):
            raise SparsePriorAuthorityError(profile.player_id, "invalid_age")
        if profile.experience_years is not None and profile.experience_years < 0:
            raise SparsePriorAuthorityError(profile.player_id, "invalid_experience")

        # Training labels must be complete before the query's exact as-of time and
        # from seasons preceding the target season. Later evidence can never leak.
        exp_band = _experience_band(profile.experience_years)
        age_band = _age_band(profile.age_years)
        key = (
            profile.position,
            profile.evaluation_season,
            profile.as_of,
            age_band,
            exp_band,
        )

        def summarize() -> tuple[object, ...]:
            history = [
                row
                for row in self._outcomes
                if row.position == profile.position
                and row.season < profile.evaluation_season
                and (
                    self.history_window_seasons is None
                    or row.season >= profile.evaluation_season - self.history_window_seasons
                )
                and row.observed_at <= profile.as_of
            ]
            candidate_pools: list[tuple[str, list[HistoricalOutcome]]] = []
            if exp_band is not None and age_band is not None:
                candidate_pools.append(
                    (
                        "position_age_experience",
                        [
                            row
                            for row in history
                            if _age_band(row.age_years) == age_band
                            and _experience_band(row.experience_years) == exp_band
                        ],
                    )
                )
            if exp_band is not None:
                candidate_pools.append(
                    (
                        "position_experience",
                        [row for row in history if _experience_band(row.experience_years) == exp_band],
                    )
                )
            if age_band is not None:
                candidate_pools.append(
                    (
                        "position_age",
                        [row for row in history if _age_band(row.age_years) == age_band],
                    )
                )
            candidate_pools.append(("position", history))

            selected_tier, selected = next(
                (
                    (tier, pool)
                    for tier, pool in candidate_pools
                    if len(pool) >= self.minimum_sample
                ),
                ("", []),
            )
            if not selected:
                return ()
            points = [row.fantasy_points for row in selected]
            return (
                selected_tier,
                len(points),
                mean(points),
                stdev(points) if len(points) > 1 else 0.0,
                _quantile(points, 0.10),
                _quantile(points, 0.25),
                _quantile(points, 0.50),
                _quantile(points, 0.75),
                _quantile(points, 0.90),
                max(row.season for row in selected),
                max(row.observed_at for row in selected),
            )

        summary = self._cached(self._forecast_cache, key, summarize)
        if not summary:
            raise SparsePriorAuthorityError(profile.player_id, "insufficient_point_in_time_history")
        (
            selected_tier,
            sample_count,
            prior_mean,
            prior_stddev,
            p10,
            p25,
            p50,
            p75,
            p90,
            training_season_max,
            training_observed_through,
        ) = summary
        return SparsePriorForecast(
            player_id=profile.player_id,
            position=profile.position,
            evaluation_season=profile.evaluation_season,
            mean=float(prior_mean),
            stddev=float(prior_stddev),
            p10=float(p10),
            p25=float(p25),
            p50=float(p50),
            p75=float(p75),
            p90=float(p90),
            sample_count=int(sample_count),
            training_season_max=int(training_season_max),
            training_observed_through=training_observed_through,
            evidence_tier=str(selected_tier),
        )


class RollingConformalPriorCalibrator:
    """Finite-sample interval correction learned from rolling-origin cases.

    Each case must have been forecast before its actual outcome was observed. The
    The correction is fitted only from earlier target seasons and recalculated
    for the requested evaluation cutoff. A position-only pool is the fallback
    when a position × evidence-tier pool is too small.
    """

    def __init__(
        self,
        cases: Iterable[PriorCalibrationCase],
        *,
        minimum_sample: int = 100,
        calibration_window_seasons: int = 10,
    ) -> None:
        if minimum_sample < 20:
            raise ValueError("minimum_sample must be at least 20")
        if calibration_window_seasons < 5:
            raise ValueError("calibration_window_seasons must be at least 5")
        self._cases = tuple(cases)
        self.minimum_sample = minimum_sample
        self.calibration_window_seasons = calibration_window_seasons
        self._cases_by_position = {
            position: tuple(row for row in self._cases if row.position == position)
            for position in SUPPORTED_POSITIONS
        }
        self._cache: OrderedDict[tuple[object, ...], tuple[object, ...]] = OrderedDict()
        for row in self._cases:
            if row.position not in SUPPORTED_POSITIONS:
                raise ValueError(f"unsupported calibration position: {row.position}")
            if row.observed_at.tzinfo is None:
                raise ValueError("calibration observed_at must be timezone-aware")
            values = (row.actual, row.p10, row.p25, row.p75, row.p90)
            if any(not math.isfinite(value) for value in values):
                raise ValueError("calibration inputs must be finite")
            if (row.p10, row.p25, row.p75, row.p90) != tuple(
                sorted((row.p10, row.p25, row.p75, row.p90))
            ):
                raise ValueError("calibration interval endpoints must be ordered")
            if row.observed_at.year <= row.evaluation_season:
                raise ValueError("calibration outcome must be observed after its target season")

    @staticmethod
    def _conformal_adjustment(scores: list[float], coverage: float) -> float:
        ordered = sorted(scores)
        # Split-conformal finite-sample rank: ceil((n + 1) * coverage).
        rank = math.ceil((len(ordered) + 1) * coverage)
        if rank > len(ordered):
            raise ValueError("too few calibration cases for requested interval coverage")
        return ordered[rank - 1]

    def calibrate(
        self,
        forecast: SparsePriorForecast,
        *,
        as_of: datetime,
    ) -> SparsePriorForecast:
        if as_of.tzinfo is None:
            raise SparsePriorAuthorityError(forecast.player_id, "as_of_not_timezone_aware")
        key = (
            forecast.position,
            forecast.evidence_tier,
            forecast.evaluation_season,
            as_of,
        )

        def summarize() -> tuple[object, ...]:
            available = [
                case
                for case in self._cases_by_position.get(forecast.position, ())
                if case.evaluation_season < forecast.evaluation_season
                and case.evaluation_season
                >= forecast.evaluation_season - self.calibration_window_seasons
                and case.observed_at <= as_of
            ]
            exact_tier = [
                case for case in available if case.evidence_tier == forecast.evidence_tier
            ]
            if len(exact_tier) >= self.minimum_sample:
                selected = exact_tier
                calibration_tier = forecast.evidence_tier
            elif len(available) >= self.minimum_sample:
                selected = available
                calibration_tier = "position"
            else:
                return ()

            score_50 = [max(case.p25 - case.actual, case.actual - case.p75) for case in selected]
            score_80 = [max(case.p10 - case.actual, case.actual - case.p90) for case in selected]
            adjust_50 = self._conformal_adjustment(score_50, 0.50)
            adjust_80 = max(adjust_50, self._conformal_adjustment(score_80, 0.90))
            return (
                adjust_50,
                adjust_80,
                len(selected),
                calibration_tier,
                max(case.observed_at for case in selected),
            )

        correction = HistoricalSparsePlayerPrior._cached(self._cache, key, summarize)
        if not correction:
            raise SparsePriorAuthorityError(
                forecast.player_id, "insufficient_point_in_time_calibration"
            )
        adjust_50, adjust_80, calibration_count, calibration_tier, calibration_through = correction
        return SparsePriorForecast(
            **{
                **forecast.__dict__,
                "p10": forecast.p10 - adjust_80,
                "p25": forecast.p25 - adjust_50,
                "p75": forecast.p75 + adjust_50,
                "p90": forecast.p90 + adjust_80,
                "calibration_status": "rolling_conformal",
                "calibration_version": f"{CALIBRATION_VERSION}:{calibration_tier}",
                "calibration_sample_count": int(calibration_count),
                "calibration_observed_through": calibration_through,
            }
        )


def to_forecast_observation(
    profile: SparsePlayerProfile,
    prior: SparsePriorForecast,
    *,
    period_start: datetime,
    period_end: datetime,
) -> ForecastObservation:
    """Adapt the prior into the canonical Forecast observation contract."""

    if prior.player_id != profile.player_id:
        raise ValueError("sparse prior and Forecast subject identity mismatch")
    if prior.position != profile.position:
        raise ValueError("sparse prior and Forecast subject position mismatch")
    if prior.evaluation_season != profile.evaluation_season:
        raise ValueError("sparse prior and Forecast evaluation season mismatch")
    if prior.calibration_status != "rolling_conformal" or prior.calibration_version is None:
        raise ValueError("sparse prior uncertainty has not passed rolling conformal calibration")
    provenance_time = max(
        prior.training_observed_through,
        prior.calibration_observed_through or prior.training_observed_through,
    )
    if provenance_time > profile.as_of:
        raise ValueError("sparse prior evidence postdates Forecast as_of")
    return ForecastObservation(
        player_id=profile.player_id,
        position=Position(profile.position),
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=period_start,
        period_end=period_end,
        distribution=ForecastDistribution(
            mean=prior.mean,
            stddev=prior.stddev,
            p10=prior.p10,
            p25=prior.p25,
            p50=prior.p50,
            p75=prior.p75,
            p90=prior.p90,
        ),
        source=prior.source,
        model_version=prior.model_version,
        as_of=profile.as_of,
        provenance=Provenance(
            source=prior.source,
            retrieved_at=provenance_time,
            effective_at=provenance_time,
            source_version=(
                f"{prior.model_version}:{prior.scoring_coordinate}:"
                f"through-{prior.training_season_max}:n-{prior.sample_count}:"
                f"{prior.calibration_version}:n-{prior.calibration_sample_count}"
            ),
        ),
    )
