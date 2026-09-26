from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, Position, Provenance

from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION = (
    "current-supplemental-coordinate-v1:fumbles-lost"
)
SUPPLEMENTAL_COORDINATE_SOURCE = "fsffl:current_supplement:fumbles_lost"


class SupplementalNormalizationMethod(StrEnum):
    PER_GAME_RATE_TO_TARGET_GAMES = "per_game_rate_to_target_games"


class SupplementalTargetSemantics(StrEnum):
    CURRENT_FORWARD_TOTAL = "current_forward_total"
    SEASON_EQUIVALENT_CURRENT_RATE = "season_equivalent_current_rate"
    FANTASY_REGULAR_SEASON_EQUIVALENT_CURRENT_RATE = (
        "fantasy_regular_season_equivalent_current_rate"
    )


class SupplementalCoordinateSourceRow(FrozenModel):
    """Canonical-player source row before any target-period normalization."""

    player_id: str
    position: Position
    projected_events: Annotated[float, Field(ge=0)]
    projected_games: Annotated[float, Field(gt=0, le=18)]

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("supplemental source row player_id cannot be blank")
        return value

    @model_validator(mode="after")
    def require_offensive_player(self) -> "SupplementalCoordinateSourceRow":
        if self.position not in {Position.QB, Position.RB, Position.WR, Position.TE}:
            raise ValueError("FUMBLES_LOST supplement applies only to QB/RB/WR/TE")
        return self


class SupplementalCoordinateSourceEvidence(FrozenModel):
    """Provider-neutral current source evidence for one material coordinate."""

    provider: str
    independence_group: str
    source_id: str
    season: Annotated[int, Field(ge=2000)]
    metric: ForecastMetric = ForecastMetric.FUMBLES_LOST
    source_horizon: ForecastHorizon = ForecastHorizon.REST_OF_SEASON
    captured_at: datetime
    effective_at: datetime
    source_period_start: datetime
    source_period_end: datetime
    source_version: str
    source_locator: str
    content_sha256: str
    private_beta_eligible: bool
    commercial_recheck_required: bool
    rights_basis: str
    rows: tuple[SupplementalCoordinateSourceRow, ...]

    @field_validator(
        "provider",
        "independence_group",
        "source_id",
        "source_version",
        "source_locator",
        "rights_basis",
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("supplemental source identifiers cannot be blank")
        return value

    @field_validator(
        "captured_at",
        "effective_at",
        "source_period_start",
        "source_period_end",
    )
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("supplemental source timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("content_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ValueError("content_sha256 must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def validate_source_contract(self) -> "SupplementalCoordinateSourceEvidence":
        if self.metric != ForecastMetric.FUMBLES_LOST:
            raise ValueError("bounded supplement contract is FUMBLES_LOST-only")
        if self.source_horizon != ForecastHorizon.REST_OF_SEASON:
            raise ValueError("current FUMBLES_LOST supplement requires explicit ROS evidence")
        if self.effective_at > self.captured_at:
            raise ValueError("source effective time cannot postdate acquisition")
        if self.source_period_end <= self.source_period_start:
            raise ValueError("source period_end must follow period_start")
        if not self.rows:
            raise ValueError("supplemental source evidence requires rows")
        ids = [row.player_id for row in self.rows]
        if len(ids) != len(set(ids)):
            raise ValueError("supplemental source rows require unique player ids")
        return self


class SupplementalCoordinateEvidencePackage(FrozenModel):
    """Durable, non-promoting source package.

    This package is safe to persist before Research certifies production authority.
    It deliberately cannot represent a promoted Forecast coordinate.
    """

    season: Annotated[int, Field(ge=2000)]
    metric: ForecastMetric = ForecastMetric.FUMBLES_LOST
    source_horizon: ForecastHorizon = ForecastHorizon.REST_OF_SEASON
    sources: tuple[SupplementalCoordinateSourceEvidence, ...]
    production_authority_promoted: Literal[False] = False
    preseason_eligible: Literal[False] = False
    historical_pit_eligible: Literal[False] = False
    model_version: Literal[
        "current-supplemental-coordinate-v1:fumbles-lost"
    ] = SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_package(self) -> "SupplementalCoordinateEvidencePackage":
        if self.metric != ForecastMetric.FUMBLES_LOST:
            raise ValueError("bounded supplement package is FUMBLES_LOST-only")
        if self.source_horizon != ForecastHorizon.REST_OF_SEASON:
            raise ValueError("bounded supplement package must retain ROS source horizon")
        if not self.sources:
            raise ValueError("supplemental evidence package requires source evidence")
        if any(source.season != self.season for source in self.sources):
            raise ValueError("supplemental source season must match package season")
        if any(source.metric != self.metric for source in self.sources):
            raise ValueError("supplemental source metric must match package metric")
        if any(source.source_horizon != self.source_horizon for source in self.sources):
            raise ValueError("supplemental source horizon must match package horizon")
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("supplemental package source ids must be unique")
        return self


class SupplementalTargetPlayerExposure(FrozenModel):
    player_id: str
    target_games: Annotated[float, Field(gt=0, le=18)]

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target exposure player_id cannot be blank")
        return value


class SupplementalTargetPeriod(FrozenModel):
    """Explicit current scoring target; never inferred from the source horizon."""

    horizon: ForecastHorizon
    period_start: datetime
    period_end: datetime
    evaluation_as_of: datetime
    semantics: SupplementalTargetSemantics
    normalization_method: Literal[
        "per_game_rate_to_target_games"
    ] = SupplementalNormalizationMethod.PER_GAME_RATE_TO_TARGET_GAMES.value
    player_exposures: tuple[SupplementalTargetPlayerExposure, ...]

    @field_validator("period_start", "period_end", "evaluation_as_of")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("supplemental target timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_target(self) -> "SupplementalTargetPeriod":
        if self.period_end <= self.period_start:
            raise ValueError("target period_end must follow period_start")
        if self.horizon not in {
            ForecastHorizon.SEASON,
            ForecastHorizon.REST_OF_SEASON,
            ForecastHorizon.FANTASY_REGULAR_SEASON,
        }:
            raise ValueError("supplement target horizon must be current scoring horizon")
        if not self.player_exposures:
            raise ValueError("supplement target requires player exposure")
        ids = [item.player_id for item in self.player_exposures]
        if len(ids) != len(set(ids)):
            raise ValueError("target player exposure requires unique player ids")
        return self


class SupplementalUncertaintyRow(FrozenModel):
    player_id: str
    stddev_events: Annotated[float, Field(gt=0)]

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("uncertainty player_id cannot be blank")
        return value


class SupplementalCoordinateUncertainty(FrozenModel):
    """Research-supplied non-zero uncertainty for the exact normalized target."""

    metric: ForecastMetric = ForecastMetric.FUMBLES_LOST
    target_horizon: ForecastHorizon
    target_period_start: datetime
    target_period_end: datetime
    evidence_id: str
    model_version: str
    source_compatible: bool
    rows: tuple[SupplementalUncertaintyRow, ...]

    @field_validator("target_period_start", "target_period_end")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("uncertainty timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("evidence_id", "model_version")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("uncertainty identifiers cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_uncertainty(self) -> "SupplementalCoordinateUncertainty":
        if self.metric != ForecastMetric.FUMBLES_LOST:
            raise ValueError("supplement uncertainty must describe FUMBLES_LOST")
        if self.target_period_end <= self.target_period_start:
            raise ValueError("uncertainty target period must be ordered")
        if not self.rows:
            raise ValueError("supplement uncertainty requires player rows")
        ids = [row.player_id for row in self.rows]
        if len(ids) != len(set(ids)):
            raise ValueError("uncertainty rows require unique player ids")
        return self


class NormalizedSupplementalSourceValue(FrozenModel):
    player_id: str
    position: Position
    provider: str
    independence_group: str
    source_id: str
    source_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: ForecastHorizon
    source_projected_events: float
    source_projected_games: float
    target_games: float
    normalized_events: float
    normalization_method: Literal["per_game_rate_to_target_games"] = (
        SupplementalNormalizationMethod.PER_GAME_RATE_TO_TARGET_GAMES.value
    )


class SupplementalCoordinateEnsemble(FrozenModel):
    """Promotable shape, constructible only after all material-coordinate gates pass."""

    season: Annotated[int, Field(ge=2000)]
    metric: Literal["fumbles_lost"] = ForecastMetric.FUMBLES_LOST.value
    authority_tier: Literal["two_source_material_coordinate"] = (
        "two_source_material_coordinate"
    )
    source_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: ForecastHorizon
    target_period_start: datetime
    target_period_end: datetime
    evaluation_as_of: datetime
    acquired_at: datetime
    normalized_source_values: tuple[NormalizedSupplementalSourceValue, ...]
    observations: tuple[ForecastObservation, ...]
    source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    uncertainty_evidence_id: str
    uncertainty_model_version: str
    lineage_class: Literal["supplemental_mixed_vintage_current"] = (
        "supplemental_mixed_vintage_current"
    )
    preseason_eligible: Literal[False] = False
    historical_pit_eligible: Literal[False] = False
    model_version: Literal[
        "current-supplemental-coordinate-v1:fumbles-lost"
    ] = SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION


class SupplementalApplicationLineage(FrozenModel):
    consumed: bool
    metric: Literal["fumbles_lost"] = ForecastMetric.FUMBLES_LOST.value
    source_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: ForecastHorizon
    acquired_at: datetime
    source_ids: tuple[str, ...]
    independence_groups: tuple[str, ...]
    lineage_class: Literal["supplemental_mixed_vintage_current"] = (
        "supplemental_mixed_vintage_current"
    )
    preseason_eligible: Literal[False] = False
    historical_pit_eligible: Literal[False] = False


class SupplementalApplicationResult(FrozenModel):
    observations: tuple[ForecastObservation, ...]
    lineage: SupplementalApplicationLineage


def _normalize_source_values(
    package: SupplementalCoordinateEvidencePackage,
    *,
    target: SupplementalTargetPeriod,
) -> tuple[NormalizedSupplementalSourceValue, ...]:
    exposures = {item.player_id: item.target_games for item in target.player_exposures}
    values: list[NormalizedSupplementalSourceValue] = []
    for source in package.sources:
        if source.captured_at > target.evaluation_as_of:
            raise ValueError("supplement source acquisition cannot postdate target evaluation")
        if not source.private_beta_eligible:
            raise ValueError(
                f"supplement source {source.source_id} is not private-beta eligible"
            )
        for row in source.rows:
            target_games = exposures.get(row.player_id)
            if target_games is None:
                continue
            normalized = (row.projected_events / row.projected_games) * target_games
            values.append(
                NormalizedSupplementalSourceValue(
                    player_id=row.player_id,
                    position=row.position,
                    provider=source.provider,
                    independence_group=source.independence_group,
                    source_id=source.source_id,
                    target_horizon=target.horizon,
                    source_projected_events=row.projected_events,
                    source_projected_games=row.projected_games,
                    target_games=target_games,
                    normalized_events=normalized,
                )
            )
    return tuple(
        sorted(
            values,
            key=lambda item: (
                item.player_id,
                item.independence_group,
                item.source_id,
            ),
        )
    )


def build_certified_supplemental_coordinate(
    package: SupplementalCoordinateEvidencePackage,
    *,
    target: SupplementalTargetPeriod,
    uncertainty: SupplementalCoordinateUncertainty,
    minimum_independent_sources: int = 2,
) -> SupplementalCoordinateEnsemble:
    """Build a target-period coordinate only after explicit material-coordinate gates.

    No production caller is registered by this module. Research must first supply a
    qualifying package and source-compatible uncertainty.
    """

    if minimum_independent_sources < 2:
        raise ValueError("material FUMBLES_LOST authority requires at least two sources")
    groups = {source.independence_group for source in package.sources if source.private_beta_eligible}
    if len(groups) < minimum_independent_sources:
        raise ValueError("supplement lacks two independent private-beta-eligible sources")
    if not uncertainty.source_compatible:
        raise ValueError("supplement uncertainty is not source-compatible")
    if uncertainty.target_horizon != target.horizon:
        raise ValueError("supplement uncertainty horizon does not match target")
    if (
        uncertainty.target_period_start != target.period_start
        or uncertainty.target_period_end != target.period_end
    ):
        raise ValueError("supplement uncertainty period does not match target")

    normalized = _normalize_source_values(package, target=target)
    uncertainty_by_player = {row.player_id: row.stddev_events for row in uncertainty.rows}
    by_player: dict[str, list[NormalizedSupplementalSourceValue]] = defaultdict(list)
    for item in normalized:
        by_player[item.player_id].append(item)

    observations: list[ForecastObservation] = []
    accepted_values: list[NormalizedSupplementalSourceValue] = []
    for player_id, rows in sorted(by_player.items()):
        by_group: dict[str, list[NormalizedSupplementalSourceValue]] = defaultdict(list)
        for row in rows:
            by_group[row.independence_group].append(row)
        if len(by_group) < minimum_independent_sources:
            continue
        stddev = uncertainty_by_player.get(player_id)
        if stddev is None or stddev <= 0:
            continue
        positions = {row.position for row in rows}
        if len(positions) != 1:
            raise ValueError(f"supplement sources disagree on position for {player_id}")
        group_means = [
            fmean(item.normalized_events for item in group_rows)
            for _group, group_rows in sorted(by_group.items())
        ]
        mean = fmean(group_means)
        accepted_values.extend(rows)
        observations.append(
            ForecastObservation(
                player_id=player_id,
                position=next(iter(positions)),
                horizon=target.horizon,
                metric=ForecastMetric.FUMBLES_LOST,
                period_start=target.period_start,
                period_end=target.period_end,
                distribution=ForecastDistribution(mean=mean, stddev=stddev),
                source=SUPPLEMENTAL_COORDINATE_SOURCE,
                model_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
                as_of=target.evaluation_as_of,
                provenance=Provenance(
                    source=SUPPLEMENTAL_COORDINATE_SOURCE,
                    retrieved_at=max(source.captured_at for source in package.sources),
                    effective_at=max(source.effective_at for source in package.sources),
                    source_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
                ),
            )
        )

    if not observations:
        raise ValueError(
            "supplement has no players with two-source normalized evidence and non-zero uncertainty"
        )

    return SupplementalCoordinateEnsemble(
        season=package.season,
        target_horizon=target.horizon,
        target_period_start=target.period_start,
        target_period_end=target.period_end,
        evaluation_as_of=target.evaluation_as_of,
        acquired_at=max(source.captured_at for source in package.sources),
        normalized_source_values=tuple(
            sorted(
                accepted_values,
                key=lambda item: (
                    item.player_id,
                    item.independence_group,
                    item.source_id,
                ),
            )
        ),
        observations=tuple(
            sorted(observations, key=lambda item: (item.player_id, item.position.value))
        ),
        source_ids=tuple(sorted(source.source_id for source in package.sources)),
        independence_groups=tuple(sorted(groups)),
        uncertainty_evidence_id=uncertainty.evidence_id,
        uncertainty_model_version=uncertainty.model_version,
    )


def league_consumes_fumbles_lost(rules: LeagueRules) -> bool:
    return any(rule.stat == "fum_lost" and rule.points != 0 for rule in rules.scoring)


def apply_certified_supplemental_coordinate(
    base_observations: tuple[ForecastObservation, ...],
    *,
    supplement: SupplementalCoordinateEnsemble,
    rules: LeagueRules,
) -> SupplementalApplicationResult:
    """Overlay only the certified FUMBLES_LOST coordinate for current scoring.

    The base observation tuple is returned unchanged for leagues that do not score
    lost fumbles. Existing FUMBLES_LOST evidence is never overwritten.
    """

    consumed = league_consumes_fumbles_lost(rules)
    lineage = SupplementalApplicationLineage(
        consumed=consumed,
        target_horizon=supplement.target_horizon,
        acquired_at=supplement.acquired_at,
        source_ids=supplement.source_ids,
        independence_groups=supplement.independence_groups,
    )
    if not consumed:
        return SupplementalApplicationResult(
            observations=base_observations,
            lineage=lineage,
        )

    existing_keys = {
        (item.player_id, item.horizon, item.period_start, item.period_end, item.metric)
        for item in base_observations
    }
    player_targets: dict[
        tuple[str, Position, ForecastHorizon, datetime, datetime],
        ForecastObservation,
    ] = {}
    for base in base_observations:
        if base.metric == ForecastMetric.FANTASY_POINTS:
            continue
        key = (
            base.player_id,
            base.position,
            base.horizon,
            base.period_start,
            base.period_end,
        )
        player_targets.setdefault(key, base)

    additions: list[ForecastObservation] = []
    for item in supplement.observations:
        target_key = (
            item.player_id,
            item.position,
            item.horizon,
            item.period_start,
            item.period_end,
        )
        anchor = player_targets.get(target_key)
        if anchor is None:
            continue
        coordinate_key = (
            item.player_id,
            item.horizon,
            item.period_start,
            item.period_end,
            ForecastMetric.FUMBLES_LOST,
        )
        if coordinate_key in existing_keys:
            raise ValueError(
                "certified supplement cannot overwrite existing FUMBLES_LOST evidence"
            )
        additions.append(
            item.model_copy(
                update={
                    # Scoring groups by the already-governed ensemble identity.
                    # Keep that identity stable while provenance marks this one
                    # coordinate as supplemental/mixed-vintage.
                    "source": anchor.source,
                    "model_version": anchor.model_version,
                }
            )
        )

    if not additions:
        raise ValueError("league consumes FUMBLES_LOST but supplement matched no base players")

    combined = base_observations + tuple(additions)
    return SupplementalApplicationResult(
        observations=tuple(
            sorted(
                combined,
                key=lambda item: (
                    item.player_id,
                    item.horizon.value,
                    item.period_start,
                    item.metric.value,
                    item.source,
                ),
            )
        ),
        lineage=lineage,
    )
