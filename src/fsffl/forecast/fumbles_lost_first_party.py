from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from typing import Callable, Mapping

from pydantic import field_validator, model_validator

from fsffl.providers.sleeper_weekly_stats import (
    SleeperWeeklyStatLine,
    SleeperWeeklyStatsSource,
)
from fsffl.state.models import FrozenModel, LeagueState, Position, Provenance

from .fumbles_lost_first_party_priors import (
    CALIBRATION_PSEUDO_CURRENT_SEASONS,
    CALIBRATION_SCALAR_2026,
    COLD_START_STDDEV_FLOOR,
    CURRENT_BOARD_SHA256,
    CURRENT_SHADOWS_GIT_BLOB_SHA,
    DATA_LINEAGE_GIT_BLOB_SHA,
    MODEL_VERSION,
    NFLVERSE_TRAINING_SHA256,
    PLAYER_PRIORS,
    POSITION_LOST_FUMBLE_PER_OPPORTUNITY,
    POSITION_OPPORTUNITY_PER_GAME,
    POSITION_RESIDUAL_STDDEV_FLOOR,
    REQUIRED_COMPLETED_THROUGH_WEEK,
    REQUIRED_TARGET_SEASON,
    ROLE_PRIOR_GAMES,
    TARGET_GAMES,
    TRAINING_SEASONS,
    VALIDATION_RESULTS_GIT_BLOB_SHA,
)
from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


FIRST_PARTY_FUMBLES_LOST_SOURCE = "fsffl:first_party:fumbles_lost"
FIRST_PARTY_FUMBLES_LOST_UNCERTAINTY_VERSION = (
    "next2-fumbles-lost-uncertainty-v1:position-oot-plus-cold-start"
)
FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION = (
    "current-supplemental-coordinate-v3:first-party-fumbles-lost"
)
SLEEPER_CURRENT_INPUT_VERSION = (
    "sleeper-weekly-opportunity-v1:pass_att+sack+rush_att|rush_att+rec"
)
_REQUIRED_SCHEMA_KEYS = frozenset({"pass_att", "sack", "rush_att", "rec"})
_ALLOWED_POSITIONS = frozenset({Position.QB, Position.RB, Position.WR, Position.TE})

Clock = Callable[[], datetime]


class FirstPartyFumblesLostEvidenceTier(StrEnum):
    HISTORY_PLUS_CURRENT = "history_plus_current"
    HISTORY_ONLY = "history_only"
    CURRENT_ONLY = "current_only"
    COLD_START = "cold_start"
    IDENTITY_LIGHT = "identity_light"


class FirstPartyFumblesLostPlayerEvidence(FrozenModel):
    player_id: str
    position: Position
    historical_gsis_id: str | None = None
    identity_method: str
    evidence_tier: FirstPartyFumblesLostEvidenceTier
    history_games: int
    history_opportunities: float
    current_games: int
    current_opportunities: float
    historical_role_opportunities_per_game: float
    role_opportunities_per_game: float
    position_lost_fumble_per_opportunity: float
    mean_fumbles_lost: float
    predictive_stddev: float

    @model_validator(mode="after")
    def validate_evidence(self) -> "FirstPartyFumblesLostPlayerEvidence":
        if self.position not in _ALLOWED_POSITIONS:
            raise ValueError("first-party FUMBLES_LOST supports QB/RB/WR/TE only")
        if self.history_games < 0 or self.current_games < 0:
            raise ValueError("model games cannot be negative")
        if self.history_opportunities < 0 or self.current_opportunities < 0:
            raise ValueError("model opportunities cannot be negative")
        if self.predictive_stddev <= 0:
            raise ValueError("first-party FUMBLES_LOST uncertainty must be non-zero")
        return self


class FirstPartyFumblesLostSupplement(FrozenModel):
    season: int
    metric: ForecastMetric = ForecastMetric.FUMBLES_LOST
    authority_tier: str = "forecast_owned_first_party_empirical_model"
    league_state_id: str
    completed_through_week: int
    model_version: str = MODEL_VERSION
    supplement_model_version: str = FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
    uncertainty_model_version: str = FIRST_PARTY_FUMBLES_LOST_UNCERTAINTY_VERSION
    calibration_scalar: float = CALIBRATION_SCALAR_2026
    training_seasons: tuple[int, ...] = TRAINING_SEASONS
    calibration_pseudo_current_seasons: tuple[int, ...] = (
        CALIBRATION_PSEUDO_CURRENT_SEASONS
    )
    current_input_version: str = SLEEPER_CURRENT_INPUT_VERSION
    current_input_provider: str = "sleeper_stats"
    current_input_captured_at: datetime
    built_at: datetime
    authority_valid_from: datetime
    observed_schema_keys: tuple[str, ...]
    current_input_sha256: str
    player_evidence: tuple[FirstPartyFumblesLostPlayerEvidence, ...]
    observations: tuple[ForecastObservation, ...]
    omitted_player_ids: tuple[str, ...] = ()
    research_current_board_sha256: str = CURRENT_BOARD_SHA256
    research_current_shadows_git_blob_sha: str = CURRENT_SHADOWS_GIT_BLOB_SHA
    research_validation_git_blob_sha: str = VALIDATION_RESULTS_GIT_BLOB_SHA
    research_lineage_git_blob_sha: str = DATA_LINEAGE_GIT_BLOB_SHA
    training_asset_sha256: tuple[tuple[int, str], ...] = tuple(
        sorted(NFLVERSE_TRAINING_SHA256.items())
    )
    exact_lost_fumble_target_semantics: str = (
        "sack_fumbles_lost+rushing_fumbles_lost+receiving_fumbles_lost"
    )
    preseason_eligible: bool = False
    annual_preseason_snapshot_eligible: bool = False
    historical_pit_eligible: bool = False
    backfill_allowed: bool = False

    @field_validator(
        "current_input_captured_at",
        "built_at",
        "authority_valid_from",
    )
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("first-party FUMBLES_LOST timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_contract(self) -> "FirstPartyFumblesLostSupplement":
        if self.season != REQUIRED_TARGET_SEASON:
            raise ValueError("first-party FUMBLES_LOST v1 is 2026-only")
        if self.completed_through_week != REQUIRED_COMPLETED_THROUGH_WEEK:
            raise ValueError("first-party FUMBLES_LOST v1 requires completed Week 2")
        if self.metric != ForecastMetric.FUMBLES_LOST:
            raise ValueError("first-party supplement owns only exact FUMBLES_LOST")
        if self.calibration_scalar != CALIBRATION_SCALAR_2026:
            raise ValueError("first-party calibration scalar does not match frozen Research")
        if self.authority_valid_from < self.current_input_captured_at:
            raise ValueError("authority cannot predate current input acquisition")
        if self.authority_valid_from < self.built_at:
            raise ValueError("authority cannot predate model build")
        if not self.observations:
            raise ValueError("first-party supplement requires at least one observation")
        if len({row.player_id for row in self.observations}) != len(self.observations):
            raise ValueError("first-party supplement observations require unique players")
        return self

    @property
    def authority_fingerprint(self) -> str:
        payload = {
            "league_state_id": self.league_state_id,
            "completed_through_week": self.completed_through_week,
            "model_version": self.model_version,
            "calibration_scalar": self.calibration_scalar,
            "current_input_sha256": self.current_input_sha256,
            "observations": [
                (
                    row.player_id,
                    row.distribution.mean,
                    row.distribution.stddev,
                )
                for row in self.observations
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _numeric(stats: Mapping[str, float], key: str) -> float:
    value = stats.get(key, 0.0)
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"Sleeper current input {key} must be finite and non-negative")
    return numeric


def _opportunities(stats: Mapping[str, float], position: Position) -> float:
    if position == Position.QB:
        # Sleeper offensive player stats use 'sack' for times the passer was
        # sacked. Defensive sacks live in the distinct idp_sack namespace.
        return (
            _numeric(stats, "pass_att")
            + _numeric(stats, "sack")
            + _numeric(stats, "rush_att")
        )
    if position in {Position.RB, Position.WR, Position.TE}:
        return _numeric(stats, "rush_att") + _numeric(stats, "rec")
    raise ValueError("first-party FUMBLES_LOST supports QB/RB/WR/TE only")


def _current_input_rows_sha256(
    rows_by_week: Mapping[int, tuple[SleeperWeeklyStatLine, ...]],
) -> str:
    payload = [
        (
            week,
            row.player_id,
            sorted((str(key), float(value)) for key, value in row.stats.items()),
            row.source_company,
        )
        for week in sorted(rows_by_week)
        for row in rows_by_week[week]
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _evidence_tier(
    *,
    accepted_tier: str,
    identity_method: str,
    history_games: int,
    current_games: int,
) -> FirstPartyFumblesLostEvidenceTier:
    if identity_method == "unmapped" or accepted_tier == "unmapped":
        return FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT
    if history_games > 0 and current_games > 0:
        return FirstPartyFumblesLostEvidenceTier.HISTORY_PLUS_CURRENT
    if history_games > 0:
        return FirstPartyFumblesLostEvidenceTier.HISTORY_ONLY
    if current_games > 0:
        return FirstPartyFumblesLostEvidenceTier.CURRENT_ONLY
    return FirstPartyFumblesLostEvidenceTier.COLD_START


def build_first_party_fumbles_lost_supplement(
    league_state: LeagueState,
    *,
    base_observations: tuple[ForecastObservation, ...],
    stats_source: SleeperWeeklyStatsSource | None = None,
    clock: Clock | None = None,
) -> FirstPartyFumblesLostSupplement:
    """Build the accepted current-only exact FUMBLES_LOST Forecast supplement.

    This function never changes ordinary raw Forecast observations. It only emits
    the separate current supplement consumed later by the PR #253/#255 scorer lane.
    """

    if league_state.league.season != REQUIRED_TARGET_SEASON:
        raise ValueError("first-party FUMBLES_LOST v1 is authorized only for 2026")
    if league_state.completed_through_week != REQUIRED_COMPLETED_THROUGH_WEEK:
        raise ValueError(
            "first-party FUMBLES_LOST v1 requires canonical completed_through_week=2"
        )
    if any(
        row.metric == ForecastMetric.FUMBLES_LOST
        for row in base_observations
    ):
        raise ValueError(
            "first-party FUMBLES_LOST supplement cannot replace ordinary raw Forecast truth"
        )

    source = stats_source or SleeperWeeklyStatsSource()
    provider_state = source.fetch_nfl_state()
    if provider_state.season != league_state.league.season:
        raise ValueError("Sleeper current-input season does not match canonical State")
    if provider_state.completed_through_week != REQUIRED_COMPLETED_THROUGH_WEEK:
        raise ValueError(
            "Sleeper current-input cutoff does not match accepted completed Week 2"
        )
    if provider_state.completed_through_week != league_state.completed_through_week:
        raise ValueError("Sleeper current-input cutoff does not match canonical State")

    rows_by_week = {
        week: source.fetch_week(season=REQUIRED_TARGET_SEASON, week=week)
        for week in range(1, REQUIRED_COMPLETED_THROUGH_WEEK + 1)
    }
    all_rows = tuple(
        row
        for week in sorted(rows_by_week)
        for row in rows_by_week[week]
    )
    if not all_rows:
        raise ValueError("Sleeper current-input feed returned no Week 1-2 stat rows")
    observed_schema = frozenset(
        str(key)
        for row in all_rows
        for key in row.stats.keys()
    )
    missing_schema = sorted(_REQUIRED_SCHEMA_KEYS.difference(observed_schema))
    if missing_schema:
        raise ValueError(
            "Sleeper current-input feed lacks accepted opportunity semantics: "
            + ",".join(missing_schema)
        )

    stats_by_player: dict[str, list[SleeperWeeklyStatLine]] = defaultdict(list)
    for row in all_rows:
        stats_by_player[row.player_id].append(row)

    # One target shape per ordinary player/horizon/period. The live ensemble groups
    # multiple raw metrics under identical target coordinates.
    targets: dict[
        tuple[str, Position, ForecastHorizon, datetime, datetime],
        ForecastObservation,
    ] = {}
    for row in base_observations:
        if row.metric == ForecastMetric.FANTASY_POINTS:
            continue
        if row.position not in _ALLOWED_POSITIONS:
            continue
        if row.horizon != ForecastHorizon.SEASON:
            continue
        key = (
            row.player_id,
            row.position,
            row.horizon,
            row.period_start,
            row.period_end,
        )
        targets.setdefault(key, row)
    if not targets:
        raise ValueError("first-party FUMBLES_LOST found no ordinary season Forecast targets")

    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise ValueError("first-party FUMBLES_LOST clock must be timezone-aware")
    built_at = now.astimezone(UTC)
    current_input_captured_at = max(
        [provider_state.captured_at] + [row.captured_at for row in all_rows]
    ).astimezone(UTC)
    authority_valid_from = max(built_at, current_input_captured_at)

    player_evidence: list[FirstPartyFumblesLostPlayerEvidence] = []
    observations: list[ForecastObservation] = []
    omitted: set[str] = set()

    for key, target in sorted(
        targets.items(),
        key=lambda item: (item[0][0], item[0][1].value),
    ):
        player_id, position, horizon, period_start, period_end = key
        prior = PLAYER_PRIORS.get(player_id)
        if prior is None:
            omitted.add(player_id)
            continue
        (
            prior_position,
            historical_gsis_id,
            identity_method,
            accepted_tier,
            history_games,
            history_opportunities,
            _accepted_current_games,
            _accepted_current_opportunities,
            _accepted_shadow_mean,
            _accepted_shadow_stddev,
        ) = prior
        if prior_position != position.value:
            omitted.add(player_id)
            continue

        current_lines = tuple(
            sorted(stats_by_player.get(player_id, ()), key=lambda row: row.week)
        )
        current_games = len({row.week for row in current_lines})
        current_opportunities = sum(
            _opportunities(row.stats, position) for row in current_lines
        )

        position_key = position.value
        position_rate = POSITION_LOST_FUMBLE_PER_OPPORTUNITY[position_key]
        position_role = POSITION_OPPORTUNITY_PER_GAME[position_key]
        historical_role = (
            float(history_opportunities) / int(history_games)
            if int(history_games) > 0
            else position_role
        )
        role = historical_role
        if current_games > 0:
            role = (
                current_opportunities + ROLE_PRIOR_GAMES * historical_role
            ) / (current_games + ROLE_PRIOR_GAMES)

        mean = max(
            0.0,
            CALIBRATION_SCALAR_2026
            * TARGET_GAMES
            * role
            * position_rate,
        )
        tier = _evidence_tier(
            accepted_tier=str(accepted_tier),
            identity_method=str(identity_method),
            history_games=int(history_games),
            current_games=current_games,
        )
        floor = POSITION_RESIDUAL_STDDEV_FLOOR[position_key]
        if tier in {
            FirstPartyFumblesLostEvidenceTier.COLD_START,
            FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
        }:
            floor = max(floor, COLD_START_STDDEV_FLOOR)
        stddev = max(math.sqrt(mean), floor)
        evidence = FirstPartyFumblesLostPlayerEvidence(
            player_id=player_id,
            position=position,
            historical_gsis_id=historical_gsis_id,
            identity_method=str(identity_method),
            evidence_tier=tier,
            history_games=int(history_games),
            history_opportunities=float(history_opportunities),
            current_games=current_games,
            current_opportunities=current_opportunities,
            historical_role_opportunities_per_game=historical_role,
            role_opportunities_per_game=role,
            position_lost_fumble_per_opportunity=position_rate,
            mean_fumbles_lost=mean,
            predictive_stddev=stddev,
        )
        player_evidence.append(evidence)

        # Scoring is evaluated for the exact canonical State cutoff. Actual model
        # acquisition/build time is retained on the supplement and is the PIT
        # authority boundary; it is deliberately not rewritten as preseason.
        observation_as_of = min(target.as_of, league_state.as_of)
        effective_at = min(current_input_captured_at, observation_as_of)
        observations.append(
            ForecastObservation(
                player_id=player_id,
                position=position,
                horizon=horizon,
                metric=ForecastMetric.FUMBLES_LOST,
                period_start=period_start,
                period_end=period_end,
                distribution=ForecastDistribution(mean=mean, stddev=stddev),
                source=FIRST_PARTY_FUMBLES_LOST_SOURCE,
                model_version=MODEL_VERSION,
                as_of=observation_as_of,
                provenance=Provenance(
                    source=FIRST_PARTY_FUMBLES_LOST_SOURCE,
                    retrieved_at=current_input_captured_at,
                    effective_at=effective_at,
                    source_version=MODEL_VERSION,
                ),
            )
        )

    if not observations:
        raise ValueError("first-party FUMBLES_LOST produced no governed player observations")

    return FirstPartyFumblesLostSupplement(
        season=league_state.league.season,
        league_state_id=league_state.state_id,
        completed_through_week=league_state.completed_through_week,
        current_input_captured_at=current_input_captured_at,
        built_at=built_at,
        authority_valid_from=authority_valid_from,
        observed_schema_keys=tuple(sorted(observed_schema)),
        current_input_sha256=_current_input_rows_sha256(rows_by_week),
        player_evidence=tuple(player_evidence),
        observations=tuple(observations),
        omitted_player_ids=tuple(sorted(omitted)),
    )
