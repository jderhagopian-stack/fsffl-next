"""Synthetic input and chronology regressions for preseason P0 research adapter."""
from __future__ import annotations

from datetime import UTC, datetime
import math

import pytest
from fsffl.product.p0_candidate_evidence import accepted_p0_source_state_authority, _current_state
from scripts.research_2026_preseason_p0_shapley import _standard_y1


def test_standard_scoring_uses_only_preseason_raw_stats():
    raw={"projected_stats":{
        "pass_yd":200.0,"pass_td":2.0,"pass_int":1.0,
        "rush_yd":20.0,"rush_td":1.0,
        "rec_yd":0.0,"rec_td":0.0,"fum_lost":1.0,
    }}
    assert math.isclose(_standard_y1(raw),20.0,abs_tol=1e-8)


def test_required_preseason_fumbles_not_inferred():
    with pytest.raises(ValueError, match="lost-fumbles"):
        _standard_y1({"projected_stats":{"rec_yd":75}})


def test_missing_entire_projection_cannot_be_zero():
    with pytest.raises(ValueError, match="projected-stat evidence"):
        _standard_y1({})


def test_threshold_authority_is_historically_bounded():
    gate=accepted_p0_source_state_authority()
    assert set(gate.thresholds_by_position)=={"QB","RB","WR","TE"}
    assert _current_state(90.0,gate.thresholds_by_position["WR"])=="premium"
    assert _current_state(150.0,gate.thresholds_by_position["WR"])=="elite"
