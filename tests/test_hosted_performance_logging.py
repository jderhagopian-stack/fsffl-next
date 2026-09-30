from pathlib import Path


def test_hosted_entrypoint_emits_existing_performance_timing_logs() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")
    coordinator = Path("src/fsffl/product/background_jobs.py").read_text(encoding="utf-8")

    assert 'logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)' in source
    assert 'logging.getLogger("fsffl.product.performance")' in coordinator
    assert "FSFFL intelligence refresh timing" in coordinator
    assert "phase_timings" in coordinator
    assert "total_elapsed_seconds" in coordinator


def test_value_consumers_emit_server_timing_for_propagation_acceptance() -> None:
    latency = Path("src/fsffl/product/latency_observability.py").read_text(encoding="utf-8")
    for path in (
        '"/api/intelligence/status"',
        '"/api/league/atlas"',
        '"/api/league/team-views"',
        '"/api/league/value-lenses"',
    ):
        assert path in latency


def test_hosted_entrypoint_logs_post_restore_runtime_readiness() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")

    assert "def _log_startup_runtime_readiness()" in source
    assert 'logging.getLogger("uvicorn.error").info(' in source
    assert "FSFFL startup runtime readiness user=%s league=%s state=%s forecast=%s simulation=%s value=%s complete=%s" in source
    restore = source.split("def _run_lightweight_startup_restore()", 1)[1].split(
        "def _start_lightweight_startup_restore()", 1
    )[0]
    assert "_log_startup_runtime_readiness()" in restore
    assert 'app.router.add_event_handler("startup", _start_lightweight_startup_restore)' in source
    assert 'app.router.add_event_handler("startup", _log_startup_runtime_readiness)' not in source
