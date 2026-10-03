from __future__ import annotations

import pytest

from fsffl.forecast.future_contract import CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_CURRENT_COHORT_SIZE,
    FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE,
    FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256,
    FOUNDATION4_LONG_HORIZON_ROW_COUNT,
    FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256,
    foundation4_long_horizon_rows,
    foundation4_standard_scoring_is_exactly_compatible,
    provide_foundation4_long_horizon_forecast_contract,
    provide_foundation4_long_horizon_forecast_contract_for_rules,
    provide_foundation4_terminal_features,
)
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    RosterSlot,
    ScoringRule,
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
    assert contract.scoring_coordinate == FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE
    assert {row.scoring_coordinate for row in contract.forecasts} == {
        FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE
    }
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


    terminal = provide_foundation4_terminal_features()
    missing_prior = [row for row in terminal.values() if row.prior_points is None]
    assert missing_prior
    assert all(row.prior_points is None for row in missing_prior)


def _standard_rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=FROZEN_I1_STANDARD_SCORING,
    )


def test_frozen_board_relabels_only_for_exact_standard_scoring_equivalence() -> None:
    rules = _standard_rules()
    assert foundation4_standard_scoring_is_exactly_compatible(rules) is True

    connected = provide_foundation4_long_horizon_forecast_contract_for_rules(rules)

    assert connected.scoring_coordinate == CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    assert {row.scoring_coordinate for row in connected.forecasts} == {
        CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    }
    assert connected.provenance["source_scoring_coordinate"] == (
        FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE
    )
    assert connected.provenance["coordinate_equivalence"] == (
        "exact_frozen_standard_scoring_match"
    )


@pytest.mark.parametrize(
    "scoring",
    (
        FROZEN_I1_STANDARD_SCORING
        + (ScoringRule(stat="rec", points=0.5),),
        tuple(
            ScoringRule(
                stat=row.stat,
                points=6.0 if row.stat == "pass_td" else row.points,
            )
            for row in FROZEN_I1_STANDARD_SCORING
        ),
    ),
)
def test_frozen_board_fails_closed_on_incompatible_connected_scoring(scoring) -> None:
    rules = _standard_rules().model_copy(update={"scoring": scoring})
    assert foundation4_standard_scoring_is_exactly_compatible(rules) is False
    with pytest.raises(ValueError, match="no governed Foundation 4 scoring transform"):
        provide_foundation4_long_horizon_forecast_contract_for_rules(rules)


def test_terminal_signature_remains_separate_from_frozen_board_identity() -> None:
    # Board identity alone is never authority for a different lineup-capacity game.
    assert CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE == (
        "a4d9a532c477b9fb2114a33009b94adbe15823748efec46d9701bdcddc8f5363"
    )
