import csv
from pathlib import Path

from scripts.replay_historical_shapley_hindsight import example_rules, replay_observed_three_year


def test_historical_hindsight_replay_reports_censoring(tmp_path: Path):
    path = tmp_path / "hindsight.csv"
    with path.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=[
            "evaluation_season", "player_id", "season", "position",
            "recorded_fantasy_points", "data_role"])
        writer.writeheader()
        for year, present in [(2003, ["a","b"]), (2004, ["a"]), (2005, ["a"])]:
            for player_id in present:
                writer.writerow({
                    "evaluation_season": 2003, "player_id": player_id, "season": year,
                    "position": "QB" if player_id == "a" else "RB",
                    "recorded_fantasy_points": 100 if player_id == "a" else 40,
                    "data_role": "hindsight_observed_outcome_not_forecast",
                })
    result = replay_observed_three_year(
        path, seasons=(2003,), rules=example_rules(), permutations=8)
    assert result[0]["status"] == "complete_observed_cohort_shapley"
    assert result[0]["horizon"] == 1
    assert result[1]["status"] == "partial_hindsight_outcomes_not_authorized_for_full_shapley"
    assert result[1]["missing_player_count"] == 1
    assert "max_raw_annual_shapley" not in result[1]
