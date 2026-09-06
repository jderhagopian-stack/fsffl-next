from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from math import sqrt

from fsffl.state.models import FrozenModel, LeagueRules, Position, Provenance, RosterSlot

from .models import ForecastDistribution, ForecastMetric, ForecastObservation


class ScoringCoverageStatus(StrEnum):
    COMPLETE = "complete"
    PROVISIONAL = "provisional"
    INCOMPLETE = "incomplete"


class ScoringCoverage(FrozenModel):
    status: ScoringCoverageStatus
    supported_rule_stats: tuple[str, ...]
    provisional_residual_rule_stats: tuple[str, ...] = ()
    unsupported_rule_stats: tuple[str, ...]
    ignored_non_lineup_rule_stats: tuple[str, ...]
    model_version: str = "next2-league-scoring-bridge-v2"


@dataclass(frozen=True)
class ProvisionalResidualPrior:
    mean_events: float
    stddev_events: float
    eligible_positions: frozenset[Position] | None = None


_SLEEPER_LINEAR_RULES: dict[str, ForecastMetric] = {
    "pass_yd": ForecastMetric.PASS_YARDS,
    "pass_td": ForecastMetric.PASS_TD,
    "pass_int": ForecastMetric.INTERCEPTIONS,
    "rush_yd": ForecastMetric.RUSH_YARDS,
    "rush_td": ForecastMetric.RUSH_TD,
    "rec": ForecastMetric.RECEPTIONS,
    "rec_yd": ForecastMetric.REC_YARDS,
    "rec_td": ForecastMetric.REC_TD,
    "fum_lost": ForecastMetric.FUMBLES_LOST,
}

_TWO_POINT_RULES: dict[str, ForecastMetric] = {
    "pass_2pt": ForecastMetric.PASS_TD,
    "rush_2pt": ForecastMetric.RUSH_TD,
    "rec_2pt": ForecastMetric.REC_TD,
}

# Explicit bounded beta priors for very rare player-scoring events that current
# vetted projection sources do not expose. These are deliberately tiny and live
# in Forecast, not Presentation. They are provisional, versioned, and intended to
# be replaced by empirical PIT historical rates. They keep known effects from
# disappearing while avoiding a hard pipeline failure over immaterial tail events.
_SKILL = frozenset({Position.RB, Position.WR, Position.TE})
_RARE_EVENT_PRIORS: dict[str, ProvisionalResidualPrior] = {
    "fum_rec": ProvisionalResidualPrior(mean_events=0.03, stddev_events=0.08),
    "fum_rec_td": ProvisionalResidualPrior(mean_events=0.003, stddev_events=0.02),
    "st_ff": ProvisionalResidualPrior(mean_events=0.005, stddev_events=0.03, eligible_positions=_SKILL),
    "st_fum_rec": ProvisionalResidualPrior(mean_events=0.005, stddev_events=0.03, eligible_positions=_SKILL),
    "st_td": ProvisionalResidualPrior(mean_events=0.02, stddev_events=0.10, eligible_positions=_SKILL),
}
_TWO_POINT_CONVERSION_PER_TD_PRIOR = 0.025

_DST_PREFIXES = (
    "blk_kick",
    "def_",
    "def_st_",
    "ff",
    "int",
    "pts_allow_",
    "safe",
    "sack",
    "tkl_loss",
)
_KICKER_PREFIXES = ("fgm", "fgmiss", "xpm", "xpmiss")


def _has_lineup_slot(rules: LeagueRules, slot: RosterSlot) -> bool:
    return any(item.slot == slot and item.count > 0 for item in rules.lineup)


def classify_scoring_coverage(rules: LeagueRules) -> ScoringCoverage:
    supported: list[str] = []
    provisional: list[str] = []
    unsupported: list[str] = []
    ignored: list[str] = []
    has_dst = _has_lineup_slot(rules, RosterSlot.DST)
    has_k = _has_lineup_slot(rules, RosterSlot.K)

    for rule in rules.scoring:
        if rule.points == 0:
            continue
        stat = rule.stat
        if stat in _SLEEPER_LINEAR_RULES:
            supported.append(stat)
            continue
        if stat in _TWO_POINT_RULES or stat in _RARE_EVENT_PRIORS:
            provisional.append(stat)
            continue
        if not has_dst and stat.startswith(_DST_PREFIXES):
            ignored.append(stat)
            continue
        if not has_k and stat.startswith(_KICKER_PREFIXES):
            ignored.append(stat)
            continue
        unsupported.append(stat)

    if unsupported:
        status = ScoringCoverageStatus.INCOMPLETE
    elif provisional:
        status = ScoringCoverageStatus.PROVISIONAL
    else:
        status = ScoringCoverageStatus.COMPLETE
    return ScoringCoverage(
        status=status,
        supported_rule_stats=tuple(sorted(supported)),
        provisional_residual_rule_stats=tuple(sorted(provisional)),
        unsupported_rule_stats=tuple(sorted(unsupported)),
        ignored_non_lineup_rule_stats=tuple(sorted(ignored)),
    )


def _provisional_residual(
    *,
    position: Position,
    by_metric: dict[ForecastMetric, ForecastObservation],
    rules: LeagueRules,
) -> tuple[float, float, tuple[str, ...]]:
    mean_points = 0.0
    variance_points = 0.0
    applied: list[str] = []
    for rule in rules.scoring:
        if rule.points == 0:
            continue
        stat = rule.stat
        td_metric = _TWO_POINT_RULES.get(stat)
        if td_metric is not None:
            td = by_metric.get(td_metric)
            if td is None:
                continue
            expected_events = max(0.0, td.distribution.mean) * _TWO_POINT_CONVERSION_PER_TD_PRIOR
            mean_points += rule.points * expected_events
            variance_points += (rule.points ** 2) * max(expected_events, 0.0)
            applied.append(stat)
            continue
        prior = _RARE_EVENT_PRIORS.get(stat)
        if prior is None:
            continue
        if prior.eligible_positions is not None and position not in prior.eligible_positions:
            continue
        mean_points += rule.points * prior.mean_events
        variance_points += (rule.points * prior.stddev_events) ** 2
        applied.append(stat)
    return mean_points, variance_points, tuple(sorted(applied))


def derive_league_fantasy_point_forecasts(
    observations: tuple[ForecastObservation, ...],
    *,
    rules: LeagueRules,
    source: str = "fsffl:league_scored",
    model_version: str = "next2-league-scoring-bridge-v2",
) -> tuple[ForecastObservation, ...]:
    coverage = classify_scoring_coverage(rules)
    if coverage.status == ScoringCoverageStatus.INCOMPLETE:
        raise ValueError(
            "league scoring cannot be reproduced from current raw forecast metrics; "
            f"unsupported rules: {list(coverage.unsupported_rule_stats)}"
        )

    coefficient_by_metric: dict[ForecastMetric, float] = {}
    for rule in rules.scoring:
        metric = _SLEEPER_LINEAR_RULES.get(rule.stat)
        if metric is not None and rule.points != 0:
            coefficient_by_metric[metric] = coefficient_by_metric.get(metric, 0.0) + rule.points

    grouped: dict[tuple[object, ...], list[ForecastObservation]] = defaultdict(list)
    for observation in observations:
        if observation.metric == ForecastMetric.FANTASY_POINTS:
            continue
        key = (
            observation.player_id,
            observation.position,
            observation.horizon,
            observation.period_start,
            observation.period_end,
            observation.as_of,
            observation.source,
            observation.model_version,
        )
        grouped[key].append(observation)

    output: list[ForecastObservation] = []
    for items in grouped.values():
        by_metric = {item.metric: item for item in items}
        active = [
            (metric, coefficient, by_metric[metric])
            for metric, coefficient in coefficient_by_metric.items()
            if metric in by_metric
        ]
        if not active:
            continue
        first = items[0]
        mean = sum(coefficient * item.distribution.mean for _, coefficient, item in active)
        variance = sum((coefficient * item.distribution.stddev) ** 2 for _, coefficient, item in active)
        residual_mean, residual_variance, applied_residuals = _provisional_residual(
            position=first.position,
            by_metric=by_metric,
            rules=rules,
        )
        mean += residual_mean
        variance += residual_variance
        effective = max(item.provenance.effective_at for _, _, item in active)
        retrieved = max(item.provenance.retrieved_at for _, _, item in active)
        provenance = Provenance(
            source=f"{source}[{first.source}]",
            retrieved_at=retrieved,
            effective_at=effective,
            source_version=model_version,
        )
        suffix = ":independent_metric_variance"
        if applied_residuals:
            suffix += ":bounded_provisional_residual_v1"
        output.append(
            ForecastObservation(
                player_id=first.player_id,
                position=first.position,
                horizon=first.horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=first.period_start,
                period_end=first.period_end,
                distribution=ForecastDistribution(mean=mean, stddev=sqrt(max(variance, 0.0))),
                source=source,
                model_version=f"{model_version}{suffix}",
                as_of=first.as_of,
                provenance=provenance,
            )
        )

    return tuple(sorted(output, key=lambda item: (item.player_id, item.horizon.value, item.period_start, item.source)))
