"""Research-only evidence-updated neutral-schedule franchise strength.

Independent of Forecast, Simulation, and published reports. This is a
provisional team-strength estimator, not a calibrated win-probability model.
Historical evidence must be complete-league and generated before kickoff.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import erf, isfinite, sqrt
from statistics import mean, median
from typing import Sequence

MODEL_VERSION = "research-current-competitive-strength-v0.1"


def _aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _valid_number(value: float, label: str, *, strictly_positive: bool = False) -> None:
    if not isfinite(value) or value < 0 or (strictly_positive and value == 0):
        raise ValueError(f"{label} must be finite and {'positive' if strictly_positive else 'nonnegative'}")


@dataclass(frozen=True)
class CurrentTeamPrior:
    team_id: str
    projected_points: float  # standardized bye-neutral roster scoring projection
    weekly_scoring_sd: float  # ordinary game-to-game scoring noise
    correction_prior_sd: float  # uncertainty of systematic projection error
    optimized_starter_ids: frozenset[str]
    evidence_as_of: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if not self.team_id.strip() or not self.source_ref.strip():
            raise ValueError("prior must have team_id and source_ref")
        for key in ("projected_points", "weekly_scoring_sd", "correction_prior_sd"):
            _valid_number(getattr(self, key), key, strictly_positive=(key != "projected_points"))
        if not self.optimized_starter_ids:
            raise ValueError("prior optimized starter identities required for continuity")
        _aware(self.evidence_as_of, "evidence_as_of")


@dataclass(frozen=True)
class PregameTeamObservation:
    team_id: str
    week: int
    projected_points: float
    actual_points: float
    projected_weekly_sd: float
    optimized_starter_ids: frozenset[str]
    projection_computed_at: datetime
    week_first_kickoff_at: datetime
    week_completed_at: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if not self.team_id.strip() or not self.source_ref.strip():
            raise ValueError("observation must have team_id and source_ref")
        if self.week < 1:
            raise ValueError("observation week must be positive")
        for key in ("projected_points", "actual_points", "projected_weekly_sd"):
            _valid_number(getattr(self, key), key, strictly_positive=(key == "projected_weekly_sd"))
        if not self.optimized_starter_ids:
            raise ValueError("historical optimized starter identities required")
        for key in ("projection_computed_at", "week_first_kickoff_at", "week_completed_at"):
            _aware(getattr(self, key), key)
        if not self.projection_computed_at < self.week_first_kickoff_at < self.week_completed_at:
            raise ValueError("historical projection must predate first kickoff and completion")


@dataclass(frozen=True)
class StrengthCalibration:
    """Research hyperparameters; must be independently fitted and validated."""
    half_life_weeks: float = 4.0
    residual_clip_sd: float = 2.5
    minimum_observation_sd: float = 20.0

    def __post_init__(self) -> None:
        for key in ("half_life_weeks", "residual_clip_sd", "minimum_observation_sd"):
            _valid_number(getattr(self, key), key, strictly_positive=True)


@dataclass(frozen=True)
class CompetitiveStrengthRow:
    rank: int
    team_id: str
    base_points: float
    posterior_mean_points: float
    posterior_correction_points: float
    posterior_correction_sd: float
    posterior_predictive_sd: float
    neutral_allplay_win_rate: float
    prior_neutral_allplay_win_rate: float
    observed_weeks: int
    effective_observations: float
    model_version: str = MODEL_VERSION


def _pairwise_win(a_mean: float, a_sd: float, b_mean: float, b_sd: float) -> float:
    sd = sqrt(a_sd * a_sd + b_sd * b_sd)
    if sd == 0:
        return 1.0 if a_mean > b_mean else (0.0 if a_mean < b_mean else 0.5)
    return 0.5 * (1 + erf((a_mean - b_mean) / (sd * sqrt(2))))


def _continuity(current: frozenset[str], historical: frozenset[str]) -> float:
    return len(current & historical) / len(current | historical)


def estimate_competitive_strength(
    priors: Sequence[CurrentTeamPrior],
    observations: Sequence[PregameTeamObservation],
    *,
    as_of: datetime,
    next_week: int,
    calibration: StrengthCalibration = StrengthCalibration(),
) -> tuple[CompetitiveStrengthRow, ...]:
    """Estimate current roster strength from neutral priors and pregame residuals.

    Each historical residual is centered on its week's league-median projection
    error. Continuity of optimized starter identities and elapsed time attenuate
    its precision; large outliers are clipped. Historical results do not replace
    the current roster forecast. All-play probability is a peer-relative
    comparison, not an upcoming fixture or postseason probability.

    Caller must separately attest the authoritative first NFL kickoff, source
    freshness, present roster membership, and lineage of each submitted input.
    """
    _aware(as_of, "as_of")
    if next_week <= 1:
        raise ValueError("next_week must be at least 2")
    if len(priors) < 2:
        raise ValueError("need at least two current team priors")
    by_team = {p.team_id: p for p in priors}
    if len(by_team) != len(priors):
        raise ValueError("duplicate team priors")
    if any(p.evidence_as_of > as_of for p in priors):
        raise ValueError("current prior has future evidence")
    by_week: dict[int, dict[str, PregameTeamObservation]] = {}
    for obs in observations:
        if obs.team_id not in by_team:
            raise ValueError("observation references a team outside current league")
        if obs.week >= next_week or obs.week_completed_at > as_of:
            raise ValueError("future or incomplete weekly evidence is prohibited")
        rows = by_week.setdefault(obs.week, {})
        if obs.team_id in rows:
            raise ValueError("duplicate observation for team and week")
        rows[obs.team_id] = obs
    if any(set(rows) != set(by_team) for rows in by_week.values()):
        raise ValueError("weekly evidence must cover every league team or be omitted")
    if any(len({r.week_first_kickoff_at for r in rows.values()}) != 1 for rows in by_week.values()):
        raise ValueError("all observations for a week must share first kickoff")

    deltas: dict[str, float] = {}
    correction_sds: dict[str, float] = {}
    evidence_counts = {tid: 0.0 for tid in by_team}
    weekly_centers = {
        week: median(row.actual_points - row.projected_points for row in rows.values())
        for week, rows in by_week.items()
    }
    for tid, prior in by_team.items():
        precision = 1.0 / prior.correction_prior_sd ** 2
        numerator = 0.0
        for week, rows in by_week.items():
            obs = rows[tid]
            residual = obs.actual_points - obs.projected_points - weekly_centers[week]
            scale = max(obs.projected_weekly_sd, calibration.minimum_observation_sd)
            clipped = max(-calibration.residual_clip_sd * scale,
                          min(calibration.residual_clip_sd * scale, residual))
            age = next_week - week - 1
            reliability = 0.5 ** (age / calibration.half_life_weeks)
            reliability *= _continuity(prior.optimized_starter_ids, obs.optimized_starter_ids)
            precision_increment = reliability / (scale ** 2)
            precision += precision_increment
            numerator += precision_increment * clipped
            evidence_counts[tid] += reliability
        posterior_var = 1.0 / precision
        deltas[tid] = posterior_var * numerator
        correction_sds[tid] = sqrt(posterior_var)

    rows = []
    for tid, prior in by_team.items():
        posterior_mean = prior.projected_points + deltas[tid]
        predictive_sd = sqrt(prior.weekly_scoring_sd ** 2 + correction_sds[tid] ** 2)
        allplay = mean(
            _pairwise_win(
                posterior_mean, predictive_sd,
                other.projected_points + deltas[oid],
                sqrt(other.weekly_scoring_sd ** 2 + correction_sds[oid] ** 2)
            )
            for oid, other in by_team.items() if oid != tid
        )
        original_allplay = mean(
            _pairwise_win(
                prior.projected_points, prior.weekly_scoring_sd,
                other.projected_points, other.weekly_scoring_sd
            )
            for oid, other in by_team.items() if oid != tid
        )
        rows.append((tid, prior, posterior_mean, predictive_sd, allplay, original_allplay))
    rows.sort(key=lambda row: (-row[4], row[0]))
    return tuple(
        CompetitiveStrengthRow(
            rank=index, team_id=tid,
            base_points=prior.projected_points,
            posterior_mean_points=posterior_mean,
            posterior_correction_points=deltas[tid],
            posterior_correction_sd=correction_sds[tid],
            posterior_predictive_sd=predictive_sd,
            neutral_allplay_win_rate=allplay,
            prior_neutral_allplay_win_rate=original_allplay,
            observed_weeks=len(by_week),
            effective_observations=evidence_counts[tid],
        )
        for index, (tid, prior, posterior_mean, predictive_sd, allplay, original_allplay)
        in enumerate(rows, start=1)
    )
