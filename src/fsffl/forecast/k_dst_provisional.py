from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from statistics import fmean
from typing import Literal

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueRules, RosterSlot

from .k_dst_calibration import (
    DST_REDUCED_2024_FINGERPRINT,
    K_REDUCED_2024_FINGERPRINT,
)
from .k_dst_scoring import (
    ForecastSubjectFamily,
    RuleEvidenceStatus,
    dst_linear_metric_for_rule,
    kicker_rule_difference_requirement,
    kicker_rule_metric_alternatives,
    rule_relevant_for_subject_family,
)
from .late_start_snapshot import (
    PRESEASON_COMPARISON_UNAVAILABLE,
    LateStartCurrentProjectionSnapshot,
    assess_late_start_subject_authority,
    ros_subject_key,
)
from .models import ForecastHorizon, ForecastMetric


PROVISIONAL_K_DST_EXCEPTION_VERSION = "2026-provisional-kdst-v1"
PROVISIONAL_K_DST_MODEL_VERSION = "2026-provisional-kdst-partial-rule-v1"

K_REDUCED_2024_SEASON_RELATIVE_RMSE = 0.38418847933549305
K_REDUCED_2024_WEEKLY_CV = 0.5223274618193781
DST_REDUCED_2024_SEASON_RELATIVE_RMSE = 0.21402833115231343
DST_REDUCED_2024_WEEKLY_CV = 0.6381941339011228


class ProvisionalKDstConsumer(StrEnum):
    PRESENTATION = "presentation"
    READINESS = "readiness"
    ANALYTICS_API = "analytics_api"
    VALUE = "value"
    SIMULATION = "simulation"
    TEAM_UTILITY = "team_utility"
    DECISION = "decision"
    SEARCH_OPTIMIZATION = "search_optimization"


class ProvisionalKDstCoordinate(FrozenModel):
    coordinate: str
    rule_stats: tuple[str, ...]
    status: RuleEvidenceStatus
    points_per_event: float
    projected_events: float
    fantasy_points: float
    metrics: tuple[ForecastMetric, ...]
    source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    @model_validator(mode="after")
    def validate_supported_coordinate(self) -> "ProvisionalKDstCoordinate":
        if self.status == RuleEvidenceStatus.UNSUPPORTED:
            raise ValueError("included provisional coordinate cannot be unsupported")
        if not self.rule_stats:
            raise ValueError("included provisional coordinate must identify scoring rules")
        if len(self.independence_groups) < 2:
            raise ValueError("provisional coordinate requires at least two independent groups")
        return self


class ProvisionalKDstOmission(FrozenModel):
    coordinate: str
    rule_stats: tuple[str, ...]
    points_per_event: float | None
    reason: str


class ProvisionalKDstUncertainty(FrozenModel):
    empirical_reference_fingerprint_id: str
    empirical_season_relative_rmse: float
    empirical_weekly_cv: float
    empirical_reference_applied_to_provisional_total: Literal[False] = False
    omitted_coordinate_uncertainty: Literal["unquantified_not_imputed"] = (
        "unquantified_not_imputed"
    )
    simulation_grade: Literal[False] = False
    explanation: str = (
        "Reduced-fingerprint empirical error/volatility is retained as evidence only. "
        "It is not applied as total-score variance, and uncertainty from omitted scoring "
        "coordinates is not estimated or set to zero."
    )


class ProvisionalKDstForecast(FrozenModel):
    season: Literal[2026] = 2026
    exception_version: Literal["2026-provisional-kdst-v1"] = (
        PROVISIONAL_K_DST_EXCEPTION_VERSION
    )
    model_version: Literal["2026-provisional-kdst-partial-rule-v1"] = (
        PROVISIONAL_K_DST_MODEL_VERSION
    )
    authority_tier: Literal["provisional_partial_rule_coverage"] = (
        "provisional_partial_rule_coverage"
    )
    subject_key: str
    subject_family: ForecastSubjectFamily
    horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    period_start: datetime
    period_end: datetime
    as_of: datetime
    available: bool
    fantasy_points_mean: float | None
    included_coordinates: tuple[ProvisionalKDstCoordinate, ...]
    omitted_coordinates: tuple[ProvisionalKDstOmission, ...]
    supported_rule_stats: tuple[str, ...]
    omitted_rule_stats: tuple[str, ...]
    partially_supported_rule_stats: tuple[str, ...]
    full_rule_authority: Literal[False] = False
    full_authority_blockers: tuple[str, ...]
    source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    uncertainty: ProvisionalKDstUncertainty
    preseason_eligible: Literal[False] = False
    preseason_comparison_status: Literal[
        "unavailable_no_qualifying_pre_week1_k_dst_evidence"
    ] = PRESEASON_COMPARISON_UNAVAILABLE

    @model_validator(mode="after")
    def validate_partial_contract(self) -> "ProvisionalKDstForecast":
        for name in ("period_start", "period_end", "as_of"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware datetime")
        if self.period_end <= self.period_start:
            raise ValueError("provisional ROS period_end must follow period_start")
        if self.available != bool(self.included_coordinates):
            raise ValueError("available must match presence of included coordinates")
        if self.available != (self.fantasy_points_mean is not None):
            raise ValueError("fantasy_points_mean must exist exactly when provisional evidence is available")
        expected_partial = tuple(
            sorted(set(self.supported_rule_stats) & set(self.omitted_rule_stats))
        )
        if self.partially_supported_rule_stats != expected_partial:
            raise ValueError("partially_supported_rule_stats must match supported/omitted overlap")
        return self


class ProvisionalKDstConsumerDecision(FrozenModel):
    consumer: ProvisionalKDstConsumer
    allowed: bool
    requires_provisional_metadata: bool
    reason: str


class ProvisionalKDstReadiness(FrozenModel):
    authority_tier: Literal["provisional_partial_rule_coverage"] = (
        "provisional_partial_rule_coverage"
    )
    current_forward_usable: bool
    full_forecast_authority_ready: Literal[False] = False
    simulation_grade_uncertainty_ready: Literal[False] = False
    preseason_comparison_available: Literal[False] = False
    omitted_coordinates: tuple[str, ...]
    status: Literal["provisional", "unavailable"]


@dataclass(frozen=True)
class _ProviderMetricEvidence:
    source_id: str
    independence_group: str
    provenance_ref: str
    metrics: dict[ForecastMetric, float]


@dataclass(frozen=True)
class _GovernedValue:
    projected_events: float
    status: RuleEvidenceStatus
    metrics: tuple[ForecastMetric, ...]
    source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    provenance_refs: tuple[str, ...]


def _subject_family(subject_key: str) -> ForecastSubjectFamily:
    if subject_key.startswith("K:"):
        return ForecastSubjectFamily.KICKER
    if subject_key.startswith("DST:"):
        return ForecastSubjectFamily.DST
    raise ValueError("provisional late-start subject must be K or D/ST")


def _require_active_slot(rules: LeagueRules, family: ForecastSubjectFamily) -> None:
    slot = RosterSlot.K if family == ForecastSubjectFamily.KICKER else RosterSlot.DST
    if not any(item.slot == slot and item.count > 0 for item in rules.lineup):
        raise ValueError(f"league has no active {slot.value} lineup slot")


def _provider_metric_evidence(
    snapshot: LateStartCurrentProjectionSnapshot,
    *,
    subject_key: str,
) -> tuple[_ProviderMetricEvidence, ...]:
    """Return only accepted, rights-cleared source rows for private-beta use."""

    output: list[_ProviderMetricEvidence] = []
    for provider in snapshot.provider_evidence:
        if not provider.production_rights_eligible:
            continue
        if subject_key not in set(provider.accepted_subject_keys):
            continue
        metrics: dict[ForecastMetric, float] = {}
        for row in provider.raw_rows:
            if ros_subject_key(row) != subject_key:
                continue
            for stat, value in row.stats:
                try:
                    metric = ForecastMetric(stat)
                except ValueError:
                    continue
                numeric = float(value)
                if metric in metrics and abs(metrics[metric] - numeric) > 1e-9:
                    raise ValueError(
                        f"provider {provider.source_id} has conflicting values for {metric.value}"
                    )
                metrics[metric] = numeric
        if not metrics:
            continue
        output.append(
            _ProviderMetricEvidence(
                source_id=provider.source_id,
                independence_group=provider.independence_group,
                provenance_ref=f"sha256:{provider.content_sha256}",
                metrics=metrics,
            )
        )
    return tuple(sorted(output, key=lambda item: item.source_id))


def _governed_value(
    providers: tuple[_ProviderMetricEvidence, ...],
    *,
    minimum_independent_sources: int,
    extractor,
) -> _GovernedValue | None:
    candidates: list[
        tuple[_ProviderMetricEvidence, float, RuleEvidenceStatus, tuple[ForecastMetric, ...]]
    ] = []
    for provider in providers:
        extracted = extractor(provider.metrics)
        if extracted is None:
            continue
        value, status, metrics = extracted
        candidates.append((provider, float(value), status, tuple(metrics)))

    groups: dict[str, list[float]] = {}
    for provider, value, _status, _metrics in candidates:
        groups.setdefault(provider.independence_group, []).append(value)
    if len(groups) < minimum_independent_sources:
        return None

    group_values = [fmean(values) for _, values in sorted(groups.items())]
    status = (
        RuleEvidenceStatus.EXACT
        if all(item[2] == RuleEvidenceStatus.EXACT for item in candidates)
        else RuleEvidenceStatus.EXACT_DERIVED
    )
    metrics = tuple(
        sorted(
            {metric for _provider, _value, _status, ms in candidates for metric in ms},
            key=lambda item: item.value,
        )
    )
    return _GovernedValue(
        projected_events=fmean(group_values),
        status=status,
        metrics=metrics,
        source_ids=tuple(sorted({item[0].source_id for item in candidates})),
        independence_groups=tuple(sorted(groups)),
        provenance_refs=tuple(sorted({item[0].provenance_ref for item in candidates})),
    )


def _metric_extractor(metric: ForecastMetric):
    def extract(metrics: dict[ForecastMetric, float]):
        if metric not in metrics:
            return None
        return metrics[metric], RuleEvidenceStatus.EXACT, (metric,)

    return extract


def _kicker_rule_extractor(stat: str):
    alternatives = kicker_rule_metric_alternatives(stat)
    difference = kicker_rule_difference_requirement(stat)

    def extract(metrics: dict[ForecastMetric, float]):
        for index, option in enumerate(alternatives):
            if all(metric in metrics for metric in option):
                return (
                    sum(metrics[metric] for metric in option),
                    RuleEvidenceStatus.EXACT if index == 0 else RuleEvidenceStatus.EXACT_DERIVED,
                    option,
                )
        if difference is not None and all(metric in metrics for metric in difference):
            mean = metrics[difference[0]] - metrics[difference[1]]
            if mean >= -1e-9:
                return (
                    max(mean, 0.0),
                    RuleEvidenceStatus.EXACT_DERIVED,
                    difference,
                )
        return None

    return extract


def _coordinate(
    *,
    name: str,
    rule_stats: tuple[str, ...],
    points_per_event: float,
    evidence: _GovernedValue,
    status: RuleEvidenceStatus | None = None,
) -> ProvisionalKDstCoordinate:
    return ProvisionalKDstCoordinate(
        coordinate=name,
        rule_stats=rule_stats,
        status=status or evidence.status,
        points_per_event=points_per_event,
        projected_events=evidence.projected_events,
        fantasy_points=points_per_event * evidence.projected_events,
        metrics=evidence.metrics,
        source_ids=evidence.source_ids,
        independence_groups=evidence.independence_groups,
        provenance_refs=evidence.provenance_refs,
    )


def _kicker_coordinates(
    snapshot: LateStartCurrentProjectionSnapshot,
    *,
    subject_key: str,
    rules: LeagueRules,
    providers: tuple[_ProviderMetricEvidence, ...],
) -> tuple[tuple[ProvisionalKDstCoordinate, ...], tuple[ProvisionalKDstOmission, ...]]:
    active = [
        rule
        for rule in rules.scoring
        if rule.points != 0
        and rule_relevant_for_subject_family(rule.stat, ForecastSubjectFamily.KICKER)
    ]
    included: list[ProvisionalKDstCoordinate] = []
    omitted: list[ProvisionalKDstOmission] = []
    skip: set[str] = set()
    minimum = snapshot.minimum_independent_sources

    by_stat = {rule.stat: rule for rule in active}

    # Exact combined 0-29 evidence is allowed only because both Hodor bands score
    # identically. It is one contribution, never a fabricated split.
    low = by_stat.get("fgm_0_19")
    high = by_stat.get("fgm_20_29")
    if low is not None and high is not None and low.points == high.points:
        low_exact = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_kicker_rule_extractor(low.stat),
        )
        high_exact = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_kicker_rule_extractor(high.stat),
        )
        combined = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_metric_extractor(ForecastMetric.FG_MADE_0_29),
        )
        if combined is not None and not (low_exact is not None and high_exact is not None):
            included.append(
                _coordinate(
                    name="fgm_0_29_equal_coefficient",
                    rule_stats=(low.stat, high.stat),
                    points_per_event=low.points,
                    evidence=combined,
                    status=RuleEvidenceStatus.EXACT_DERIVED,
                )
            )
            skip.update({low.stat, high.stat})

    # 2026 Management exception: 50+ may supply the common five-point base for
    # Hodor's 50-59=5 and 60+=6 rules. Only a governed 60+ projection can supply
    # the extra +1. No frequency split is inferred.
    fifty = by_stat.get("fgm_50_59")
    sixty_candidates = [
        by_stat[stat]
        for stat in ("fgm_60p", "fgm_60_plus")
        if stat in by_stat
    ]
    if (
        fifty is not None
        and len(sixty_candidates) == 1
        and fifty.points == 5
        and sixty_candidates[0].points == 6
    ):
        sixty = sixty_candidates[0]
        fifty_exact = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_kicker_rule_extractor(fifty.stat),
        )
        sixty_exact = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_kicker_rule_extractor(sixty.stat),
        )
        fifty_plus = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_metric_extractor(ForecastMetric.FG_MADE_50_PLUS),
        )
        if fifty_plus is not None and not (
            fifty_exact is not None and sixty_exact is not None
        ):
            included.append(
                _coordinate(
                    name="fgm_50_plus_five_point_base",
                    rule_stats=(fifty.stat, sixty.stat),
                    points_per_event=5.0,
                    evidence=fifty_plus,
                    status=RuleEvidenceStatus.PROVISIONAL_GOVERNED,
                )
            )
            sixty_plus = _governed_value(
                providers,
                minimum_independent_sources=minimum,
                extractor=_metric_extractor(ForecastMetric.FG_MADE_60_PLUS),
            )
            if sixty_plus is not None:
                included.append(
                    _coordinate(
                        name="fgm_60_plus_increment",
                        rule_stats=(sixty.stat,),
                        points_per_event=1.0,
                        evidence=sixty_plus,
                        status=RuleEvidenceStatus.PROVISIONAL_GOVERNED,
                    )
                )
            else:
                omitted.append(
                    ProvisionalKDstOmission(
                        coordinate="fgm_60_plus_increment",
                        rule_stats=(sixty.stat,),
                        points_per_event=1.0,
                        reason=(
                            "60+ frequency lacks the required independent governed evidence; "
                            "the Hodor +1 premium is omitted rather than estimated"
                        ),
                    )
                )
            skip.update({fifty.stat, sixty.stat})

    for rule in active:
        if rule.stat in skip:
            continue
        evidence = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_kicker_rule_extractor(rule.stat),
        )
        if evidence is None:
            omitted.append(
                ProvisionalKDstOmission(
                    coordinate=rule.stat,
                    rule_stats=(rule.stat,),
                    points_per_event=rule.points,
                    reason=(
                        "active kicker coordinate lacks the required independent governed "
                        "raw evidence or exact transform"
                    ),
                )
            )
            continue
        included.append(
            _coordinate(
                name=rule.stat,
                rule_stats=(rule.stat,),
                points_per_event=rule.points,
                evidence=evidence,
            )
        )

    return (
        tuple(sorted(included, key=lambda item: item.coordinate)),
        tuple(sorted(omitted, key=lambda item: item.coordinate)),
    )


def _dst_coordinates(
    snapshot: LateStartCurrentProjectionSnapshot,
    *,
    rules: LeagueRules,
    providers: tuple[_ProviderMetricEvidence, ...],
) -> tuple[tuple[ProvisionalKDstCoordinate, ...], tuple[ProvisionalKDstOmission, ...]]:
    active = [
        rule
        for rule in rules.scoring
        if rule.points != 0
        and rule_relevant_for_subject_family(rule.stat, ForecastSubjectFamily.DST)
    ]
    included: list[ProvisionalKDstCoordinate] = []
    omitted: list[ProvisionalKDstOmission] = []
    minimum = snapshot.minimum_independent_sources

    for rule in active:
        if rule.stat.startswith("pts_allow_") or rule.stat.startswith("yds_allow_"):
            omitted.append(
                ProvisionalKDstOmission(
                    coordinate=rule.stat,
                    rule_stats=(rule.stat,),
                    points_per_event=rule.points,
                    reason=(
                        "nonlinear bucket scoring requires governed per-game distributional "
                        "evidence; aggregate PA/YA is not transformed into a bucket"
                    ),
                )
            )
            continue

        metric = dst_linear_metric_for_rule(rule.stat)
        if metric is None:
            omitted.append(
                ProvisionalKDstOmission(
                    coordinate=rule.stat,
                    rule_stats=(rule.stat,),
                    points_per_event=rule.points,
                    reason="active D/ST coordinate has no governed raw-metric contract",
                )
            )
            continue

        evidence = _governed_value(
            providers,
            minimum_independent_sources=minimum,
            extractor=_metric_extractor(metric),
        )
        if evidence is None:
            omitted.append(
                ProvisionalKDstOmission(
                    coordinate=rule.stat,
                    rule_stats=(rule.stat,),
                    points_per_event=rule.points,
                    reason=(
                        "active D/ST coordinate lacks the required independent governed "
                        "raw evidence"
                    ),
                )
            )
            continue
        included.append(
            _coordinate(
                name=rule.stat,
                rule_stats=(rule.stat,),
                points_per_event=rule.points,
                evidence=evidence,
            )
        )

    return (
        tuple(sorted(included, key=lambda item: item.coordinate)),
        tuple(sorted(omitted, key=lambda item: item.coordinate)),
    )


def _uncertainty(family: ForecastSubjectFamily) -> ProvisionalKDstUncertainty:
    if family == ForecastSubjectFamily.KICKER:
        return ProvisionalKDstUncertainty(
            empirical_reference_fingerprint_id=K_REDUCED_2024_FINGERPRINT.fingerprint_id,
            empirical_season_relative_rmse=K_REDUCED_2024_SEASON_RELATIVE_RMSE,
            empirical_weekly_cv=K_REDUCED_2024_WEEKLY_CV,
        )
    return ProvisionalKDstUncertainty(
        empirical_reference_fingerprint_id=DST_REDUCED_2024_FINGERPRINT.fingerprint_id,
        empirical_season_relative_rmse=DST_REDUCED_2024_SEASON_RELATIVE_RMSE,
        empirical_weekly_cv=DST_REDUCED_2024_WEEKLY_CV,
    )


def build_provisional_k_dst_forecast(
    snapshot: LateStartCurrentProjectionSnapshot,
    *,
    subject_key: str,
    rules: LeagueRules,
    promoted_uncertainty_fingerprint_ids: frozenset[str] = frozenset(),
) -> ProvisionalKDstForecast:
    """Build 2026 private-beta K/DST points from only governed supported rules.

    The output is intentionally not a ForecastObservation. Keeping this contract
    structurally distinct prevents Value/Simulation/Decision/Search from consuming
    a partial score as full Forecast authority.
    """

    if snapshot.season != 2026:
        raise ValueError("provisional K/DST exception is authorized only for 2026")
    family = _subject_family(subject_key)
    _require_active_slot(rules, family)

    full = assess_late_start_subject_authority(
        snapshot,
        subject_key=subject_key,
        rules=rules,
        promoted_uncertainty_fingerprint_ids=promoted_uncertainty_fingerprint_ids,
    )
    if full.authoritative:
        raise ValueError(
            "full K/DST Forecast authority is available; provisional path must not supersede it"
        )

    providers = _provider_metric_evidence(snapshot, subject_key=subject_key)
    if family == ForecastSubjectFamily.KICKER:
        included, omitted = _kicker_coordinates(
            snapshot,
            subject_key=subject_key,
            rules=rules,
            providers=providers,
        )
    else:
        included, omitted = _dst_coordinates(
            snapshot,
            rules=rules,
            providers=providers,
        )

    supported_rules = tuple(
        sorted({stat for coordinate in included for stat in coordinate.rule_stats})
    )
    omitted_rules = tuple(
        sorted({stat for omission in omitted for stat in omission.rule_stats})
    )
    partial_rules = tuple(sorted(set(supported_rules) & set(omitted_rules)))
    source_ids = tuple(
        sorted({source for coordinate in included for source in coordinate.source_ids})
    )
    groups = tuple(
        sorted(
            {
                group
                for coordinate in included
                for group in coordinate.independence_groups
            }
        )
    )
    provenance = tuple(
        sorted(
            {
                ref
                for coordinate in included
                for ref in coordinate.provenance_refs
            }
        )
    )
    available = bool(included)
    mean = sum(item.fantasy_points for item in included) if available else None

    return ProvisionalKDstForecast(
        subject_key=subject_key,
        subject_family=family,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        as_of=snapshot.evaluation_as_of,
        available=available,
        fantasy_points_mean=mean,
        included_coordinates=included,
        omitted_coordinates=omitted,
        supported_rule_stats=supported_rules,
        omitted_rule_stats=omitted_rules,
        partially_supported_rule_stats=partial_rules,
        full_authority_blockers=full.blockers,
        source_ids=source_ids,
        independence_groups=groups,
        provenance_refs=provenance,
        uncertainty=_uncertainty(family),
    )


def assess_provisional_k_dst_consumer(
    forecast: ProvisionalKDstForecast,
    consumer: ProvisionalKDstConsumer,
) -> ProvisionalKDstConsumerDecision:
    """Prevent provisional evidence from silently becoming downstream model truth."""

    if consumer in {
        ProvisionalKDstConsumer.PRESENTATION,
        ProvisionalKDstConsumer.READINESS,
        ProvisionalKDstConsumer.ANALYTICS_API,
    }:
        if not forecast.available:
            return ProvisionalKDstConsumerDecision(
                consumer=consumer,
                allowed=False,
                requires_provisional_metadata=True,
                reason="no governed scoring coordinate is available for this subject",
            )
        return ProvisionalKDstConsumerDecision(
            consumer=consumer,
            allowed=True,
            requires_provisional_metadata=True,
            reason=(
                "consumer may expose the provisional contract only when authority tier, "
                "coverage omissions, provenance, and uncertainty limitations stay attached"
            ),
        )

    return ProvisionalKDstConsumerDecision(
        consumer=consumer,
        allowed=False,
        requires_provisional_metadata=True,
        reason=(
            "Value/Simulation/Team Utility/Decision/Search require full Forecast authority; "
            "a 2026 partial-rule K/DST score cannot be silently upgraded"
        ),
    )


def provisional_k_dst_readiness(
    forecast: ProvisionalKDstForecast,
) -> ProvisionalKDstReadiness:
    decision = assess_provisional_k_dst_consumer(
        forecast,
        ProvisionalKDstConsumer.READINESS,
    )
    return ProvisionalKDstReadiness(
        current_forward_usable=decision.allowed,
        omitted_coordinates=tuple(
            item.coordinate for item in forecast.omitted_coordinates
        ),
        status="provisional" if decision.allowed else "unavailable",
    )
