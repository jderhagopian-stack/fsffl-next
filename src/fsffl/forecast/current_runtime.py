from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from fsffl.providers.cbs_live import CBSLiveProjectionSource
from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource
from fsffl.providers.razzball_live import RazzballLiveProjectionSource
from fsffl.state.models import FrozenModel, LeagueState

from .current_normalization import current_snapshot_from_razzball, normalize_current_projection_snapshot
from .league_scoring import derive_league_fantasy_point_forecasts
from .live_ensemble import LiveEnsembleCoverage, LiveForecastSourceBatch, build_authoritative_live_ensemble
from .models import ForecastObservation


CurrentSnapshotFetcher = Callable[[int], CurrentProjectionSnapshot]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class NamedCurrentProjectionFetcher:
    source_id: str
    fetch: CurrentSnapshotFetcher


class LiveForecastRuntimeResult(FrozenModel):
    raw_ensemble: tuple[ForecastObservation, ...]
    fantasy_point_forecasts: tuple[ForecastObservation, ...]
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    evaluation_as_of: datetime
    model_version: str = "next2-current-runtime-v1"


def default_current_projection_fetchers() -> tuple[NamedCurrentProjectionFetcher, ...]:
    razzball = RazzballLiveProjectionSource()
    fftoday = FFTodayLiveProjectionSource()
    cbs = CBSLiveProjectionSource()
    return (
        NamedCurrentProjectionFetcher(
            source_id="razzball",
            fetch=lambda season: current_snapshot_from_razzball(razzball.fetch_latest()),
        ),
        NamedCurrentProjectionFetcher(
            source_id="fftoday",
            fetch=lambda season: fftoday.fetch_latest(season=season),
        ),
        NamedCurrentProjectionFetcher(
            source_id="cbs",
            fetch=lambda season: cbs.fetch_latest(season=season),
        ),
    )


def build_current_live_forecasts(
    league_state: LeagueState,
    *,
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    clock: Clock | None = None,
    minimum_independent_sources: int = 2,
) -> LiveForecastRuntimeResult:
    """Build current authoritative FSFFL forecasts from independent live evidence.

    Acquisition happens before the shared FSFFL evaluation cutoff is established.
    This matters for sources such as CBS whose retrieval time is the earliest
    demonstrable evidence timestamp. Provider failures are isolated when enough
    independent evidence remains. Only the normalized NEXT-2 ensemble and its
    league-scored derivative leave this service as authoritative forecasts.
    """

    active_fetchers = fetchers or default_current_projection_fetchers()
    if len({item.source_id for item in active_fetchers}) != len(active_fetchers):
        raise ValueError("current projection fetcher ids must be unique")

    snapshots: list[tuple[str, CurrentProjectionSnapshot]] = []
    failed: list[str] = []
    for fetcher in active_fetchers:
        try:
            snapshot = fetcher.fetch(league_state.league.season)
            if snapshot.provider != fetcher.source_id:
                raise ValueError("current projection fetcher returned wrong provider id")
            snapshots.append((fetcher.source_id, snapshot))
        except Exception as exc:
            failed.append(f"{fetcher.source_id}: {type(exc).__name__}: {exc}")

    cutoff = (clock or (lambda: datetime.now(UTC)))()
    if cutoff.tzinfo is None:
        raise ValueError("current forecast runtime clock must be timezone-aware")
    evaluation_as_of = cutoff.astimezone(UTC)
    if snapshots:
        evaluation_as_of = max(
            evaluation_as_of,
            *(snapshot.captured_at.astimezone(UTC) for _, snapshot in snapshots),
            *(snapshot.effective_at.astimezone(UTC) for _, snapshot in snapshots),
        )

    batches: list[LiveForecastSourceBatch] = []
    successful: list[str] = []
    for source_id, snapshot in snapshots:
        try:
            observations = normalize_current_projection_snapshot(
                snapshot,
                league_state=league_state,
                season=league_state.league.season,
                evaluation_as_of=evaluation_as_of,
            )
            if not observations:
                raise ValueError("provider produced no canonical player observations")
        except Exception as exc:
            failed.append(f"{source_id}: {type(exc).__name__}: {exc}")
            continue
        batches.append(LiveForecastSourceBatch(source_id=source_id, observations=observations))
        successful.append(source_id)

    raw_ensemble, coverage = build_authoritative_live_ensemble(
        tuple(batches),
        minimum_independent_sources=minimum_independent_sources,
    )
    fantasy_points = derive_league_fantasy_point_forecasts(
        raw_ensemble,
        rules=league_state.league.rules,
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v1",
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=raw_ensemble,
        fantasy_point_forecasts=fantasy_points,
        coverage=coverage,
        successful_source_ids=tuple(sorted(successful)),
        failed_sources=tuple(sorted(failed)),
        evaluation_as_of=evaluation_as_of,
    )
