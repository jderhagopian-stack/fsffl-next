from __future__ import annotations

import csv
import importlib.util
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from types import SimpleNamespace

from fsffl.product.foundation4_dynamic_candidate_runtime import (
    _accepted_materializer_manifest,
    _candidate_rows,
    _write_candidate_failures,
)
from fsffl.product.foundation4_accepted_bundle import (
    _COMMIT as ACCEPTED_BUNDLE_COMMIT,
    _PATHS as ACCEPTED_BUNDLE_PATHS,
    _file_sha256,
)

FILE = Path(__file__).parents[1] / "scripts/materialize_foundation4_dynamic_candidates.py"
SPEC = importlib.util.spec_from_file_location("career_dynamic", FILE)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def _write_accepted_mount(root: Path) -> tuple[dict[str, object], Path]:
    payload: dict[str, object] = {
        "accepted_commit": ACCEPTED_BUNDLE_COMMIT,
        "files": {},
        "sha256": {},
    }
    files = payload["files"]
    digests = payload["sha256"]
    assert isinstance(files, dict) and isinstance(digests, dict)
    for key, relative in ACCEPTED_BUNDLE_PATHS.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"accepted fixture {key}".encode())
        resolved = path.resolve()
        digest = _file_sha256(resolved)
        files[key] = str(resolved)
        digests[key] = digest
        payload[key] = str(resolved)
    manifest_path = root / "foundation4_dynamic_materializer_manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload, manifest_path


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


def test_raw_history_reader_limits_columns_to_accepted_feature_contract(tmp_path):
    required = {
        "player_id": ["gsis-1"], "season": [2025], "position": ["QB"],
        "team": ["TST"], "fantasy_points": [10.0], "fantasy_points_ppr": [10.0],
        "receptions": [0], "passing_interceptions": [0], "sack_fumbles_lost": [0],
        "rushing_fumbles_lost": [0], "receiving_fumbles_lost": [0],
    }
    source = tmp_path / "wide-history.csv"
    pd.DataFrame({**required, "unconsumed_column": ["unused"]}).to_csv(source, index=False)
    frame = MOD.read_raw_history(source)
    assert "unconsumed_column" not in frame
    assert set(required).issubset(frame.columns)


def test_raw_history_reader_fails_closed_when_scoring_evidence_missing(tmp_path):
    source = tmp_path / "incomplete-history.csv"
    pd.DataFrame({"player_id": ["gsis-1"], "season": [2025]}).to_csv(source, index=False)
    with pytest.raises(ValueError, match="raw scoring evidence missing required columns"):
        MOD.read_raw_history(source)


def test_route_label_compaction_preserves_model_category_values():
    class Dev:
        CATEGORICAL = ("trajectory_state",)

    frame = pd.DataFrame({
        "position": ["QB", "WR"] * 100,
        "trajectory_state": ["stable", None] * 100,
        "actual": [1.0, 2.0] * 100,
    })
    compact = MOD.compact_history_categories(frame, Dev())
    assert compact.position.astype(str).tolist() == frame.position.astype(str).tolist()
    assert (
        compact.trajectory_state.fillna("MISSING").astype(str).tolist()
        == frame.trajectory_state.fillna("MISSING").astype(str).tolist()
    )
    assert compact.memory_usage(index=True, deep=True).sum() < frame.memory_usage(
        index=True, deep=True
    ).sum()


def test_invalid_fringe_candidate_is_failed_without_dropping_valid_roster_input():
    valid_id, invalid_id = "sleeper:player:9001", "sleeper:player:9002"
    roster = pd.DataFrame([
        {"state_hash":"state-1", "player_id":valid_id, "position":"QB", "team_id":"team-1", "roster_slot":"BENCH", "age":24.0, "state_as_of":"2026-10-08T00:00:00Z"},
        {"state_hash":"state-1", "player_id":invalid_id, "position":"WR", "team_id":"team-2", "roster_slot":"TAXI", "age":22.0, "state_as_of":"2026-10-08T00:00:00Z"},
    ])
    frame = pd.DataFrame([
        row(player_id=valid_id),
        row(player_id=invalid_id, position="WR", team_id="team-2", roster_slot="TAXI", age=22, experience=0, y2_player_league_expected_points=None),
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
    assert "invalid candidate y2_player_league_expected_points" in status.loc[invalid_id, "full_career_failure"]


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


def test_slim_frozen_reference_coordinates_match_accepted_current_transform():
    positions = ["QB", "RB", "WR", "TE"]
    board = pd.DataFrame({
        "player_id": [f"reference-{index}" for index in range(335)],
        "position": [positions[index % len(positions)] for index in range(335)],
        "league_y1_points": [None if index == 0 else (-2 if index == 1 else index)
                             for index in range(335)],
        "historical_gsis_id": [""] * 335,
        "age": [24.0] * 335,
        "experience": [2.0] * 335,
        "y2_player_league_expected_points": [20.0] * 335,
        "y3_player_league_expected_points": [30.0] * 335,
    })

    class Dev:
        @staticmethod
        def merge_lags(frame, _raw): return frame.copy()
        @staticmethod
        def add_engineered_features(frame, _players): return frame.copy()
        @staticmethod
        def merge_trajectory(frame, _residual, _innovation): return frame.copy()

    source_file = FILE.with_name("materialize_foundation4_fsffl_coordinate.py")
    source_spec = importlib.util.spec_from_file_location("foundation4_coordinate_test", source_file)
    assert source_spec and source_spec.loader
    source = importlib.util.module_from_spec(source_spec)
    source_spec.loader.exec_module(source)
    accepted = source.build_current(
        Dev(), board, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    )
    slim = MOD.frozen_current_reference_coordinates(board)

    pd.testing.assert_frame_equal(
        slim.reset_index(drop=True),
        accepted.loc[:, ["output_player_id", "position", "y1"]].reset_index(drop=True),
    )


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


def test_dynamic_materializer_input_failure_isolated_to_missing_future_player():
    good, missing = "sleeper:player:9001", "sleeper:player:9002"
    state = SimpleNamespace(
        state_id="state-1",
        as_of=pd.Timestamp("2026-10-08T00:00:00Z").to_pydatetime(),
        players=[
            SimpleNamespace(player_id=good, position=SimpleNamespace(value="QB")),
            SimpleNamespace(player_id=missing, position=SimpleNamespace(value="WR")),
        ],
        player_states=[
            SimpleNamespace(player_id=good, age_years=24.0),
            SimpleNamespace(player_id=missing, age_years=22.0),
        ],
        team_states=[
            SimpleNamespace(team_id="t1", roster=[SimpleNamespace(player_id=good, slot=SimpleNamespace(value="BENCH"))]),
            SimpleNamespace(team_id="t2", roster=[SimpleNamespace(player_id=missing, slot=SimpleNamespace(value="TAXI"))]),
        ],
    )
    future_rows = {
        (good, 2): SimpleNamespace(central_expectation=30.0),
        (good, 3): SimpleNamespace(central_expectation=35.0),
    }
    live = SimpleNamespace(
        future=SimpleNamespace(contract=SimpleNamespace(
            forecast_model_version="accepted-v1",
            scoring_coordinate="connected_league_fantasy_points",
        )),
        candidate_source_rows={
            player_id: SimpleNamespace(
                historical_gsis_id=None,
                experience=1,
                connected_league_y1_points=20.0,
            )
            for player_id in (good, missing)
        },
        evaluation_as_of=pd.Timestamp("2026-10-10T00:00:00Z").to_pydatetime(),
    )
    rows, failures = _candidate_rows(
        SimpleNamespace(league_state=state), live, (good, missing), future_rows
    )
    assert [row["player_id"] for row in rows] == [good]
    assert failures == {
        missing: "dynamic candidate inputs invalid: ValueError: accepted P0 Y2/Y3 FutureForecastContract rows missing"
    }


def test_hosted_materializer_resolves_manifest_from_mounted_bundle_root(tmp_path, monkeypatch):
    manifest, manifest_path = _write_accepted_mount(tmp_path)
    monkeypatch.delenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_MANIFEST", raising=False)
    monkeypatch.setenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_ROOT", str(tmp_path))
    loaded, path = _accepted_materializer_manifest()
    assert loaded == manifest
    assert path == manifest_path


def test_hosted_materializer_rejects_modified_mounted_input(tmp_path, monkeypatch):
    _, manifest_path = _write_accepted_mount(tmp_path)
    (tmp_path / ACCEPTED_BUNDLE_PATHS["model-a-rows"]).write_text(
        "modified after manifest creation", encoding="utf-8"
    )
    monkeypatch.setenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_MANIFEST", str(manifest_path))
    monkeypatch.delenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_ROOT", raising=False)
    with pytest.raises(ValueError, match="accepted-commit and per-file SHA256 verification"):
        _accepted_materializer_manifest()


def test_hosted_materializer_rejects_unconfigured_bundle(monkeypatch):
    monkeypatch.delenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_MANIFEST", raising=False)
    monkeypatch.delenv("FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_ROOT", raising=False)
    with pytest.raises(ValueError, match="accepted Foundation 4 materializer bundle is not configured"):
        _accepted_materializer_manifest()


def test_hosted_materializer_checkpoint_receives_explicit_candidate_failures(tmp_path):
    live = SimpleNamespace(
        evaluation_as_of=pd.Timestamp("2026-10-11T14:12:26.851497Z").to_pydatetime(),
        future=SimpleNamespace(contract=SimpleNamespace(
            forecast_model_version="accepted-p0-v1",
            scoring_coordinate="connected_league_fantasy_points",
        )),
        failures={"sleeper:player:9002": "accepted Y1 raw metrics incomplete"},
    )
    target = tmp_path / "candidate-failures.csv"
    _write_candidate_failures(
        target, {}, live
    )
    failure = next(csv.DictReader(target.open(encoding="utf-8")))
    assert failure["failure_detail"] == "accepted Y1 raw metrics incomplete"
    assert json.loads(failure["evidence_checked"]) == [
        "accepted_p0_year1", "accepted_p0_y2_y3", "exact_state_roster"
    ]
    assert json.loads(failure["provenance"])["future_forecast_model_version"] == "accepted-p0-v1"



def test_durable_roster_checkpoint_atomically_accounts_for_success_and_failure(tmp_path):
    success = "sleeper:player:9001"
    failed = "sleeper:player:9002"
    roster = [
        {"player_id": success, "position": "QB", "team_id": "t1", "roster_slot": "BENCH",
         "state_hash": "state-1", "state_as_of": "2026-10-08T00:00:00.036832Z"},
        {"player_id": failed, "position": "RB", "team_id": "t2", "roster_slot": "IR",
         "state_hash": "state-1", "state_as_of": "2026-10-08T00:00:00.036832Z"},
    ]
    candidate_inputs = pd.DataFrame([row(
        team_id="t1", state_as_of="2026-10-08T00:00:00.036832Z"
    )])
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
        state_as_of="2026-10-08T00:00:00.036832Z",
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
