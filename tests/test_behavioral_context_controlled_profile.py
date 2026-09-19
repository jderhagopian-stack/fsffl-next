from __future__ import annotations

from datetime import UTC, datetime

from fsffl.behavioral.context_controlled_profile import build_owner_context_controlled_preference_profile
from fsffl.behavioral.context_expectation import (
    BehavioralContextExpectationResult,
    BehavioralPositionContextExpectation,
)
from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.residual_preference import BehavioralResidualPolicy
from fsffl.state.models import Position


def at(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=UTC)


def owner_profile(*, acquired_positions: dict[str, int]) -> OwnerBehaviorProfile:
    total = sum(acquired_positions.values())
    return OwnerBehaviorProfile(
        league_family_id="league-family",
        owner_id="owner",
        as_of=at(9),
        event_count=total,
        trade_count=total,
        balanced_trade_count=total,
        acquired_player_count=total,
        acquired_positions=acquired_positions,
        seasons_observed=(2026,),
    )


def expectation() -> BehavioralContextExpectationResult:
    shares = {
        Position.QB: 0.10,
        Position.RB: 0.25,
        Position.WR: 0.50,
        Position.TE: 0.15,
    }
    return BehavioralContextExpectationResult(
        owner_id="owner",
        as_of=at(10),
        expectations=tuple(
            BehavioralPositionContextExpectation(
                position=position,
                expected_acquisition_share=share,
                raw_neighbor_share=share,
                pooled_prior_share=share,
                neighbor_count=8,
                distinct_owner_count=4,
                neighbor_positioned_acquisitions=20,
                evidence_weight=0.8,
            )
            for position, share in shares.items()
        ),
        training_observation_count=80,
        training_owner_count=8,
        training_through=at(8),
        policy_parameter_id="behavioral:context-knn-v1",
        source_model_version="behavioral-context-expectation-knn-v1",
    )


def policy() -> BehavioralResidualPolicy:
    return BehavioralResidualPolicy(
        parameter_id="behavioral:residual-v1",
        prior_strength=4.0,
        evidence_through=at(8),
        provenance="test fixture",
    )


def test_profile_builds_ordered_context_controlled_position_residuals() -> None:
    profile = build_owner_context_controlled_preference_profile(
        owner_profile(acquired_positions={"QB": 1, "RB": 5, "WR": 3, "TE": 1}),
        context_expectation=expectation(),
        residual_policy=policy(),
        as_of=at(10),
    )

    assert [row.position for row in profile.positions] == [Position.QB, Position.RB, Position.WR, Position.TE]
    assert profile.estimated_position_count == 4
    assert profile.observed_positioned_acquisitions == 10
    assert profile.position("RB").observed_acquisition_share == 0.5
    assert profile.position("RB").context_expected_acquisition_share == 0.25
    assert profile.position("RB").raw_residual_share == 0.25
    assert profile.position("WR").raw_residual_share == -0.20
    assert abs(sum((row.raw_residual_share or 0.0) for row in profile.positions)) < 1e-12
    assert abs(sum((row.shrunk_residual_share or 0.0) for row in profile.positions)) < 1e-12
    assert profile.context_training_owner_count == 8


def test_profile_keeps_missing_owner_history_unavailable_not_neutral() -> None:
    profile = build_owner_context_controlled_preference_profile(
        owner_profile(acquired_positions={}),
        context_expectation=expectation(),
        residual_policy=policy(),
        as_of=at(10),
    )

    assert profile.estimated_position_count == 0
    assert profile.mean_confidence == 0.0
    assert all(row.status == "unavailable" for row in profile.positions)
    assert all("no positioned acquisition history" in (row.unavailable_reason or "") for row in profile.positions)


def test_profile_propagates_context_model_unavailability_to_every_position() -> None:
    unavailable = BehavioralContextExpectationResult(
        owner_id="owner",
        as_of=at(10),
        unavailable_reason="insufficient PIT history",
        policy_parameter_id="behavioral:context-knn-v1",
        source_model_version="behavioral-context-expectation-knn-v1",
    )
    profile = build_owner_context_controlled_preference_profile(
        owner_profile(acquired_positions={"RB": 3, "WR": 1}),
        context_expectation=unavailable,
        residual_policy=policy(),
        as_of=at(10),
    )

    assert profile.estimated_position_count == 0
    assert all(row.status == "unavailable" for row in profile.positions)
    assert all("context expectation unavailable" in (row.unavailable_reason or "") for row in profile.positions)
