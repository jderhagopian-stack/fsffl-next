from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactMetadataRecord
from fsffl.persistence.postgres import PostgresPersistenceStore


class _Cursor:
    def __init__(self, row):
        self.row = row
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self._cursor


@pytest.mark.parametrize("lookup", ["exact", "latest"])
def test_artifact_metadata_lookups_never_select_json_payload(lookup):
    computed_at = datetime(2026, 10, 6, 11, 0, tzinfo=UTC)
    row = {
        "artifact_kind": "runtime_presentation_surface",
        "scope_kind": "user_league_presentation",
        "scope_id": "jimmy:league:promotion",
        "input_fingerprint": "sha-state",
        "model_version": "runtime-presentation-continuity-v2",
        "computed_at": computed_at,
        "invalidated_at": None,
        "invalidation_reason": None,
    }
    cursor = _Cursor(row)
    store = PostgresPersistenceStore("postgresql://unused")
    store._connect = lambda: _Connection(cursor)
    key = ArtifactKey(
        artifact_kind=row["artifact_kind"],
        scope_kind=row["scope_kind"],
        scope_id=row["scope_id"],
        input_fingerprint=row["input_fingerprint"],
        model_version=row["model_version"],
    )

    if lookup == "exact":
        result = store.get_reusable_artifact_metadata(key)
    else:
        result = store.get_latest_reusable_artifact_metadata(
            artifact_kind=key.artifact_kind,
            scope_kind=key.scope_kind,
            scope_id=key.scope_id,
            model_version=key.model_version,
        )

    assert isinstance(result, ReusableArtifactMetadataRecord)
    assert result.key == key
    assert result.computed_at == computed_at
    assert result.reusable
    assert "payload" not in cursor.query.lower()
