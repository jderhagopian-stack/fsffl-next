from __future__ import annotations

import csv
from pathlib import Path

from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.product.p0_forecast_runtime import (
    P0_CURRENT_SOURCE_CSV_SHA256,
    P0_PACKAGE_SHA256,
    frozen_p0_standard_materialization,
)


def test_frozen_p0_package_and_current_source_are_exact_authority() -> None:
    assert P0_PACKAGE_SHA256 == "ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7"
    assert P0_CURRENT_SOURCE_CSV_SHA256 == "eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a"


def test_frozen_p0_standard_materialization_replays_all_335_corrected_rows() -> None:
    expected_path = Path(
        "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/"
        "CORRECTED_P0_PRESEASON_BOARD_335.csv"
    )
    with expected_path.open(newline="", encoding="utf-8") as handle:
        expected = {
            row["current_player_id"]: row
            for row in csv.DictReader(handle)
        }

    actual = frozen_p0_standard_materialization()
    assert actual.player_count == 335
    assert set(actual.players) == set(expected)

    max_diff = 0.0
    for player_id, player in actual.players.items():
        row = expected[player_id]
        assert player.source.position == row["position"]
        for horizon in (2, 3):
            result = player.result_for(horizon)
            assert player.route_for(horizon) == row[f"y{horizon}_candidate"]
            expected_active = float(row[f"y{horizon}_active_probability"])
            max_diff = max(
                max_diff,
                abs(result.persistence_probability - expected_active),
                abs(
                    result.anticipated_points
                    - float(row[f"y{horizon}_standard_expected_points"])
                ),
            )
            conditional = (
                result.anticipated_points / result.persistence_probability
                if result.persistence_probability > 1e-15
                else 0.0
            )
            max_diff = max(
                max_diff,
                abs(
                    conditional
                    - float(row[f"y{horizon}_standard_conditional_active_points"])
                ),
            )
            for state in STATE_NAMES:
                max_diff = max(
                    max_diff,
                    abs(
                        float(result.probabilities[state])
                        - float(row[f"y{horizon}_p_{state}"])
                    ),
                )
            assert result.state_means["out"] == 0.0
            for state in STATE_NAMES[1:]:
                max_diff = max(
                    max_diff,
                    abs(
                        float(result.state_means[state])
                        - float(row[f"y{horizon}_standard_mean_{state}"])
                    ),
                )

    assert max_diff <= 1e-8
