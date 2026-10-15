import json
import os

import pytest

from fsffl.product.rostered_career_journal import (
    append_verified_rostered_career_records,
)


def test_private_journal_persists_exact_state_result_and_failure_per_roster_player(tmp_path):
    state_hash = "state-current-verified"
    roster = [
        {"player_id": "sleeper:player:new-44", "position": "WR", "team_id": "t1",
         "roster_slot": "IR", "state_hash": state_hash},
        {"player_id": "sleeper:player:gap-77", "position": "QB", "team_id": "t2",
         "roster_slot": "BENCH", "state_hash": state_hash},
    ]
    state_players = [
        {"player_id": "sleeper:player:new-44", "position": "WR"},
        {"player_id": "sleeper:player:gap-77", "position": "QB"},
    ]
    records = {
        "sleeper:player:new-44": {
            "player_id": "sleeper:player:new-44",
            "state_hash": state_hash,
            "evaluation_as_of": "2026-10-11T20:00:00+00:00",
            "provenance": {"adapter": "approved-p0-449", "input_sha256": "abc123"},
            "career_result": {"raw_career_forward_reference": 82.5},
        },
        "sleeper:player:gap-77": {
            "player_id": "sleeper:player:gap-77",
            "state_hash": state_hash,
            "evaluation_as_of": "2026-10-11T20:00:00Z",
            "provenance": {"adapter": "approved-p0-449", "sources_checked": ["Sleeper", "CBS", "Razzball"]},
            "evidence_failure": {"reason": "complete_year_one_packet_unavailable",
                                 "missing_input": "canonical P0 Year-1 fantasy-points packet"},
        },
    }
    journal = tmp_path / "private" / "rostered.jsonl"
    rows = append_verified_rostered_career_records(
        journal_path=journal,
        state_hash=state_hash,
        roster_rows=roster,
        state_players=state_players,
        records_by_player=records,
    )
    saved = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [row["player_id"] for row in saved] == [
        "sleeper:player:gap-77", "sleeper:player:new-44",
    ]
    assert [row["status"] for row in saved] == ["evidence_failure", "complete"]
    assert all(row["state_hash"] == state_hash and row["artifact_digest"] for row in saved)
    assert saved[0]["evidence_failure"]["missing_input"].startswith("canonical P0")
    assert saved[1]["career_result"]["raw_career_forward_reference"] == 82.5
    assert len(rows) == 2
    assert os.stat(journal).st_mode & 0o777 == 0o600


def test_journal_rejects_provider_identity_outside_current_roster(tmp_path):
    with pytest.raises(ValueError, match="nonrostered identities"):
        append_verified_rostered_career_records(
            journal_path=tmp_path / "private.jsonl",
            state_hash="state-1",
            roster_rows=[{"player_id": "p1", "position": "TE", "state_hash": "state-1"}],
            state_players=[{"player_id": "p1", "position": "TE"}],
            records_by_player={"p-outside": {"player_id": "p-outside"}},
        )
    assert not (tmp_path / "private.jsonl").exists()


def test_journal_rejects_state_identity_or_metric_gaps_instead_of_filling(tmp_path):
    base = {
        "player_id": "p1", "state_hash": "state-1",
        "evaluation_as_of": "2026-10-11T20:00:00Z",
        "provenance": {"adapter": "approved-p0-449"},
        "career_result": {},
    }
    with pytest.raises(ValueError, match="Career result is empty"):
        append_verified_rostered_career_records(
            journal_path=tmp_path / "empty.jsonl",
            state_hash="state-1",
            roster_rows=[{"player_id": "p1", "position": "RB", "state_hash": "state-1"}],
            state_players=[{"player_id": "p1", "position": "RB"}],
            records_by_player={"p1": base},
        )
    wrong_state = {**base, "state_hash": "state-old"}
    with pytest.raises(ValueError, match="another State"):
        append_verified_rostered_career_records(
            journal_path=tmp_path / "wrong-state.jsonl",
            state_hash="state-1",
            roster_rows=[{"player_id": "p1", "position": "RB", "state_hash": "state-1"}],
            state_players=[{"player_id": "p1", "position": "RB"}],
            records_by_player={"p1": wrong_state},
        )
