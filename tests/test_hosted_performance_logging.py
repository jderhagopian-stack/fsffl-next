from pathlib import Path


def test_hosted_entrypoint_emits_existing_performance_timing_logs() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")
    coordinator = Path("src/fsffl/product/background_jobs.py").read_text(encoding="utf-8")

    assert 'logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)' in source
    assert 'logging.getLogger("fsffl.product.performance")' in coordinator
    assert "FSFFL intelligence refresh timing" in coordinator
    assert "phase_timings" in coordinator
    assert "total_elapsed_seconds" in coordinator


def test_hosted_entrypoint_logs_post_restore_runtime_readiness() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")

    assert "def _log_startup_runtime_readiness()" in source
    assert 'logging.getLogger("uvicorn.error").info(' in source
    assert "FSFFL startup runtime readiness user=%s league=%s state=%s forecast=%s simulation=%s value=%s complete=%s" in source
    assert 'app.router.add_event_handler("startup", _log_startup_runtime_readiness)' in source
