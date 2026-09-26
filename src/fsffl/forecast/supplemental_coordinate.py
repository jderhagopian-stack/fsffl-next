from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import (
    FrozenModel,
    LeagueRules,
    Position,
    Provenance,
    canonical_nfl_team,
)

from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION = (
    "current-supplemental-coordinate-v2:fumbles-lost-current-pace"
)
SUPPLEMENTAL_COORDINATE_SOURCE = "fsffl:current_supplement:fumbles_lost"
FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR = 1.13855744535
FUMBLES_LOST_UNCERTAINTY_EVIDENCE_ID = (
    "research:2024-cbs-fantasysharks-two-source-rmse"
)
FUMBLES_LOST_UNCERTAINTY_MODEL_VERSION = (
    "fumbles-lost-current-pace-uncertainty-v1"
)


class SupplementalNormalizationMethod(StrEnum):
    CANONICAL_REMAINING_RATE_TO_17_GAME_PACE = (
        "canonical_remaining_rate_to_17_game_pace"
    )


class SupplementalTargetSemantics(StrEnum):
    SEASON_EQUIVALENT_CURRENT_RATE = "season_equivalent_current_rate"


class SupplementalSourceDenominatorSemantics(StrEnum):
    CANONICAL_REMAINING_GAMES = "canonical_remaining_games"


class SupplementalCoordinateSourceRow(FrozenModel):
    """Canonical-player provider row before target-shape normalization.

    source_games_represented is retained as provider evidence and must match the
    canonical NFL remaining-game count at that source's acquisition cutoff.
    """

    player_id: str
    position: Position
    nfl_team: str
    projected_events: Annotated[float, Field(ge=0)]
    source_games_represented: Annotated[int, Field(ge=1, le=17)]
    canonical_remaining_games_at_capture: Annotated[int, Field(ge=1, le=17)]
    denominator_semantics: Literal["canonical_remaining_games"] = (
        SupplementalSourceDenominatorSemantics.CANONICAL_REMAINING_GAMES.value
    )

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("supplemental source row player_id cannot be blank")
        return value

    @field_validator("nfl_team")
    @classmethod
    def normalize_team(cls, value: str) -> str:
        return canonical_nfl_team(value)

    @model_validator(mode="after")
    def validate_row(self) -> "SupplementalCoordinateSourceRow":
        if self.position not in {Position.QB, Position.RB, Position.WR, Position.TE}:
            raise ValueError("FUMBLES_LOST supplement applies only to QB/RB/WR/TE")
        if self.source_games_represented != self.canonical_remaining_games_at_capture:
            raise ValueError(
                "supplement source remaining-game state does not match canonical schedule"
            )
        return self


class SupplementalCoordinateSourceEvidence(FrozenModel):
    """Provider-neutral current source evidence for one material coordinate."""

    provider: str
    independence_group: str
    source_id: str
    season: Literal[2026] = 2026
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
    source_health_passed: bool
    exact_lost_fumble_semantics: bool
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
    """Durable source package that is explicitly non-promoting by itself."""

    season: Literal[2026] = 2026
    metric: ForecastMetric = ForecastMetric.FUMBLES_LOST
    source_horizon: ForecastHorizon = ForecastHorizon.REST_OF_SEASON
    sources: tuple[SupplementalCoordinateSourceEvidence, ...]
    production_authority_promoted: Literal[False] = False
    preseason_eligible: Literal[False] = False
    annual_preseason_snapshot_eligible: Literal[False] = False
    historical_pit_eligible: Literal[False] = False
    backfill_allowed: Literal[False] = False
    model_version: Literal[
        "current-supplemental-coordinate-v2:fumbles-lost-current-pace"
    ] = SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_package(self) -> "SupplementalCoordinateEvidencePackage":
        if self.metric != ForecastMetric.FUMBLES_LOST:
            raise ValueError("bounded supplement package is FUMBLES_LOST-only")
        if self.source_horizon != ForecastHorizon.REST_OF_SEASON:
            raise ValueError("bounded supplement package must retain ROS source horizon")
        if not self.sources:
            raise ValueError("supplemental evidence package requires source evidence")
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("supplemental package source ids must be unique")
        return self


class SupplementalTargetPeriod(FrozenModel):
    """Current target shape expected by the existing season-mean scoring bridge."""

    horizon: Literal["season"] = ForecastHorizon.SEASON.value
    period_start: datetime
    period_end: datetime
    evaluation_as_of: datetime
    semantics: Literal["season_equivalent_current_rate"] = (
        SupplementalTargetSemantics.SEASON_EQUIVALENT_CURRENT_RATE.value
    )
    target_games: Literal[17] = 17
    normalization_method: Literal[
        "canonical_remaining_rate_to_17_game_pace"
    ] = (
        SupplementalNormalizationMethod.CANONICAL_REMAINING_RATE_TO_17_GAME_PACE.value
    )
    required_player_ids: tuple[str, ...]

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
        if not self.required_player_ids:
            raise ValueError("supplement target requires the governed player universe")
        if len(self.required_player_ids) != len(set(self.required_player_ids)):
            raise ValueError("supplement target player ids must be unique")
        if any(not player_id.strip() for player_id in self.required_player_ids):
            raise ValueError("supplement target player ids cannot be blank")
        return self


class NormalizedSupplementalSourceValue(FrozenModel):
    player_id: str
    position: Position
    nfl_team: str
    provider: str
    independence_group: str
    source_id: str
    source_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: Literal["season"] = ForecastHorizon.SEASON.value
    source_projected_events: float
    source_games_represented: int
    canonical_remaining_games_at_capture: int
    source_rate_per_game: float
    target_games: Literal[17] = 17
    normalized_events: float
    normalization_method: Literal[
        "canonical_remaining_rate_to_17_game_pace"
    ] = (
        SupplementalNormalizationMethod.CANONICAL_REMAINING_RATE_TO_17_GAME_PACE.value
    )


class SupplementalCoordinateEnsemble(FrozenModel):
    """Future certified current-only coordinate; still not a preseason artifact."""

    season: Literal[2026] = 2026
    metric: Literal["fumbles_lost"] = ForecastMetric.FUMBLES_LOST.value
    authority_tier: Literal["two_source_material_coordinate"] = (
        "two_source_material_coordinate"
    )
    evidence_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: Literal["season"] = ForecastHorizon.SEASON.value
    target_quantity_kind: Literal["season_equivalent_current_pace"] = (
        "season_equivalent_current_pace"
    )
    target_games: Literal[17] = 17
    target_period_start: datetime
    target_period_end: datetime
    evaluation_as_of: datetime
    authority_valid_from: datetime
    normalized_source_values: tuple[NormalizedSupplementalSourceValue, ...]
    observations: tuple[ForecastObservation, ...]
    source_ids: tuple[str, str]
    independence_groups: tuple[str, str]
    empirical_coordinate_floor: float = FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR
    uncertainty_evidence_id: Literal[
        "research:2024-cbs-fantasysharks-two-source-rmse"
    ] = FUMBLES_LOST_UNCERTAINTY_EVIDENCE_ID
    uncertainty_model_version: Literal[
        "fumbles-lost-current-pace-uncertainty-v1"
    ] = FUMBLES_LOST_UNCERTAINTY_MODEL_VERSION
    lineage_class: Literal["supplemental_mixed_vintage_current"] = (
        "supplemental_mixed_vintage_current"
    )
    preseason_eligible: Literal[False] = False
    annual_preseason_snapshot_eligible: Literal[False] = False
    historical_pit_before_authority_valid_from: Literal[False] = False
    backfill_allowed: Literal[False] = False
    model_version: Literal[
        "current-supplemental-coordinate-v2:fumbles-lost-current-pace"
    ] = SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION

    @field_validator(
        "target_period_start",
        "target_period_end",
        "evaluation_as_of",
        "authority_valid_from",
    )
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("supplement ensemble timestamps must be timezone-aware")
        return value.astimezone(UTC)


class SupplementalApplicationLineage(FrozenModel):
    consumed: bool
    metric: Literal["fumbles_lost"] = ForecastMetric.FUMBLES_LOST.value
    evidence_horizon: Literal["rest_of_season"] = ForecastHorizon.REST_OF_SEASON.value
    target_horizon: Literal["season"] = ForecastHorizon.SEASON.value
    authority_valid_from: datetime
    source_ids: tuple[str, str]
    independence_groups: tuple[str, str]
    lineage_class: Literal["supplemental_mixed_vintage_current"] = (
        "supplemental_mixed_vintage_current"
    )
    preseason_eligible: Literal[False] = False
    historical_pit_eligible: Literal[False] = False
    backfill_allowed: Literal[False] = False


class SupplementalApplicationResult(FrozenModel):
    """Keep ordinary raw Forecast and current supplement as separate inputs."""

    base_observations: tuple[ForecastObservation, ...]
    supplemental_observations: tuple[ForecastObservation, ...]
    lineage: SupplementalApplicationLineage


def _normalize_source_values(
    package: SupplementalCoordinateEvidencePackage,
    *,
    target: SupplementalTargetPeriod,
) -> tuple[NormalizedSupplementalSourceValue, ...]:
    values: list[NormalizedSupplementalSourceValue] = []
    required = set(target.required_player_ids)
    for source in package.sources:
        if source.captured_at > target.evaluation_as_of:
            raise ValueError("supplement source acquisition cannot postdate target evaluation")
        if not source.private_beta_eligible:
            raise ValueError(
                f"supplement source {source.source_id} is not private-beta eligible"
            )
        if not source.source_health_passed:
            raise ValueError(f"supplement source {source.source_id} failed source health")
        if not source.exact_lost_fumble_semantics:
            raise ValueError(
                f"supplement source {source.source_id} is not exact lost-fumble evidence"
            )
        source_ids = {row.player_id for row in source.rows}
        missing = sorted(required.difference(source_ids))
        if missing:
            raise ValueError(
                f"supplement source {source.source_id} lacks required player coverage: {missing[:5]}"
            )
        for row in source.rows:
            if row.player_id not in required:
                continue
            rate = row.projected_events / row.canonical_remaining_games_at_capture
            normalized = rate * target.target_games
            values.append(
                NormalizedSupplementalSourceValue(
                    player_id=row.player_id,
                    position=row.position,
                    nfl_team=row.nfl_team,
                    provider=source.provider,
                    independence_group=source.independence_group,
                    source_id=source.source_id,
                    source_projected_events=row.projected_events,
                    source_games_represented=row.source_games_represented,
                    canonical_remaining_games_at_capture=row.canonical_remaining_games_at_capture,
                    source_rate_per_game=rate,
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
) -> SupplementalCoordinateEnsemble:
    """Build the target-shape coordinate only after the external gates are green.

    No production caller is registered here. The input package must already encode
    stage-appropriate rights eligibility, exact semantics and source-health results.
    """

    if len(package.sources) != 2:
        raise ValueError(
            "material FUMBLES_LOST authority requires exactly two accepted sources"
        )
    if any(not source.private_beta_eligible for source in package.sources):
        raise ValueError("supplement sources are not private-beta eligible")
    groups = tuple(sorted(source.independence_group for source in package.sources))
    if len(set(groups)) != 2:
        raise ValueError("supplement lacks two independent sources")

    authority_valid_from = max(source.captured_at for source in package.sources)
    if target.evaluation_as_of < authority_valid_from:
        raise ValueError("target evaluation predates supplemental authority_valid_from")

    normalized = _normalize_source_values(package, target=target)
    by_player: dict[str, list[NormalizedSupplementalSourceValue]] = defaultdict(list)
    for item in normalized:
        by_player[item.player_id].append(item)

    observations: list[ForecastObservation] = []
    accepted_values: list[NormalizedSupplementalSourceValue] = []
    for player_id in sorted(target.required_player_ids):
        rows = by_player.get(player_id, [])
        if len(rows) != 2 or len({row.independence_group for row in rows}) != 2:
            raise ValueError(f"supplement lacks two-source normalized coverage for {player_id}")
        positions = {row.position for row in rows}
        teams = {row.nfl_team for row in rows}
        if len(positions) != 1 or len(teams) != 1:
            raise ValueError(f"supplement sources disagree on player identity for {player_id}")
        x_a, x_b = sorted(row.normalized_events for row in rows)
        mean = fmean((x_a, x_b))
        provider_disagreement_std = abs(x_a - x_b) / 2.0
        stddev = max(
            provider_disagreement_std,
            FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR,
        )
        accepted_values.extend(rows)
        observations.append(
            ForecastObservation(
                player_id=player_id,
                position=next(iter(positions)),
                horizon=ForecastHorizon.SEASON,
                metric=ForecastMetric.FUMBLES_LOST,
                period_start=target.period_start,
                period_end=target.period_end,
                distribution=ForecastDistribution(mean=mean, stddev=stddev),
                source=SUPPLEMENTAL_COORDINATE_SOURCE,
                model_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
                as_of=target.evaluation_as_of,
                provenance=Provenance(
                    source=SUPPLEMENTAL_COORDINATE_SOURCE,
                    retrieved_at=authority_valid_from,
                    effective_at=max(source.effective_at for source in package.sources),
                    source_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
                ),
            )
        )

    return SupplementalCoordinateEnsemble(
        target_period_start=target.period_start,
        target_period_end=target.period_end,
        evaluation_as_of=target.evaluation_as_of,
        authority_valid_from=authority_valid_from,
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
        independence_groups=tuple(sorted(set(groups))),
    )


def league_consumes_fumbles_lost(rules: LeagueRules) -> bool:
    return any(rule.stat == "fum_lost" and rule.points != 0 for rule in rules.scoring)


def apply_certified_supplemental_coordinate(
    base_observations: tuple[ForecastObservation, ...],
    *,
    supplement: SupplementalCoordinateEnsemble,
    rules: LeagueRules,
    evaluation_as_of: datetime,
) -> SupplementalApplicationResult:
    """Prepare current scoring inputs without mutating ordinary raw Forecast."""

    if evaluation_as_of.tzinfo is None:
        raise ValueError("supplement evaluation cutoff must be timezone-aware")
    evaluation_as_of = evaluation_as_of.astimezone(UTC)
    consumed = league_consumes_fumbles_lost(rules)
    lineage = SupplementalApplicationLineage(
        consumed=consumed,
        authority_valid_from=supplement.authority_valid_from,
        source_ids=supplement.source_ids,
        independence_groups=supplement.independence_groups,
    )
    if not consumed:
        return SupplementalApplicationResult(
            base_observations=base_observations,
            supplemental_observations=(),
            lineage=lineage,
        )
    if evaluation_as_of < supplement.authority_valid_from:
        raise ValueError("supplement is unavailable before authority_valid_from")

    existing_keys = {
        (item.player_id, item.horizon, item.period_start, item.period_end, item.metric)
        for item in base_observations
    }
    base_targets = {
        (item.player_id, item.position, item.horizon, item.period_start, item.period_end)
        for item in base_observations
        if item.metric != ForecastMetric.FANTASY_POINTS
    }
    additions: list[ForecastObservation] = []
    for item in supplement.observations:
        target_key = (
            item.player_id,
            item.position,
            item.horizon,
            item.period_start,
            item.period_end,
        )
        if target_key not in base_targets:
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
        additions.append(item)

    if not additions:
        raise ValueError("league consumes FUMBLES_LOST but supplement matched no base players")

    return SupplementalApplicationResult(
        base_observations=base_observations,
        supplemental_observations=tuple(
            sorted(additions, key=lambda item: (item.player_id, item.position.value))
        ),
        lineage=lineage,
    )
