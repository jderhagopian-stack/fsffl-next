from __future__ import annotations

import pytest

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.career_tail import (
    CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE,
    CAREER_TAIL_RESEARCH_ARTIFACT_ID,
    CAREER_TAIL_RESEARCH_ARTIFACT_SHA256,
    CAREER_TAIL_RESEARCH_RUN_ID,
    CareerTailFeatures,
    build_career_tail_authority,
    lineup_capacity_signature,
)


def _rules(*, wr_count: int = 3) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=wr_count),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )


def test_frozen_terminal_signature_and_research_evidence_are_exact() -> None:
    assert lineup_capacity_signature(_rules()) == CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE
    assert CAREER_TAIL_RESEARCH_RUN_ID == 37086000162
    assert CAREER_TAIL_RESEARCH_ARTIFACT_ID == 11260487964
    assert CAREER_TAIL_RESEARCH_ARTIFACT_SHA256 == (
        "505ba72e71ddcb868c1673386f2a516d64e1a087fe2d8d9807572cb24cd99aa6"
    )


def test_terminal_consumer_reproduces_frozen_duan_smearing_models() -> None:
    features = CareerTailFeatures(
        player_id="p1",
        position=Position.WR,
        age_years=25.0,
        experience_years=3.0,
        current_points=100.0,
        prior_points=80.0,
    )
    result = build_career_tail_authority(features, rules=_rules())

    direct, two_part = result.model_predictions
    assert direct.model_id == "direct_ridge"
    assert direct.central == pytest.approx(18.699463819835348)
    assert two_part.model_id == "two_part_state"
    assert two_part.central == pytest.approx(41.14841166841441)
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
        CareerTailFeatures(
            player_id="p1",
            position=Position.RB,
            age_years=25.0,
            experience_years=3.0,
            current_points=100.0,
            prior_points=None,
        ),
        rules=_rules(),
    )
    observed_zero = build_career_tail_authority(
        CareerTailFeatures(
            player_id="p1",
            position=Position.RB,
            age_years=25.0,
            experience_years=3.0,
            current_points=100.0,
            prior_points=0.0,
        ),
        rules=_rules(),
    )
    assert missing.features.feature_vector[-1] == 1.0
    assert observed_zero.features.feature_vector[-1] == 0.0
    assert missing.reference_center != observed_zero.reference_center


def test_terminal_consumer_fails_closed_on_different_lineup_capacity() -> None:
    with pytest.raises(ValueError, match="lineup-capacity signature"):
        build_career_tail_authority(
            CareerTailFeatures(
                player_id="p1",
                position=Position.WR,
                age_years=25.0,
                experience_years=3.0,
                current_points=100.0,
                prior_points=80.0,
            ),
            rules=_rules(wr_count=2),
        )
