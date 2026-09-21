from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from fsffl.providers.cbs_live import CBSLiveProjectionSource
from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource
from fsffl.providers.nfl_fantasy_live import NFLFantasyLiveProjectionSource
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource
from fsffl.state.models import FrozenModel, LeagueState

from .current_normalization import current_snapshot_from_razzball, normalize_current_projection_snapshot
from .league_scoring import derive_league_fantasy_point_forecasts
from .live_ensemble import LiveEnsembleCoverage, LiveForecastSourceBatch, build_authoritative_live_ensemble
from .models import ForecastObservation
from .regular_season import derive_fantasy_regular_season_forecasts
from .season_uncertainty import apply_empirical_season_fantasy_point_uncertainty
from .source_health import (
    CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
    current_projection_payload_sha256,
    validate_current_projection_snapshot_health,
)


CurrentSnapshotFetcher = Callable[[int], CurrentProjectionSnapshot]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class NamedCurrentProjectionFetcher:
    source_id: str
    fetch: CurrentSnapshotFetcher


class LiveForecastSourceProvenance(FrozenModel):
    provider: str
    source_version: str
    captured_at: datetime
    effective_at: datetime
    usage_class: str
    provider_payload_sha256: str
    health_contract_version: str
    health_disposition: str = "accepted"


class LiveForecastRuntimeResult(FrozenModel):
    raw_ensemble: tuple[ForecastObservation, ...]
    fantasy_point_forecasts: tuple[ForecastObservation, ...]
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    evaluation_as_of: datetime
    fantasy_regular_season_forecasts: tuple[ForecastObservation, ...] = ()
    source_provenance: tuple[LiveForecastSourceProvenance, ...] = ()
    model_version: str = "next2-current-runtime-v5:source-health-provenance"


def default_current_projection_fetchers() -> tuple[NamedCurrentProjectionFetcher, ...]:
    razzball = RazzballSeasonProjectionSource()
    fftoday = FFTodayLiveProjectionSource()
    cbs = CBSLiveProjectionSource()
    nfl_fantasy = NFLFantasyLiveProjectionSource()
    return (
        NamedCurrentProjectionFetcher(
            source_id="razzball",
            fetch=lambda season: current_snapshot_from_razzball(
                razzball.fetch_latest(season=season)
            ),
        ),
        NamedCurrentProjectionFetcher(
            source_id="fftoday",
            fetch=lambda season: fftoday.fetch_latest(season=season),
        ),
        NamedCurrentProjectionFetcher(
            source_id="cbs",
            fetch=lambda season: cbs.fetch_latest(season=season),
        ),
        NamedCurrentProjectionFetcher(
            source_id="nfl_fantasy",
            fetch=lambda season: nfl_fantasy.fetch_latest(season=season),
        ),
    )


def _fetch_current_snapshots(
    fetchers: tuple[NamedCurrentProjectionFetcher, ...],
    *,
    season: int,
) -> tuple[list[tuple[str, CurrentProjectionSnapshot]], list[str]]:
    """Acquire independent provider snapshots concurrently without changing evidence semantics."""

    if not fetchers:
        return [], []
    snapshots: list[tuple[str, CurrentProjectionSnapshot]] = []
    failed: list[str] = []
    with ThreadPoolExecutor(
        max_workers=len(fetchers),
        thread_name_prefix="fsffl-forecast-provider",
    ) as executor:
        future_by_source = {
            executor.submit(fetcher.fetch, season): fetcher.source_id
            for fetcher in fetchers
        }
        for future in as_completed(future_by_source):
            source_id = future_by_source[future]
            try:
                snapshot = future.result()
                if snapshot.provider != source_id:
                    raise ValueError("current projection fetcher returned wrong provider id")
                validate_current_projection_snapshot_health(snapshot)
                snapshots.append((source_id, snapshot))
            except Exception as exc:
                failed.append(f"{source_id}: {type(exc).__name__}: {exc}")

    snapshots.sort(key=lambda item: item[0])
    failed.sort()
    return snapshots, failed


def build_current_live_forecasts(
    league_state: LeagueState,
    *,
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    clock: Clock | None = None,
    minimum_independent_sources: int = 2,
) -> LiveForecastRuntimeResult:
    """Build current authoritative FSFFL forecasts from independent live evidence.

    Independent network acquisitions run concurrently. Normalization, source gates,
    ensemble construction, scoring and uncertainty remain deterministic and unchanged.
    """

    active_fetchers = fetchers or default_current_projection_fetchers()
    if len({item.source_id for item in active_fetchers}) != len(active_fetchers):
        raise ValueError("current projection fetcher ids must be unique")

    snapshots, failed = _fetch_current_snapshots(
        active_fetchers,
        season=league_state.league.season,
    )

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
    provenance_by_source: dict[str, LiveForecastSourceProvenance] = {}
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
        provenance_by_source[source_id] = LiveForecastSourceProvenance(
            provider=snapshot.provider,
            source_version=snapshot.source_version,
            captured_at=snapshot.captured_at.astimezone(UTC),
            effective_at=snapshot.effective_at.astimezone(UTC),
            usage_class=snapshot.usage_class,
            provider_payload_sha256=current_projection_payload_sha256(snapshot),
            health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
            health_disposition="accepted",
        )

    if len(batches) < minimum_independent_sources:
        detail = "; ".join(sorted(failed)) if failed else "no provider-specific failure details"
        raise ValueError(
            "authoritative live ensemble requires at least "
            f"{minimum_independent_sources} independent sources; found {len(batches)}; "
            f"successful={sorted(successful)}; failures={detail}"
        )

    raw_ensemble, coverage = build_authoritative_live_ensemble(
        tuple(batches),
        minimum_independent_sources=minimum_independent_sources,
    )
    league_scored = derive_league_fantasy_point_forecasts(
        raw_ensemble,
        rules=league_state.league.rules,
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v5:source-health-provenance",
    )
    fantasy_points = apply_empirical_season_fantasy_point_uncertainty(league_scored)
    fantasy_regular_season = (
        derive_fantasy_regular_season_forecasts(league_state, fantasy_points)
        if league_state.matchups
        else ()
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=raw_ensemble,
        fantasy_point_forecasts=fantasy_points,
        fantasy_regular_season_forecasts=fantasy_regular_season,
        coverage=coverage,
        successful_source_ids=tuple(sorted(successful)),
        failed_sources=tuple(sorted(failed)),
        evaluation_as_of=evaluation_as_of,
        source_provenance=tuple(
            provenance_by_source[source_id]
            for source_id in sorted(successful)
        ),
    )
