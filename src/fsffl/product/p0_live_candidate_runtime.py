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
from fsffl.forecast.in_season_runtime import build_in_season_forecasts
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
            "sleeper-nfl-stats-v2:season-aggregate+current-cbs-razzball-ros-v1"
        ),
        facts_digest=digest,
    )


def build_live_p0_rostered_candidate_forecasts(
    league_state: LeagueState,
    *,
    stats_source: SleeperWeeklyStatsSource | None = None,
    sleeper_source: SleeperLiveSource | None = None,
    evaluation_as_of: datetime | None = None,
    authority: P0SourceStateAuthority | None = None,
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
    ros_runtime = build_in_season_forecasts(
        league_state,
        horizon=ForecastHorizon.REST_OF_SEASON,
        period_start=period_start,
        period_end=period_end,
        clock=lambda: cutoff,
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

    cached_stats = _CachedSleeperWeeklyStatsSource(
        nfl_state=nfl_state,
        lines_by_week=weekly,
    )
    ros_fumbles_lost: tuple[ForecastObservation, ...] = ()
    fumbles_supplement_failure: str | None = None
    try:
        ros_fumbles_lost = build_current_ros_fumbles_lost_supplement_observations(
            league_state,
            current_runtime=ros_runtime,
            stats_source=cached_stats,  # type: ignore[arg-type]
            completed_through_week=completed,
            as_of=cutoff,
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

    live_rostered_ids = {
        entry.player_id
        for team_state in current_state.team_states
        for entry in team_state.roster
    }
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
    candidates = out_of_cohort_p0_subject_ids(
        live_rostered_ids & set(current_positions)
    )
    facts: dict[str, P0CandidateFacts] = {}
    failures: dict[str, str] = {}
    for player_id in candidates:
        if player_id not in positions:
            failures[player_id] = "live roster candidate is absent from governed State identity universe"
            continue
        if positions[player_id] != current_positions[player_id]:
            failures[player_id] = "canonical position differs between governed and current State"
            continue
        standard_item = y1_standard.get(player_id)
        league_item = y1_league.get(player_id)
        if standard_item is None or league_item is None:
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
                            for item in ros_runtime.source_observations
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
            )
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
    )

