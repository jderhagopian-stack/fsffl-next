"""Research-only weekly Power Index (v2); no production routing or persistence.

This is an editorial ordinal ranking, NOT a calibrated win probability. Callers
must supply complete, point-in-time evidence produced before the target week.
Do not reuse this output as matchup odds or future-win simulation input.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, isfinite, sqrt
from statistics import fmean
from typing import Sequence


POWER_INDEX_RESEARCH_VERSION = "weekly-power-index-research-v2"


@dataclass(frozen=True)
class PowerIndexWeights:
    roster: float = 0.40
    season: float = 0.35
    momentum: float = 0.15
    record: float = 0.10

    def __post_init__(self) -> None:
        values = (self.roster, self.season, self.momentum, self.record)
        if not all(isfinite(value) and value >= 0 for value in values):
            raise ValueError("power index weights must be finite and nonnegative")
        if abs(sum(values) - 1.0) > 1e-10:
            raise ValueError("power index weights must sum to 1")


@dataclass(frozen=True)
class PowerIndexEvidence:
    """One team's independently prepared frozen evidence.

    neutral_weekly_mean/stddev: standardized future scoring evidence WITHOUT
    scheduled bye-week suppression; this does not mean an assumed healthy team.
    season_allplay: completed games only, ties count half.
    recent/earlier_allplay: disjoint historical windows for the momentum delta.
    record_win_rate: scheduled wins + half scheduled ties per completed game.
    """

    team_id: str
    neutral_weekly_mean: float
    neutral_weekly_stddev: float
    season_allplay: float
    recent_allplay: float
    earlier_allplay: float
    record_win_rate: float

    def __post_init__(self) -> None:
        if not self.team_id.strip():
            raise ValueError("team_id is required")
        values = (
            self.neutral_weekly_mean, self.neutral_weekly_stddev,
            self.season_allplay, self.recent_allplay,
            self.earlier_allplay, self.record_win_rate,
        )
        if not all(isfinite(x) for x in values):
            raise ValueError("power index evidence must be finite")
        if self.neutral_weekly_stddev < 0 or self.neutral_weekly_mean < 0:
            raise ValueError("scoring distribution cannot have negative mean or stddev")
        if any(not 0 <= x <= 1 for x in values[2:]):
            raise ValueError("all-play and record fractions must be within [0, 1]")


@dataclass(frozen=True)
class PowerIndexRanking:
    rank: int
    team_id: str
    score: float
    neutral_model_win_rate: float
    season_allplay: float
    momentum_change: float
    record_win_rate: float
    model_version: str = POWER_INDEX_RESEARCH_VERSION


def _win_probability(left: PowerIndexEvidence, right: PowerIndexEvidence) -> float:
    stddev = sqrt(left.neutral_weekly_stddev**2 + right.neutral_weekly_stddev**2)
    if stddev == 0:
        return 1.0 if left.neutral_weekly_mean > right.neutral_weekly_mean else (
            0.0 if left.neutral_weekly_mean < right.neutral_weekly_mean else 0.5
        )
    z = (left.neutral_weekly_mean - right.neutral_weekly_mean) / stddev
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def rank_weekly_power(
    evidence: Sequence[PowerIndexEvidence],
    *,
    weights: PowerIndexWeights = PowerIndexWeights(),
) -> tuple[PowerIndexRanking, ...]:
    """Return a stable, league-agnostic ordinal ranking of complete evidence.

    The model component is the expected win fraction against each of the other
    teams in this specific league, not a constructed league-average opponent.
    Momentum is centered at 0.5 and shrinks recent-vs-earlier change by half.
    This prototype does not tune weights or claim calibrated absolute scores.
    """
    if len(evidence) < 2:
        raise ValueError("at least two teams required")
    ids = [item.team_id for item in evidence]
    if len(ids) != len(set(ids)):
        raise ValueError("each team_id must appear exactly once")
    scoring = []
    for row in evidence:
        model_strength = fmean(
            _win_probability(row, peer) for peer in evidence if peer.team_id != row.team_id
        )
        momentum_change = 0.5 + 0.5 * (row.recent_allplay - row.earlier_allplay)
        score = 100.0 * (
            weights.roster * model_strength
            + weights.season * row.season_allplay
            + weights.momentum * momentum_change
            + weights.record * row.record_win_rate
        )
        scoring.append((row.team_id, score, model_strength, row.season_allplay,
                        momentum_change, row.record_win_rate))
    scoring.sort(key=lambda item: (-item[1], item[0]))
    return tuple(PowerIndexRanking(
        rank=index, team_id=tid, score=score, neutral_model_win_rate=model,
        season_allplay=season, momentum_change=momentum,
        record_win_rate=record,
    ) for index, (tid, score, model, season, momentum, record) in enumerate(scoring, start=1))
