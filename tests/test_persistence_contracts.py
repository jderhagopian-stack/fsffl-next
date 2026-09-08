from datetime import datetime, timezone

import pytest

from fsffl.persistence import (
    ArtifactKey,
    LeagueSnapshotRecord,
    ReusableArtifactRecord,
    canonical_fingerprint,
)


def test_canonical_fingerprint_is_order_stable_for_mapping_content() -> None:
    first = canonical_fingerprint({"b": 2, "a": 1}, ["x", "y"], "v1")
    second = canonical_fingerprint({"a": 1, "b": 2}, ["x", "y"], "v1")

    assert first == second
    assert len(first) == 64


def test_canonical_fingerprint_changes_when_upstream_identity_changes() -> None:
    baseline = canonical_fingerprint({"roster_hash": "abc"}, "forecast-v1")
    changed = canonical_fingerprint({"roster_hash": "def"}, "forecast-v1")

    assert baseline != changed


def test_snapshot_requires_timezone_aware_recorded_time() -> None:
    with pytest.raises(ValueError, match="recorded_at must be timezone-aware"):
        LeagueSnapshotRecord(
            provider="sleeper",
            league_id="league-1",
            season=2026,
            state_hash="state-1",
            payload={},
            recorded_at=datetime(2026, 9, 8, 12, 0),
        )


def test_reusable_artifact_is_valid_only_until_explicitly_invalidated() -> None:
    now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    key = ArtifactKey(
        artifact_kind="team_view",
        scope_kind="team",
        scope_id="team-1",
        input_fingerprint="fingerprint",
        model_version="next4-team-view-v1",
    )

    current = ReusableArtifactRecord(key=key, payload={"expected_wins": 7.2}, computed_at=now)
    invalidated = ReusableArtifactRecord(
        key=key,
        payload={"expected_wins": 7.2},
        computed_at=now,
        invalidated_at=now,
        invalidation_reason="roster_changed",
    )

    assert current.reusable is True
    assert invalidated.reusable is False
