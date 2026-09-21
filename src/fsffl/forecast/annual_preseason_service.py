from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    NFL_SEASON_SCOPE_KIND,
    annual_preseason_projection_snapshot_artifact,
    decode_annual_preseason_projection_snapshot,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.state.models import Player

from .annual_preseason_snapshot import (
    ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    AnnualPreseasonProjectionSnapshot,
    capture_annual_preseason_projection_snapshot,
)
from .current_runtime import NamedCurrentProjectionFetcher


@dataclass(frozen=True)
class AnnualPreseasonCapturePersistenceResult:
    snapshot: AnnualPreseasonProjectionSnapshot
    created: bool


def capture_first_valid_annual_preseason_snapshot(
    persistence_store: PersistenceStore,
    *,
    season: int,
    canonical_players: tuple[Player, ...],
    schedule_rows: Sequence[Mapping[str, Any]],
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    clock: callable | None = None,
    minimum_independent_sources: int = 2,
) -> AnnualPreseasonCapturePersistenceResult:
    """Persist only the first valid governed NFL-season preseason snapshot.

    This service is idempotent and safe for daily scheduling. Existing valid season
    evidence is returned unchanged. Failed capture attempts never call put_artifact,
    allowing the next scheduled invocation before kickoff to retry without rewriting
    or degrading evidence.
    """

    existing = persistence_store.get_latest_reusable_artifact(
        artifact_kind=ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        scope_kind=NFL_SEASON_SCOPE_KIND,
        scope_id=str(season),
        model_version=ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    )
    if existing is not None:
        return AnnualPreseasonCapturePersistenceResult(
            snapshot=decode_annual_preseason_projection_snapshot(dict(existing.payload)),
            created=False,
        )

    snapshot = capture_annual_preseason_projection_snapshot(
        season=season,
        canonical_players=canonical_players,
        schedule_rows=schedule_rows,
        fetchers=fetchers,
        clock=clock,
        minimum_independent_sources=minimum_independent_sources,
    )

    # Recheck immediately before the write so repeated/overlapping invocations do not
    # intentionally replace an already-persisted first-valid coordinate.
    existing = persistence_store.get_latest_reusable_artifact(
        artifact_kind=ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        scope_kind=NFL_SEASON_SCOPE_KIND,
        scope_id=str(season),
        model_version=ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    )
    if existing is not None:
        return AnnualPreseasonCapturePersistenceResult(
            snapshot=decode_annual_preseason_projection_snapshot(dict(existing.payload)),
            created=False,
        )

    persistence_store.put_artifact(
        annual_preseason_projection_snapshot_artifact(snapshot=snapshot)
    )
    return AnnualPreseasonCapturePersistenceResult(snapshot=snapshot, created=True)
