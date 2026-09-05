from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from math import sqrt

from fsffl.state.models import FrozenModel, LeagueRules, Provenance, RosterSlot

from .models import ForecastDistribution, ForecastMetric, ForecastObservation


class ScoringCoverageStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class ScoringCoverage(FrozenModel):
    status: ScoringCoverageStatus
    supported_rule_stats: tuple[str, ...]
    unsupported_rule_stats: tuple[str, ...]
    ignored_non_lineup_rule_stats: tuple[str, ...]
    model_version: str = "next2-league-scoring-bridge-v1"


# Canonical Sleeper scoring keys whose effects are exactly linear in the raw
# NEXT-2 forecast metrics.  This table is a provider-key translation only; the
# actual coefficient always comes from LeagueRules.scoring.
_SLEEPER_LINEAR_RULES: dict[str, ForecastMetric] = {
    "pass_yd": ForecastMetric.PASS_YARDS,
    "pass_td": ForecastMetric.PASS_TD,
    "pass_int": ForecastMetric.INTERCEPTIONS,
    "rush_yd": ForecastMetric.RUSH_YARDS,
    "rush_td": ForecastMetric.RUSH_TD,
    "rec": ForecastMetric.RECEPTIONS,
    "rec_yd": ForecastMetric.REC_YARDS,
    "rec_td": ForecastMetric.REC_TD,
}

# Sleeper may retain scoring settings for positions that are not in the league's
# starting lineup. They do not affect offensive player scoring and should not
# block an offensive forecast transformation when those lineup positions do not
# exist. This is intentionally narrow and prefix-based rather than a general
# "ignore unknown rules" escape hatch.
_DST_PREFIXES = (
    "blk_kick",
    "def_",
    "def_st_",
    "ff",
    "fum_rec",
    "fum_rec_td",
    "int",
    "pts_allow_",
    "safe",
    "sack",
    "st_",
    "tkl_loss",
)
_KICKER_PREFIXES = ("fgm", "fgmiss", "xpm", "xpmiss")


def _has_lineup_slot(rules: LeagueRules, slot: RosterSlot) -> bool:
    return any(item.slot == slot and item.count > 0 for item in rules.lineup)


def classify_scoring_coverage(rules: LeagueRules) -> ScoringCoverage:
    """Classify whether raw NEXT-2 offensive stats can reproduce league scoring.

    Any nonzero offensive scoring rule that cannot be represented by the current
    raw forecast metrics is explicit and blocks a COMPLETE result. Nothing is
    silently dropped. K/DST-only settings may be ignored only when that position
    is absent from the starting lineup.
    """

    supported: list[str] = []
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
        if not has_dst and stat.startswith(_DST_PREFIXES):
            ignored.append(stat)
            continue
        if not has_k and stat.startswith(_KICKER_PREFIXES):
            ignored.append(stat)
            continue
        unsupported.append(stat)

    return ScoringCoverage(
        status=(
            ScoringCoverageStatus.COMPLETE
            if not unsupported
            else ScoringCoverageStatus.INCOMPLETE
        ),
        supported_rule_stats=tuple(sorted(supported)),
        unsupported_rule_stats=tuple(sorted(unsupported)),
        ignored_non_lineup_rule_stats=tuple(sorted(ignored)),
    )


def derive_league_fantasy_point_forecasts(
    observations: tuple[ForecastObservation, ...],
    *,
    rules: LeagueRules,
    source: str = "fsffl:league_scored",
    model_version: str = "next2-league-scoring-bridge-v1",
) -> tuple[ForecastObservation, ...]:
    """Convert raw-stat forecasts into league-scored fantasy-point forecasts.

    Means use the league's exact canonical scoring coefficients. For uncertainty,
    v1 combines raw-stat marginal variances under an explicit independent-metric
    assumption; this is visible in the model version and can be replaced by a
    calibrated covariance model later. Unsupported nonzero scoring rules fail
    closed instead of producing a deceptively precise fantasy-point forecast.
    """

    coverage = classify_scoring_coverage(rules)
    if coverage.status != ScoringCoverageStatus.COMPLETE:
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
        variance = sum(
            (coefficient * item.distribution.stddev) ** 2
            for _, coefficient, item in active
        )
        effective = max(item.provenance.effective_at for _, _, item in active)
        retrieved = max(item.provenance.retrieved_at for _, _, item in active)
        provenance = Provenance(
            source=f"{source}[{first.source}]",
            retrieved_at=retrieved,
            effective_at=effective,
            source_version=model_version,
        )
        output.append(
            ForecastObservation(
                player_id=first.player_id,
                position=first.position,
                horizon=first.horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=first.period_start,
                period_end=first.period_end,
                distribution=ForecastDistribution(
                    mean=mean,
                    stddev=sqrt(max(variance, 0.0)),
                ),
                source=source,
                model_version=f"{model_version}:independent_metric_variance",
                as_of=first.as_of,
                provenance=provenance,
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: (
                item.player_id,
                item.horizon.value,
                item.period_start,
                item.source,
            ),
        )
    )
