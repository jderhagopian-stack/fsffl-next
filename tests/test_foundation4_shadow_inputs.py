from __future__ import annotations

import pytest

from fsffl.forecast.future_contract import CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_CURRENT_COHORT_SIZE,
    FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE,
    FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    FOUNDATION4_FSFFL_SCORING_COORDINATE,
    FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256,
    FOUNDATION4_LONG_HORIZON_ROW_COUNT,
    FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256,
    foundation4_fsffl_scoring_is_compatible,
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
    assert contract.scoring_coordinate == FOUNDATION4_FSFFL_SCORING_COORDINATE
    assert {row.scoring_coordinate for row in contract.forecasts} == {
        FOUNDATION4_FSFFL_SCORING_COORDINATE
    }
    assert contract.provenance["current_board_semantic_sha256"] == (
        FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256
    )
    assert FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256 == (
        "3caddc5c33be83088eaca30d8c1ac7031022f08668a031a0a3b08616aed773c2"
    )
    assert FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256 == (
        "ef52ccaaef0749d6d1e5786c351714570c0d0a0ea811cc1cf940fe2adac8c867"
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
    assert wr_y4.central_expectation == pytest.approx(70.94683777854785)
    assert wr_y4.absolute_error_80 == pytest.approx(49.06099766506673)
    assert wr_y4.absolute_error_90 == pytest.approx(78.2335011086601)
    assert wr_y4.scoring_coordinate == FOUNDATION4_FSFFL_SCORING_COORDINATE

    feature = provide_foundation4_terminal_features()["sleeper:player:10213"]
    assert feature.age_years == pytest.approx(24.485102363498225)
    assert feature.experience_years == pytest.approx(3.0)
    assert feature.current_points == pytest.approx(106.353)
    assert feature.prior_points == pytest.approx(133.2)
    assert feature.current_points_coordinate == FOUNDATION4_FSFFL_SCORING_COORDINATE
    assert feature.prior_points_coordinate == FOUNDATION4_FSFFL_SCORING_COORDINATE
    assert "exact FSFFL scoring transform" in (
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


def _fsffl_rules() -> LeagueRules:
    return _standard_rules().model_copy(
        update={"scoring": FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING}
    )


def test_frozen_board_uses_direct_fsffl_scoring_authority() -> None:
    rules = _fsffl_rules()
    assert foundation4_fsffl_scoring_is_compatible(rules) is True
    assert foundation4_standard_scoring_is_exactly_compatible(rules) is False

    connected = provide_foundation4_long_horizon_forecast_contract_for_rules(rules)

    assert connected.scoring_coordinate == CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    assert {row.scoring_coordinate for row in connected.forecasts} == {
        CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    }
    assert connected.provenance["source_scoring_coordinate"] == (
        FOUNDATION4_FSFFL_SCORING_COORDINATE
    )
    assert connected.provenance["coordinate_compatibility"] == (
        "exact_fsffl_scoring_freeze"
    )
    assert connected.provenance["scoring_materialization"] == (
        "direct_historical_fsffl_target_recalibration"
    )


def test_zero_point_exotic_rule_does_not_break_fsffl_scoring_freeze() -> None:
    rules = _fsffl_rules().model_copy(
        update={
            "scoring": FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
            + (ScoringRule(stat="bonus_pass_yd_400", points=0.0),)
        }
    )
    assert foundation4_fsffl_scoring_is_compatible(rules) is True
    assert provide_foundation4_long_horizon_forecast_contract_for_rules(rules)


@pytest.mark.parametrize(
    "scoring",
    (
        FROZEN_I1_STANDARD_SCORING,
        tuple(
            ScoringRule(
                stat=row.stat,
                points=6.0 if row.stat == "pass_td" else row.points,
            )
            for row in FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        ),
        FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        + (ScoringRule(stat="bonus_pass_yd_400", points=5.0),),
    ),
)
def test_frozen_board_fails_closed_on_materially_incompatible_scoring(scoring) -> None:
    rules = _fsffl_rules().model_copy(update={"scoring": scoring})
    assert foundation4_fsffl_scoring_is_compatible(rules) is False
    with pytest.raises(ValueError, match="active player-offense scoring is incompatible"):
        provide_foundation4_long_horizon_forecast_contract_for_rules(rules)


def test_terminal_signature_remains_separate_from_frozen_board_identity() -> None:
    # Board identity alone is never authority for a different lineup-capacity game.
    assert CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE == (
        "a4d9a532c477b9fb2114a33009b94adbe15823748efec46d9701bdcddc8f5363"
    )
