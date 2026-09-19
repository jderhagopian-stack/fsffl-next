from datetime import UTC, datetime

import pytest

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.residual_preference import (
    BehavioralResidualPolicy,
    estimate_owner_position_preference_residual,
)
from fsffl.trade_decision.behavioral_contextual_value import derive_owner_behavior_contextual_signal
from fsffl.trade_decision.contextual_value import ContextualValueAdjustmentKind
from fsffl.trade_decision.contextual_value_estimator import (
    BoundedContextualValuePrior,
    estimate_contextual_adjustment,
)

AS_OF = datetime(2026, 9, 8, tzinfo=UTC)


def profile(*, acquired_positions: dict[str, int]) -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="league-family",
        owner_id="owner-a",
        as_of=AS_OF,
        first_observed_at=datetime(2024, 1, 1, tzinfo=UTC),
        event_count=5,
        trade_count=5,
        consolidation_trade_count=2,
        diversification_trade_count=2,
        balanced_trade_count=1,
        acquired_player_count=sum(acquired_positions.values()),
        acquired_positions=acquired_positions,
        seasons_observed=(2024, 2025, 2026),
    )


def residual_policy(prior_strength: float = 10.0) -> BehavioralResidualPolicy:
    return BehavioralResidualPolicy(
        parameter_id="behavioral.owner_position_residual.prior_strength.v1",
        prior_strength=prior_strength,
        evidence_through=AS_OF,
        provenance=(
            "bounded provisional shrinkage prior; replace with hierarchical owner-effect calibration "
            "using point-in-time reconstructed transaction context"
        ),
    )


def test_owner_position_preference_is_residualized_against_explicit_context() -> None:
    residual = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 5, "WR": 3, "QB": 1, "TE": 1}),
        position="RB",
        context_expected_acquisition_share=0.30,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    assert residual.observed_positioned_acquisitions == 10
    assert residual.observed_acquisition_share == pytest.approx(0.50)
    assert residual.raw_residual_share == pytest.approx(0.20)
    assert residual.confidence == pytest.approx(0.50)
    assert residual.shrunk_residual_share == pytest.approx(0.10)
    assert residual.context_authority_ids == ("decision:contextual-team-need",)


def test_context_explains_behavior_before_owner_specific_residual_is_claimed() -> None:
    residual = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 5, "WR": 3, "QB": 1, "TE": 1}),
        position="RB",
        context_expected_acquisition_share=0.50,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    assert residual.raw_residual_share == pytest.approx(0.0)
    assert residual.shrunk_residual_share == pytest.approx(0.0)


def test_sparse_history_is_shrunk_more_strongly_than_deeper_history() -> None:
    sparse = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 1, "WR": 1}),
        position="RB",
        context_expected_acquisition_share=0.25,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    deep = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 10, "WR": 10}),
        position="RB",
        context_expected_acquisition_share=0.25,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    assert sparse.raw_residual_share == pytest.approx(deep.raw_residual_share)
    assert abs(sparse.shrunk_residual_share) < abs(deep.shrunk_residual_share)
    assert sparse.confidence < deep.confidence


def test_missing_positioned_history_remains_unestimated_not_neutral() -> None:
    residual = estimate_owner_position_preference_residual(
        profile(acquired_positions={}),
        position="RB",
        context_expected_acquisition_share=0.25,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    assert residual.observed_acquisition_share is None
    assert residual.raw_residual_share is None
    assert residual.shrunk_residual_share is None
    assert residual.confidence == 0.0
    assert derive_owner_behavior_contextual_signal(residual) is None


def test_only_residualized_behavior_can_bridge_into_contextual_value() -> None:
    residual = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 5, "WR": 3, "QB": 1, "TE": 1}),
        position="RB",
        context_expected_acquisition_share=0.30,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    signal = derive_owner_behavior_contextual_signal(residual)
    assert signal is not None
    assert signal.kind == ContextualValueAdjustmentKind.OWNER_BEHAVIOR
    assert signal.signal_center == pytest.approx(0.10)
    assert signal.residualized_against == ("decision:contextual-team-need",)
    assert signal.confidence == pytest.approx(0.50)


def test_residual_owner_signal_uses_separate_explicit_value_prior() -> None:
    residual = estimate_owner_position_preference_residual(
        profile(acquired_positions={"RB": 5, "WR": 3, "QB": 1, "TE": 1}),
        position="RB",
        context_expected_acquisition_share=0.30,
        context_authority_ids=("decision:contextual-team-need",),
        context_model_version="pit-team-context-v1",
        policy=residual_policy(),
        as_of=AS_OF,
    )
    signal = derive_owner_behavior_contextual_signal(residual)
    assert signal is not None
    value_prior = BoundedContextualValuePrior(
        kind=ContextualValueAdjustmentKind.OWNER_BEHAVIOR,
        parameter_id="decision.contextual.owner_behavior.max_delta.v1",
        max_abs_delta=300.0,
        signal_saturation_abs=0.30,
        evidence_through=AS_OF,
        provenance="bounded provisional owner-behavior value prior",
    )
    adjustment = estimate_contextual_adjustment(signal, value_prior, as_of=AS_OF)
    assert adjustment.delta_mean == pytest.approx(100.0)
    assert adjustment.residualized_against == ("decision:contextual-team-need",)
    assert adjustment.kind == ContextualValueAdjustmentKind.OWNER_BEHAVIOR


def test_future_context_or_policy_evidence_is_rejected() -> None:
    future_profile = profile(acquired_positions={"RB": 1}).model_copy(
        update={"as_of": datetime(2026, 9, 9, tzinfo=UTC)}
    )
    with pytest.raises(ValueError, match="future profile"):
        estimate_owner_position_preference_residual(
            future_profile,
            position="RB",
            context_expected_acquisition_share=0.25,
            context_authority_ids=("decision:contextual-team-need",),
            context_model_version="pit-team-context-v1",
            policy=residual_policy(),
            as_of=AS_OF,
        )
