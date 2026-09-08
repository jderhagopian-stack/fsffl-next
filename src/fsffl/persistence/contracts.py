from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol, Sequence

JsonMapping = Mapping[str, Any]


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def canonical_fingerprint(*parts: Any) -> str:
    """Return a stable SHA-256 fingerprint for dependency-aware cache reuse.

    The fingerprint is identity only. It does not calculate model truth or decide whether
    an artifact is authoritative; callers must include the exact upstream evidence and
    model-version identifiers on which reuse depends.
    """

    encoded = json.dumps(
        parts,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class LeagueSnapshotRecord:
    provider: str
    league_id: str
    season: int
    state_hash: str
    payload: JsonMapping
    recorded_at: datetime
    source_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.recorded_at, field="recorded_at")
        if self.source_updated_at is not None:
            _require_aware(self.source_updated_at, field="source_updated_at")


@dataclass(frozen=True)
class TeamSnapshotRecord:
    provider: str
    league_id: str
    team_id: str
    state_hash: str
    payload: JsonMapping
    recorded_at: datetime
    source_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.recorded_at, field="recorded_at")
        if self.source_updated_at is not None:
            _require_aware(self.source_updated_at, field="source_updated_at")


@dataclass(frozen=True)
class SyncCursorRecord:
    provider: str
    scope_kind: str
    scope_id: str
    cursor_payload: JsonMapping
    synced_at: datetime
    source_updated_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.synced_at, field="synced_at")
        if self.source_updated_at is not None:
            _require_aware(self.source_updated_at, field="source_updated_at")


@dataclass(frozen=True)
class UserRuntimeContextRecord:
    user_id: str
    provider: str
    league_external_id: str
    league_id: str
    season: int
    state_hash: str
    updated_at: datetime
    selected_team_id: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.updated_at, field="updated_at")


@dataclass(frozen=True)
class ArtifactKey:
    artifact_kind: str
    scope_kind: str
    scope_id: str
    input_fingerprint: str
    model_version: str


@dataclass(frozen=True)
class ReusableArtifactRecord:
    key: ArtifactKey
    payload: JsonMapping
    computed_at: datetime
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.computed_at, field="computed_at")
        if self.invalidated_at is not None:
            _require_aware(self.invalidated_at, field="invalidated_at")

    @property
    def reusable(self) -> bool:
        return self.invalidated_at is None


class PersistenceStore(Protocol):
    """Server-side persistence boundary.

    Implementations may use Supabase, Neon, Render Postgres, RDS, or another PostgreSQL
    provider. They must never become a second calculation authority. A cached artifact is
    reusable only when its exact input fingerprint and model version match.
    """

    def get_user_runtime_context(self, *, user_id: str) -> UserRuntimeContextRecord | None: ...

    def put_user_runtime_context(self, record: UserRuntimeContextRecord) -> None: ...

    def get_league_snapshot(
        self, *, provider: str, league_id: str, season: int
    ) -> LeagueSnapshotRecord | None: ...

    def put_league_snapshot(self, record: LeagueSnapshotRecord) -> None: ...

    def get_team_snapshot(
        self, *, provider: str, league_id: str, team_id: str
    ) -> TeamSnapshotRecord | None: ...

    def put_team_snapshot(self, record: TeamSnapshotRecord) -> None: ...

    def get_sync_cursor(
        self, *, provider: str, scope_kind: str, scope_id: str
    ) -> SyncCursorRecord | None: ...

    def put_sync_cursor(self, record: SyncCursorRecord) -> None: ...

    def get_reusable_artifact(self, key: ArtifactKey) -> ReusableArtifactRecord | None: ...

    def get_latest_reusable_artifact(
        self,
        *,
        artifact_kind: str,
        scope_kind: str,
        scope_id: str,
        model_version: str,
    ) -> ReusableArtifactRecord | None: ...

    def put_artifact(self, record: ReusableArtifactRecord) -> None: ...

    def invalidate_scope(
        self,
        *,
        scope_kind: str,
        scope_id: str,
        cause_kind: str,
        cause_ref: str | None,
        artifact_kinds: Sequence[str],
        observed_at: datetime | None = None,
    ) -> None: ...

    def append_market_value_snapshot(
        self,
        *,
        asset_ref: str,
        asset_kind: str,
        scale_id: str,
        market_context_id: str,
        estimate_as_of: datetime,
        value: float,
        source_lineage: JsonMapping,
        recorded_at: datetime | None = None,
    ) -> None: ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
