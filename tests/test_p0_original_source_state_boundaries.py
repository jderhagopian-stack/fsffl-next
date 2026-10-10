"""Regression proof for the recovered, byte-identical accepted P0 boundaries."""

from pathlib import Path

from fsffl.product.p0_candidate_evidence import (
    P0SourceStateAuthority,
    P0_ACCEPTED_SOURCE_STATE_BOUNDARIES_JSON,
    accepted_p0_source_state_authority,
)
from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows


BOUNDARIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919"
    / "current_state_boundaries_2026.json"
)


def test_recovered_p0_boundaries_match_original_digest_and_335_source_states():
    original = BOUNDARIES_PATH.read_bytes()
    assert P0_ACCEPTED_SOURCE_STATE_BOUNDARIES_JSON.encode('utf-8') == original
    authority = accepted_p0_source_state_authority()
    assert authority == P0SourceStateAuthority.from_artifact_bytes(original)
    assert set(authority.thresholds_by_position) == {"QB", "RB", "WR", "TE"}
    reference = frozen_p0_source_rows()
    assert len(reference) == 335
    names = ("depth", "usable", "starter", "premium", "elite")
    for row in reference:
        if row.standard_y1_points <= 0:
            expected = "out"
        else:
            cutpoints = authority.thresholds_by_position[row.position]
            expected = names[sum(row.standard_y1_points > point for point in cutpoints)]
        assert row.source_state == expected, row.player_id
