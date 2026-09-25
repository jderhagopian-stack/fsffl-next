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
from .late_start_projection_snapshot import (
    LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    decode_late_start_current_projection_snapshot,
    encode_late_start_current_projection_snapshot,
    late_start_current_projection_snapshot_artifact,
)
from .provisional_k_dst_forecast import (
    PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND,
    PROVISIONAL_K_DST_SCOPE_KIND,
    decode_provisional_k_dst_forecast,
    encode_provisional_k_dst_forecast,
    provisional_k_dst_forecast_artifact,
    provisional_k_dst_scope_id,
)
from .postgres import PostgresPersistenceStore, persistence_store_from_env
from .projection_history import (
    PostgresProjectionHistoryStore,
    projection_history_store_from_env,
)
from .state_history import PostgresStateSnapshotStore, state_snapshot_store_from_env

__all__ = [
    "provisional_k_dst_scope_id",
    "provisional_k_dst_forecast_artifact",
    "encode_provisional_k_dst_forecast",
    "decode_provisional_k_dst_forecast",
    "PROVISIONAL_K_DST_SCOPE_KIND",
    "PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND",
    "late_start_current_projection_snapshot_artifact",
    "encode_late_start_current_projection_snapshot",
    "decode_late_start_current_projection_snapshot",
    "LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND",
    "ArtifactKey",
    "LeagueSnapshotRecord",
    "PersistenceStore",
    "PostgresPersistenceStore",
    "PostgresProjectionHistoryStore",
    "PostgresStateSnapshotStore",
    "ReusableArtifactRecord",
    "SyncCursorRecord",
    "TeamSnapshotRecord",
    "UserPerceivedLatencyRecord",
    "UserRuntimeContextRecord",
    "canonical_fingerprint",
    "persistence_store_from_env",
    "projection_history_store_from_env",
    "state_snapshot_store_from_env",
    "utc_now",
]
