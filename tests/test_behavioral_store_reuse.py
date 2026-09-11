from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fsffl.product.behavioral_runtime as behavioral_runtime


PERSISTENT_WEBAPP = Path("src/fsffl/product/persistent_webapp.py")


def test_hosted_postgres_behavioral_store_is_reused(monkeypatch) -> None:
    created: list[str] = []

    class FakePostgresStore:
        def __init__(self, database_url: str) -> None:
            created.append(database_url)
            self.database_url = database_url

    behavioral_runtime._hosted_postgres_stores.clear()
    monkeypatch.setenv("FSFFL_DATABASE_URL", "postgresql://latency-test")
    monkeypatch.setattr(
        behavioral_runtime,
        "PostgresBehavioralIntelligenceStore",
        FakePostgresStore,
    )

    first = behavioral_runtime.default_behavioral_store()
    second = behavioral_runtime.default_behavioral_store()

    assert first is second
    assert created == ["postgresql://latency-test"]
    behavioral_runtime._hosted_postgres_stores.clear()


def test_concurrent_hosted_store_requests_bootstrap_once(monkeypatch) -> None:
    created: list[str] = []

    class FakePostgresStore:
        def __init__(self, database_url: str) -> None:
            created.append(database_url)

    behavioral_runtime._hosted_postgres_stores.clear()
    monkeypatch.setenv("FSFFL_DATABASE_URL", "postgresql://concurrent-test")
    monkeypatch.setattr(
        behavioral_runtime,
        "PostgresBehavioralIntelligenceStore",
        FakePostgresStore,
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        stores = list(executor.map(lambda _: behavioral_runtime.default_behavioral_store(), range(24)))

    assert len({id(store) for store in stores}) == 1
    assert created == ["postgresql://concurrent-test"]
    behavioral_runtime._hosted_postgres_stores.clear()


def test_hosted_app_prewarms_behavioral_store_before_serving_requests() -> None:
    source = PERSISTENT_WEBAPP.read_text(encoding="utf-8")

    assert "_behavioral_store = default_behavioral_store()" in source
    assert "Behavioral store prewarm unavailable; runtime will retry" in source
    assert "store_factory=(" in source
    assert "if _behavioral_store is not None" in source
