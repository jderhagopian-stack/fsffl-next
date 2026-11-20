"""Synthetic admission regressions; never commit private FSFFL league data."""
from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research_modern_preseason_replay import (
    REQUIRED_MODEL_RECEIPTS,
    REQUIRED_STATE_RECEIPTS,
    RUN_KIND,
    admit_historical_modern_simulation,
)

CUTOFF = "2026-09-10T00:20:00Z"
EVIDENCE_AT = "2026-09-09T19:00:00Z"
MODEL_SHA = "2eaa9fb6526fad607ee12b59e8319743f8fda61e"


def sample():
    return {
        "run_kind": RUN_KIND,
        "cutoff": CUTOFF,
        "model_git_sha": MODEL_SHA,
        "historical_state": {
            "league": {"league_id": "sleeper:example", "season": 2026},
            "as_of": EVIDENCE_AT, "completed_through_week": None,
            "matchups": [{"week": 1, "team_a_id": "t1", "team_b_id": "t2",
                          "team_a_points": None, "team_b_points": None}],
            "nfl_team_byes": [{"season": 2026, "nfl_team": "SEA", "week": 8}],
            "teams": [{"team_id": "t1"}, {"team_id": "t2"}],
            "team_states": [{"team_id": "t1"}, {"team_id": "t2"}],
            "players": [{"player_id": "p1"}], "player_states": [{"player_id": "p1"}],
            "draft_picks": [{"pick_id": "pk1"}],
            "pick_ownership": [{"pick_id": "pk1"}],
        },
        "historical_forecasts": [
            {
                "player_id": "p1", "horizon": "season", "metric": "fantasy_points",
                "period_start": "2026-09-01T00:00:00Z", "period_end": "2027-03-01T00:00:00Z",
                "as_of": EVIDENCE_AT,
                "provenance": {"effective_at": EVIDENCE_AT, "retrieved_at": EVIDENCE_AT},
            },
        ],
        "state_receipts": [
            {"role": role, "source_id": "historical-provider-evidence",
             "source_sha256": "a" * 64, "authority": "independently_reconstructed",
             "effective_at": EVIDENCE_AT, "available_at": EVIDENCE_AT}
            for role in sorted(REQUIRED_STATE_RECEIPTS)
        ],
        "model_receipts": [
            {"role": role, "source_id": "governed-model-reference",
             "source_sha256": "b" * 64, "model_version": "version-1",
             "training_through": "2025-12-31T00:00:00Z"}
            for role in sorted(REQUIRED_MODEL_RECEIPTS)
        ],
    }


def blockers(sample_data):
    return admit_historical_modern_simulation(sample_data)["blockers"]


def test_eligible_inputs_do_not_automatically_approve_publication():
    result = admit_historical_modern_simulation(sample())
    assert result["eligible_to_run"]
    assert result["eligible_to_publish"] is False
    assert not result["blockers"]


def test_later_capture_is_not_a_preseason_state():
    x = sample()
    x["historical_state"]["as_of"] = "2026-09-10T12:44:36Z"
    assert "later than historical cutoff" in " ".join(blockers(x))


def test_no_post_kickoff_points_even_if_week_not_complete():
    x = sample()
    x["historical_state"]["matchups"][0]["team_a_points"] = 6.7
    assert "scored/post-kickoff" in " ".join(blockers(x))


def test_missing_bye_evidence_blocks():
    x = sample()
    x["historical_state"]["nfl_team_byes"] = []
    assert "bye evidence" in " ".join(blockers(x))


def test_retrospective_ownership_alone_cannot_be_input():
    x = sample()
    x["state_receipts"][0]["source_only_from_later_snapshot"] = True
    assert "later retrospective" in " ".join(blockers(x))


def test_model_trained_on_inseason_results_blocks():
    x = sample()
    x["model_receipts"][0]["training_through"] = "2026-11-01T00:00:00Z"
    assert "training_through: later" in " ".join(blockers(x))


def test_model_release_after_cutoff_is_allowed_if_training_frozen():
    x = sample()
    x["model_receipts"][0]["code_release_at"] = "2026-11-20T00:00:00Z"
    assert admit_historical_modern_simulation(x)["eligible_to_run"]


def test_missing_model_receipt_blocks():
    x = sample()
    x["model_receipts"].pop()
    assert "missing model receipt" in " ".join(blockers(x))


def test_later_forecast_source_retrieval_blocks():
    x = sample()
    x["historical_forecasts"][0]["provenance"]["retrieved_at"] = "2026-10-01T00:00:00Z"
    assert "later than historical cutoff" in " ".join(blockers(x))


def test_duplicate_forecast_subject_blocks():
    x = sample()
    x["historical_forecasts"].append(deepcopy(x["historical_forecasts"][0]))
    assert "duplicate canonical" in " ".join(blockers(x))


def test_current_ros_not_relabelled_preseason():
    x = sample()
    x["historical_forecasts"][0]["horizon"] = "rest_of_season"
    assert "requires season" in " ".join(blockers(x))


def test_no_fabricated_state_from_missing_input():
    x = sample()
    x.pop("historical_state")
    assert "historical_state missing" in " ".join(blockers(x))


def test_scored_zero_also_forbidden_without_preseason_receipt():
    x = sample()
    x["historical_state"]["matchups"][0]["team_a_points"] = 0
    x["historical_state"]["matchups"][0]["team_b_points"] = 0
    assert "scored/post-kickoff" in " ".join(blockers(x))


def test_invalid_code_sha_blocks():
    x = sample()
    x["model_git_sha"] = "main"
    assert "exact 40-hex" in " ".join(blockers(x))
