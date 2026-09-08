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
    canonical_fingerprint,
)

__all__ = [
    "ArtifactKey",
    "LeagueSnapshotRecord",
    "PersistenceStore",
    "ReusableArtifactRecord",
    "SyncCursorRecord",
    "TeamSnapshotRecord",
    "canonical_fingerprint",
]
