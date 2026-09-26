from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import sqrt
from typing import Literal

from fsffl.state.models import FrozenModel, LeagueRules, Position, Provenance, RosterSlot

from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from .supplemental_coordinate import SUPPLEMENTAL_COORDINATE_SOURCE


class ScoringCoverageStatus(StrEnum):
    COMPLETE = "complete"
    PROVISIONAL = "provisional"
    INCOMPLETE = "incomplete"


class ForecastCapabilityStatus(StrEnum):
    FULL = "FULL"
    PARTIAL_PROVISIONAL = "PARTIAL_PROVISIONAL"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ScoringCoverage(FrozenModel):
    status: ScoringCoverageStatus
    capability_status: ForecastCapabilityStatus
    supported_rule_stats: tuple[str, ...]
    provisional_residual_rule_stats: tuple[str, ...] = ()
    unsupported_rule_stats: tuple[str, ...]
    ignored_non_lineup_rule_stats: tuple[str, ...]
    separate_subject_rule_stats: tuple[str, ...] = ()
    blocks_full_downstream_authority: bool = False
    model_version: str = "next2-league-scoring-bridge-v4:subject-family-isolation"


class ForecastRuleFamilyCoverage(FrozenModel):
    family: Literal["player_offense", "kicker", "dst"]
    status: ForecastCapabilityStatus
    supported_rule_stats: tuple[str, ...] = ()
    provisional_rule_stats: tuple[str, ...] = ()
    omitted_rule_stats: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    blocks_full_downstream_authority: bool


class PartialFantasyPointForecast(FrozenModel):
    authority_tier: Literal["partial_provisional"] = "partial_provisional"
    player_id: str
    position: Position
    horizon: ForecastHorizon
    period_start: datetime
    period_end: datetime
    distribution: ForecastDistribution
    supported_rule_stats: tuple[str, ...]
    omitted_rule_stats: tuple[str, ...]
    omission_reasons: tuple[str, ...]
    source: str
    model_version: str
    as_of: datetime
    provenance: Provenance


class LeagueScoringResult(FrozenModel):
    authoritative_forecasts: tuple[ForecastObservation, ...]
    partial_forecasts: tuple[PartialFantasyPointForecast, ...]
    coverage: ScoringCoverage
    family_coverage: tuple[ForecastRuleFamilyCoverage, ...]


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

# A scored fantasy-points observation is authoritative only when every material
# component in each active player domain is present. Without this guard a QB can
# retain pass/rush yards while TD metrics fall below ensemble coverage and still
# be mislabeled as a complete full-season fantasy projection.
_MATERIAL_SCORING_DOMAINS: tuple[frozenset[ForecastMetric], ...] = (
    frozenset({ForecastMetric.PASS_YARDS, ForecastMetric.PASS_TD, ForecastMetric.INTERCEPTIONS}),
    frozenset({ForecastMetric.RUSH_YARDS, ForecastMetric.RUSH_TD}),
    frozenset({ForecastMetric.RECEPTIONS, ForecastMetric.REC_YARDS, ForecastMetric.REC_TD}),
)

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
    separate: list[str] = []
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
        if stat.startswith(_DST_PREFIXES):
            (separate if has_dst else ignored).append(stat)
            continue
        if stat.startswith(_KICKER_PREFIXES):
            (separate if has_k else ignored).append(stat)
            continue
        unsupported.append(stat)

    if unsupported:
        status = ScoringCoverageStatus.INCOMPLETE
        capability = (
            ForecastCapabilityStatus.PARTIAL_PROVISIONAL
            if supported or provisional
            else ForecastCapabilityStatus.UNSUPPORTED
        )
        blocks = True
    elif provisional:
        status = ScoringCoverageStatus.PROVISIONAL
        capability = ForecastCapabilityStatus.PARTIAL_PROVISIONAL
        # Existing bounded residual priors remain governed by their prior contract.
        # Merely labeling them provisional must not regress accepted leagues.
        blocks = False
    else:
        status = ScoringCoverageStatus.COMPLETE
        capability = ForecastCapabilityStatus.FULL
        blocks = False
    return ScoringCoverage(
        status=status,
        capability_status=capability,
        supported_rule_stats=tuple(sorted(supported)),
        provisional_residual_rule_stats=tuple(sorted(provisional)),
        unsupported_rule_stats=tuple(sorted(unsupported)),
        ignored_non_lineup_rule_stats=tuple(sorted(ignored)),
        separate_subject_rule_stats=tuple(sorted(separate)),
        blocks_full_downstream_authority=blocks,
    )


def classify_forecast_rule_family_coverage(
    rules: LeagueRules,
) -> tuple[ForecastRuleFamilyCoverage, ...]:
    """Report authority by scoring subject family without cross-family collapse."""

    offense = classify_scoring_coverage(rules)
    offense_reasons: list[str] = []
    if offense.unsupported_rule_stats:
        offense_reasons.append("unsupported_player_offense_rules")
    if offense.provisional_residual_rule_stats:
        offense_reasons.append("bounded_provisional_residual_rules")
    if not offense_reasons:
        offense_reasons.append("all_active_player_offense_rules_supported")

    output: list[ForecastRuleFamilyCoverage] = [
        ForecastRuleFamilyCoverage(
            family="player_offense",
            status=offense.capability_status,
            supported_rule_stats=offense.supported_rule_stats,
            provisional_rule_stats=offense.provisional_residual_rule_stats,
            omitted_rule_stats=offense.unsupported_rule_stats,
            reason_codes=tuple(offense_reasons),
            blocks_full_downstream_authority=offense.blocks_full_downstream_authority,
        )
    ]

    for family, slot, prefixes in (
        ("kicker", RosterSlot.K, _KICKER_PREFIXES),
        ("dst", RosterSlot.DST, _DST_PREFIXES),
    ):
        active = tuple(
            sorted(
                rule.stat
                for rule in rules.scoring
                if rule.points != 0 and rule.stat.startswith(prefixes)
            )
        )
        if not _has_lineup_slot(rules, slot):
            output.append(
                ForecastRuleFamilyCoverage(
                    family=family,
                    status=ForecastCapabilityStatus.NOT_APPLICABLE,
                    omitted_rule_stats=(),
                    reason_codes=("lineup_slot_not_active",),
                    blocks_full_downstream_authority=False,
                )
            )
            continue
        output.append(
            ForecastRuleFamilyCoverage(
                family=family,
                status=ForecastCapabilityStatus.UNSUPPORTED,
                omitted_rule_stats=active,
                reason_codes=("separate_k_dst_forecast_authority_required",),
                blocks_full_downstream_authority=True,
            )
        )
    return tuple(output)


def _missing_material_scored_metrics(
    *,
    by_metric: dict[ForecastMetric, ForecastObservation],
    coefficient_by_metric: dict[ForecastMetric, float],
) -> tuple[ForecastMetric, ...]:
    missing: set[ForecastMetric] = set()
    for domain in _MATERIAL_SCORING_DOMAINS:
        configured = {
            metric
            for metric in domain
            if coefficient_by_metric.get(metric, 0.0) != 0.0
        }
        if not configured:
            continue
        # A domain is relevant to this player only when at least one raw forecast
        # observation from that domain exists. This avoids requiring passing stats
        # for ordinary RB/WR/TE projections while still preventing partial domains.
        if any(metric in by_metric for metric in domain):
            missing.update(configured.difference(by_metric))

    # Fumble loss is a standalone active scoring coordinate rather than a member
    # of the pass/rush/receiving domain triplets above. If a league scores it,
    # missing raw evidence must never be interpreted as zero. This closes the
    # late-connect replay integrity hole identified by Forecast Research.
    if (
        coefficient_by_metric.get(ForecastMetric.FUMBLES_LOST, 0.0) != 0.0
        and by_metric
        and ForecastMetric.FUMBLES_LOST not in by_metric
    ):
        missing.add(ForecastMetric.FUMBLES_LOST)

    return tuple(sorted(missing, key=lambda metric: metric.value))


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


def derive_league_scoring_result(
    observations: tuple[ForecastObservation, ...],
    *,
    rules: LeagueRules,
    source: str = "fsffl:league_scored",
    model_version: str = "next2-league-scoring-bridge-v4:subject-family-isolation",
) -> LeagueScoringResult:
    """Score supported player-offense coordinates without hiding canonical Forecast.

    K/DST rules are a separate subject family and never invalidate ordinary player
    offense here. Unsupported ordinary player rules produce an explicit partial
    subtotal rather than an authoritative FANTASY_POINTS observation.
    """

    coverage = classify_scoring_coverage(rules)
    coefficient_by_metric: dict[ForecastMetric, float] = {}
    rule_stats_by_metric: dict[ForecastMetric, list[str]] = defaultdict(list)
    for rule in rules.scoring:
        metric = _SLEEPER_LINEAR_RULES.get(rule.stat)
        if metric is not None and rule.points != 0:
            coefficient_by_metric[metric] = coefficient_by_metric.get(metric, 0.0) + rule.points
            rule_stats_by_metric[metric].append(rule.stat)

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

    authoritative: list[ForecastObservation] = []
    partial: list[PartialFantasyPointForecast] = []
    for items in grouped.values():
        by_metric = {item.metric: item for item in items}
        missing_metrics = _missing_material_scored_metrics(
            by_metric=by_metric,
            coefficient_by_metric=coefficient_by_metric,
        )
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
        supplemental_mixed_vintage = any(
            item.provenance.source == SUPPLEMENTAL_COORDINATE_SOURCE
            for _metric, _coefficient, item in active
        )
        lineage_suffix = (
            ":supplemental_mixed_vintage_current"
            if supplemental_mixed_vintage
            else ""
        )
        provenance = Provenance(
            source=(
                f"{source}[{first.source};supplemental_mixed_vintage_current]"
                if supplemental_mixed_vintage
                else f"{source}[{first.source}]"
            ),
            retrieved_at=retrieved,
            effective_at=effective,
            source_version=f"{model_version}{lineage_suffix}",
        )
        supported_stats = tuple(
            sorted(
                {
                    stat
                    for metric, _coefficient, _item in active
                    for stat in rule_stats_by_metric.get(metric, ())
                }
                | set(applied_residuals)
            )
        )
        missing_rule_stats = {
            stat
            for metric in missing_metrics
            for stat in rule_stats_by_metric.get(metric, ())
        }
        omitted_stats = tuple(
            sorted(set(coverage.unsupported_rule_stats) | missing_rule_stats)
        )
        omission_reasons: list[str] = []
        if coverage.unsupported_rule_stats:
            omission_reasons.append(
                "unsupported active player-offense scoring coordinates are omitted"
            )
        if missing_metrics:
            omission_reasons.append(
                "material raw Forecast metrics are undercovered and are not interpreted as zero: "
                + ",".join(metric.value for metric in missing_metrics)
            )

        distribution = ForecastDistribution(
            mean=mean,
            stddev=sqrt(max(variance, 0.0)),
        )
        suffix = ":independent_metric_variance"
        if applied_residuals:
            suffix += ":bounded_provisional_residual_v1"
        suffix += lineage_suffix

        if omitted_stats:
            partial.append(
                PartialFantasyPointForecast(
                    player_id=first.player_id,
                    position=first.position,
                    horizon=first.horizon,
                    period_start=first.period_start,
                    period_end=first.period_end,
                    distribution=distribution,
                    supported_rule_stats=supported_stats,
                    omitted_rule_stats=omitted_stats,
                    omission_reasons=tuple(omission_reasons),
                    source=source,
                    model_version=f"{model_version}:partial_supported_subtotal{suffix}",
                    as_of=first.as_of,
                    provenance=provenance,
                )
            )
            continue

        authoritative.append(
            ForecastObservation(
                player_id=first.player_id,
                position=first.position,
                horizon=first.horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=first.period_start,
                period_end=first.period_end,
                distribution=distribution,
                source=source,
                model_version=f"{model_version}{suffix}",
                as_of=first.as_of,
                provenance=provenance,
            )
        )

    return LeagueScoringResult(
        authoritative_forecasts=tuple(
            sorted(
                authoritative,
                key=lambda item: (
                    item.player_id,
                    item.horizon.value,
                    item.period_start,
                    item.source,
                ),
            )
        ),
        partial_forecasts=tuple(
            sorted(
                partial,
                key=lambda item: (
                    item.player_id,
                    item.horizon.value,
                    item.period_start,
                    item.source,
                ),
            )
        ),
        coverage=coverage,
        family_coverage=classify_forecast_rule_family_coverage(rules),
    )


def derive_league_fantasy_point_forecasts(
    observations: tuple[ForecastObservation, ...],
    *,
    rules: LeagueRules,
    source: str = "fsffl:league_scored",
    model_version: str = "next2-league-scoring-bridge-v4:subject-family-isolation",
) -> tuple[ForecastObservation, ...]:
    """Strict authoritative scorer retained for consumers that require full offense truth."""

    result = derive_league_scoring_result(
        observations,
        rules=rules,
        source=source,
        model_version=model_version,
    )
    if result.coverage.status == ScoringCoverageStatus.INCOMPLETE:
        raise ValueError(
            "league player-offense scoring cannot be fully reproduced from current raw "
            "forecast metrics; unsupported rules: "
            f"{list(result.coverage.unsupported_rule_stats)}"
        )
    # Per-subject missing material metrics remain fail-closed and therefore appear
    # only in partial_forecasts; authoritative output contains no silent zeroes.
    return result.authoritative_forecasts
