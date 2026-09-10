"""Durable persistence contracts for FSFFL NEXT.

Persistence stores authoritative inputs and reusable outputs with provenance. It does not
own State, Forecast, Value, Decision, Search, or Simulation truth.
"""

from .contracts import (
    ArtifactKey,
    LeagueSnapshotRecord,
    PersistenceStore,
    ReusableArtifactRecord,
    SyncCursorRecord,
    TeamSnapshotRecord,
    UserPerceivedLatencyRecord,
    UserRuntimeContextRecord,
    canonical_fingerprint,
    utc_now,
)
from .postgres import PostgresPersistenceStore, persistence_store_from_env
from .state_history import PostgresStateSnapshotStore, state_snapshot_store_from_env

__all__ = [
    "ArtifactKey",
    "LeagueSnapshotRecord",
    "PersistenceStore",
    "PostgresPersistenceStore",
    "PostgresStateSnapshotStore",
    "ReusableArtifactRecord",
    "SyncCursorRecord",
    "TeamSnapshotRecord",
    "UserPerceivedLatencyRecord",
    "UserRuntimeContextRecord",
    "canonical_fingerprint",
    "persistence_store_from_env",
    "state_snapshot_store_from_env",
    "utc_now",
]
