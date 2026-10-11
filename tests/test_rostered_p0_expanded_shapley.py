from __future__ import annotations

import runpy
from pathlib import Path

from fsffl.forecast.future_contract import FutureForecastContract


ROOT = Path(__file__).parents[1]


def test_saved_p0_forecasts_convert_to_six_state_future_contract() -> None:
    helpers = runpy.run_path(
        str(ROOT / "scripts/compose_rostered_p0_expanded_shapley.py")
    )
    scenarios = [
        {"scenario_id": state, "probability": probability, "fantasy_points": points}
        for state, probability, points in (
            ("out", 0.1, 0.0),
            ("depth", 0.1, 5.0),
            ("usable", 0.2, 15.0),
            ("starter", 0.2, 40.0),
            ("premium", 0.2, 80.0),
            ("elite", 0.2, 140.0),
        )
    ]
    artifact = {
        "saved_state_hash": "state-hash",
        "evaluation_as_of": "2026-10-11T21:16:00+00:00",
        "future_forecasts": [
            {
                "player_id": "sleeper:player:90001",
                "position": "WR",
                "year_index": year_index,
                "target_season": 2026 + year_index - 1,
                "central_expectation": sum(
                    row["probability"] * row["fantasy_points"]
                    for row in scenarios
                ),
                "scoring_coordinate": "connected_league_fantasy_points",
                "model_version": "fixture-p0-v1",
                "source": "fixture:approved-p0",
                "scenarios": scenarios,
            }
            for year_index in (2, 3)
        ],
    }

    rows = helpers["_candidate_future_rows"](artifact)
    contract = FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate="connected_league_fantasy_points",
        forecast_model_version="fixture",
        forecast_source="fixture",
        forecasts=tuple(rows),
    )

    assert len(contract.forecasts) == 2
    for forecast, year_index in zip(contract.forecasts, (2, 3), strict=True):
        assert forecast.player_id == "sleeper:player:90001"
        assert forecast.year_index == year_index
        assert [row.scenario_id for row in forecast.scenarios] == [
            "out", "depth", "usable", "starter", "premium", "elite"
        ]
        assert abs(
            sum(row.probability * row.fantasy_points for row in forecast.scenarios)
            - forecast.central_expectation
        ) <= 1e-9


def test_candidate_forecast_conversion_rejects_missing_state() -> None:
    helpers = runpy.run_path(
        str(ROOT / "scripts/compose_rostered_p0_expanded_shapley.py")
    )
    artifact = {
        "saved_state_hash": "state-hash",
        "evaluation_as_of": "2026-10-11T21:16:00+00:00",
        "future_forecasts": [{
            "player_id": "sleeper:player:90001",
            "position": "WR",
            "year_index": 2,
            "target_season": 2027,
            "central_expectation": 10.0,
            "scoring_coordinate": "connected_league_fantasy_points",
            "model_version": "fixture-p0-v1",
            "source": "fixture:approved-p0",
            "scenarios": [{
                "scenario_id": "out",
                "probability": 1.0,
                "fantasy_points": 10.0,
            }],
        }],
    }

    try:
        helpers["_candidate_future_rows"](artifact)
    except ValueError as exc:
        assert "state geometry mismatch" in str(exc)
    else:
        raise AssertionError("incomplete six-state forecast must fail closed")
