from __future__ import annotations

from fsffl.value.fsffl_foundation3_pick_curve import (
    FSFFL_FOUNDATION3_CURVES,
    FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
    FSFFL_FOUNDATION3_EVIDENCE_SEASONS,
    FSFFL_FOUNDATION3_EVIDENCE_SHA256,
    FSFFL_FOUNDATION3_SCALE,
    FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
    FSFFL_FOUNDATION3_TARGET_LEAGUE_EXTERNAL_ID,
    FSFFL_FOUNDATION3_TARGET_LEAGUE_ID,
    fsffl_foundation3_live_curves,
)


def test_frozen_fsffl_curve_is_complete_exact_and_structurally_monotone() -> None:
    assert tuple(curve.round for curve in FSFFL_FOUNDATION3_CURVES) == (1, 2, 3)
    assert all(len(curve.slots) == 12 for curve in FSFFL_FOUNDATION3_CURVES)
    assert all(
        tuple(row.slot_in_round for row in curve.slots) == tuple(range(1, 13))
        for curve in FSFFL_FOUNDATION3_CURVES
    )
    assert all(curve.scale == FSFFL_FOUNDATION3_SCALE for curve in FSFFL_FOUNDATION3_CURVES)
    assert all(
        curve.model_version == FSFFL_FOUNDATION3_CURVE_MODEL_VERSION
        for curve in FSFFL_FOUNDATION3_CURVES
    )
    assert FSFFL_FOUNDATION3_EVIDENCE_SEASONS == (2024, 2025, 2026)
    assert len(FSFFL_FOUNDATION3_EVIDENCE_SHA256) == 64

    flattened = [
        row.value.mean
        for curve in FSFFL_FOUNDATION3_CURVES
        for row in curve.slots
    ]
    assert all(
        earlier + 1e-12 >= later
        for earlier, later in zip(flattened, flattened[1:])
    )
    assert FSFFL_FOUNDATION3_CURVES[0].slots[0].value.mean == 6434.333333333333
    assert FSFFL_FOUNDATION3_CURVES[0].slots[-1].value.mean == 965.2222222222222
    assert FSFFL_FOUNDATION3_CURVES[2].slots[-1].value.mean == 120.0


def test_live_curve_is_scoped_to_exact_fsffl_2027_coordinate() -> None:
    assert FSFFL_FOUNDATION3_TARGET_LEAGUE_ID == (
        f"sleeper:{FSFFL_FOUNDATION3_TARGET_LEAGUE_EXTERNAL_ID}"
    )
    accepted = fsffl_foundation3_live_curves(
        league_id=FSFFL_FOUNDATION3_TARGET_LEAGUE_ID,
        draft_season=FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
        team_count=12,
        rookie_draft_rounds=3,
    )
    assert accepted == FSFFL_FOUNDATION3_CURVES

    assert fsffl_foundation3_live_curves(
        league_id="other-league",
        draft_season=FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
        team_count=12,
        rookie_draft_rounds=3,
    ) == ()
    assert fsffl_foundation3_live_curves(
        league_id=FSFFL_FOUNDATION3_TARGET_LEAGUE_ID,
        draft_season=2028,
        team_count=12,
        rookie_draft_rounds=3,
    ) == ()
    assert fsffl_foundation3_live_curves(
        league_id=FSFFL_FOUNDATION3_TARGET_LEAGUE_ID,
        draft_season=FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
        team_count=10,
        rookie_draft_rounds=3,
    ) == ()


def test_frozen_curve_provenance_excludes_stale_2023_and_names_pit_sources() -> None:
    all_provenance = {
        item
        for curve in FSFFL_FOUNDATION3_CURVES
        for row in curve.slots
        for item in row.provenance
    }
    assert any("2023 FSFFL rookie draft excluded" in item for item in all_provenance)
    assert any("2024-06-01" in item and "a106fdf" in item for item in all_provenance)
    assert any("2025-05-31" in item and "e5035554" in item for item in all_provenance)
    assert any("2026-07-11" in item and "41c11510" in item for item in all_provenance)
    assert all("early/mid/late" not in item for item in all_provenance)
