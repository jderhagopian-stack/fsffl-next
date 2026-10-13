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
from dataclasses import dataclass
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
from fsffl.state.models import LeagueState, Provenance, ProviderRef
from fsffl.forecast.projection_history import ProjectionSelector
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


@dataclass(frozen=True)
class StatusBasedZeroRosEvidence:
    """Explicit recorded evidence that a player has no expected 2026 participation."""

    player_id: str
    status: str
    source: str
    source_version: str
    observed_at: datetime
    no_expected_2026_participation: bool

    def validate(self) -> None:
        if self.status not in {"out_for_season", "unsigned_no_expected_2026_participation"}:
            raise ValueError("status evidence does not establish season-long nonparticipation")
        if not self.source.strip() or not self.source_version.strip():
            raise ValueError("status evidence lacks source provenance")
        if self.observed_at.tzinfo is None:
            raise ValueError("status evidence timestamp must be timezone-aware")
        if not self.no_expected_2026_participation:
            raise ValueError("status evidence does not confirm no expected 2026 participation")


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
    evidence: StatusBasedZeroRosEvidence,
    as_of: datetime,
) -> tuple[ForecastObservation, ...]:
    evidence.validate()
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
) -> set[str]:
    """Require recorded NFL depth-chart evidence before single-source fallback."""
    active = {
        item.player_id
        for item in league_state.player_states
        if item.status.value == "active" and item.nfl_team
    }
    rostered = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    backups: set[str] = set()
    for player_id in active & rostered:
        catalog_row = current_catalog.get(player_id.rsplit(":", 1)[-1])
        if not isinstance(catalog_row, Mapping):
            continue
        state = next(item for item in league_state.player_states if item.player_id == player_id)
        try:
            depth_order = int(catalog_row.get("depth_chart_order"))
        except (TypeError, ValueError):
            continue
        catalog_team = str(catalog_row.get("team") or "").upper()
        if depth_order > 1 and catalog_team == str(state.nfl_team).upper():
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
    output: list[ForecastObservation] = []
    for ros in ros_forecasts:
        if ros.horizon != ForecastHorizon.REST_OF_SEASON:
            raise ValueError("live P0 Year-1 input requires ROS raw-stat observations")
        actual = actual_by_key.get((ros.player_id, ros.metric))
        actual_points = float(actual.distribution.mean) if actual is not None else 0.0
        latest_actual_at = (
            max(
                actual.as_of.astimezone(UTC),
                actual.provenance.retrieved_at.astimezone(UTC),
                actual.provenance.effective_at.astimezone(UTC),
            )
            if actual is not None
            else ros.as_of.astimezone(UTC)
        )
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
                    "as_of": max(ros.as_of.astimezone(UTC), latest_actual_at),
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
) -> tuple[dict[str, ForecastObservation], dict[str, Any]]:
    rules = league_state.league.rules
    if standard:
        rules = rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING})
    result = derive_league_scoring_result(
        raw,
        rules=rules,
        source=(
            "fsffl:p0-live-standard-year-one"
            if standard
            else "fsffl:p0-live-league-year-one"
        ),
        model_version="p0-live-y1-scoring-v1",
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


def build_live_p0_rostered_candidate_forecasts(
    league_state: LeagueState,
    *,
    stats_source: SleeperWeeklyStatsSource | None = None,
    sleeper_source: SleeperLiveSource | None = None,
    evaluation_as_of: datetime | None = None,
    authority: P0SourceStateAuthority | None = None,
    projection_history_reader: ProjectionHistoryReader | None = None,
    status_based_zero_ros_evidence: Mapping[str, StatusBasedZeroRosEvidence] | None = None,
    fallback_ros_observations: tuple[ForecastObservation, ...] = (),
) -> P0LiveCandidateResult:
    """Acquire current inputs once and score rostered non-reference subjects.

    The caller supplies the accepted published State. This function never
    publishes/rebuilds State and never fits or modifies P0. Source failures are
    represented per player where possible; provider ensemble and missingness
    failures remain explicit.
    """
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
    if cutoff < nfl_state.captured_at.astimezone(UTC):
        raise ValueError("P0 live evaluation time predates Sleeper NFL state acquisition")

    latest_snapshot = sleeper.fetch_latest(
        league_external_id=league_state.league.league_id.rsplit(":", 1)[-1]
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
        saved_ros_revisions = projection_history_reader.latest_revisions(
            ProjectionSelector(
                season=league_state.league.season,
                horizon=ForecastHorizon.REST_OF_SEASON,
                as_of=cutoff,
            )
        )
    ros_runtime = build_in_season_forecasts(
        league_state,
        horizon=ForecastHorizon.REST_OF_SEASON,
        period_start=period_start,
        period_end=period_end,
        clock=lambda: cutoff,
        source_revisions=saved_ros_revisions,
    )
    cutoff = max(
        cutoff,
        ros_runtime.evaluation_as_of.astimezone(UTC),
        *(line.captured_at.astimezone(UTC) for rows in weekly.values() for line in rows),
        *(line.captured_at.astimezone(UTC) for line in prior_lines),
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
    available_ros_rows = tuple(ros_runtime.source_observations) + tuple(fallback_ros_observations)
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
    y1_raw = _year_one_raw_forecasts(
        league_state=league_state,
        completed_actuals=completed_raw,
        ros_forecasts=ros_runtime.raw_ensemble + ros_fumbles_lost,
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
    fallback_status_evidence = status_based_zero_ros_evidence or {}
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
    active_backup_ids = _active_backup_player_ids(league_state, catalog)
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
                    )
                    status_league, _ = _score_season_points(
                        tuple(item for item in status_raw if item.player_id == player_id),
                        league_state=league_state,
                        standard=False,
                    )
                    standard_item = status_standard.get(player_id)
                    league_item = status_league.get(player_id)
                    if standard_item is None or league_item is None:
                        raise ValueError("status-based Year-1 scoring remains incomplete")
                    evidence_mode = f"status_based_zero_ros:{status_evidence.status}"
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
                        f"standard_missing_rule_stats={list(standard_missing.omitted_rule_stats) if standard_missing else []}; "
                        f"league_missing_rule_stats={list(league_missing.omitted_rule_stats) if league_missing else []}"
                    )
                    continue
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
                    continue
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
                continue
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

    if candidate_rows:
        try:
            # Keep the accepted 335 reference inputs/outputs byte-for-byte
            # separate. This live dynamic batch passes only out-of-cohort rows;
            # it must never re-feed current Y1 evidence into the frozen benchmark
            # parity gate or alter a reference output.
            dynamic_ids = set(candidate_rows)
            future = build_p0_future_forecast_contract(
                league_state=league_state,
                raw_forecasts=tuple(
                    item for item in y1_raw if item.player_id in dynamic_ids
                ),
                league_year_one=tuple(
                    item for player_id, item in y1_league.items()
                    if player_id in dynamic_ids
                ),
                candidate_source_rows=candidate_rows,
                evaluation_as_of=cutoff,
            )
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
        ros_runtime=ros_runtime,
        year_one_evidence_modes=evidence_modes,
        ros_fumbles_lost=ros_fumbles_lost,
        fumbles_eligible_player_ids=tuple(sorted(fumbles_eligible_player_ids)),
        fumbles_supplement_failure=fumbles_supplement_failure,
    )

