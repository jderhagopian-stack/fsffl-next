from __future__ import annotations

import csv
from pathlib import Path

import pytest

from fsffl.product.selected_future_forecast import (
    SELECTED_FUTURE_FORECAST_PACKAGE_SHA256,
    SELECTED_FUTURE_FORECAST_SOURCE_SHA256,
    SELECTED_FUTURE_FORECAST_VERSION,
    SelectedFutureForecast,
    selected_future_source_player_ids,
)

BOARD = Path(
    "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/"
    "CORRECTED_P0_PRESEASON_BOARD_335.csv"
)


def test_selected_future_forecast_embeds_exact_frozen_authority() -> None:
    assert SELECTED_FUTURE_FORECAST_PACKAGE_SHA256 == (
        "ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7"
    )
    assert SELECTED_FUTURE_FORECAST_SOURCE_SHA256 == (
        "eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a"
    )
    assert len(selected_future_source_player_ids()) == 335


def test_selected_future_forecast_replays_corrected_p0_board_exactly() -> None:
    forecast = SelectedFutureForecast()
    with BOARD.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 335

    max_probability_error = 0.0
    max_mean_error = 0.0
    max_expected_error = 0.0
    route_mismatches = 0

    for row in rows:
        player_id = row["current_player_id"]
        for horizon in (2, 3):
            result = forecast.predict(player_id, horizon)
            route = row[f"y{horizon}_candidate"]
            route_mismatches += int(result.evidence_path != f"selected_routed_{route}")
            for state in ("out", "depth", "usable", "starter", "premium", "elite"):
                max_probability_error = max(
                    max_probability_error,
                    abs(result.probabilities[state] - float(row[f"y{horizon}_p_{state}"])),
                )
            for state in ("depth", "usable", "starter", "premium", "elite"):
                max_mean_error = max(
                    max_mean_error,
                    abs(
                        result.state_means[state]
                        - float(row[f"y{horizon}_standard_mean_{state}"])
                    ),
                )
            max_expected_error = max(
                max_expected_error,
                abs(
                    result.anticipated_points
                    - float(row[f"y{horizon}_standard_expected_points"])
                ),
            )
            assert SELECTED_FUTURE_FORECAST_VERSION in result.model_version

    assert route_mismatches == 0
    assert max_probability_error <= 1e-10
    assert max_mean_error <= 1e-8
    assert max_expected_error <= 1e-8


def test_selected_future_forecast_fails_closed_on_unknown_identity_or_horizon() -> None:
    forecast = SelectedFutureForecast()
    with pytest.raises(ValueError, match="lacks governed source row"):
        forecast.predict("unknown-player", 2)
    with pytest.raises(ValueError, match="only owns direct Y2/Y3"):
        forecast.predict(selected_future_source_player_ids()[0], 1)
