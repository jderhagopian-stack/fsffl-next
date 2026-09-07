from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .historical_trade import HistoricalTradeReport


class HistoricalArtifactKind(StrEnum):
    TRANSACTION_FACT = "transaction_fact"
    POINT_IN_TIME_STATE = "point_in_time_state"
    POINT_IN_TIME_ANALYSIS = "point_in_time_analysis"
    RETROSPECTIVE_ANALYSIS = "retrospective_analysis"
    ASSET_LINEAGE = "asset_lineage"
    FINAL_REPORT = "final_report"


class HistoricalArtifactIdentity(FrozenModel):
    league_id: str
    transaction_id: str
    artifact_kind: HistoricalArtifactKind
    artifact_version: str
    as_of: datetime | None = None
    dependency_fingerprint: str | None = None

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("historical artifact as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "HistoricalArtifactIdentity":
        if any(not value.strip() for value in (self.league_id, self.transaction_id, self.artifact_version)):
            raise ValueError("historical artifact identifiers cannot be blank")
        if self.dependency_fingerprint is not None and not self.dependency_fingerprint.strip():
            raise ValueError("dependency_fingerprint cannot be blank")
        if self.artifact_kind in {
            HistoricalArtifactKind.RETROSPECTIVE_ANALYSIS,
            HistoricalArtifactKind.ASSET_LINEAGE,
            HistoricalArtifactKind.FINAL_REPORT,
        } and self.as_of is None:
            raise ValueError("refreshable historical artifacts require an as_of timestamp")
        return self


class HistoricalSyncCheckpoint(FrozenModel):
    league_id: str
    provider: str
    last_completed_at: datetime
    provider_cursor: str | None = None
    model_version: str = "historical-sync-checkpoint-v1"

    @field_validator("last_completed_at")
    @classmethod
    def require_checkpoint_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("sync checkpoint timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "HistoricalSyncCheckpoint":
        if any(not value.strip() for value in (self.league_id, self.provider, self.model_version)):
            raise ValueError("sync checkpoint identifiers cannot be blank")
        if self.provider_cursor is not None and not self.provider_cursor.strip():
            raise ValueError("provider_cursor cannot be blank")
        return self


class HistoricalInvalidationRequest(FrozenModel):
    league_id: str
    dependency_component: str
    old_version: str
    new_version: str
    affected_transaction_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_request(self) -> "HistoricalInvalidationRequest":
        if any(
            not value.strip()
            for value in (
                self.league_id,
                self.dependency_component,
                self.old_version,
                self.new_version,
            )
        ):
            raise ValueError("invalidation identifiers cannot be blank")
        if self.old_version == self.new_version:
            raise ValueError("invalidation requires a changed dependency version")
        if len(self.affected_transaction_ids) != len(set(self.affected_transaction_ids)):
            raise ValueError("affected transaction ids must be unique")
        return self


class HistoricalReportRepository(Protocol):
    def get(self, identity: HistoricalArtifactIdentity) -> HistoricalTradeReport | None: ...

    def put(self, identity: HistoricalArtifactIdentity, report: HistoricalTradeReport) -> None: ...

    def invalidate(self, request: HistoricalInvalidationRequest) -> tuple[HistoricalArtifactIdentity, ...]: ...


class HistoricalSyncCheckpointRepository(Protocol):
    def get(self, league_id: str, provider: str) -> HistoricalSyncCheckpoint | None: ...

    def put(self, checkpoint: HistoricalSyncCheckpoint) -> None: ...


class InMemoryHistoricalReportRepository:
    """Reference implementation for versioned historical report persistence.

    Production storage can use a database/object store while preserving this contract.
    Immutable point-in-time artifacts are never overwritten across versions. Refreshable
    hindsight artifacts are stored under their own ``as_of`` and dependency fingerprint.
    """

    def __init__(
        self,
        entries: Mapping[HistoricalArtifactIdentity, HistoricalTradeReport] | None = None,
    ) -> None:
        self._entries = dict(entries or {})

    def get(self, identity: HistoricalArtifactIdentity) -> HistoricalTradeReport | None:
        return self._entries.get(identity)

    def put(self, identity: HistoricalArtifactIdentity, report: HistoricalTradeReport) -> None:
        existing = self._entries.get(identity)
        if existing is not None and existing != report:
            raise ValueError("historical artifact identity is immutable once persisted")
        self._entries[identity] = report

    def invalidate(self, request: HistoricalInvalidationRequest) -> tuple[HistoricalArtifactIdentity, ...]:
        removed: list[HistoricalArtifactIdentity] = []
        affected = set(request.affected_transaction_ids)
        for identity in tuple(self._entries):
            if identity.league_id != request.league_id:
                continue
            if affected and identity.transaction_id not in affected:
                continue
            fingerprint = identity.dependency_fingerprint or ""
            if request.old_version not in fingerprint:
                continue
            if identity.artifact_kind in {
                HistoricalArtifactKind.TRANSACTION_FACT,
                HistoricalArtifactKind.POINT_IN_TIME_STATE,
            }:
                continue
            removed.append(identity)
            del self._entries[identity]
        return tuple(sorted(removed, key=lambda item: (item.transaction_id, item.artifact_kind.value, item.artifact_version)))


class InMemoryHistoricalSyncCheckpointRepository:
    def __init__(self, checkpoints: tuple[HistoricalSyncCheckpoint, ...] = ()) -> None:
        self._checkpoints: dict[tuple[str, str], HistoricalSyncCheckpoint] = {}
        for checkpoint in checkpoints:
            self.put(checkpoint)

    def get(self, league_id: str, provider: str) -> HistoricalSyncCheckpoint | None:
        return self._checkpoints.get((league_id, provider))

    def put(self, checkpoint: HistoricalSyncCheckpoint) -> None:
        key = (checkpoint.league_id, checkpoint.provider)
        previous = self._checkpoints.get(key)
        if previous is not None and checkpoint.last_completed_at < previous.last_completed_at:
            raise ValueError("sync checkpoints cannot move backward")
        self._checkpoints[key] = checkpoint
