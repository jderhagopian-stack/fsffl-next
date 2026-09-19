from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence

from fsffl.state.models import LeagueState


@dataclass(frozen=True)
class ProviderSnapshot:
    """Provider data captured at a known time.

    Payloads remain provider-specific here. They may not cross into downstream
    model code until a normalizer has converted them into canonical LeagueState.
    """

    provider_name: str
    league_external_id: str
    captured_at: datetime
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


class ProviderSnapshotSource(Protocol):
    """Acquire live or archived provider snapshots without model logic."""

    provider_name: str

    def fetch_latest(self, *, league_external_id: str) -> ProviderSnapshot: ...

    def fetch_at_or_before(
        self, *, league_external_id: str, as_of: datetime
    ) -> ProviderSnapshot | None: ...


class CanonicalStateNormalizer(Protocol):
    """Convert provider-specific snapshots into canonical state."""

    provider_name: str

    def normalize_snapshot(self, snapshot: ProviderSnapshot, *, as_of: datetime) -> LeagueState: ...


class ProviderBackedStateService:
    """Small orchestration boundary joining acquisition to normalization.

    The service refuses to answer a historical request with a snapshot captured
    after the requested cutoff. This prevents a live-provider response from
    silently masquerading as historical evidence.
    """

    def __init__(
        self,
        *,
        source: ProviderSnapshotSource,
        normalizer: CanonicalStateNormalizer,
    ) -> None:
        if source.provider_name != normalizer.provider_name:
            raise ValueError("provider source and normalizer must match")
        self._source = source
        self._normalizer = normalizer

    def materialize_live(self, *, league_external_id: str) -> LeagueState:
        snapshot = self._source.fetch_latest(league_external_id=league_external_id)
        return self._normalizer.normalize_snapshot(snapshot, as_of=snapshot.captured_at)

    def materialize_historical(
        self, *, league_external_id: str, as_of: datetime
    ) -> LeagueState | None:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        snapshot = self._source.fetch_at_or_before(
            league_external_id=league_external_id,
            as_of=as_of,
        )
        if snapshot is None:
            return None
        if snapshot.captured_at > as_of:
            raise ValueError("historical source returned a future snapshot")
        return self._normalizer.normalize_snapshot(snapshot, as_of=as_of)
