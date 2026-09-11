from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol

from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.providers.in_season_projection_sources import (
    CBSInSeasonProjectionSource,
    FFTodayWeeklyProjectionSource,
    RazzballRestOfSeasonProjectionSource,
)
from fsffl.state.models import FrozenModel, LeagueState

from .current_normalization import current_snapshot_from_razzball, normalize_projection_snapshot
from .league_scoring import derive_league_fantasy_point_forecasts
from .live_ensemble import LiveEnsembleCoverage, LiveForecastSourceBatch, build_authoritative_live_ensemble
from .models import ForecastHorizon, ForecastObservation
from .projection_history import ProjectionRevision, revision_from_forecast_observations


Clock = Callable[[], datetime]
InSeasonSnapshotFetcher = Callable[[int, int | None], CurrentProjectionSnapshot]


class ProjectionHistoryWriter(Protocol):
    def save_revision(self, revision: ProjectionRevision) -> int: ...


@dataclass(frozen=True)
class NamedInSeasonProjectionFetcher:
    source_id: str
    fetch: InSeasonSnapshotFetcher


class InSeasonForecastRuntimeResult(FrozenModel):
    """Authoritative horizon-specific Forecast means plus retained source evidence.

    ROS and WEEK uncertainty is not yet promoted to Simulation authority. The
    ensemble/scored distributions remain valid Forecast evidence, but callers must
    not treat them as simulation-ready until horizon-specific residual calibration
    has passed governance.
    """

    horizon: ForecastHorizon
    week: int | None = None
    source_observations: tuple[ForecastObservation, ...]
    raw_ensemble: tuple[ForecastObservation, ...]
    fantasy_point_forecasts: tuple[ForecastObservation, ...]
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    persistence_failures: tuple[str, ...] = ()
    evaluation_as_of: datetime
    uncertainty_authority: str = "not_promoted_for_in_season_simulation"
    simulation_ready: bool = False
    model_version: str = "next2-in-season-runtime-v1"


def default_in_season_projection_fetchers(
    *,
    horizon: ForecastHorizon,
) -> tuple[NamedInSeasonProjectionFetcher, ...]:
    if horizon == ForecastHorizon.REST_OF_SEASON:
        razzball = RazzballRestOfSeasonProjectionSource()
        cbs = CBSInSeasonProjectionSource()
        return (
            NamedInSeasonProjectionFetcher(
                source_id="razzball",
                fetch=lambda season, week: current_snapshot_from_razzball(razzball.fetch_latest()),
            ),
            NamedInSeasonProjectionFetcher(
                source_id="cbs",
                fetch=lambda season, week: cbs.fetch_rest_of_season(season=season),
            ),
        )
    if horizon == ForecastHorizon.WEEK:
        fftoday = FFTodayWeeklyProjectionSource()
        cbs = CBSInSeasonProjectionSource()

        def fftoday_week(season: int, week: int | None) -> CurrentProjectionSnapshot:
            if week is None:
                raise ValueError("FFToday weekly fetch requires week")
            return fftoday.fetch_week(season=season, week=week)

        def cbs_week(season: int, week: int | None) -> CurrentProjectionSnapshot:
            if week is None:
                raise ValueError("CBS weekly fetch requires week")
            return cbs.fetch_week(season=season, week=week)

        return (
            NamedInSeasonProjectionFetcher(source_id="fftoday", fetch=fftoday_week),
            NamedInSeasonProjectionFetcher(source_id="cbs", fetch=cbs_week),
        )
    raise ValueError("in-season runtime supports only REST_OF_SEASON or WEEK")


def _fetch_snapshots(
    fetchers: tuple[NamedInSeasonProjectionFetcher, ...],
    *,
    season: int,
    week: int | None,
) -> tuple[list[tuple[str, CurrentProjectionSnapshot]], list[str]]:
    if not fetchers:
        return [], []
    snapshots: list[tuple[str, CurrentProjectionSnapshot]] = []
    failed: list[str] = []
    with ThreadPoolExecutor(
        max_workers=len(fetchers),
        thread_name_prefix="fsffl-in-season-provider",
    ) as executor:
        future_by_source = {
            executor.submit(fetcher.fetch, season, week): fetcher.source_id
            for fetcher in fetchers
        }
        for future in as_completed(future_by_source):
            source_id = future_by_source[future]
            try:
                snapshot = future.result()
                if snapshot.provider != source_id:
                    raise ValueError("in-season projection fetcher returned wrong provider id")
                snapshots.append((source_id, snapshot))
            except Exception as exc:
                failed.append(f"{source_id}: {type(exc).__name__}: {exc}")
    snapshots.sort(key=lambda item: item[0])
    failed.sort()
    return snapshots, failed


def build_in_season_forecasts(
    league_state: LeagueState,
    *,
    horizon: ForecastHorizon,
    period_start: datetime,
    period_end: datetime,
    week: int | None = None,
    fetchers: tuple[NamedInSeasonProjectionFetcher, ...] | None = None,
    clock: Clock | None = None,
    history_writer: ProjectionHistoryWriter | None = None,
    minimum_independent_sources: int = 2,
) -> InSeasonForecastRuntimeResult:
    """Build governed ROS or week forecasts from independent provider evidence.

    The canonical period is supplied by the caller and must already represent the
    intended remaining schedule or target week. This runtime never subtracts
    completed games from an ambiguous source and never combines WEEK evidence with
    ROS evidence. Persistence is best-effort evidence retention and cannot change
    which observations become Forecast truth.
    """

    if horizon not in {ForecastHorizon.REST_OF_SEASON, ForecastHorizon.WEEK}:
        raise ValueError("in-season runtime supports only REST_OF_SEASON or WEEK")
    if horizon == ForecastHorizon.WEEK and week is None:
        raise ValueError("WEEK in-season forecast requires week")
    if horizon != ForecastHorizon.WEEK and week is not None:
        raise ValueError("week may be supplied only for WEEK in-season forecast")
    if period_start.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("in-season forecast period must be timezone-aware")
    if period_end <= period_start:
        raise ValueError("in-season forecast period_end must be after period_start")

    active_fetchers = fetchers or default_in_season_projection_fetchers(horizon=horizon)
    if len({item.source_id for item in active_fetchers}) != len(active_fetchers):
        raise ValueError("in-season projection fetcher ids must be unique")

    snapshots, failed = _fetch_snapshots(
        active_fetchers,
        season=league_state.league.season,
        week=week,
    )
    cutoff = (clock or (lambda: datetime.now(UTC)))()
    if cutoff.tzinfo is None:
        raise ValueError("in-season forecast runtime clock must be timezone-aware")
    evaluation_as_of = cutoff.astimezone(UTC)
    if snapshots:
        evaluation_as_of = max(
            evaluation_as_of,
            *(snapshot.captured_at.astimezone(UTC) for _, snapshot in snapshots),
            *(snapshot.effective_at.astimezone(UTC) for _, snapshot in snapshots),
        )

    batches: list[LiveForecastSourceBatch] = []
    source_observations: list[ForecastObservation] = []
    successful: list[str] = []
    persistence_failures: list[str] = []
    for source_id, snapshot in snapshots:
        try:
            observations = normalize_projection_snapshot(
                snapshot,
                league_state=league_state,
                horizon=horizon,
                period_start=period_start,
                period_end=period_end,
                evaluation_as_of=evaluation_as_of,
            )
            if not observations:
                raise ValueError("provider produced no canonical player observations")
        except Exception as exc:
            failed.append(f"{source_id}: {type(exc).__name__}: {exc}")
            continue

        if history_writer is not None:
            try:
                history_writer.save_revision(
                    revision_from_forecast_observations(
                        observations,
                        provider=source_id,
                        season=league_state.league.season,
                        horizon=horizon,
                        week=week,
                        usage_class=snapshot.usage_class,
                    )
                )
            except Exception as exc:
                persistence_failures.append(
                    f"{source_id}: {type(exc).__name__}: {exc}"
                )

        source_observations.extend(observations)
        batches.append(LiveForecastSourceBatch(source_id=source_id, observations=observations))
        successful.append(source_id)

    if len(batches) < minimum_independent_sources:
        detail = "; ".join(sorted(failed)) if failed else "no provider-specific failure details"
        raise ValueError(
            "authoritative in-season ensemble requires at least "
            f"{minimum_independent_sources} independent sources; found {len(batches)}; "
            f"successful={sorted(successful)}; failures={detail}"
        )

    raw_ensemble, coverage = build_authoritative_live_ensemble(
        tuple(batches),
        minimum_independent_sources=minimum_independent_sources,
        model_version="next2-in-season-equal-weight-v1",
    )
    fantasy_points = derive_league_fantasy_point_forecasts(
        raw_ensemble,
        rules=league_state.league.rules,
        source="fsffl:in-season-league-scored",
        model_version="next2-in-season-runtime-v1",
    )
    return InSeasonForecastRuntimeResult(
        horizon=horizon,
        week=week,
        source_observations=tuple(
            sorted(
                source_observations,
                key=lambda item: (item.source, item.player_id, item.metric.value),
            )
        ),
        raw_ensemble=raw_ensemble,
        fantasy_point_forecasts=fantasy_points,
        coverage=coverage,
        successful_source_ids=tuple(sorted(successful)),
        failed_sources=tuple(sorted(failed)),
        persistence_failures=tuple(sorted(persistence_failures)),
        evaluation_as_of=evaluation_as_of,
    )
