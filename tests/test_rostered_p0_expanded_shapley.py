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



def test_year_one_full_season_and_future_inputs_fail_per_player():
    from datetime import datetime, timezone
    from fsffl.forecast.models import ForecastHorizon

    helpers = runpy.run_path(
        str(ROOT / "scripts/compose_rostered_p0_expanded_shapley.py")
    )
    as_of = datetime(2026, 10, 12, tzinfo=timezone.utc)
    good = helpers["_make_observation"](
        player_id="sleeper:player:good",
        position="RB",
        points=88.5,
        as_of=as_of,
        source="fsffl:completed-actuals-plus-ros",
        model_version="next2-completed-actuals-plus-ros-v1",
    )
    wrong_horizon = helpers["_make_observation"](
        player_id="sleeper:player:bad-y1",
        position="WR",
        points=24.0,
        as_of=as_of,
        source="fsffl:completed-actuals-plus-ros",
        model_version="next2-completed-actuals-plus-ros-v1",
    ).model_copy(update={"horizon": ForecastHorizon.REST_OF_SEASON})
    wrong_source = helpers["_make_observation"](
        player_id="sleeper:player:bad-source",
        position="TE",
        points=40.0,
        as_of=as_of,
        source="provider:uncomposed-ros",
        model_version="fixture-v1",
    )
    year_one, failures = helpers["_candidate_year_one_index"](
        (good, wrong_horizon, wrong_source),
        candidate_ids={"sleeper:player:good", "sleeper:player:bad-y1", "sleeper:player:bad-source", "sleeper:player:missing"},
        expected_positions={
            "sleeper:player:good": "RB",
            "sleeper:player:bad-y1": "WR",
            "sleeper:player:bad-source": "TE",
            "sleeper:player:missing": "TE",
        },
    )
    assert set(year_one) == {"sleeper:player:good"}
    assert year_one["sleeper:player:good"].distribution.mean == 88.5
    assert failures["sleeper:player:bad-y1"] == "year_one_input_is_not_full_season"
    assert failures["sleeper:player:bad-source"] == "year_one_input_not_governed_actuals_plus_ros"
    assert failures["sleeper:player:missing"] == "full_season_year_one_input_missing"

    states = [
        {"scenario_id": state, "probability": probability, "fantasy_points": points}
        for state, probability, points in (
            ("out", 0.1, 0.0), ("depth", 0.1, 5.0), ("usable", 0.2, 15.0),
            ("starter", 0.2, 40.0), ("premium", 0.2, 80.0), ("elite", 0.2, 140.0),
        )
    ]
    future = []
    for player_id in ("sleeper:player:good", "sleeper:player:bad-future"):
        for year_index in (2, 3):
            future.append({
                "player_id": player_id,
                "position": "RB",
                "year_index": year_index,
                "target_season": 2026 + year_index - 1,
                "central_expectation": 50.0,
                "scoring_coordinate": "connected_league_fantasy_points",
                "model_version": "fixture-p0-v1",
                "source": "fixture:accepted-p0",
                "scenarios": states if player_id == "sleeper:player:good" else states[:1],
            })
    valid_future, future_failures = helpers["_candidate_future_rows_per_player"](
        {"saved_state_hash": "state-hash", "evaluation_as_of": as_of.isoformat(), "future_forecasts": future},
        candidate_ids={"sleeper:player:good", "sleeper:player:bad-future", "sleeper:player:no-future"},
    )
    assert {row.player_id for row in valid_future} == {"sleeper:player:good"}
    assert future_failures["sleeper:player:bad-future"].startswith("ValueError: state geometry mismatch")
    assert future_failures["sleeper:player:no-future"] == "accepted_future_years_y2_y3_missing_or_duplicated"



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
