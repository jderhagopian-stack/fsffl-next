from __future__ import annotations

import base64
import io
import json
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from scripts.run_career_405_roster_runner import (
    decode_private_input,
    encrypt_result,
    to_composer_artifact,
    validate_exact_roster,
)


STATE_ID = "state-exact-fixture"
STATE_TIME = datetime(2026, 10, 8, 16, 20, 14, tzinfo=timezone.utc)
PLAYER_ID = "sleeper:player:rostered-fixture"


def _state():
    player = SimpleNamespace(player_id=PLAYER_ID, position=SimpleNamespace(value="QB"))
    entry = SimpleNamespace(player_id=PLAYER_ID, slot=SimpleNamespace(value="BENCH"))
    team = SimpleNamespace(team_id="team-fixture", roster=(entry,))
    return SimpleNamespace(
        state_id=STATE_ID,
        as_of=STATE_TIME,
        players=(player,),
        team_states=(team,),
    )


def _checkpoint():
    states = ("out", "depth", "usable", "starter", "premium", "elite")
    packets = {}
    for year in (2, 3):
        packets[f"Y{year}"] = {
            "player_id": PLAYER_ID,
            "position": "QB",
            "year_index": year,
            "target_season": 2026 + year - 1,
            "central_expectation": 2.5,
            "scoring_coordinate": "connected_league_fantasy_points",
            "model_version": "fixture-model",
            "source": "accepted-fixture",
            "probabilities": {name: 1 / 6 for name in states},
            "conditional_means": {name: float(index) for index, name in enumerate(states)},
        }
    success = {
        "player_id": PLAYER_ID,
        "position": "QB",
        "team_id": "team-fixture",
        "roster_slot": "BENCH",
        "state_hash": STATE_ID,
        "p0_input": {
            "league_y1_points": 15.0,
            "p0_canonical_packets": packets,
        },
    }
    failure_id = "sleeper:player:unsupported-fixture"
    failure = {
        "player_id": failure_id,
        "position": "WR",
        "team_id": "team-fixture",
        "roster_slot": "TAXI",
        "state_hash": STATE_ID,
        "status": "p0_failure",
        "failure": {
            "failure_code": "source_evidence_missing",
            "failure_detail": "fixture missing evidence",
            "evidence_checked": ["existing-approved-source"],
            "provenance": {"source": "fixture"},
        },
    }
    # Add the explicit-failure identity to the fixture State.
    failure_player = SimpleNamespace(player_id=failure_id, position=SimpleNamespace(value="WR"))
    failure_entry = SimpleNamespace(player_id=failure_id, slot=SimpleNamespace(value="TAXI"))
    state = _state()
    state.players = (*state.players, failure_player)
    state.team_states = (SimpleNamespace(
        team_id="team-fixture", roster=(*state.team_states[0].roster, failure_entry)
    ),)
    return {
        "schema_version": "fsffl-career-roster-p0-checkpoint-v1",
        "state_hash": STATE_ID,
        "state_as_of": STATE_TIME.isoformat(),
        "evaluation_as_of": "2026-10-11T21:16:00+00:00",
        "players": [success, failure],
    }, state


def test_exact_state_roster_guard_and_per_player_composer_conversion():
    artifact, state = _checkpoint()
    exact = validate_exact_roster(artifact, state)
    converted = to_composer_artifact(artifact, exact)

    assert set(converted["candidate_ids"]) == set(exact)
    assert set(converted["candidate_source_rows"]) == {PLAYER_ID}
    assert len(converted["future_forecasts"]) == 2
    assert [len(row["scenarios"]) for row in converted["future_forecasts"]] == [6, 6]
    assert converted["failures"]["sleeper:player:unsupported-fixture"]["failure_code"] == "source_evidence_missing"


def test_runner_rejects_state_mismatch_and_outside_roster_player():
    artifact, state = _checkpoint()
    artifact["state_hash"] = "another-state"
    with pytest.raises(ValueError, match="State hash differs"):
        validate_exact_roster(artifact, state)

    artifact, state = _checkpoint()
    artifact["players"][0]["player_id"] = "sleeper:player:not-rostered"
    with pytest.raises(ValueError, match="outside the latest State roster"):
        validate_exact_roster(artifact, state)


def test_private_input_zip_is_bounded_and_has_one_json_file():
    artifact, _ = _checkpoint()
    payload = json.dumps(artifact).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("roster.json", payload)
    decoded, raw = decode_private_input(base64.b64encode(buffer.getvalue()).decode())
    assert decoded["state_hash"] == STATE_ID
    assert raw == payload

    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("../escape.json", payload)
    with pytest.raises(ValueError, match="directory paths"):
        decode_private_input(base64.b64encode(bad.getvalue()).decode())


def test_output_is_authenticated_ciphertext_and_never_plaintext():
    pytest.importorskip("cryptography")
    plaintext = b'{"career":"private fixture"}'
    encrypted = encrypt_result(plaintext, "a-long-random-test-passphrase-405")
    assert encrypted.startswith(b"C405AESGCM1")
    assert plaintext not in encrypted
    with pytest.raises(ValueError, match="at least 20"):
        encrypt_result(plaintext, "too-short")
