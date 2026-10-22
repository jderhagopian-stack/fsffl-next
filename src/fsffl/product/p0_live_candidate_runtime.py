"""Live point-in-time Year-1 assembly for dynamic P0 subjects.

This module joins the existing Sleeper weekly-stat and player-catalog adapters
with the existing governed CBS/Razzball in-season ensemble, then calls the
unchanged P0 future scorer. It deliberately uses the accepted P0 missingness
path for role and multi-year age-state features that are not produced by the
live acquisition contract.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from fsffl.forecast.current_normalization import _STAT_METRICS
from fsffl.forecast.fumbles_lost_first_party import FIRST_PARTY_FUMBLES_LOST_SOURCE
from fsffl.forecast.in_season_runtime import (
    ProjectionHistoryReader,
    build_in_season_forecasts,
)
from fsffl.forecast.league_scoring import (
    ScoringCoverageStatus,
    classify_scoring_coverage,
    derive_league_scoring_result,
)
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.providers.sleeper_weekly_stats import (
    SleeperNflState,
    SleeperSeasonStatLine,
    SleeperWeeklyStatLine,
    SleeperWeeklyStatsSource,
)
from fsffl.state.models import LeagueState, Position, Provenance, ProviderRef
from fsffl.forecast.in_season_orchestration import canonical_week_window

from .i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from .p0_candidate_evidence import (
    P0CandidateFacts,
    P0SourceStateAuthority,
    accepted_p0_source_state_authority,
)
from .p0_forecast_runtime import P0SourceRow, frozen_p0_source_rows
from .p0_future_forecast_provider import (
    P0FutureForecastContractMaterialization,
    build_p0_future_forecast_contract,
)


class _CachedSleeperWeeklyStatsSource:
    """Expose this run's validated Sleeper feed to accepted supplement logic."""

    def __init__(
        self,
        *,
        nfl_state: SleeperNflState,
        lines_by_week: Mapping[int, tuple[SleeperWeeklyStatLine, ...]],
    ) -> None:
        self._nfl_state = nfl_state
        self._lines_by_week = lines_by_week

    def fetch_nfl_state(self) -> SleeperNflState:
        return self._nfl_state

    def fetch_week(
        self, *, season: int, week: int
    ) -> tuple[SleeperWeeklyStatLine, ...]:
        if season != self._nfl_state.season:
            raise ValueError("cached Sleeper weekly season differs from acquired NFL state")
        if week not in self._lines_by_week:
            raise ValueError("requested Sleeper week was not acquired in this run")
        return self._lines_by_week[week]


def out_of_cohort_p0_subject_ids(
    canonical_player_ids: set[str] | tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    """Filter exact canonical IDs against the frozen benchmark's canonical IDs."""
    reference_ids = {row.player_id for row in frozen_p0_source_rows()}
    return tuple(sorted(set(canonical_player_ids) - reference_ids))


def exact_state_rostered_p0_subject_ids(league_state: LeagueState) -> tuple[str, ...]:
    """Return dynamic P0 candidates from the exact State being materialized.

    A fresh Sleeper snapshot is used to validate the live identity universe, but
    it is not the roster authority for a State-bound Career calculation. Using
    its roster can silently omit players who were rostered in the requested
    saved State but have since been dropped or moved.
    """
    rostered_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    return out_of_cohort_p0_subject_ids(rostered_ids)


@dataclass(frozen=True)
class P0LiveCandidateResult:
    evaluation_as_of: datetime
    completed_through_week: int
    candidate_ids: tuple[str, ...]
    candidate_source_rows: Mapping[str, P0SourceRow]
    year_one_standard: Mapping[str, ForecastObservation]
    year_one_league: Mapping[str, ForecastObservation]
    future: P0FutureForecastContractMaterialization | None
    failures: Mapping[str, str]
    ros_runtime: Any
    year_one_evidence_modes: Mapping[str, str]
    ros_fumbles_lost: tuple[ForecastObservation, ...] = ()
    fumbles_eligible_player_ids: tuple[str, ...] = ()
    fumbles_supplement_failure: str | None = None
    source_manifest: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class P0RosRuntimeSummary:
    """Small ROS readiness receipt retained after hosted Career acquisition."""

    ensemble_ready: bool
    ensemble_unavailability_reason: str | None
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    coverage: Any


LIVE_INPUT_MANIFEST_VERSION = "career-live-input-manifest-v1"
LIVE_INPUT_SOURCE_NAMES = frozenset({
    "canonical_state", "nfl_state", "current_catalog", "completed_week_stats",
    "prior_season_stats", "ros", "fumbles_supplement", "status_receipts",
    "reference_scoring", "candidate_facts",
})


def _input_digest(value) -> str:
    # Streaming encoding avoids a second whole-catalog/observation JSON string.
    digest = hashlib.sha256()
    for chunk in json.JSONEncoder(sort_keys=True, separators=(",", ":"), default=str).iterencode(value):
        digest.update(chunk.encode())
    return digest.hexdigest()


def _rows_digest(rows) -> str:
    return _input_digest(sorted(_input_digest(
        row.model_dump(mode="json") if hasattr(row, "model_dump") else asdict(row)
    ) for row in rows))


def live_source_manifest(*, captured_at: datetime, fingerprints: Mapping[str, str]) -> dict[str, object]:
    payload = {"version": LIVE_INPUT_MANIFEST_VERSION,
               "captured_at": captured_at.isoformat(), "fingerprints": dict(fingerprints)}
    return {**payload, "digest": _input_digest(payload)}


def valid_live_source_manifest(manifest) -> bool:
    if not isinstance(manifest, Mapping) or manifest.get("version") != LIVE_INPUT_MANIFEST_VERSION:
        return False
    try:
        captured = datetime.fromisoformat(manifest["captured_at"])
        fingerprints = manifest["fingerprints"]
        if captured.tzinfo is None or set(fingerprints) != LIVE_INPUT_SOURCE_NAMES:
            return False
        if any(not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
               for v in fingerprints.values()):
            return False
        return manifest.get("digest") == live_source_manifest(
            captured_at=captured, fingerprints=fingerprints)["digest"]
    except (KeyError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class StatusBasedZeroRosEvidence:
    """Explicit recorded evidence that a player has no expected 2026 participation."""

    player_id: str
    status: str
    source: str
    source_version: str
    observed_at: datetime
    no_expected_2026_participation: bool
    season: int = 2026
    entire_season_unavailable: bool = False

    def validate(self) -> None:
        if self.status not in {"out_for_season", "unsigned_no_expected_2026_participation"}:
            raise ValueError("status evidence does not establish season-long nonparticipation")
        if not self.source.strip() or not self.source_version.strip():
            raise ValueError("status evidence lacks source provenance")
        if self.observed_at.tzinfo is None:
            raise ValueError("status evidence timestamp must be timezone-aware")
        if not self.no_expected_2026_participation:
            raise ValueError("status evidence does not confirm no expected 2026 participation")


STATUS_BASED_YEAR_ONE_SCORING_VERSION = "status-y1-v2:verified-whole-season-no-residual"


def recorded_status_based_zero_ros_evidence(
    league_state: LeagueState, *, as_of: datetime,
) -> dict[str, StatusBasedZeroRosEvidence]:
    """Admit captured official facts for exact roster identities and cutoff.

    No provider fetch, fantasy-slot inference, or unsigned-player assumption.
    A newly acquired receipt cannot change a pre-capture replay/publication.
    """
    from fsffl.providers.nfl_status_evidence import SEASON_UNAVAILABILITY_RECEIPTS

    if as_of.tzinfo is None:
        raise ValueError("NFL status admission cutoff must be timezone-aware")
    roster_ids = {entry.player_id for team in league_state.team_states for entry in team.roster}
    players = {player.player_id: player for player in league_state.players}
    return {
        receipt.player_id: StatusBasedZeroRosEvidence(
            player_id=receipt.player_id, status="out_for_season",
            source=receipt.source_url,
            source_version=f"official-season-unavailability-v1:{receipt.fingerprint}",
            observed_at=receipt.captured_at,
            no_expected_2026_participation=True, season=receipt.season,
            entire_season_unavailable=True,
        )
        for receipt in SEASON_UNAVAILABILITY_RECEIPTS
        if receipt.season == league_state.league.season
        and receipt.captured_at <= as_of.astimezone(UTC)
        and receipt.player_id in roster_ids
        and receipt.player_id in players
        and players[receipt.player_id].position.value == receipt.position
    }


@dataclass(frozen=True)
class YtdOnlyYearOneEvidence:
    """Approved low-confidence input assumption; never an NFL absence fact."""

    player_id: str
    season: int
    source: str
    source_version: str
    observed_at: datetime
    status: str = "low_confidence_ytd_only_no_additional_production_assumed"

    def validate(self) -> None:
        if (not self.source or not self.source_version or self.observed_at.tzinfo is None
                or self.status != "low_confidence_ytd_only_no_additional_production_assumed"):
            raise ValueError("YTD-only assumption lacks approved provenance")


def recorded_ytd_only_year_one_evidence(
    league_state: LeagueState, *, as_of: datetime,
    verified_roles: Mapping[str, object] | None = None,
) -> dict[str, YtdOnlyYearOneEvidence]:
    from fsffl.providers.nfl_status_evidence import (
        recorded_nfl_role_receipts, YTD_ONLY_APPROVED_ROLES,
        YTD_ONLY_POLICY_VERSION, YTD_ONLY_POLICY_APPROVED_AT,
    )
    roles = verified_roles if verified_roles is not None else recorded_nfl_role_receipts(league_state, as_of=as_of)
    if as_of < YTD_ONLY_POLICY_APPROVED_AT:
        return {}
    return {pid: YtdOnlyYearOneEvidence(
        player_id=pid, season=row.season, source=row.source_url,
        source_version=f"{YTD_ONLY_POLICY_VERSION}:{row.fingerprint}",
        observed_at=max(row.captured_at, YTD_ONLY_POLICY_APPROVED_AT),
    ) for pid, row in roles.items() if YTD_ONLY_APPROVED_ROLES.get(pid) == row.status}


def _metrics_for_zero_ros(league_state: LeagueState) -> tuple[ForecastMetric, ...]:
    stats = {rule.stat for rule in FROZEN_I1_STANDARD_SCORING}
    stats.update(rule.stat for rule in league_state.league.rules.scoring)
    metrics = {_STAT_METRICS[stat] for stat in stats if stat in _STAT_METRICS}
    if not metrics:
        raise ValueError("no governed scoring metrics available for status-based ROS")
    return tuple(sorted(metrics, key=lambda item: item.value))


def _status_based_zero_ros(
    *,
    league_state: LeagueState,
    evidence: StatusBasedZeroRosEvidence | YtdOnlyYearOneEvidence,
    as_of: datetime,
) -> tuple[ForecastObservation, ...]:
    evidence.validate()
    if evidence.season != league_state.league.season:
        raise ValueError("status evidence season differs from governed State")
    if evidence.player_id not in {item.player_id for item in league_state.players}:
        raise ValueError("status evidence identity is outside the exact State")
    if evidence.observed_at.astimezone(UTC) > as_of.astimezone(UTC):
        raise ValueError("status evidence postdates the Year-1 evaluation")
    player = next(item for item in league_state.players if item.player_id == evidence.player_id)
    period_start, _ = canonical_week_window(league_state.league.season, 1)
    _, period_end = canonical_week_window(league_state.league.season, 18)
    return tuple(
        ForecastObservation(
            player_id=player.player_id,
            position=player.position,
            horizon=ForecastHorizon.REST_OF_SEASON,
            metric=metric,
            period_start=period_start,
            period_end=period_end,
            distribution=_constant_distribution(0.0),
            source=f"fsffl:status-based-zero-ros:{evidence.source}",
            model_version=f"status-based-zero-ros-v1:{evidence.source_version}",
            as_of=evidence.observed_at.astimezone(UTC),
            provenance=Provenance(
                source=evidence.source,
                retrieved_at=evidence.observed_at.astimezone(UTC),
                effective_at=evidence.observed_at.astimezone(UTC),
                source_version=evidence.source_version,
            ),
        )
        for metric in _metrics_for_zero_ros(league_state)
    )


def _active_backup_player_ids(
    league_state: LeagueState,
    current_catalog: Mapping[str, Any],
    *,
    current_status_state: LeagueState | None = None,
    as_of: datetime | None = None,
    role_evidence_as_of: datetime | None = None,
) -> set[str]:
    """Require current NFL status and role evidence before one-source fallback.

    Exact State roster rows bound the candidates. When available, status comes
    from the captured NFL player catalog, never from a fantasy roster slot.
    """
    status_state = current_status_state or league_state
    state_rows = {item.player_id: item for item in status_state.player_states}
    active = {
        player_id
        for player_id, item in state_rows.items()
        if item.status.value in {"active", "practice_squad", "injured", "pup"}
        and item.nfl_team
        and (
            as_of is None
            or item.as_of.astimezone(UTC) <= as_of.astimezone(UTC)
        )
        and (
            current_status_state is None
            or item.provenance.source == "sleeper:current_player_universe"
        )
    }
    rostered = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    backups: set[str] = set()
    from fsffl.providers.nfl_status_evidence import recorded_nfl_role_receipts
    roles = recorded_nfl_role_receipts(
        league_state, as_of=role_evidence_as_of or as_of or status_state.as_of,
    )
    for player_id in active & rostered:
        if player_id in roles and roles[player_id].status in {"reserve_left_squad", "unsigned"}:
            continue
        catalog_row = current_catalog.get(player_id.rsplit(":", 1)[-1])
        if not isinstance(catalog_row, Mapping):
            continue
        state = state_rows.get(player_id)
        if state is None:
            continue
        try:
            depth_order = int(catalog_row.get("depth_chart_order"))
        except (TypeError, ValueError):
            depth_order = None
        catalog_team = str(catalog_row.get("team") or "").upper()
        status = state.status.value
        supported_role = (
            (status == "practice_squad" and depth_order in {None, 0})
            or (status == "active" and depth_order is not None and depth_order > 1)
            or (
                status in {"injured", "pup"}
                and depth_order is not None
                and depth_order >= 1
            )
        )
        if supported_role and catalog_team == str(state.nfl_team).upper():
            backups.add(player_id)
    return backups


def _weekly_actual_observations(
    *,
    league_state: LeagueState,
    lines_by_week: Mapping[int, tuple[SleeperWeeklyStatLine, ...]],
    completed_through_week: int,
) -> tuple[ForecastObservation, ...]:
    players = {item.player_id: item for item in league_state.players}
    season_start = datetime(league_state.league.season, 9, 1, tzinfo=UTC)
    season_end = datetime(league_state.league.season + 1, 3, 1, tzinfo=UTC)
    totals: dict[tuple[str, ForecastMetric], float] = {}
    latest_capture: dict[str, datetime] = {}
    for week in range(1, completed_through_week + 1):
        for line in lines_by_week[week]:
            if line.season != league_state.league.season or line.week != week:
                raise ValueError("Sleeper weekly stat line does not match its requested window")
            player = players.get(line.player_id)
            if player is None or player.position.value not in {"QB", "RB", "WR", "TE"}:
                continue
            latest_capture[line.player_id] = max(
                latest_capture.get(line.player_id, line.captured_at), line.captured_at
            )
            for stat, value in line.stats.items():
                metric = _STAT_METRICS.get(stat)
                if metric is None:
                    continue
                key = (line.player_id, metric)
                totals[key] = totals.get(key, 0.0) + float(value)

    result: list[ForecastObservation] = []
    for (player_id, metric), value in sorted(
        totals.items(), key=lambda item: (item[0][0], item[0][1].value)
    ):
        player = players[player_id]
        captured = latest_capture[player_id]
        result.append(
            ForecastObservation(
                player_id=player_id,
                position=player.position,
                horizon=ForecastHorizon.SEASON,
                metric=metric,
                period_start=season_start,
                period_end=season_end,
                distribution=_constant_distribution(value),
                source="sleeper:completed-weekly-actuals",
                model_version="sleeper-nfl-stats-v2:season-aggregate",
                as_of=captured,
                provenance=Provenance(
                    source="sleeper:weekly_nfl_stats",
                    retrieved_at=captured,
                    effective_at=datetime(
                        league_state.league.season, 9, 1, tzinfo=UTC
                    ) + timedelta(weeks=completed_through_week),
                    provider_ref=ProviderRef(
                        provider="sleeper",
                        external_id=f"nfl:regular:{league_state.league.season}:weeks:1-{completed_through_week}",
                    ),
                    source_version="sleeper-nfl-stats-v2:season-aggregate",
                ),
            )
        )
    return tuple(result)


def _constant_distribution(value: float):
    from fsffl.forecast.models import ForecastDistribution

    return ForecastDistribution(mean=value, stddev=0.0, p10=value, p50=value, p90=value)


def _year_one_raw_forecasts(
    *,
    league_state: LeagueState,
    completed_actuals: tuple[ForecastObservation, ...],
    ros_forecasts: tuple[ForecastObservation, ...],
) -> tuple[ForecastObservation, ...]:
    """Combine disjoint actual weeks and ROS at the raw-stat coordinate."""
    actual_by_key = {
        (item.player_id, item.metric): item for item in completed_actuals
    }
    # Scoring groups one complete coordinate by as_of. Weekly acquisitions can
    # differ by metric/player, so use this assembly's common evaluation instant
    # while preserving each input's effective/retrieved timestamps below.
    evaluation_as_of = max(
        (instant.astimezone(UTC)
         for item in (*completed_actuals, *ros_forecasts)
         for instant in (item.as_of, item.provenance.retrieved_at, item.provenance.effective_at)),
        default=None,
    )
    output: list[ForecastObservation] = []
    for ros in ros_forecasts:
        if ros.horizon != ForecastHorizon.REST_OF_SEASON:
            raise ValueError("live P0 Year-1 input requires ROS raw-stat observations")
        actual = actual_by_key.get((ros.player_id, ros.metric))
        actual_points = float(actual.distribution.mean) if actual is not None else 0.0
        output.append(
            ros.model_copy(
                update={
                    "horizon": ForecastHorizon.SEASON,
                    "period_start": datetime(league_state.league.season, 9, 1, tzinfo=UTC),
                    "distribution": ros.distribution.model_copy(
                        update={"mean": actual_points + float(ros.distribution.mean)}
                    ),
                    "source": "fsffl:sleeper-actuals-plus-governed-ros",
                    "model_version": "p0-live-y1-raw-v1",
                    "as_of": evaluation_as_of,
                    "provenance": Provenance(
                        source="fsffl:sleeper-actuals-plus-governed-ros",
                        retrieved_at=max(
                            ros.provenance.retrieved_at.astimezone(UTC),
                            actual.provenance.retrieved_at.astimezone(UTC)
                            if actual is not None
                            else ros.provenance.retrieved_at.astimezone(UTC),
                        ),
                        effective_at=max(
                            ros.provenance.effective_at.astimezone(UTC),
                            actual.provenance.effective_at.astimezone(UTC)
                            if actual is not None
                            else ros.provenance.effective_at.astimezone(UTC),
                        ),
                        source_version="p0-live-y1-raw-v1",
                    ),
                }
            )
        )
    return tuple(
        sorted(output, key=lambda item: (item.player_id, item.metric.value))
    )


def _score_season_points(
    raw: tuple[ForecastObservation, ...],
    *,
    league_state: LeagueState,
    standard: bool,
    nonparticipation_evidence: StatusBasedZeroRosEvidence | None = None,
) -> tuple[dict[str, ForecastObservation], dict[str, Any]]:
    rules = league_state.league.rules
    if standard:
        rules = rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING})
    version = "p0-live-y1-scoring-v1"
    if nonparticipation_evidence is not None and nonparticipation_evidence.entire_season_unavailable:
        nonparticipation_evidence.validate()
        if nonparticipation_evidence.season != league_state.league.season:
            raise ValueError("whole-season nonparticipation evidence season mismatch")
        if not raw or any(
            row.player_id != nonparticipation_evidence.player_id
            or row.distribution.mean != 0.0 or row.distribution.stddev != 0.0
            or row.as_of < nonparticipation_evidence.observed_at
            for row in raw
        ):
            raise ValueError("whole-season nonparticipation conflicts with Year-1 raw evidence")
        # Existing residual priors estimate unobserved rare events for players
        # who may participate. An official entire-season absence establishes
        # those events as zero; it must not create 0.208 phantom league points.
        # Keep all ordinary and unsupported scoring coordinates and their gates.
        known_zero = set(classify_scoring_coverage(rules).provisional_residual_rule_stats)
        rules = rules.model_copy(update={"scoring":tuple(
            rule for rule in rules.scoring if rule.stat not in known_zero)})
        version += ":" + STATUS_BASED_YEAR_ONE_SCORING_VERSION + ":" + nonparticipation_evidence.source_version
    result = derive_league_scoring_result(
        raw,
        rules=rules,
        source=(
            "fsffl:p0-live-standard-year-one"
            if standard
            else "fsffl:p0-live-league-year-one"
        ),
        model_version=version,
    )
    if result.coverage.status == ScoringCoverageStatus.INCOMPLETE:
        raise ValueError(
            "league scoring authority does not support complete player-offense Year 1: "
            f"{list(result.coverage.unsupported_rule_stats)}"
        )
    return (
        {item.player_id: item for item in result.authoritative_forecasts},
        {item.player_id: item for item in result.partial_forecasts},
    )


def _score_ytd_only_year_one(
    *, league_state: LeagueState, evidence: YtdOnlyYearOneEvidence,
    completed_actuals: tuple[ForecastObservation, ...],
    lines_by_week: Mapping[int, tuple[SleeperWeeklyStatLine, ...]],
    completed_through_week: int, as_of: datetime,
) -> tuple[tuple[ForecastObservation, ...], ForecastObservation, ForecastObservation]:
    """Retain earned actuals; assume no extra production, including rare events.

    This is an approved input assumption, not a change to P0 or Career math.
    Residual *forecast* priors cannot represent YTD: score their actually earned
    weekly statistics instead. Unsupported scoring still fails closed.
    """
    zero_ros = _status_based_zero_ros(league_state=league_state, evidence=evidence, as_of=as_of)
    actuals = tuple(row for row in completed_actuals if row.player_id == evidence.player_id)
    if any(row.as_of > as_of or row.provenance.retrieved_at > as_of for row in actuals):
        raise ValueError("YTD actuals postdate evaluation")
    raw = _year_one_raw_forecasts(league_state=league_state, completed_actuals=actuals,
                                 ros_forecasts=zero_ros)
    scored = []
    for standard in (True, False):
        rules = league_state.league.rules
        if standard:
            rules = rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING})
        coverage = classify_scoring_coverage(rules)
        if coverage.status == ScoringCoverageStatus.INCOMPLETE:
            raise ValueError("YTD-only scoring contains unsupported rules")
        residual = set(coverage.provisional_residual_rule_stats)
        earned_residual = 0.0
        for week in range(1, completed_through_week + 1):
            if week not in lines_by_week:
                raise ValueError("YTD-only scoring lacks a completed weekly acquisition")
            for line in lines_by_week[week]:
                if line.season != evidence.season or line.week != week or line.captured_at > as_of:
                    raise ValueError("YTD-only weekly evidence window mismatch")
                if line.player_id == evidence.player_id:
                    earned_residual += sum(float(line.stats.get(rule.stat, 0.0)) * rule.points
                                           for rule in rules.scoring if rule.stat in residual)
        reduced = league_state.model_copy(update={"league": league_state.league.model_copy(
            update={"rules": rules.model_copy(update={"scoring": tuple(
                rule for rule in rules.scoring if rule.stat not in residual)})})})
        index, _ = _score_season_points(raw, league_state=reduced, standard=False)
        item = index.get(evidence.player_id)
        if item is None:
            raise ValueError("YTD-only scoring remains incomplete")
        mean = float(item.distribution.mean) + earned_residual
        if not math.isfinite(mean):
            raise ValueError("YTD-only actual scoring is nonfinite")
        scored.append(item.model_copy(update={
            "distribution": _constant_distribution(mean),
            "model_version": item.model_version + ":" + evidence.source_version,
        }))
    return raw, scored[0], scored[1]


def _score_complete_single_source_year_one(
    *,
    player_id: str,
    source_rows: tuple[ForecastObservation, ...],
    completed_actuals: tuple[ForecastObservation, ...],
    league_state: LeagueState,
    supplemental_rows: tuple[ForecastObservation, ...] = (),
) -> tuple[
    tuple[ForecastObservation, ...],
    ForecastObservation | None,
    ForecastObservation | None,
] | None:
    """Score one provider's complete ROS plus the accepted FUMBLES_LOST coordinate.

    The first-party coordinate remains separately sourced and validated; it does
    not count as a second provider or make an otherwise partial provider estimate
    eligible. It only closes the single missing fum_lost scoring coordinate.
    """
    if not source_rows:
        return None
    provider_id = source_rows[0].source
    if any(
        item.player_id != player_id
        or item.horizon != ForecastHorizon.REST_OF_SEASON
        or item.source != provider_id
        for item in source_rows
    ):
        return None
    supplement_keys = {
        (item.player_id, item.position, item.metric, item.period_start, item.period_end)
        for item in source_rows
    }
    if any(
        item.player_id != player_id
        or item.position != source_rows[0].position
        or item.horizon != ForecastHorizon.REST_OF_SEASON
        or item.metric != ForecastMetric.FUMBLES_LOST
        or item.source != FIRST_PARTY_FUMBLES_LOST_SOURCE
        or item.period_start != source_rows[0].period_start
        or item.period_end != source_rows[0].period_end
        or (item.player_id, item.position, item.metric, item.period_start, item.period_end)
        in supplement_keys
        for item in supplemental_rows
    ):
        return None
    if len(supplemental_rows) > 1:
        return None
    raw = _year_one_raw_forecasts(
        league_state=league_state,
        completed_actuals=completed_actuals,
        ros_forecasts=source_rows + supplemental_rows,
    )
    try:
        standard, _ = _score_season_points(raw, league_state=league_state, standard=True)
        league, _ = _score_season_points(raw, league_state=league_state, standard=False)
    except ValueError:
        return None
    standard_item = standard.get(player_id)
    league_item = league.get(player_id)
    if standard_item is None or league_item is None:
        return None
    return raw, standard_item, league_item


def _standard_score_stats(stats: Mapping[str, float]) -> float:
    return sum(float(stats.get(rule.stat, 0.0)) * float(rule.points) for rule in FROZEN_I1_STANDARD_SCORING)


def _candidate_facts(
    *,
    league_state: LeagueState,
    player_id: str,
    standard_y1: ForecastObservation,
    league_y1: ForecastObservation,
    current_catalog: Mapping[str, Any],
    prior_season: Mapping[str, SleeperSeasonStatLine],
    year_one_actual_inputs: tuple[ForecastObservation, ...],
    year_one_raw_inputs: tuple[ForecastObservation, ...],
    evaluation_as_of: datetime,
    year_one_evidence_mode: str = "two_source",
) -> P0CandidateFacts:
    player = next(item for item in league_state.players if item.player_id == player_id)
    player_state = next(item for item in league_state.player_states if item.player_id == player_id)
    external_id = player_id.rsplit(":", 1)[-1]
    catalog_row = current_catalog.get(external_id)
    if not isinstance(catalog_row, Mapping):
        raise ValueError("current Sleeper player catalog row unavailable")
    try:
        experience = int(catalog_row["years_exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("current Sleeper years_exp field unavailable") from exc
    if player_state.age_years is None:
        raise ValueError("governed State age_years unavailable")
    history = prior_season.get(player_id)
    prior_points = _standard_score_stats(history.stats) if history else None
    facts_payload = {
        "player_id": player_id,
        "age": player_state.age_years,
        "experience": experience,
        "year1_standard": standard_y1.distribution.mean,
        "year1_league": league_y1.distribution.mean,
        "prior1": prior_points,
        "prior1_source": SleeperWeeklyStatsSource.source_version if history else None,
        "prior1_retrieved_at": history.captured_at.isoformat() if history else None,
        "prior1_raw_stats": dict(sorted(history.stats.items())) if history else None,
        "completed_week_actual_inputs": [
            {
                "metric": item.metric.value,
                "mean": float(item.distribution.mean),
                "source": item.source,
                "model_version": item.model_version,
                "as_of": item.as_of.isoformat(),
                "retrieved_at": item.provenance.retrieved_at.isoformat(),
                "effective_at": item.provenance.effective_at.isoformat(),
                "provider_ref": (
                    item.provenance.provider_ref.external_id
                    if item.provenance.provider_ref
                    else None
                ),
            }
            for item in sorted(year_one_actual_inputs, key=lambda row: row.metric.value)
        ],
        "year1_raw_inputs": [
            {
                "metric": item.metric.value,
                "mean": float(item.distribution.mean),
                "stddev": float(item.distribution.stddev),
                "source": item.source,
                "model_version": item.model_version,
                "as_of": item.as_of.isoformat(),
                "provenance_source": item.provenance.source,
                "retrieved_at": item.provenance.retrieved_at.isoformat(),
                "effective_at": item.provenance.effective_at.isoformat(),
                "provider_ref": (
                    item.provenance.provider_ref.external_id
                    if item.provenance.provider_ref
                    else None
                ),
            }
            for item in sorted(year_one_raw_inputs, key=lambda row: row.metric.value)
        ],
        "role_and_age_state_features": "unavailable_in_live_source_contract; accepted model missingness path",
        "year_one_evidence_mode": year_one_evidence_mode,
        "evaluation_as_of": evaluation_as_of.isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(facts_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    gsis_id = catalog_row.get("gsis_id")
    return P0CandidateFacts(
        player_id=player_id,
        current_player_id=player_id,
        player_name=player.full_name,
        position=player.position.value,
        age=float(player_state.age_years),
        experience=experience,
        mapping_status="EXACT_CANONICAL_ID",
        historical_gsis_id=str(gsis_id) if gsis_id else None,
        history_status="MAPPED_2025" if history else "MAPPED_NO_2025_ROW",
        standard_y1_points=float(standard_y1.distribution.mean),
        connected_league_y1_points=float(league_y1.distribution.mean),
        prior1_points=prior_points,
        prior1_coverage=1 if history else 0,
        source_role_band="unknown",
        games=None,
        opportunity_per_game=None,
        prior_age_state_resid_z=None,
        prior2_coverage=0,
        prior2_mean_age_state_z=None,
        prior2_gap_age_state_z=None,
        facts_as_of=evaluation_as_of,
        facts_source_version=(
            "sleeper-nfl-stats-v2:season-aggregate+"
            f"{year_one_evidence_mode}:current-cbs-razzball-ros-v1"
        ),
        facts_digest=digest,
    )


def _single_source_fumbles_gap_player_ids(
    *,
    league_state: LeagueState,
    candidate_ids: set[str] | frozenset[str],
    source_observations: tuple[ForecastObservation, ...],
) -> set[str]:
    """Select roster candidates with one provider complete except FUMBLES_LOST."""
    configured_coefficients: dict[ForecastMetric, float] = {}
    for rule in league_state.league.rules.scoring:
        metric = _STAT_METRICS.get(rule.stat)
        if metric is not None:
            configured_coefficients[metric] = (
                configured_coefficients.get(metric, 0.0) + float(rule.points)
            )
    if configured_coefficients.get(ForecastMetric.FUMBLES_LOST, 0.0) == 0.0:
        return set()
    metric_domains = (
        frozenset({
            ForecastMetric.PASS_YARDS,
            ForecastMetric.PASS_TD,
            ForecastMetric.INTERCEPTIONS,
        }),
        frozenset({ForecastMetric.RUSH_YARDS, ForecastMetric.RUSH_TD}),
        frozenset({
            ForecastMetric.RECEPTIONS,
            ForecastMetric.REC_YARDS,
            ForecastMetric.REC_TD,
        }),
    )
    primary_domain_by_position = {
        Position.QB: metric_domains[0],
        Position.RB: metric_domains[1],
        Position.WR: metric_domains[2],
        Position.TE: metric_domains[2],
    }
    positions = {player.player_id: player.position for player in league_state.players}
    provider_metrics: dict[tuple[str, str], set[ForecastMetric]] = {}
    for item in source_observations:
        if (
            item.horizon == ForecastHorizon.REST_OF_SEASON
            and item.player_id in candidate_ids
        ):
            provider_metrics.setdefault((item.player_id, item.source), set()).add(item.metric)
    eligible: set[str] = set()
    for (player_id, _source), metrics in provider_metrics.items():
        if ForecastMetric.FUMBLES_LOST in metrics:
            continue
        primary_domain = primary_domain_by_position.get(positions.get(player_id))
        required_primary_metrics = {
            metric
            for metric in primary_domain or ()
            if configured_coefficients.get(metric, 0.0) != 0.0
        }
        if not required_primary_metrics or not required_primary_metrics.issubset(metrics):
            continue
        complete_other_domains = all(
            not metrics.intersection(domain)
            or {
                metric
                for metric in domain
                if configured_coefficients.get(metric, 0.0) != 0.0
            }.issubset(metrics)
            for domain in metric_domains
        )
        if complete_other_domains and any(
            metric != ForecastMetric.FUMBLES_LOST for metric in metrics
        ):
            eligible.add(player_id)
    return eligible


def _all_ros_source_observations(
    ros_runtime: Any,
    fallback_ros_observations: tuple[ForecastObservation, ...],
) -> tuple[ForecastObservation, ...]:
    """Include retained roster-only rows in same-source supplement eligibility."""
    return tuple(ros_runtime.source_observations) + tuple(fallback_ros_observations)


def _ensemble_ros_with_fumbles(ensemble, supplement):
    """The one-stat supplement cannot create a standalone Year-1 subject."""
    player_ids = {item.player_id for item in ensemble}
    return tuple(ensemble) + tuple(item for item in supplement if item.player_id in player_ids)


def _catalog_evidence_cutoff(
    cutoff: datetime, catalog_captured_at: datetime, *, explicit_cutoff: bool
) -> datetime:
    """Validate replay chronology and include live catalog evidence in the cutoff."""
    return _source_evidence_cutoff(
        cutoff,
        (("live Sleeper catalog snapshot", catalog_captured_at),),
        explicit_cutoff=explicit_cutoff,
    )


def _source_evidence_cutoff(
    cutoff: datetime,
    source_captures: tuple[tuple[str, datetime], ...],
    *,
    explicit_cutoff: bool,
) -> datetime:
    """Reject post-cutoff inputs in replays; otherwise retain latest provenance."""
    latest = cutoff
    for source, captured_at in source_captures:
        if captured_at.tzinfo is None:
            raise ValueError(f"{source} capture time must be timezone-aware")
        captured = captured_at.astimezone(UTC)
        if explicit_cutoff and captured > cutoff:
            raise ValueError(f"{source} postdates the requested P0 evidence cutoff")
        latest = max(latest, captured)
    return latest


def build_live_p0_rostered_candidate_forecasts(
    league_state: LeagueState,
    *,
    stats_source: SleeperWeeklyStatsSource | None = None,
    sleeper_source: SleeperLiveSource | None = None,
    evaluation_as_of: datetime | None = None,
    projection_history_as_of: datetime | None = None,
    authority: P0SourceStateAuthority | None = None,
    projection_history_reader: ProjectionHistoryReader | None = None,
    status_based_zero_ros_evidence: Mapping[str, StatusBasedZeroRosEvidence] | None = None,
    fallback_ros_observations: tuple[ForecastObservation, ...] = (),
    reference_standard_year_one: tuple[ForecastObservation, ...] = (),
    reference_league_year_one: tuple[ForecastObservation, ...] = (),
    retain_ros_runtime_details: bool = True,
) -> P0LiveCandidateResult:
    """Acquire current inputs once and score rostered non-reference subjects.

    The caller supplies the accepted published State. This function never
    publishes/rebuilds State and never fits or modifies P0. Source failures are
    represented per player where possible; provider ensemble and missingness
    failures remain explicit.
    """
    source_reference_standard = reference_standard_year_one
    source_reference_league = reference_league_year_one
    stats = stats_source or SleeperWeeklyStatsSource()
    sleeper = sleeper_source or SleeperLiveSource(max_workers=4)
    nfl_state = stats.fetch_nfl_state()
    if nfl_state.season != league_state.league.season:
        raise ValueError("live Sleeper NFL season differs from governed State")
    completed = nfl_state.completed_through_week
    if league_state.completed_through_week is not None and completed != league_state.completed_through_week:
        raise ValueError("governed State completed-week boundary is stale")
    cutoff = evaluation_as_of or datetime.now(UTC)
    if cutoff.tzinfo is None:
        raise ValueError("P0 live candidate evaluation time must be timezone-aware")
    cutoff = cutoff.astimezone(UTC)
    ros_revision_cutoff = projection_history_as_of or cutoff
    if ros_revision_cutoff.tzinfo is None:
        raise ValueError("P0 ROS revision-selection time must be timezone-aware")
    ros_revision_cutoff = ros_revision_cutoff.astimezone(UTC)
    if cutoff < nfl_state.captured_at.astimezone(UTC):
        raise ValueError("P0 live evaluation time predates Sleeper NFL state acquisition")

    latest_snapshot = sleeper.fetch_latest(
        league_external_id=league_state.league.league_id.rsplit(":", 1)[-1]
    )
    # The live catalog supplies identity, experience, and depth-chart evidence.
    # Include its capture time in the run cutoff before selecting persisted ROS
    # revisions or stamping any derived Year-1 rows.
    cutoff = _catalog_evidence_cutoff(
        cutoff, latest_snapshot.captured_at, explicit_cutoff=evaluation_as_of is not None
    )
    current_state = SleeperSnapshotNormalizer().normalize_snapshot(
        latest_snapshot,
        as_of=latest_snapshot.captured_at,
    )
    if current_state.league.league_id != league_state.league.league_id:
        raise ValueError("live Sleeper league identity differs from governed State")
    if current_state.league.rules != league_state.league.rules:
        raise ValueError("live Sleeper scoring/roster rules differ from governed State")
    if current_state.completed_through_week != league_state.completed_through_week:
        raise ValueError("live completed-week boundary differs from governed State")
    current_by_id = {item.player_id: item for item in current_state.players}
    governed_by_id = {item.player_id: item for item in league_state.players}
    for team_state in league_state.team_states:
        for entry in team_state.roster:
            old = governed_by_id.get(entry.player_id)
            fresh = current_by_id.get(entry.player_id)
            if old is None or fresh is None or old.position != fresh.position:
                raise ValueError(
                    f"live canonical identity/position changed for rostered {entry.player_id}"
                )
    catalog = latest_snapshot.payload.get("players")
    if not isinstance(catalog, Mapping):
        raise ValueError("Sleeper current player universe is not a mapping")
    # Preserve the full source identity, but retain only roster facts while
    # acquiring stats/projections. The raw NFL catalog is much larger than the
    # bounded roster and otherwise overlaps every later acquisition workspace.
    catalog_fingerprint = _input_digest(catalog)
    # Corroborate previous verified roles with a fresh independently acquired
    # player catalog. No time extension is possible without new source evidence.
    from fsffl.providers.nfl_status_evidence import corroborated_current_role_receipts
    corroborated_roles = corroborated_current_role_receipts(
        league_state, as_of=cutoff, captured_at=latest_snapshot.captured_at,
        catalog=catalog,
    )
    from fsffl.providers.nfl_status_evidence import acquire_official_reserve_role_receipts
    # Only the real producer-owned acquisition fetches remote NFL roster
    # evidence. Fixture callers with injected transports stay deterministic.
    # Historical/pinned evaluations never fetch current future evidence.
    official_roles = (
        acquire_official_reserve_role_receipts(
            league_state, evaluation_cutoff=cutoff, allow_current_capture=True,
        ) if stats_source is None and sleeper_source is None
        and evaluation_as_of is None else {}
    )
    if official_roles and evaluation_as_of is None:
        cutoff = max(cutoff, *(receipt.captured_at for receipt in official_roles.values()))
    roster_external_ids = {
        entry.player_id.rsplit(":", 1)[-1]
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    catalog = {key: value for key, value in catalog.items() if key in roster_external_ids}
    del latest_snapshot
    from .resource_coordinator import release_unused_process_memory
    release_unused_process_memory(label="career-p0-unrostered-catalog-released")
    weekly: dict[int, tuple[SleeperWeeklyStatLine, ...]] = {
        week: stats.fetch_week(season=league_state.league.season, week=week)
        for week in range(1, completed + 1)
    }
    prior_lines = stats.fetch_season(season=league_state.league.season - 1)
    prior = {item.player_id: item for item in prior_lines}

    next_week = completed + 1
    from fsffl.forecast.in_season_orchestration import canonical_week_window

    period_start, _ = canonical_week_window(league_state.league.season, next_week)
    _, period_end = canonical_week_window(league_state.league.season, 18)
    saved_ros_revisions = None
    if projection_history_reader is not None:
        from fsffl.forecast.projection_history import career_ros_projection_selector

        saved_ros_revisions = projection_history_reader.latest_revisions(
            career_ros_projection_selector(
                season=league_state.league.season,
                completed_through_week=completed,
                as_of=ros_revision_cutoff,
            )
        )
    ros_runtime = build_in_season_forecasts(
        league_state,
        horizon=ForecastHorizon.REST_OF_SEASON,
        period_start=period_start,
        period_end=period_end,
        clock=lambda: cutoff,
        source_revisions=saved_ros_revisions,
        supplement_missing_sources=projection_history_reader is not None,
        allow_undercovered_sources=True,
    )
    source_captures = (
        ("REST-of-season projections", ros_runtime.evaluation_as_of),
        *(
            (f"Sleeper weekly stats week {week}", line.captured_at)
            for week, rows in weekly.items()
            for line in rows
        ),
        *( ("Sleeper prior-season stats", line.captured_at) for line in prior_lines ),
    )
    cutoff = _source_evidence_cutoff(
        cutoff,
        source_captures,
        explicit_cutoff=evaluation_as_of is not None,
    )
    completed_raw = _weekly_actual_observations(
        league_state=league_state,
        lines_by_week=weekly,
        completed_through_week=completed,
    )
    from fsffl.forecast.in_season_orchestration import (
        build_current_ros_fumbles_lost_supplement_observations,
    )

    # Rebind the acquired weeks to the exact saved-State boundary. Sleeper's
    # live calendar may have advanced, but this run contains only Week 1 through
    # the State's completed week and the accepted model requires that exact cut.
    cached_stats = _CachedSleeperWeeklyStatsSource(
        nfl_state=SleeperNflState(
            season=nfl_state.season,
            week=completed + 1,
            season_type=nfl_state.season_type,
            captured_at=nfl_state.captured_at,
            display_week=completed + 1,
            leg=completed + 1,
        ),
        lines_by_week=weekly,
    )
    ros_fumbles_lost: tuple[ForecastObservation, ...] = ()
    fumbles_supplement_failure: str | None = None
    available_ros_rows = _all_ros_source_observations(ros_runtime, fallback_ros_observations)
    fumbles_eligible_player_ids = _single_source_fumbles_gap_player_ids(
        league_state=league_state,
        candidate_ids=set(exact_state_rostered_p0_subject_ids(league_state)),
        source_observations=available_ros_rows,
    )
    try:
        ros_for_fumbles = ros_runtime.model_copy(update={
            "source_observations": available_ros_rows,
        })
        ros_fumbles_lost = build_current_ros_fumbles_lost_supplement_observations(
            league_state,
            current_runtime=ros_for_fumbles,
            stats_source=cached_stats,  # type: ignore[arg-type]
            completed_through_week=completed,
            as_of=cutoff,
            eligible_player_ids=fumbles_eligible_player_ids,
        )
    except Exception as exc:
        fumbles_supplement_failure = f"{type(exc).__name__}: {exc}"
    # A first-party coordinate is not a standalone provider projection. Join it
    # only onto existing ensemble rows here; complete single-source fallbacks
    # join it separately below after their eligibility check.
    y1_raw = _year_one_raw_forecasts(
        league_state=league_state,
        completed_actuals=completed_raw,
        ros_forecasts=_ensemble_ros_with_fumbles(ros_runtime.raw_ensemble, ros_fumbles_lost),
    )
    y1_standard, y1_standard_partial = _score_season_points(
        y1_raw, league_state=league_state, standard=True
    )
    y1_league, y1_league_partial = _score_season_points(
        y1_raw, league_state=league_state, standard=False
    )

    # The normal two-source ensemble remains authoritative whenever it yields
    # both Year-1 coordinates. Explicit status evidence is a narrowly scoped
    # fallback; complete one-source rows are considered only when the current
    # accepted player catalog confirms an active NFL backup. No missing metric
    # is synthesized, and a fantasy bench slot alone is not role evidence.
    evidence_modes: dict[str, str] = {}
    fallback_status_evidence = (
        status_based_zero_ros_evidence
        if status_based_zero_ros_evidence is not None
        else recorded_status_based_zero_ros_evidence(
            league_state, as_of=min(cutoff, ros_revision_cutoff),
        )
    )
    one_source_rows: dict[tuple[str, str], tuple[ForecastObservation, ...]] = {}
    for item in (*ros_runtime.source_observations, *fallback_ros_observations):
        if item.horizon != ForecastHorizon.REST_OF_SEASON:
            continue
        state_player = next(
            (player for player in league_state.players if player.player_id == item.player_id),
            None,
        )
        if state_player is None or state_player.position != item.position:
            continue
        if item.as_of.astimezone(UTC) > cutoff:
            continue
        one_source_rows.setdefault((item.player_id, item.source), ())
        one_source_rows[(item.player_id, item.source)] += (item,)

    positions = {
        player.player_id: player.position.value
        for player in league_state.players
        if player.position.value in {"QB", "RB", "WR", "TE"}
    }
    current_positions = {
        player.player_id: player.position.value
        for player in current_state.players
        if player.position.value in {"QB", "RB", "WR", "TE"}
    }
    candidates = tuple(
        player_id
        for player_id in exact_state_rostered_p0_subject_ids(league_state)
        if player_id in current_positions
    )
    facts: dict[str, P0CandidateFacts] = {}
    failures: dict[str, str] = {}
    active_backup_ids = _active_backup_player_ids(
        league_state,
        catalog,
        current_status_state=current_state,
        as_of=cutoff,
        role_evidence_as_of=min(cutoff, ros_revision_cutoff),
    )
    from fsffl.providers.nfl_status_evidence import recorded_nfl_role_receipts
    role_cutoff = min(cutoff, ros_revision_cutoff)
    role_receipts = recorded_nfl_role_receipts(league_state, as_of=role_cutoff)
    # A capture cannot be used to alter an older pinned projection revision.
    role_receipts.update({
        pid: row for pid, row in corroborated_roles.items()
        if row.captured_at <= cutoff
    })
    role_receipts.update({
        pid: row for pid, row in official_roles.items()
        if row.captured_at <= cutoff
    })
    ytd_only_receipts = recorded_ytd_only_year_one_evidence(
        league_state, as_of=role_cutoff, verified_roles=role_receipts,
    )
    def admit_ytd_only(player_id):
        evidence = ytd_only_receipts.get(player_id)
        if evidence is None:
            return None
        # This approval covers projectionless cases, not replacing partial or
        # malformed provider evidence with a more convenient assumption.
        if any(row.player_id == player_id for row in available_ros_rows):
            return None
        try:
            return _score_ytd_only_year_one(
                league_state=league_state, evidence=evidence, completed_actuals=completed_raw,
                lines_by_week=weekly, completed_through_week=completed,
                as_of=cutoff,
            )
        except ValueError as exc:
            failures[player_id] = f"approved YTD-only fallback rejected: {exc}"
            return None

    for player_id in candidates:
        if player_id not in positions:
            failures[player_id] = "live roster candidate is absent from governed State identity universe"
            continue
        if positions[player_id] != current_positions[player_id]:
            failures[player_id] = "canonical position differs between governed and current State"
            continue
        standard_item = y1_standard.get(player_id)
        league_item = y1_league.get(player_id)
        evidence_mode = "two_source"
        if standard_item is None or league_item is None:
            status_evidence = fallback_status_evidence.get(player_id)
            if status_evidence is not None:
                try:
                    zero_ros = _status_based_zero_ros(
                        league_state=league_state,
                        evidence=status_evidence,
                        as_of=cutoff,
                    )
                    status_raw = _year_one_raw_forecasts(
                        league_state=league_state,
                        completed_actuals=completed_raw,
                        ros_forecasts=zero_ros,
                    )
                    status_standard, _ = _score_season_points(
                        tuple(item for item in status_raw if item.player_id == player_id),
                        league_state=league_state,
                        standard=True,
                        nonparticipation_evidence=status_evidence,
                    )
                    status_league, _ = _score_season_points(
                        tuple(item for item in status_raw if item.player_id == player_id),
                        league_state=league_state,
                        standard=False,
                        nonparticipation_evidence=status_evidence,
                    )
                    standard_item = status_standard.get(player_id)
                    league_item = status_league.get(player_id)
                    if standard_item is None or league_item is None:
                        raise ValueError("status-based Year-1 scoring remains incomplete")
                    evidence_mode = (
                        f"status_based_zero_ros:{status_evidence.status}:"
                        f"{status_evidence.source_version}"
                    )
                    y1_raw = tuple(
                        item for item in y1_raw if item.player_id != player_id
                    ) + tuple(item for item in status_raw if item.player_id == player_id)
                    y1_standard[player_id] = standard_item
                    y1_league[player_id] = league_item
                    evidence_modes[player_id] = evidence_mode
                except ValueError as exc:
                    failures[player_id] = f"status-based Year-1 fallback rejected: {exc}"
                    continue
            elif player_id in active_backup_ids:
                accepted = False
                for (source_player, source_id), source_rows in sorted(one_source_rows.items()):
                    if source_player != player_id:
                        continue
                    fumbles_rows = tuple(
                        item
                        for item in ros_fumbles_lost
                        if item.player_id == player_id
                    )
                    candidate_year_one = _score_complete_single_source_year_one(
                        player_id=player_id,
                        source_rows=source_rows,
                        completed_actuals=completed_raw,
                        league_state=league_state,
                        supplemental_rows=fumbles_rows,
                    )
                    if candidate_year_one is None:
                        continue
                    source_raw, standard_item, league_item = candidate_year_one
                    if standard_item is None or league_item is None:
                        continue
                    evidence_mode = f"single_source_low_confidence:{source_id}"
                    candidate_status = next(
                        (
                            item.status.value
                            for item in current_state.player_states
                            if item.player_id == player_id
                        ),
                        "unknown",
                    )
                    if candidate_status in {"injured", "pup", "practice_squad"}:
                        evidence_mode += f"+nfl_status:{candidate_status}"
                    if fumbles_rows:
                        evidence_mode += "+first_party_fumbles_lost"
                    y1_raw = tuple(
                        item for item in y1_raw if item.player_id != player_id
                    ) + source_raw
                    y1_standard[player_id] = standard_item
                    y1_league[player_id] = league_item
                    evidence_modes[player_id] = evidence_mode
                    accepted = True
                    break
                if accepted:
                    pass
                else:
                    standard_missing = y1_standard_partial.get(player_id)
                    league_missing = y1_league_partial.get(player_id)
                    failures[player_id] = (
                        "active backup lacks a complete single-source Year-1 projection; "
                        "admissible_provider_row_counts="
                        f"{ {source_id: len(rows) for (pid, source_id), rows in one_source_rows.items() if pid == player_id} }; "
                        f"standard_missing_rule_stats={list(standard_missing.omitted_rule_stats) if standard_missing else []}; "
                        f"league_missing_rule_stats={list(league_missing.omitted_rule_stats) if league_missing else []}"
                    )
            else:
                standard_missing = y1_standard_partial.get(player_id)
                league_missing = y1_league_partial.get(player_id)
                if standard_missing or league_missing:
                    failures[player_id] = (
                        "Year-1 raw evidence failed strict scoring coverage; "
                        f"standard_missing_rule_stats={list(standard_missing.omitted_rule_stats) if standard_missing else []}; "
                        f"league_missing_rule_stats={list(league_missing.omitted_rule_stats) if league_missing else []}"
                    )
                    if fumbles_supplement_failure and "fum_lost" in failures[player_id]:
                        failures[player_id] += (
                            "; accepted first-party FUMBLES_LOST supplement unavailable: "
                            f"{fumbles_supplement_failure}"
                        )
                else:
                    source_metrics = {
                        source_id: sorted(
                            {
                                item.metric.value
                                for item in available_ros_rows
                                if item.player_id == player_id and item.source == source_id
                            }
                        )
                        for source_id in ros_runtime.successful_source_ids
                    }
                    raw_metrics = sorted({
                        item.metric.value
                        for item in y1_raw
                        if item.player_id == player_id
                    })
                    failures[player_id] = (
                        "no complete Year-1 raw scoring row; "
                        f"per-provider canonical ROS metrics={source_metrics}; "
                        f"two-source raw-ensemble metrics={raw_metrics or 'none'}"
                    )
                    if player_id in role_receipts:
                        role = role_receipts[player_id]
                        failures[player_id] += (
                            f"; verified NFL role={role.status}; source={role.source_url}; "
                            f"captured_at={role.captured_at.isoformat()}; "
                            "role does not establish whole-season absence or a return projection"
                        )
            if standard_item is None or league_item is None:
                fallback = admit_ytd_only(player_id)
                if fallback is None:
                    continue
                source_raw, standard_item, league_item = fallback
                evidence_mode = (
                    "low_confidence_ytd_only:no_additional_production_assumed:"
                    + ytd_only_receipts[player_id].source_version
                )
                y1_raw = tuple(item for item in y1_raw if item.player_id != player_id) + source_raw
                y1_standard[player_id] = standard_item
                y1_league[player_id] = league_item
                evidence_modes[player_id] = evidence_mode
                failures.pop(player_id, None)
        if standard_item is None or league_item is None:
            # This is reachable only if a supplied fallback contract was
            # malformed; retain a player-specific failure rather than aborting.
            failures[player_id] = "Year-1 fallback did not produce both scoring coordinates"
            continue
        try:
            facts[player_id] = _candidate_facts(
                league_state=league_state,
                player_id=player_id,
                standard_y1=standard_item,
                league_y1=league_item,
                current_catalog=catalog,
                prior_season=prior,
                year_one_actual_inputs=tuple(
                    item for item in completed_raw if item.player_id == player_id
                ),
                year_one_raw_inputs=tuple(
                    item for item in y1_raw if item.player_id == player_id
                ),
                evaluation_as_of=cutoff,
                year_one_evidence_mode=evidence_mode,
            )
            evidence_modes.setdefault(player_id, evidence_mode)
        except ValueError as exc:
            failures[player_id] = str(exc)

    source_state_authority = authority or accepted_p0_source_state_authority()
    candidate_rows: dict[str, P0SourceRow] = {}
    for player_id, fact in facts.items():
        try:
            from fsffl.product.p0_candidate_evidence import build_p0_candidate_source_rows

            candidate_rows.update(
                build_p0_candidate_source_rows(
                    league_state=league_state,
                    candidate_facts={player_id: fact},
                    source_state_authority=source_state_authority,
                    evaluation_as_of=cutoff,
                )
            )
        except ValueError as exc:
            failures[player_id] = str(exc)

    # Facts and source identities are now complete. Do not keep the full live
    # catalog/snapshot and acquired stat packets alongside the future-model
    # workspace. Fingerprint the complete inputs before releasing ownership;
    # the returned contract retains the same evidence and numerical rows.
    source_manifest = live_source_manifest(captured_at=cutoff, fingerprints={
        "canonical_state": league_state.state_id,
        "nfl_state": _input_digest(asdict(nfl_state)),
        "current_catalog": catalog_fingerprint,
        "completed_week_stats": _input_digest({str(week): _rows_digest(rows)
                                               for week, rows in sorted(weekly.items())}),
        "prior_season_stats": _rows_digest(prior_lines),
        "ros": _input_digest({
            "observations": _rows_digest(available_ros_rows),
            "ensemble_ready": getattr(ros_runtime, "ensemble_ready", True),
            "unavailability_reason": getattr(ros_runtime, "ensemble_unavailability_reason", None),
            "successful_sources": ros_runtime.successful_source_ids,
            "failed_sources": getattr(ros_runtime, "failed_sources", ()),
            "minimum_sources": getattr(
                getattr(ros_runtime, "coverage", None),
                "minimum_independent_sources", 2,
            ),
        }),
        "fumbles_supplement": _rows_digest(ros_fumbles_lost),
        "status_receipts": _input_digest({
            **{pid: asdict(row) for pid, row in sorted(fallback_status_evidence.items())},
            **{f"nfl_role:{pid}": asdict(row) for pid, row in sorted(role_receipts.items())},
            **{f"ytd_only:{pid}": asdict(row) for pid, row in sorted(ytd_only_receipts.items())},
        }),
        "reference_scoring": _rows_digest((*source_reference_standard, *source_reference_league)),
        "candidate_facts": _input_digest({pid: fact.facts_digest for pid, fact in sorted(facts.items())}),
    })
    ros_runtime_result = ros_runtime
    if not retain_ros_runtime_details:
        # The hosted Career caller needs only readiness and source-coverage
        # metadata after acquisition. Do not carry the full projection/ensemble
        # row payload alongside the subsequent candidate future-model workspace.
        ros_runtime_result = P0RosRuntimeSummary(
            ensemble_ready=ros_runtime.ensemble_ready,
            ensemble_unavailability_reason=ros_runtime.ensemble_unavailability_reason,
            successful_source_ids=tuple(ros_runtime.successful_source_ids),
            failed_sources=tuple(ros_runtime.failed_sources),
            coverage=ros_runtime.coverage,
        )
        del ros_runtime, ros_for_fumbles, available_ros_rows, one_source_rows
    del catalog, current_state, current_by_id, governed_by_id
    del weekly, cached_stats, prior, prior_lines, source_captures, completed_raw
    release_unused_process_memory(label="career-p0-acquisition-inputs-released")

    if candidate_rows:
        from .i1_player_scoring import career_player_scoring_multipliers
        from .p0_forecast_runtime import governed_p0_player_ids
        reference_ids = set(governed_p0_player_ids(league_state))
        # Incomplete or late reference evidence disables only the optional
        # conversion; it must not discard otherwise supported candidates.
        if any({row.player_id for row in rows} != reference_ids for rows in (
            reference_standard_year_one, reference_league_year_one,
        )) or any(row.as_of > cutoff for row in (
            *reference_standard_year_one, *reference_league_year_one,
        )):
            reference_standard_year_one = reference_league_year_one = ()
        future_ready = dict(candidate_rows)
        for player_id in candidate_rows:
            try:
                career_player_scoring_multipliers(
                    standard_year_one=(y1_standard[player_id],),
                    league_year_one=(y1_league[player_id],),
                    reference_standard_year_one=reference_standard_year_one,
                    reference_league_year_one=reference_league_year_one,
                )
            except ValueError as exc:
                failures[player_id] = f"P0 future authority failure: {exc}"
                future_ready.pop(player_id)
        try:
            # Keep the accepted 335 reference inputs/outputs byte-for-byte
            # separate. This live dynamic batch passes only out-of-cohort rows;
            # it must never re-feed current Y1 evidence into the frozen benchmark
            # parity gate or alter a reference output.
            dynamic_ids = set(future_ready)
            future = build_p0_future_forecast_contract(
                league_state=league_state,
                raw_forecasts=tuple(
                    item for item in y1_raw if item.player_id in dynamic_ids
                ),
                league_year_one=tuple(
                    item for player_id, item in y1_league.items()
                    if player_id in dynamic_ids
                ),
                candidate_source_rows=future_ready,
                reference_standard_year_one=reference_standard_year_one,
                reference_league_year_one=reference_league_year_one,
                evaluation_as_of=cutoff,
            ) if future_ready else None
        except ValueError as exc:
            for player_id in candidate_rows:
                failures.setdefault(player_id, f"P0 future authority failure: {exc}")
            future = None
    else:
        future = None
    scored_ids = {item.player_id for item in future.contract.forecasts} if future else set()
    for player_id in candidate_rows:
        if player_id not in scored_ids:
            failures.setdefault(player_id, "P0 future contract omitted candidate")
    return P0LiveCandidateResult(
        evaluation_as_of=cutoff,
        completed_through_week=completed,
        candidate_ids=candidates,
        candidate_source_rows=candidate_rows,
        year_one_standard=y1_standard,
        year_one_league=y1_league,
        future=future,
        failures=failures,
        ros_runtime=ros_runtime_result,
        year_one_evidence_modes=evidence_modes,
        ros_fumbles_lost=ros_fumbles_lost,
        fumbles_eligible_player_ids=tuple(sorted(fumbles_eligible_player_ids)),
        fumbles_supplement_failure=fumbles_supplement_failure,
        source_manifest=source_manifest,
    )

