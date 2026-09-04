from datetime import UTC, datetime, timedelta

import pytest

from fsffl.providers.acquisition import ProviderBackedStateService, ProviderSnapshot
from fsffl.state.models import LeagueState
from tests.test_state_foundation import make_state


NOW = datetime(2026, 9, 4, 15, 0, tzinfo=UTC)


class FakeSource:
    provider_name = "fake"

    def __init__(self, snapshot: ProviderSnapshot | None) -> None:
        self.snapshot = snapshot

    def fetch_latest(self, *, league_external_id: str) -> ProviderSnapshot:
        if self.snapshot is None:
            raise LookupError("missing")
        return self.snapshot

    def fetch_at_or_before(self, *, league_external_id: str, as_of: datetime) -> ProviderSnapshot | None:
        return self.snapshot


class FakeNormalizer:
    provider_name = "fake"

    def normalize_snapshot(self, snapshot: ProviderSnapshot, *, as_of: datetime) -> LeagueState:
        return make_state(as_of)


class WrongNormalizer(FakeNormalizer):
    provider_name = "other"


def test_historical_service_rejects_future_snapshot() -> None:
    snapshot = ProviderSnapshot(
        provider_name="fake",
        league_external_id="league",
        captured_at=NOW + timedelta(hours=1),
        payload={},
    )
    service = ProviderBackedStateService(source=FakeSource(snapshot), normalizer=FakeNormalizer())
    with pytest.raises(ValueError, match="future snapshot"):
        service.materialize_historical(league_external_id="league", as_of=NOW)


def test_historical_service_accepts_snapshot_at_cutoff() -> None:
    snapshot = ProviderSnapshot(
        provider_name="fake",
        league_external_id="league",
        captured_at=NOW - timedelta(minutes=5),
        payload={},
    )
    service = ProviderBackedStateService(source=FakeSource(snapshot), normalizer=FakeNormalizer())
    state = service.materialize_historical(league_external_id="league", as_of=NOW)
    assert state is not None
    assert state.as_of == NOW


def test_historical_service_returns_none_when_archive_has_no_snapshot() -> None:
    service = ProviderBackedStateService(source=FakeSource(None), normalizer=FakeNormalizer())
    assert service.materialize_historical(league_external_id="league", as_of=NOW) is None


def test_provider_mismatch_is_rejected() -> None:
    snapshot = ProviderSnapshot(
        provider_name="fake",
        league_external_id="league",
        captured_at=NOW,
        payload={},
    )
    with pytest.raises(ValueError, match="must match"):
        ProviderBackedStateService(source=FakeSource(snapshot), normalizer=WrongNormalizer())
