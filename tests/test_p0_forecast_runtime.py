from __future__ import annotations

import csv
from pathlib import Path

from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.product.p0_forecast_runtime import (
    P0_CURRENT_SOURCE_CSV_SHA256,
    P0_FINAL_ROUTE_AUTHORITY,
    P0_FINAL_ROUTE_AUTHORITY_SHA256,
    P0_FINAL_ROUTE_AUTHORITY_VERSION,
    P0_FORECAST_VERSION,
    P0_PACKAGE_SHA256,
    frozen_p0_standard_materialization,
)


EXPECTED_FINAL_ROUTES = {
    "2": {
        "QB|developmental": "D1",
        "QB|established": "D1",
        "QB|veteran": "D1",
        "RB|developmental": "D1",
        "RB|established": "D1",
        "RB|veteran": "D1",
        "TE|developmental": "D1",
        "TE|established": "D1",
        "TE|veteran": "D1",
        "WR|developmental": "D1",
        "WR|established": "D1",
        "WR|veteran": "D1",
    },
    "3": {
        "QB|developmental": "D1",
        "QB|established": "D1",
        "QB|veteran": "D1",
        "RB|developmental": "D1",
        "RB|established": "D1",
        "RB|veteran": "D0",
        "TE|developmental": "D1",
        "TE|established": "D1",
        "TE|veteran": "D0",
        "WR|developmental": "D1",
        "WR|established": "D1",
        "WR|veteran": "D0",
    },
}
_CHANGED_CELLS = {"QB|developmental", "RB|established"}
_ALLOWED_CHANGED_STANDARD_FIELDS = {
    "y3_candidate",
    "y3_standard_conditional_active_points",
    "y3_standard_expected_points",
    "y3_standard_conditional_to_y1_ratio",
    "y3_standard_expected_to_y1_ratio",
    "y3_standard_mean_depth",
    "y3_standard_mean_usable",
    "y3_standard_mean_starter",
    "y3_standard_mean_premium",
    "y3_standard_mean_elite",
}


def _load(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["current_player_id"]: row for row in csv.DictReader(handle)}


def test_frozen_p0_package_source_and_final_route_authority_are_exact() -> None:
    assert P0_PACKAGE_SHA256 == "ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7"
    assert P0_CURRENT_SOURCE_CSV_SHA256 == "eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a"
    assert P0_FINAL_ROUTE_AUTHORITY_SHA256 == "cf5e3c0d375cdb6248ead9eeba853e71dabebaf017c292c6186d2fe765bfddda"
    assert P0_FINAL_ROUTE_AUTHORITY_VERSION == "p0-final-route-authority-v1:cf5e3c0d375c"
    assert P0_FORECAST_VERSION.endswith(P0_FINAL_ROUTE_AUTHORITY_VERSION)
    assert P0_FINAL_ROUTE_AUTHORITY == EXPECTED_FINAL_ROUTES


def test_final_route_board_diff_is_bounded_to_the_two_earned_cells() -> None:
    old = _load(
        Path(
            "artifacts/implementation/authoritative_p0_final_sanity_20260919/"
            "FINAL_STANDARD_COMPATIBILITY_BOARD_335.csv"
        )
    )
    new = _load(
        Path(
            "artifacts/implementation/final_forecast_route_implementation_20260920/"
            "FINAL_STANDARD_COORDINATE_BOARD_335.csv"
        )
    )
    assert set(old) == set(new)
    affected = 0
    for player_id, before in old.items():
        after = new[player_id]
        route_cell = after["y3_route_cell"]
        if route_cell not in _CHANGED_CELLS:
            assert after == before
            continue
        affected += 1
        assert before["y3_candidate"] == "D0"
        assert after["y3_candidate"] == "D1"
        for key, before_value in before.items():
            if key in _ALLOWED_CHANGED_STANDARD_FIELDS:
                continue
            assert after[key] == before_value
    assert affected == 50


def test_frozen_p0_standard_materialization_replays_all_335_final_route_rows() -> None:
    expected = _load(
        Path(
            "artifacts/implementation/final_forecast_route_implementation_20260920/"
            "FINAL_STANDARD_COORDINATE_BOARD_335.csv"
        )
    )

    actual = frozen_p0_standard_materialization()
    assert actual.player_count == 335
    assert actual.route_authority_sha256 == P0_FINAL_ROUTE_AUTHORITY_SHA256
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
