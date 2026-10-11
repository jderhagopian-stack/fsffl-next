from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

FILE = Path(__file__).parents[1] / "scripts/materialize_foundation4_dynamic_candidates.py"
SPEC = importlib.util.spec_from_file_location("career_dynamic", FILE)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(**updates):
    values = {
        "player_id": "sleeper:player:9001", "position": "QB", "historical_gsis_id": "00-0039001",
        "age": 24, "experience": 2, "league_y1_points": 20,
        "y2_player_league_expected_points": 30, "y3_player_league_expected_points": 35,
        "state_hash": "state-1", "state_as_of": "2026-10-08T00:00:00Z",
        "evaluation_as_of": "2026-10-10T00:00:00Z", "forecast_as_of": "2026-10-09T00:00:00Z",
        "identity_as_of": "2026-10-09T00:00:00Z",
        "evidence_source": "approved-p0", "evidence_version": "p0-v1",
        "scoring_coordinate": "connected_league_fantasy_points", "team_id": "team-1", "roster_slot": "BENCH",
    }
    values.update(updates)
    return values


def test_dynamic_input_is_canonical_and_point_in_time():
    roster = pd.DataFrame([{"state_hash":"state-1", "player_id":"sleeper:player:9001", "position":"QB", "team_id":"team-1", "roster_slot":"BENCH", "age":24.0, "state_as_of":"2026-10-08T00:00:00Z"}])
    assert MOD.validate_candidates(pd.DataFrame([row()]), {"frozen"}, 2026, roster).iloc[0].player_id == "sleeper:player:9001"
    with pytest.raises(ValueError, match="later than evaluation"):
        MOD.validate_candidates(pd.DataFrame([row(forecast_as_of="2026-10-11T00:00:00Z")]), set(), 2026, roster)
    with pytest.raises(ValueError, match="overlaps frozen"):
        MOD.validate_candidates(pd.DataFrame([row(player_id="frozen")]), {"frozen"}, 2026, roster)


def test_candidate_y1_percentile_uses_frozen_reference():
    class Dev:
        @staticmethod
        def merge_lags(frame, raw): return frame.copy()
        @staticmethod
        def add_engineered_features(frame, players):
            result = frame.copy(); result["y1_pct"] = 1.0; return result
        @staticmethod
        def merge_trajectory(frame, residual, innovation): return frame
    candidate = pd.DataFrame([row()])
    ref = pd.DataFrame({"position": ["QB"] * 3, "y1": [10.0, 20.0, 30.0]})
    result = MOD.build_candidate_features(Dev(), candidate, ref, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    assert result.iloc[0].y1_pct == pytest.approx(0.5)
    assert result.iloc[0].age == 24


def test_missing_historical_crosswalk_uses_canonical_key_without_zero_filling():
    seen = {}
    class Dev:
        @staticmethod
        def merge_lags(frame, raw):
            seen["player_id"] = frame.player_id.tolist()
            return frame.copy()
        @staticmethod
        def add_engineered_features(frame, players):
            result = frame.copy(); result["y1_pct"] = 1.0; return result
        @staticmethod
        def merge_trajectory(frame, residual, innovation): return frame
    candidate = pd.DataFrame([row(historical_gsis_id="", league_y1_points=16.0)])
    reference = pd.DataFrame({"position": ["QB"] * 2, "y1": [8.0, 24.0]})
    output = MOD.build_candidate_features(
        Dev(), candidate, reference, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    assert seen["player_id"] == ["sleeper:player:9001"]
    assert output.iloc[0].output_player_id == "sleeper:player:9001"
    assert output.iloc[0].y1 == 16.0
    assert output.iloc[0].historical_gsis_id == ""


def test_roster_authority_status_covers_reference_partial_and_missing_subjects():
    roster = pd.DataFrame([
        {"player_id":"ref", "position":"RB", "team_id":"t1", "roster_slot":"IR", "state_hash":"s"},
        {"player_id":"candidate", "position":"QB", "team_id":"t1", "roster_slot":"TAXI", "state_hash":"s"},
        {"player_id":"missing", "position":"WR", "team_id":"t2", "roster_slot":"BENCH", "state_hash":"s"},
    ])
    result = MOD.build_roster_authority_status(roster, {"ref"}, {"candidate"})
    assert len(result) == 3
    assert result.set_index("player_id").loc["ref", "coverage_status"] == "reference_estimate_available"
    assert result.set_index("player_id").loc["candidate", "coverage_status"] == "partial_authority"
    assert result.set_index("player_id").loc["missing", "coverage_status"] == "unavailable"
