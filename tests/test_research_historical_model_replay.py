"""Synthetic-only regression tests for the archived simulation research reader."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research_historical_model_replay import (
    ReplayValidationError,
    recover_archived_preseason_simulation,
)


CUT = "2026-09-10T00:20:00Z"
LEAGUE = "sleeper:example"


def fixture():
    warnings = [{"code": "weekly_mean_decomposition_provisional"}]
    teams = []
    for idx in [1, 2]:
        tid = f"{LEAGUE}:team:{idx}"
        forecast = {"as_of": "2026-09-09T23:00:00Z", "provenance": {
            "effective_at": "2026-09-08T12:00:00Z", "retrieved_at": "2026-09-09T23:00:00Z"}}
        teams.append({"team_id": tid, "context": {"as_of": "2026-09-09T23:00:00Z", "warnings": warnings},
                      "players": [{"player_id": f"player:{idx}", "forecasts": [forecast]}],
                      "draft_picks": [{"pick": {"pick_id": f"pick:{idx}"}}]})
    payload = {
        "simulation_result": {"simulation_count": 100, "seed": 42, "model_version": "accepted-foo",
                              "outcomes": [
                                  {"team_id": teams[0]["team_id"], "simulation_count": 100, "expected_wins": 0.6,
                                   "playoff_probability": 0.75, "championship_probability": 0.6, "first_place_probability": 0.6},
                                  {"team_id": teams[1]["team_id"], "simulation_count": 100, "expected_wins": 0.4,
                                   "playoff_probability": 0.25, "championship_probability": 0.4, "first_place_probability": 0.4},
                              ]},
        "league_view": {"context": {"as_of": "2026-09-09T23:00:00Z"}, "teams": [
            {"team_id": t["team_id"], "display_name": "provider username",
             "optimized_expected_points": 80, "player_count": 1, "draft_pick_count": 1} for t in teams]},
        "team_views": teams,
    }
    artifact = {"id": 1, "artifact_kind": "live_simulation_analytics", "computed_at": "2026-09-09T23:05:00Z",
                "scope_id": "state-sha", "input_fingerprint": "inputs-sha",
                "model_version": "sim-publication-v1", "payload": payload}
    anchor = {"team_states": [
        {"team_id": t["team_id"], "roster": [{"player_id": f"player:{i}"}]}
        for i, t in enumerate(teams, start=1)],
        "pick_ownership": [{"pick_id": f"pick:{i}", "owner_team_id": t["team_id"]}
                           for i, t in enumerate(teams, start=1)]}
    return artifact, anchor


class TestHistoricalReplay(unittest.TestCase):
    def test_recovered_vintage_with_anchor(self):
        artifact, anchor = fixture()
        got = recover_archived_preseason_simulation(artifact, cutoff_iso=CUT,
            expected_league_id=LEAGUE, retrospective_anchor=anchor,
            expected_wins_total=1, expected_playoff_berths=1)
        self.assertEqual(got["status"], "original_historical_simulation_recovered_not_rerun")
        self.assertEqual(got["checks"]["forecast_records_checked"], 2)
        self.assertEqual(got["checks"]["anchor"]["status"], "exact_membership_match")
        self.assertEqual(got["teams"][0]["expected_wins"], 0.6)

    def test_artifact_after_cutoff_is_blocked(self):
        a, _ = fixture()
        a["computed_at"] = "2026-09-10T01:00:00Z"
        with self.assertRaisesRegex(ReplayValidationError, "future-information leak"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_source_forecast_after_cutoff_is_blocked(self):
        a, _ = fixture()
        a["payload"]["team_views"][0]["players"][0]["forecasts"][0]["provenance"]["retrieved_at"] = "2026-09-10T01:00:00Z"
        with self.assertRaisesRegex(ReplayValidationError, "future-information leak"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_missing_provenance_is_blocked(self):
        a, _ = fixture()
        a["payload"]["team_views"][0]["players"][0]["forecasts"][0]["provenance"].pop("effective_at")
        with self.assertRaisesRegex(ReplayValidationError, "missing timestamp"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_duplicate_roster_player_is_blocked(self):
        a, _ = fixture()
        a["payload"]["team_views"][1]["players"][0]["player_id"] = "player:1"
        with self.assertRaisesRegex(ReplayValidationError, "duplicate player"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_anchor_conflict_is_blocked(self):
        a, anchor = fixture()
        anchor["team_states"][1]["roster"][0]["player_id"] = "player:1"
        with self.assertRaisesRegex(ReplayValidationError, "duplicate anchor"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT, retrospective_anchor=anchor)

    def test_probability_mass_is_checked(self):
        a, _ = fixture()
        a["payload"]["simulation_result"]["outcomes"][1]["championship_probability"] = 0.2
        with self.assertRaisesRegex(ReplayValidationError, "mass does not sum"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_win_sum_is_checked(self):
        a, _ = fixture()
        with self.assertRaisesRegex(ReplayValidationError, "win-sum invariant"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT, expected_wins_total=8)

    def test_no_forecasts_is_blocked(self):
        a, _ = fixture()
        for t in a["payload"]["team_views"]:
            t["players"][0]["forecasts"] = []
        with self.assertRaisesRegex(ReplayValidationError, "missing archived forecast"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT)

    def test_league_mismatch_is_blocked(self):
        a, _ = fixture()
        with self.assertRaisesRegex(ReplayValidationError, "unexpected league"):
            recover_archived_preseason_simulation(a, cutoff_iso=CUT, expected_league_id="sleeper:wrong")

    def test_missing_anchor_does_not_claim_full_reconstruction(self):
        a, _ = fixture()
        result = recover_archived_preseason_simulation(a, cutoff_iso=CUT)
        self.assertEqual(result["checks"]["anchor"]["status"], "not_checked")


if __name__ == "__main__":
    unittest.main()
