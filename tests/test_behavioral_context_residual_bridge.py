from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.behavioral.context_expectation import (
    BehavioralContextExpectationResult,
    BehavioralPositionContextExpectation,
)
from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.residual_preference import (
    BehavioralResidualPolicy,
    estimate_owner_position_preference_from_context_expectation,
)
from fsffl.state.models import Position


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def profile(owner: str = "owner") -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="league-family",
        owner_id=owner,
        as_of=at(9),
        event_count=4,
        trade_count=4,
        balanced_trade_count=4,
        acquired_player_count=4,
        acquired_positions={"RB": 3, "WR": 1},
        seasons_observed=(2026,),
    )


def expectation(owner: str = "owner") -> BehavioralContextExpectationResult:
    shares = {
        Position.QB: 0.10,
        Position.RB: 0.25,
        Position.WR: 0.50,
        Position.TE: 0.15,
    }
    return BehavioralContextExpectationResult(
        owner_id=owner,
        as_of=at(10),
        expectations=tuple(
            BehavioralPositionContextExpectation(
                position=position,
                expected_acquisition_share=share,
                raw_neighbor_share=share,
                pooled_prior_share=share,
                neighbor_count=8,
                distinct_owner_count=4,
                neighbor_positioned_acquisitions=8,
                evidence_weight=1.0,
            )
            for position, share in shares.items()
        ),
        training_observation_count=32,
        training_owner_count=4,
        training_through=at(8),
        policy_parameter_id="behavioral:context-knn-v1",
        source_model_version="behavioral-context-expectation-knn-v1",
    )


def residual_policy() -> BehavioralResidualPolicy:
    return BehavioralResidualPolicy(
        parameter_id="behavioral:residual-shrink-v1",
        prior_strength=4.0,
        evidence_through=at(8),
        provenance="test fixture",
    )


def test_bridge_uses_empirical_context_share_without_manual_middle_value() -> None:
    result = estimate_owner_position_preference_from_context_expectation(
        profile(),
        position="RB",
        context_expectation=expectation(),
        policy=residual_policy(),
        as_of=at(10),
    )

    assert result.unavailable_reason is None
    assert result.residual is not None
    assert result.residual.context_expected_acquisition_share == 0.25
    assert result.residual.observed_acquisition_share == 0.75
    assert result.residual.raw_residual_share == 0.50
    assert result.residual.shrunk_residual_share == 0.25
    assert any("context-expectation" in item for item in result.residual.context_authority_ids)
    assert any("context-policy" in item for item in result.residual.context_authority_ids)


def test_bridge_propagates_context_unavailability_instead_of_assuming_neutral() -> None:
    unavailable = BehavioralContextExpectationResult(
        owner_id="owner",
        as_of=at(10),
        unavailable_reason="insufficient distinct other-owner PIT history",
        policy_parameter_id="behavioral:context-knn-v1",
        source_model_version="behavioral-context-expectation-knn-v1",
    )

    result = estimate_owner_position_preference_from_context_expectation(
        profile(),
        position="RB",
        context_expectation=unavailable,
        policy=residual_policy(),
        as_of=at(10),
    )

    assert result.residual is None
    assert "context expectation unavailable" in (result.unavailable_reason or "")


def test_bridge_rejects_owner_identity_mismatch() -> None:
    with pytest.raises(ValueError, match="owner must match"):
        estimate_owner_position_preference_from_context_expectation(
            profile("owner-a"),
            position="RB",
            context_expectation=expectation("owner-b"),
            policy=residual_policy(),
            as_of=at(10),
        )


def test_bridge_rejects_future_context_expectation() -> None:
    with pytest.raises(ValueError, match="future context expectation"):
        estimate_owner_position_preference_from_context_expectation(
            profile(),
            position="RB",
            context_expectation=expectation(),
            policy=residual_policy(),
            as_of=at(9),
        )
