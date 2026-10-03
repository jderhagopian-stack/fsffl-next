from __future__ import annotations

import pytest

from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_CURRENT_COHORT_SIZE,
    FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256,
    FOUNDATION4_LONG_HORIZON_ROW_COUNT,
    FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256,
    foundation4_long_horizon_rows,
    provide_foundation4_long_horizon_forecast_contract,
    provide_foundation4_terminal_features,
)
from fsffl.value.career_tail import CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE


def test_frozen_foundation4_current_boards_are_complete_and_semantically_pinned() -> None:
    rows = foundation4_long_horizon_rows()
    terminal = provide_foundation4_terminal_features()
    contract = provide_foundation4_long_horizon_forecast_contract()

    assert len(rows) == FOUNDATION4_LONG_HORIZON_ROW_COUNT == 5360
    assert len(terminal) == FOUNDATION4_CURRENT_COHORT_SIZE == 335
    assert len(contract.player_ids) == 335
    assert set(contract.player_ids) == set(terminal)
    assert contract.provenance["current_board_semantic_sha256"] == (
        FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256
    )
    assert FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256 == (
        "dad883347facaccbf98bdfc86835b8e650ddfc2789c1ebb95de31ec4a6640f71"
    )
    assert FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256 == (
        "be5c6b8d5523c0c3af70aaf0eace0bc268d97b97efa4191482a522252933b81b"
    )

    grouped: dict[str, list] = {}
    for row in rows:
        grouped.setdefault(row.player_id, []).append(row)
    assert {len(value) for value in grouped.values()} == {16}
    assert {
        (row.year_index, row.policy_id)
        for row in grouped["sleeper:player:10213"]
    } == {
        (year, policy)
        for year in (4, 5, 6, 7)
        for policy in ("baseline", "hard_router", "soft_stack", "blanket_75_25")
    }


def test_frozen_board_known_coordinate_and_terminal_transport_are_exact() -> None:
    rows = foundation4_long_horizon_rows()
    wr_y4 = next(
        row
        for row in rows
        if row.player_id == "sleeper:player:10213"
        and row.year_index == 4
        and row.policy_id == "baseline"
    )
    assert wr_y4.central_expectation == pytest.approx(43.51065415007779)
    assert wr_y4.absolute_error_80 == pytest.approx(39.53513665106696)
    assert wr_y4.absolute_error_90 == pytest.approx(62.73912571756577)

    feature = provide_foundation4_terminal_features()["sleeper:player:10213"]
    assert feature.age_years == pytest.approx(24.485102363498225)
    assert feature.experience_years == pytest.approx(3.0)
    assert feature.current_points == pytest.approx(80.75)
    assert feature.prior_points == pytest.approx(106.7)
    assert feature.current_points_coordinate == (
        "governed_2026_standard_y1_full_season_expectation_proxy"
    )
    assert "without inventing a YTD annualization multiplier" in (
        feature.live_feature_transport_limitation or ""
    )


def test_terminal_signature_remains_separate_from_frozen_board_identity() -> None:
    # Board identity alone is never authority for a different lineup-capacity game.
    assert CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE == (
        "fe6d07a77a7f11cd61e1af476e9d6b3fe89b7e59c6aecdeab5eb61c991b21349"
    )
