from __future__ import annotations

from pathlib import Path


SOURCE = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")


def test_foundation4_hosted_acceptance_is_explicit_bounded_and_non_sensitive() -> None:
    assert "FSFFL_RUN_FOUNDATION4_ACCEPTANCE" in SOURCE
    assert "FSFFL_FOUNDATION4_ACCEPTANCE_MODE" in SOURCE
    assert '"build", "restore"' in SOURCE or '{"build", "restore"}' in SOURCE
    assert "/health/foundation4-shadow-acceptance" in SOURCE
    assert "FSFFL FOUNDATION4 SHADOW ACCEPTANCE PASS" in SOURCE
    assert "semantic_input_fingerprint" in SOURCE
    assert "dependency_fingerprint" in SOURCE
    assert "player_count=contract.player_count" in SOURCE
    assert "after.peak_rss_bytes > after.memory_budget_bytes" in SOURCE

    # Acceptance metadata must never expose the player-level board.
    health_block = SOURCE.split(
        '@app.get("/health/foundation4-shadow-acceptance")', 1
    )[1].split('@app.get("/health/runtime-resources")', 1)[0]
    assert "estimates" not in health_block
    assert "raw_career_forward_reference" not in health_block


def test_foundation4_restore_mode_requires_persisted_compatible_shadow() -> None:
    assert "_career_intrinsic_coordinator.restore_compatible_staged(context)" in SOURCE
    assert "No compatible persisted Foundation 4 shadow was restored" in SOURCE
    assert "_career_intrinsic_coordinator.wait_for_terminal(" in SOURCE
    assert "Foundation 4 Y1-Y3 raw Shapley semantics drifted" in SOURCE
    assert "Foundation 4 career-forward economics do not reconcile" in SOURCE
