from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    NFL_SEASON_SCOPE_KIND,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import (
    canonical_players_from_sleeper_player_universe,
)

from .annual_preseason_service import capture_first_valid_annual_preseason_snapshot
from .annual_preseason_snapshot import ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION
from .current_runtime import NamedCurrentProjectionFetcher


@dataclass(frozen=True)
class AnnualPreseasonSchedulerResult:
    season: int
    attempted: bool
    outcome: str
    detail: str


def run_annual_preseason_scheduler_tick(
    persistence_store: PersistenceStore | None,
    *,
    clock: callable | None = None,
    sleeper_source: SleeperLiveSource | None = None,
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    minimum_independent_sources: int = 2,
) -> AnnualPreseasonSchedulerResult:
    """Run one production-safe annual preseason capture attempt.

    The runner is league-agnostic. Sleeper supplies the canonical current player
    universe and regular-season schedule coordinate; the existing annual capture
    service remains authoritative for T-14 eligibility, healthy-source coverage,
    first-valid persistence, and immutability.
    """

    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        return AnnualPreseasonSchedulerResult(
            season=now.year,
            attempted=True,
            outcome="failed-with-reason",
            detail="scheduler clock must be timezone-aware",
        )
    now = now.astimezone(UTC)
    season = now.year

    if persistence_store is None:
        return AnnualPreseasonSchedulerResult(
            season=season,
            attempted=True,
            outcome="failed-with-reason",
            detail="FSFFL_DATABASE_URL is unavailable; durable persistence is required",
        )

    existing = persistence_store.get_latest_reusable_artifact(
        artifact_kind=ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        scope_kind=NFL_SEASON_SCOPE_KIND,
        scope_id=str(season),
        model_version=ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    )
    if existing is not None:
        return AnnualPreseasonSchedulerResult(
            season=season,
            attempted=True,
            outcome="already-frozen",
            detail="first valid annual preseason snapshot already exists",
        )

    source = sleeper_source or SleeperLiveSource()
    try:
        raw_players = source.fetch_nfl_player_universe()
        canonical_players = canonical_players_from_sleeper_player_universe(raw_players)
        if not canonical_players:
            raise ValueError("Sleeper canonical NFL player universe is unavailable")

        schedule_rows = source.fetch_nfl_regular_season_schedule(season=season)
        if not isinstance(schedule_rows, Sequence) or isinstance(
            schedule_rows, (str, bytes)
        ):
            raise ValueError("Sleeper regular-season schedule payload is not a sequence")

        result = capture_first_valid_annual_preseason_snapshot(
            persistence_store,
            season=season,
            canonical_players=canonical_players,
            schedule_rows=tuple(
                row for row in schedule_rows if isinstance(row, Mapping)
            ),
            fetchers=fetchers,
            clock=lambda: now,
            minimum_independent_sources=minimum_independent_sources,
        )
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        if "annual preseason capture window has not opened" in str(exc):
            return AnnualPreseasonSchedulerResult(
                season=season,
                attempted=True,
                outcome="before-window",
                detail=message,
            )
        return AnnualPreseasonSchedulerResult(
            season=season,
            attempted=True,
            outcome="failed-with-reason",
            detail=message,
        )

    return AnnualPreseasonSchedulerResult(
        season=season,
        attempted=True,
        outcome=("captured" if result.created else "already-frozen"),
        detail=(
            "persisted first valid governed annual preseason snapshot"
            if result.created
            else "first valid annual preseason snapshot already exists"
        ),
    )
