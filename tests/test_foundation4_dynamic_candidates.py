from __future__ import annotations

import importlib.util
import json
import os
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



def test_durable_roster_checkpoint_atomically_accounts_for_success_and_failure(tmp_path):
    success = "sleeper:player:9001"
    failed = "sleeper:player:9002"
    roster = [
        {"player_id": success, "position": "QB", "team_id": "t1", "roster_slot": "BENCH",
         "state_hash": "state-1"},
        {"player_id": failed, "position": "RB", "team_id": "t2", "roster_slot": "IR",
         "state_hash": "state-1"},
    ]
    candidate_inputs = pd.DataFrame([row(team_id="t1")])
    y4_y7 = pd.DataFrame([
        {"player_id": success, "year_index": year, "policy_id": policy,
         "central_expectation": 10.0 + year}
        for year in range(4, 8)
        for policy in ("baseline", "hard_router", "soft_stack", "blanket_75_25")
    ])
    y8_plus = pd.DataFrame([{"player_id": success, "model_version": "career-tail-v1"}])
    failures = {
        failed: {
            "failure_code": "p0_source_missing",
            "failure_detail": "No eligible governed source row",
            "evidence_checked": ["provider-a", "provider-b"],
            "provenance": {"run_id": "fixture"},
        }
    }
    path = tmp_path / "private" / "roster-checkpoint.json"
    digest = MOD.write_durable_roster_checkpoint(
        path,
        state_hash="state-1",
        state_as_of="2026-10-08T00:00:00Z",
        evaluation_as_of="2026-10-10T00:00:00Z",
        roster_rows=roster,
        candidate_inputs=candidate_inputs,
        y4_y7_rows=y4_y7,
        y8_plus_rows=y8_plus,
        failures=failures,
    )
    payload = json.loads(path.read_text())
    assert len(digest) == 64
    assert payload["player_count"] == 2
    assert payload["success_count"] == 1
    assert payload["failure_count"] == 1
    assert [item["player_id"] for item in payload["players"]] == [success, failed]
    assert payload["players"][0]["status"] == "p0_inputs_available_career_partial"
    assert len(payload["players"][0]["y4_y7"]) == 16
    assert payload["players"][1]["failure"]["evidence_checked"] == ["provider-a", "provider-b"]
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_durable_roster_checkpoint_rejects_unaccounted_player(tmp_path):
    with pytest.raises(ValueError, match="account for every roster player"):
        MOD.write_durable_roster_checkpoint(
            tmp_path / "roster.json",
            state_hash="state-1",
            state_as_of="2026-10-08T00:00:00Z",
            evaluation_as_of="2026-10-10T00:00:00Z",
            roster_rows=[
                {"player_id": "missing", "position": "TE", "team_id": "t1",
                 "roster_slot": "TAXI", "state_hash": "state-1"}
            ],
            candidate_inputs=pd.DataFrame(),
            y4_y7_rows=pd.DataFrame(),
            y8_plus_rows=pd.DataFrame(),
            failures={},
        )



def test_durable_roster_checkpoint_rejects_candidate_identity_drift(tmp_path):
    success = "sleeper:player:9001"
    roster = [
        {"player_id": success, "position": "QB", "team_id": "t1", "roster_slot": "BENCH",
         "state_hash": "state-1"},
    ]
    with pytest.raises(ValueError, match="team_id differs from exact State"):
        MOD.write_durable_roster_checkpoint(
            tmp_path / "roster.json",
            state_hash="state-1",
            state_as_of="2026-10-08T00:00:00Z",
            evaluation_as_of="2026-10-10T00:00:00Z",
            roster_rows=roster,
            candidate_inputs=pd.DataFrame([row(team_id="stale-team")]),
            y4_y7_rows=pd.DataFrame(),
            y8_plus_rows=pd.DataFrame(),
            failures={},
        )



def test_invalid_fringe_candidate_is_failed_without_dropping_valid_roster_input():
    valid_id, invalid_id = "sleeper:player:9001", "sleeper:player:9002"
    roster = pd.DataFrame([
        {"state_hash": "state-1", "player_id": valid_id, "position": "QB", "team_id": "team-1", "roster_slot": "BENCH", "age": 24.0, "state_as_of": "2026-10-08T00:00:00Z"},
        {"state_hash": "state-1", "player_id": invalid_id, "position": "WR", "team_id": "team-2", "roster_slot": "TAXI", "age": 22.0, "state_as_of": "2026-10-08T00:00:00Z"},
    ])
    frame = pd.DataFrame([
        row(player_id=valid_id),
        row(
            player_id=invalid_id,
            position="WR",
            team_id="team-2",
            roster_slot="TAXI",
            age=22,
            experience=0,
            y2_player_league_expected_points=None,
        ),
    ])

    valid, failures = MOD.validate_candidates_per_player(frame, set(), 2026, roster)

    assert valid.player_id.tolist() == [valid_id]
    assert set(failures) == {invalid_id}
    assert failures[invalid_id]["failure_code"] == "candidate_input_invalid"
    status = MOD.build_roster_authority_status(
        roster, set(), {valid_id}, failures
    ).set_index("player_id")
    assert status.loc[valid_id, "coverage_status"] == "partial_authority"
    assert status.loc[invalid_id, "coverage_status"] == "unavailable"
    assert "invalid candidate y2_player_league_expected_points" in status.loc[
        invalid_id, "full_career_failure"
    ]
