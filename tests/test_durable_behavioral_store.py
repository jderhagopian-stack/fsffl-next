from __future__ import annotations

from pathlib import Path

import fsffl.product.behavioral_runtime as runtime


def test_behavioral_store_defaults_to_sqlite_without_hosted_database(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FSFFL_DATABASE_URL", raising=False)
    cache = tmp_path / "behavior.sqlite3"
    monkeypatch.setenv("FSFFL_BEHAVIOR_CACHE_PATH", str(cache))

    store = runtime.default_behavioral_store()

    assert store.__class__.__name__ == "BehavioralIntelligenceStore"
    assert store.path == cache


def test_behavioral_store_prefers_postgres_when_hosted_database_is_configured(monkeypatch) -> None:
    seen: list[str] = []

    class FakePostgresStore:
        def __init__(self, database_url: str) -> None:
            seen.append(database_url)

    monkeypatch.setenv("FSFFL_DATABASE_URL", "postgresql://example/fsffl")
    monkeypatch.setattr(runtime, "PostgresBehavioralIntelligenceStore", FakePostgresStore)

    store = runtime.default_behavioral_store()

    assert isinstance(store, FakePostgresStore)
    assert seen == ["postgresql://example/fsffl"]


def test_postgres_behavioral_store_has_same_narrow_service_contract() -> None:
    from fsffl.behavioral.postgres_store import PostgresBehavioralIntelligenceStore

    required = {
        "put_events",
        "load_events",
        "put_profiles",
        "load_profiles",
        "mark_season_complete",
        "season_is_complete",
        "complete_league_ids",
    }
    assert required <= set(dir(PostgresBehavioralIntelligenceStore))


def test_behavioral_migration_preserves_evidence_profile_and_season_layers() -> None:
    sql = Path("db/migrations/20260909_004_durable_behavioral_evidence.sql").read_text()

    assert "fsffl.behavior_event" in sql
    assert "fsffl.behavior_profile" in sql
    assert "fsffl.behavior_season" in sql
    assert "primary key (league_family_id, event_id)" in sql
    assert "primary key (league_family_id, owner_id)" in sql
    assert "primary key (league_family_id, league_external_id)" in sql
