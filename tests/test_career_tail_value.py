from __future__ import annotations

import pytest

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.career_tail import (
    CAREER_TAIL_LEGACY_RESEARCH_LINEUP_CAPACITY_SIGNATURE,
    CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE,
    CAREER_TAIL_MODEL_VERSION,
    CAREER_TAIL_RESEARCH_ARTIFACT_ID,
    CAREER_TAIL_RESEARCH_ARTIFACT_SHA256,
    CAREER_TAIL_RESEARCH_RUN_ID,
    CAREER_TAIL_SCORING_COORDINATE,
    CareerTailFeatures,
    build_career_tail_authority,
    lineup_capacity_signature,
)


def _rules(*, wr_count: int = 3, sleeper_order: bool = False) -> LeagueRules:
    lineup = (
        LineupRequirement(slot=RosterSlot.QB, count=1),
        LineupRequirement(slot=RosterSlot.RB, count=2),
        LineupRequirement(slot=RosterSlot.WR, count=wr_count),
        LineupRequirement(slot=RosterSlot.TE, count=1),
        LineupRequirement(slot=RosterSlot.FLEX, count=1),
        LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
    )
    if sleeper_order:
        lineup = tuple(sorted(lineup, key=lambda row: row.slot.value))
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=lineup,
        scoring=(),
    )


def _features(
    *,
    position: Position,
    current_points: float = 100.0,
    prior_points: float | None = 80.0,
) -> CareerTailFeatures:
    return CareerTailFeatures(
        player_id="p1",
        position=position,
        age_years=25.0,
        experience_years=3.0,
        current_points=current_points,
        prior_points=prior_points,
        current_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
        prior_points_coordinate=CAREER_TAIL_SCORING_COORDINATE,
    )


def test_frozen_terminal_signature_and_research_evidence_are_exact() -> None:
    assert lineup_capacity_signature(_rules()) == CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE
    assert lineup_capacity_signature(_rules(sleeper_order=True)) == (
        CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE
    )
    assert CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE == (
        "a4d9a532c477b9fb2114a33009b94adbe15823748efec46d9701bdcddc8f5363"
    )
    assert CAREER_TAIL_LEGACY_RESEARCH_LINEUP_CAPACITY_SIGNATURE == (
        "fe6d07a77a7f11cd61e1af476e9d6b3fe89b7e59c6aecdeab5eb61c991b21349"
    )
    assert CAREER_TAIL_RESEARCH_RUN_ID == 37096263982
    assert CAREER_TAIL_RESEARCH_ARTIFACT_ID == 11263913850
    assert CAREER_TAIL_RESEARCH_ARTIFACT_SHA256 == (
        "33158a26d50e71809cf0f38a7d479fda05ccbaa9fbd5703ba894c1cba4560537"
    )
    assert CAREER_TAIL_SCORING_COORDINATE == "connected_league_fantasy_points"
    assert CAREER_TAIL_MODEL_VERSION == (
        "career-tail-two-family-v1:fsffl-connected-scoring-recalibration-v1"
    )


def test_terminal_consumer_reproduces_frozen_duan_smearing_models() -> None:
    features = _features(position=Position.WR)
    result = build_career_tail_authority(features, rules=_rules())

    direct, two_part = result.model_predictions
    assert direct.model_id == "direct_ridge"
    assert direct.central == pytest.approx(22.726148609726526)
    assert two_part.model_id == "two_part_state"
    assert two_part.central == pytest.approx(49.55368760450343)
    assert result.model_authority_low == pytest.approx(direct.central)
    assert result.model_authority_high == pytest.approx(two_part.central)
    assert result.reference_center == pytest.approx(
        (direct.central + two_part.central) / 2.0
    )
    assert result.outcome_outer_80[0] == pytest.approx(
        max(0.0, direct.central - direct.residual_q80)
    )
    assert result.outcome_outer_90[1] == pytest.approx(
        two_part.central + two_part.residual_q90
    )
    assert result.cumulative_outcome_sd_authorized is False


def test_prior_missing_is_explicit_feature_not_imputed_as_observed_zero() -> None:
    missing = build_career_tail_authority(
        _features(position=Position.RB, prior_points=None),
        rules=_rules(),
    )
    observed_zero = build_career_tail_authority(
        _features(position=Position.RB, prior_points=0.0),
        rules=_rules(),
    )
    assert missing.features.feature_vector[-1] == 1.0
    assert observed_zero.features.feature_vector[-1] == 0.0
    assert missing.reference_center != observed_zero.reference_center


def test_terminal_consumer_fails_closed_on_different_lineup_capacity() -> None:
    with pytest.raises(ValueError, match="lineup-capacity signature"):
        build_career_tail_authority(
            _features(position=Position.WR),
            rules=_rules(wr_count=2),
        )



def test_terminal_consumer_rejects_pre_recalibration_point_coordinate() -> None:
    with pytest.raises(ValueError, match="outside the governed FSFFL scoring coordinate"):
        build_career_tail_authority(
            CareerTailFeatures(
                player_id="p1",
                position=Position.WR,
                age_years=25.0,
                experience_years=3.0,
                current_points=100.0,
                prior_points=80.0,
            ),
            rules=_rules(),
        )
