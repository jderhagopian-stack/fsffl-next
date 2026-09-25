from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from math import sqrt
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, Position, Provenance, RosterSlot

from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
    NflTeamUnitForecastSubject,
    TeamUnitForecastObservation,
)


class ForecastSubjectFamily(StrEnum):
    PLAYER_OFFENSE = "player_offense"
    KICKER = "kicker"
    DST = "dst"


class RuleEvidenceStatus(StrEnum):
    EXACT = "exact"
    EXACT_DERIVED = "exact_derived"
    DISTRIBUTIONAL = "distributional"
    PROVISIONAL_GOVERNED = "provisional_governed"
    UNSUPPORTED = "unsupported"


class SourceRuleEvidence(FrozenModel):
    """Rule-level evidence exposed by one projection source.

    independence_group is the governed anti-double-counting identity. Two source
    products that share the same underlying projection corpus must share this value
    and therefore count only once toward the two-source threshold.
    """

    source_id: str
    independence_group: str
    metrics: frozenset[ForecastMetric] = frozenset()
    distributional_rule_stats: frozenset[str] = frozenset()
    provenance_ref: str | None = None

    @field_validator("source_id", "independence_group")
    @classmethod
    def require_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source evidence identifiers cannot be empty")
        return value


class RuleEvidenceCoverage(FrozenModel):
    rule_stat: str
    points: float
    subject_family: ForecastSubjectFamily
    status: RuleEvidenceStatus
    required_metrics: tuple[ForecastMetric, ...] = ()
    eligible_source_ids: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    explanation: str


class RuleProbability(FrozenModel):
    rule_stat: str
    probability: Annotated[float, Field(ge=0.0, le=1.0)]

    @field_validator("rule_stat")
    @classmethod
    def require_rule_stat(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("rule_stat cannot be empty")
        return value


class GameRuleProbabilityDistribution(FrozenModel):
    game_key: str
    probabilities: tuple[RuleProbability, ...]

    @field_validator("game_key")
    @classmethod
    def require_game_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("game_key cannot be empty")
        return value

    @model_validator(mode="after")
    def unique_rules(self) -> "GameRuleProbabilityDistribution":
        rule_stats = [item.rule_stat for item in self.probabilities]
        if len(rule_stats) != len(set(rule_stats)):
            raise ValueError("game distribution cannot repeat a scoring bucket")
        if sum(item.probability for item in self.probabilities) > 1.000001:
            raise ValueError("game bucket probabilities cannot sum above one")
        return self


class TeamUnitDistributionalEvidence(FrozenModel):
    """Per-game bucket probabilities for one D/ST team-season subject."""

    subject: NflTeamUnitForecastSubject
    family: Literal["points_allowed", "yards_allowed"]
    horizon: ForecastHorizon
    period_start: object
    period_end: object
    games: tuple[GameRuleProbabilityDistribution, ...]
    source: str
    model_version: str
    as_of: object
    provenance: Provenance

    @model_validator(mode="after")
    def validate_metadata(self) -> "TeamUnitDistributionalEvidence":
        from datetime import datetime

        for name in ("period_start", "period_end", "as_of"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError(f"{name} must be a timezone-aware datetime")
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        if self.provenance.effective_at > self.as_of:
            raise ValueError("distributional evidence cannot postdate as_of")
        if not self.games:
            raise ValueError("distributional evidence requires at least one game")
        return self


_K_MADE_BINS = (
    ForecastMetric.FG_MADE_0_19,
    ForecastMetric.FG_MADE_20_29,
    ForecastMetric.FG_MADE_30_39,
    ForecastMetric.FG_MADE_40_49,
    ForecastMetric.FG_MADE_50_59,
    ForecastMetric.FG_MADE_60_PLUS,
)
_K_MISS_BINS = (
    ForecastMetric.FG_MISS_0_19,
    ForecastMetric.FG_MISS_20_29,
    ForecastMetric.FG_MISS_30_39,
    ForecastMetric.FG_MISS_40_49,
    ForecastMetric.FG_MISS_50_59,
    ForecastMetric.FG_MISS_60_PLUS,
)

_K_RULE_REQUIREMENTS: dict[str, tuple[tuple[ForecastMetric, ...], ...]] = {
    "fga": ((ForecastMetric.FG_ATTEMPT,),),
    "fgm": ((ForecastMetric.FG_MADE,), _K_MADE_BINS),
    "fgmiss": ((ForecastMetric.FG_MISS,), _K_MISS_BINS),
    "fgm_0_19": ((ForecastMetric.FG_MADE_0_19,),),
    "fgm_20_29": ((ForecastMetric.FG_MADE_20_29,),),
    "fgm_30_39": ((ForecastMetric.FG_MADE_30_39,),),
    "fgm_40_49": ((ForecastMetric.FG_MADE_40_49,),),
    "fgm_50_59": ((ForecastMetric.FG_MADE_50_59,),),
    "fgm_60p": ((ForecastMetric.FG_MADE_60_PLUS,),),
    "fgm_60_plus": ((ForecastMetric.FG_MADE_60_PLUS,),),
    "fgm_50p": (
        (ForecastMetric.FG_MADE_50_PLUS,),
        (ForecastMetric.FG_MADE_50_59, ForecastMetric.FG_MADE_60_PLUS),
    ),
    "fgmiss_0_19": ((ForecastMetric.FG_MISS_0_19,),),
    "fgmiss_20_29": ((ForecastMetric.FG_MISS_20_29,),),
    "fgmiss_30_39": ((ForecastMetric.FG_MISS_30_39,),),
    "fgmiss_40_49": ((ForecastMetric.FG_MISS_40_49,),),
    "fgmiss_50_59": ((ForecastMetric.FG_MISS_50_59,),),
    "fgmiss_60p": ((ForecastMetric.FG_MISS_60_PLUS,),),
    "fgm_yds": ((ForecastMetric.FG_MADE_YARDS,),),
    "fgm_yds_over_30": ((ForecastMetric.FG_MADE_YARDS_OVER_30,),),
    "xpa": ((ForecastMetric.XP_ATTEMPT,),),
    "xpm": ((ForecastMetric.XP_MADE,),),
    "xpmiss": ((ForecastMetric.XP_MISS,),),
}

_DST_LINEAR_RULES: dict[str, ForecastMetric] = {
    "sack": ForecastMetric.DST_SACK,
    "int": ForecastMetric.DST_INTERCEPTION,
    "fum_rec": ForecastMetric.DST_FUMBLE_RECOVERY,
    "ff": ForecastMetric.DST_FORCED_FUMBLE,
    "safe": ForecastMetric.DST_SAFETY,
    "blk_kick": ForecastMetric.DST_BLOCKED_KICK,
    "def_td": ForecastMetric.DST_DEFENSIVE_TD,
    "def_2pt": ForecastMetric.DST_DEFENSIVE_TWO_POINT_RETURN,
    "def_st_td": ForecastMetric.DST_TEAM_ST_TD,
    "def_st_ff": ForecastMetric.DST_TEAM_ST_FORCED_FUMBLE,
    "def_st_fum_rec": ForecastMetric.DST_TEAM_ST_FUMBLE_RECOVERY,
    "int_ret_yd": ForecastMetric.DST_INT_RETURN_YARDS,
    "fum_ret_yd": ForecastMetric.DST_FUMBLE_RETURN_YARDS,
    "blk_kick_ret_yd": ForecastMetric.DST_BLOCKED_KICK_RETURN_YARDS,
    "sack_yd": ForecastMetric.DST_SACK_YARDS,
    "tkl": ForecastMetric.DST_TACKLE,
    "solo_tkl": ForecastMetric.DST_SOLO_TACKLE,
    "asst_tkl": ForecastMetric.DST_ASSISTED_TACKLE,
    "tkl_loss": ForecastMetric.DST_TACKLE_FOR_LOSS,
    "qb_hit": ForecastMetric.DST_QB_HIT,
    "pass_def": ForecastMetric.DST_PASS_DEFENDED,
    "def_st_tkl_solo": ForecastMetric.DST_TEAM_ST_SOLO_TACKLE,
    "punt_ret_yd": ForecastMetric.DST_PUNT_RETURN_YARDS,
    "kick_ret_yd": ForecastMetric.DST_KICK_RETURN_YARDS,
    "miss_fg_ret_yd": ForecastMetric.DST_MISSED_FG_RETURN_YARDS,
    "three_and_out": ForecastMetric.DST_THREE_AND_OUT,
    "fourth_down_stop": ForecastMetric.DST_FOURTH_DOWN_STOP,
    "forced_punt": ForecastMetric.DST_FORCED_PUNT,
}

_K_PREFIXES = ("fg", "xp")
_DST_PREFIXES = (
    "blk_kick",
    "def_",
    "def_st_",
    "ff",
    "fum_rec",
    "int",
    "pts_allow_",
    "safe",
    "sack",
    "tkl",
    "qb_hit",
    "pass_def",
    "yds_allow_",
    "three_and_out",
    "fourth_down_stop",
    "forced_punt",
)


def _has_lineup_slot(rules: LeagueRules, slot: RosterSlot) -> bool:
    return any(item.slot == slot and item.count > 0 for item in rules.lineup)


def _rule_relevant(stat: str, family: ForecastSubjectFamily) -> bool:
    if family == ForecastSubjectFamily.KICKER:
        return stat in _K_RULE_REQUIREMENTS or stat.startswith(_K_PREFIXES)
    if family == ForecastSubjectFamily.DST:
        return (
            stat in _DST_LINEAR_RULES
            or stat.startswith("pts_allow_")
            or stat.startswith("yds_allow_")
            or stat.startswith(_DST_PREFIXES)
        )
    return False


def evaluate_rule_evidence_coverage(
    rules: LeagueRules,
    *,
    subject_family: ForecastSubjectFamily,
    sources: tuple[SourceRuleEvidence, ...],
    minimum_independent_sources: int = 2,
) -> tuple[RuleEvidenceCoverage, ...]:
    """Evaluate active league rules against exact source-level evidence."""

    if minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources must be positive")
    if subject_family == ForecastSubjectFamily.KICKER and not _has_lineup_slot(rules, RosterSlot.K):
        return ()
    if subject_family == ForecastSubjectFamily.DST and not _has_lineup_slot(rules, RosterSlot.DST):
        return ()

    coverage: list[RuleEvidenceCoverage] = []
    for rule in rules.scoring:
        stat = rule.stat
        if not _rule_relevant(stat, subject_family):
            continue
        if rule.points == 0:
            coverage.append(
                RuleEvidenceCoverage(
                    rule_stat=stat,
                    points=rule.points,
                    subject_family=subject_family,
                    status=RuleEvidenceStatus.EXACT,
                    explanation="zero-point rule is non-material and requires no Forecast evidence",
                )
            )
            continue

        if subject_family == ForecastSubjectFamily.KICKER:
            alternatives = _K_RULE_REQUIREMENTS.get(stat)
            if alternatives is None:
                coverage.append(
                    RuleEvidenceCoverage(
                        rule_stat=stat,
                        points=rule.points,
                        subject_family=subject_family,
                        status=RuleEvidenceStatus.UNSUPPORTED,
                        explanation="active kicker rule has no governed raw-metric contract",
                    )
                )
                continue
            direct_eligible = [source for source in sources if set(alternatives[0]).issubset(source.metrics)]
            any_eligible = [
                source
                for source in sources
                if any(set(option).issubset(source.metrics) for option in alternatives)
            ]
            direct_groups = {item.independence_group for item in direct_eligible}
            any_groups = {item.independence_group for item in any_eligible}
            if len(direct_groups) >= minimum_independent_sources:
                status = RuleEvidenceStatus.EXACT
                eligible = direct_eligible
                required = alternatives[0]
                explanation = "direct raw metric is covered by the required independent sources"
            elif len(any_groups) >= minimum_independent_sources:
                status = RuleEvidenceStatus.EXACT_DERIVED
                eligible = any_eligible
                required = tuple(
                    sorted(
                        {metric for option in alternatives for metric in option},
                        key=lambda item: item.value,
                    )
                )
                explanation = "rule is covered by exact algebraic raw-metric alternatives"
            else:
                status = RuleEvidenceStatus.UNSUPPORTED
                eligible = any_eligible
                required = alternatives[0]
                explanation = (
                    "insufficient independent raw evidence for active kicker rule; "
                    f"required={minimum_independent_sources}, found={len(any_groups)}"
                )
        else:
            if stat.startswith("pts_allow_") or stat.startswith("yds_allow_"):
                eligible = [source for source in sources if stat in source.distributional_rule_stats]
                groups = {item.independence_group for item in eligible}
                if len(groups) >= minimum_independent_sources:
                    status = RuleEvidenceStatus.DISTRIBUTIONAL
                    explanation = "per-game distributional rule evidence meets the independence gate"
                else:
                    status = RuleEvidenceStatus.UNSUPPORTED
                    explanation = (
                        "bucket scoring requires per-game distributional evidence; "
                        f"required={minimum_independent_sources}, found={len(groups)}"
                    )
                required = ()
            else:
                metric = _DST_LINEAR_RULES.get(stat)
                if metric is None:
                    coverage.append(
                        RuleEvidenceCoverage(
                            rule_stat=stat,
                            points=rule.points,
                            subject_family=subject_family,
                            status=RuleEvidenceStatus.UNSUPPORTED,
                            explanation="active D/ST rule has no governed raw-metric contract",
                        )
                    )
                    continue
                eligible = [source for source in sources if metric in source.metrics]
                groups = {item.independence_group for item in eligible}
                if len(groups) >= minimum_independent_sources:
                    status = RuleEvidenceStatus.EXACT
                    explanation = "linear D/ST raw metric meets the independence gate"
                else:
                    status = RuleEvidenceStatus.UNSUPPORTED
                    explanation = (
                        "insufficient independent raw evidence for active D/ST rule; "
                        f"required={minimum_independent_sources}, found={len(groups)}"
                    )
                required = (metric,)

        coverage.append(
            RuleEvidenceCoverage(
                rule_stat=stat,
                points=rule.points,
                subject_family=subject_family,
                status=status,
                required_metrics=tuple(required),
                eligible_source_ids=tuple(sorted({item.source_id for item in eligible})),
                provenance_refs=tuple(
                    sorted(
                        {
                            item.provenance_ref
                            for item in eligible
                            if item.provenance_ref is not None
                        }
                    )
                ),
                explanation=explanation,
            )
        )

    return tuple(sorted(coverage, key=lambda item: item.rule_stat))


def _combined_distribution(
    by_metric: dict[ForecastMetric, ForecastObservation | TeamUnitForecastObservation],
    alternatives: tuple[tuple[ForecastMetric, ...], ...],
) -> ForecastDistribution | None:
    for option in alternatives:
        if not all(metric in by_metric for metric in option):
            continue
        observations = [by_metric[metric] for metric in option]
        return ForecastDistribution(
            mean=sum(item.distribution.mean for item in observations),
            stddev=sqrt(sum(item.distribution.stddev ** 2 for item in observations)),
        )
    return None


def derive_kicker_fantasy_point_forecasts(
    observations: tuple[ForecastObservation, ...],
    *,
    rules: LeagueRules,
    source: str = "fsffl:kicker_league_scored",
    model_version: str = "next2-kicker-scoring-v1",
) -> tuple[ForecastObservation, ...]:
    """Score authoritative K raw-event observations under league rules."""

    if not _has_lineup_slot(rules, RosterSlot.K):
        return ()

    active_rules = [
        rule
        for rule in rules.scoring
        if rule.points != 0 and _rule_relevant(rule.stat, ForecastSubjectFamily.KICKER)
    ]
    unsupported = [rule.stat for rule in active_rules if rule.stat not in _K_RULE_REQUIREMENTS]
    if unsupported:
        raise ValueError(f"unsupported active kicker scoring rules: {sorted(set(unsupported))}")

    grouped: dict[tuple[object, ...], list[ForecastObservation]] = defaultdict(list)
    for observation in observations:
        if observation.position != Position.K or observation.metric == ForecastMetric.FANTASY_POINTS:
            continue
        key = (
            observation.player_id,
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
        scored: list[tuple[float, ForecastDistribution]] = []
        missing = False
        for rule in active_rules:
            distribution = _combined_distribution(by_metric, _K_RULE_REQUIREMENTS[rule.stat])
            if distribution is None:
                missing = True
                break
            scored.append((rule.points, distribution))
        if missing or not scored:
            continue

        first = items[0]
        mean = sum(points * distribution.mean for points, distribution in scored)
        variance = sum((points * distribution.stddev) ** 2 for points, distribution in scored)
        provenance = Provenance(
            source=f"{source}[{first.source}]",
            retrieved_at=max(item.provenance.retrieved_at for item in items),
            effective_at=max(item.provenance.effective_at for item in items),
            source_version=model_version,
        )
        output.append(
            ForecastObservation(
                player_id=first.player_id,
                position=Position.K,
                horizon=first.horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=first.period_start,
                period_end=first.period_end,
                distribution=ForecastDistribution(mean=mean, stddev=sqrt(max(variance, 0.0))),
                source=source,
                model_version=f"{model_version}:independent_metric_variance",
                as_of=first.as_of,
                provenance=provenance,
            )
        )

    return tuple(sorted(output, key=lambda item: (item.player_id, item.horizon.value, item.period_start)))


def _team_key(
    subject: NflTeamUnitForecastSubject,
    horizon: ForecastHorizon,
    period_start,
    period_end,
    as_of,
) -> tuple[object, ...]:
    return (
        subject.season,
        subject.nfl_team,
        subject.unit,
        horizon,
        period_start,
        period_end,
        as_of,
    )


def derive_dst_fantasy_point_forecasts(
    observations: tuple[TeamUnitForecastObservation, ...],
    *,
    distributional_evidence: tuple[TeamUnitDistributionalEvidence, ...] = (),
    rules: LeagueRules,
    source: str = "fsffl:dst_league_scored",
    model_version: str = "next2-dst-scoring-v1",
) -> tuple[TeamUnitForecastObservation, ...]:
    """Score D/ST team-unit raw events plus per-game bucket distributions."""

    if not _has_lineup_slot(rules, RosterSlot.DST):
        return ()

    active_rules = [
        rule
        for rule in rules.scoring
        if rule.points != 0 and _rule_relevant(rule.stat, ForecastSubjectFamily.DST)
    ]
    unsupported = [
        rule.stat
        for rule in active_rules
        if rule.stat not in _DST_LINEAR_RULES
        and not rule.stat.startswith("pts_allow_")
        and not rule.stat.startswith("yds_allow_")
    ]
    if unsupported:
        raise ValueError(f"unsupported active D/ST scoring rules: {sorted(set(unsupported))}")

    grouped: dict[tuple[object, ...], list[TeamUnitForecastObservation]] = defaultdict(list)
    subjects_by_key: dict[tuple[object, ...], NflTeamUnitForecastSubject] = {}
    for observation in observations:
        if observation.metric == ForecastMetric.FANTASY_POINTS:
            continue
        key = _team_key(
            observation.subject,
            observation.horizon,
            observation.period_start,
            observation.period_end,
            observation.as_of,
        )
        grouped[key].append(observation)
        subjects_by_key[key] = observation.subject

    distributions_by_key: dict[tuple[object, ...], list[TeamUnitDistributionalEvidence]] = defaultdict(list)
    for evidence in distributional_evidence:
        key = _team_key(
            evidence.subject,
            evidence.horizon,
            evidence.period_start,
            evidence.period_end,
            evidence.as_of,
        )
        distributions_by_key[key].append(evidence)
        subjects_by_key[key] = evidence.subject

    output: list[TeamUnitForecastObservation] = []
    for key, subject in subjects_by_key.items():
        items = grouped.get(key, [])
        by_metric = {item.metric: item for item in items}
        mean = 0.0
        variance = 0.0
        missing = False

        for rule in active_rules:
            if rule.stat.startswith("pts_allow_") or rule.stat.startswith("yds_allow_"):
                continue
            metric = _DST_LINEAR_RULES[rule.stat]
            item = by_metric.get(metric)
            if item is None:
                missing = True
                break
            mean += rule.points * item.distribution.mean
            variance += (rule.points * item.distribution.stddev) ** 2
        if missing:
            continue

        evidence_items = distributions_by_key.get(key, [])
        for family, prefix in (("points_allowed", "pts_allow_"), ("yards_allowed", "yds_allow_")):
            family_rules = [rule for rule in active_rules if rule.stat.startswith(prefix)]
            if not family_rules:
                continue
            evidence = next((item for item in evidence_items if item.family == family), None)
            if evidence is None:
                missing = True
                break
            for game in evidence.games:
                probabilities = {item.rule_stat: item.probability for item in game.probabilities}
                if any(rule.stat not in probabilities for rule in family_rules):
                    missing = True
                    break
                game_mean = sum(rule.points * probabilities[rule.stat] for rule in family_rules)
                game_second_moment = sum(
                    (rule.points ** 2) * probabilities[rule.stat] for rule in family_rules
                )
                mean += game_mean
                variance += max(game_second_moment - game_mean ** 2, 0.0)
            if missing:
                break
        if missing:
            continue

        metadata = items[0] if items else evidence_items[0]
        all_provenance = [item.provenance for item in items] + [item.provenance for item in evidence_items]
        provenance = Provenance(
            source=source,
            retrieved_at=max(item.retrieved_at for item in all_provenance),
            effective_at=max(item.effective_at for item in all_provenance),
            source_version=model_version,
        )
        output.append(
            TeamUnitForecastObservation(
                subject=subject,
                horizon=metadata.horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=metadata.period_start,
                period_end=metadata.period_end,
                distribution=ForecastDistribution(mean=mean, stddev=sqrt(max(variance, 0.0))),
                source=source,
                model_version=f"{model_version}:linear-plus-distributional",
                as_of=metadata.as_of,
                provenance=provenance,
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: (
                item.subject.season,
                item.subject.nfl_team,
                item.horizon.value,
                item.period_start,
            ),
        )
    )
