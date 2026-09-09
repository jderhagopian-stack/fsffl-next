from __future__ import annotations

from collections import defaultdict
from math import erf, sqrt
from statistics import fmean, median, pstdev

from fsffl.state.models import FrozenModel

from .models import OptimizedTeamLineup
from .simulation import RegularSeasonSimulationResult, WeeklyTeamScoringDistribution


class TeamScoringDispersionDiagnostic(FrozenModel):
    """Read-only diagnostic of one team's scoring signal versus weekly noise."""

    team_id: str
    average_weekly_mean: float
    minimum_weekly_mean: float
    maximum_weekly_mean: float
    average_weekly_stddev: float
    average_weekly_cv: float | None
    league_mean_delta: float
    neutral_opponent_win_probability: float
    expected_wins: float
    fallback_starter_count: int = 0
    starter_count: int = 0
    fallback_starter_share: float | None = None


class LeagueScoringDispersionDiagnostic(FrozenModel):
    """Diagnostic evidence for whether projected standings are over-compressed.

    This object does not recalibrate Forecast or Simulation. It exposes the scale
    of between-team scoring differences relative to ordinary within-week scoring
    noise so calibration work can target the earliest authoritative cause.
    """

    teams: tuple[TeamScoringDispersionDiagnostic, ...]
    league_average_weekly_mean: float
    between_team_mean_stddev: float
    median_within_team_weekly_stddev: float
    signal_to_noise_ratio: float
    best_worst_weekly_mean_spread: float
    best_worst_expected_win_spread: float
    expected_win_stddev: float
    fallback_starter_count: int
    total_starter_count: int
    fallback_starter_share: float | None
    model_version: str = "next4-scoring-dispersion-diagnostic-v1"


def _normal_win_probability(
    left_mean: float,
    left_stddev: float,
    right_mean: float,
    right_stddev: float,
) -> float:
    difference_stddev = sqrt(left_stddev * left_stddev + right_stddev * right_stddev)
    if difference_stddev <= 0:
        if left_mean > right_mean:
            return 1.0
        if left_mean < right_mean:
            return 0.0
        return 0.5
    z = (left_mean - right_mean) / difference_stddev
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def build_scoring_dispersion_diagnostic(
    weekly_scoring: tuple[WeeklyTeamScoringDistribution, ...],
    simulation: RegularSeasonSimulationResult,
    *,
    baseline_lineups: dict[str, OptimizedTeamLineup] | None = None,
    fallback_player_ids: set[str] | frozenset[str] = frozenset(),
) -> LeagueScoringDispersionDiagnostic:
    """Measure score separation before changing any Forecast/Simulation parameter."""

    if not weekly_scoring:
        raise ValueError("scoring dispersion diagnostic requires weekly scoring evidence")

    rows_by_team: dict[str, list[WeeklyTeamScoringDistribution]] = defaultdict(list)
    for row in weekly_scoring:
        rows_by_team[row.team_id].append(row)
    outcomes = {row.team_id: row for row in simulation.outcomes}
    if set(rows_by_team) != set(outcomes):
        raise ValueError("weekly scoring and simulation teams must match exactly")

    team_average_means = {
        team_id: fmean(row.mean_points for row in rows)
        for team_id, rows in rows_by_team.items()
    }
    team_average_stddevs = {
        team_id: fmean(row.stddev_points for row in rows)
        for team_id, rows in rows_by_team.items()
    }
    league_average_mean = fmean(team_average_means.values())
    neutral_stddev = median(team_average_stddevs.values())

    team_rows: list[TeamScoringDispersionDiagnostic] = []
    total_fallback_starters = 0
    total_starters = 0
    for team_id in sorted(rows_by_team):
        rows = rows_by_team[team_id]
        mean = team_average_means[team_id]
        stddev = team_average_stddevs[team_id]
        lineup = (baseline_lineups or {}).get(team_id)
        starter_ids = {item.player_id for item in lineup.assignments} if lineup is not None else set()
        fallback_count = len(starter_ids.intersection(fallback_player_ids))
        starter_count = len(starter_ids)
        total_fallback_starters += fallback_count
        total_starters += starter_count
        team_rows.append(
            TeamScoringDispersionDiagnostic(
                team_id=team_id,
                average_weekly_mean=mean,
                minimum_weekly_mean=min(row.mean_points for row in rows),
                maximum_weekly_mean=max(row.mean_points for row in rows),
                average_weekly_stddev=stddev,
                average_weekly_cv=(stddev / mean if mean > 0 else None),
                league_mean_delta=mean - league_average_mean,
                neutral_opponent_win_probability=_normal_win_probability(
                    mean,
                    stddev,
                    league_average_mean,
                    neutral_stddev,
                ),
                expected_wins=outcomes[team_id].expected_wins,
                fallback_starter_count=fallback_count,
                starter_count=starter_count,
                fallback_starter_share=(fallback_count / starter_count if starter_count else None),
            )
        )

    mean_values = list(team_average_means.values())
    expected_wins = [outcomes[team_id].expected_wins for team_id in sorted(outcomes)]
    between = pstdev(mean_values) if len(mean_values) > 1 else 0.0
    within = median(team_average_stddevs.values())
    return LeagueScoringDispersionDiagnostic(
        teams=tuple(team_rows),
        league_average_weekly_mean=league_average_mean,
        between_team_mean_stddev=between,
        median_within_team_weekly_stddev=within,
        signal_to_noise_ratio=(between / within if within > 0 else 0.0),
        best_worst_weekly_mean_spread=max(mean_values) - min(mean_values),
        best_worst_expected_win_spread=max(expected_wins) - min(expected_wins),
        expected_win_stddev=(pstdev(expected_wins) if len(expected_wins) > 1 else 0.0),
        fallback_starter_count=total_fallback_starters,
        total_starter_count=total_starters,
        fallback_starter_share=(total_fallback_starters / total_starters if total_starters else None),
    )
