from pathlib import Path


def test_hosted_entrypoint_emits_existing_performance_timing_logs() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")
    coordinator = Path("src/fsffl/product/background_jobs.py").read_text(encoding="utf-8")

    assert 'logging.getLogger("fsffl.product.performance").setLevel(logging.INFO)' in source
    assert 'logging.getLogger("fsffl.product.performance")' in coordinator
    assert "FSFFL intelligence refresh timing" in coordinator
    assert "phase_timings" in coordinator
    assert "total_elapsed_seconds" in coordinator
