from datetime import UTC, datetime

import pytest

from fsffl.state.models import Position
from fsffl.team_utility.position_strength import LeagueRelativePositionStrength
from fsffl.trade_decision.contextual_value import ContextualValueAdjustmentKind
from fsffl.trade_decision.contextual_value_estimator import (
    BoundedContextualValuePrior,
    ContextualValueSignal,
    build_team_owner_adjusted_value,
    derive_team_need_signal,
    estimate_contextual_adjustment,
)
from fsffl.value.models import MarketPriceEstimate, ValueAssetKind, ValueDistribution, ValueScale

AS_OF = datetime(2026, 9, 8, tzinfo=UTC)
SCALE = ValueScale(scale_id="fsffl-cardinal", version="test-v1", unit_label="points")


def market(mean: float = 8000.0) -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id="player-1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(
            mean=mean,
            stddev=400.0,
            p10=7400.0,
            p50=8000.0,
            p90=8600.0,
        ),
        scale=SCALE,
        as_of=AS_OF,
        market_context_id="league-market",
        model_version="market-test-v1",
        evidence_sources=("source-a",),
    )


def strength(index: float) -> LeagueRelativePositionStrength:
    return LeagueRelativePositionStrength(
        team_id="team-a",
        position=Position.RB,
        starter_count=2,
        expected_points=index * 2,
        league_average_expected_points=200.0,
        strength_index=index,
        league_rank=8,
        team_count=12,
    )


def need_prior(max_abs_delta: float = 500.0) -> BoundedContextualValuePrior:
    return BoundedContextualValuePrior(
        kind=ContextualValueAdjustmentKind.TEAM_NEED,
        parameter_id="decision.contextual.team_need.max_delta.private_beta_v1",
        max_abs_delta=max_abs_delta,
        signal_saturation_abs=0.50,
        evidence_through=AS_OF,
        provenance=(
            "bounded provisional prior supplied explicitly for private-beta evaluation; "
            "replace with point-in-time transaction calibration"
        ),
    )


def test_team_need_signal_is_structurally_derived_without_cardinal_coefficient() -> None:
    signal = derive_team_need_signal(strength(80.0))
    assert signal is not None
    assert signal.kind == ContextualValueAdjustmentKind.TEAM_NEED
    assert signal.signal_center == pytest.approx(0.20)
    assert signal.authority_id == "decision:contextual-team-need"
    assert "team-utility:position-strength" in signal.evidence_ids[0]


def test_explicit_prior_converts_need_signal_to_bounded_additive_delta() -> None:
    signal = derive_team_need_signal(strength(80.0))
    assert signal is not None
    adjustment = estimate_contextual_adjustment(signal, need_prior(), as_of=AS_OF)
    assert adjustment.delta_mean == pytest.approx(200.0)
    assert adjustment.confidence == 1.0
    assert adjustment.overlap_group == "team-need:RB"
    assert any(item.startswith("parameter:") for item in adjustment.evidence_ids)


def test_relative_surplus_can_reduce_contextual_willingness_to_pay() -> None:
    signal = derive_team_need_signal(strength(120.0))
    assert signal is not None
    adjustment = estimate_contextual_adjustment(signal, need_prior(), as_of=AS_OF)
    assert adjustment.delta_mean == pytest.approx(-200.0)


def test_contextual_adjustment_saturates_at_explicit_prior_bound() -> None:
    signal = derive_team_need_signal(strength(20.0))
    assert signal is not None
    adjustment = estimate_contextual_adjustment(signal, need_prior(max_abs_delta=500.0), as_of=AS_OF)
    assert adjustment.delta_mean == pytest.approx(500.0)


def test_estimator_shifts_market_distribution_without_mutating_market_baseline() -> None:
    baseline = market()
    signal = derive_team_need_signal(strength(80.0))
    assert signal is not None
    estimate = build_team_owner_adjusted_value(
        team_id="team-a",
        owner_id="owner-a",
        market_baseline=baseline,
        signals=(signal,),
        priors=(need_prior(),),
        as_of=AS_OF,
    )
    assert baseline.distribution.mean == 8000.0
    assert estimate.market_baseline is baseline
    assert estimate.adjusted_distribution.mean == pytest.approx(8200.0)
    assert estimate.adjusted_distribution.p10 == pytest.approx(7600.0)
    assert estimate.adjusted_distribution.p50 == pytest.approx(8200.0)
    assert estimate.adjusted_distribution.p90 == pytest.approx(8800.0)
    assert estimate.adjusted_distribution.stddev == baseline.distribution.stddev
    assert estimate.adjustment_bound_abs == 500.0


def test_estimator_requires_explicit_prior_instead_of_hiding_default_coefficient() -> None:
    signal = derive_team_need_signal(strength(80.0))
    assert signal is not None
    with pytest.raises(ValueError, match="missing contextual value prior"):
        build_team_owner_adjusted_value(
            team_id="team-a",
            market_baseline=market(),
            signals=(signal,),
            priors=(),
            as_of=AS_OF,
        )


def test_estimator_rejects_future_parameter_evidence() -> None:
    future = datetime(2026, 9, 9, tzinfo=UTC)
    prior = need_prior().model_copy(update={"evidence_through": future})
    signal = derive_team_need_signal(strength(80.0))
    assert signal is not None
    with pytest.raises(ValueError, match="future evidence"):
        estimate_contextual_adjustment(signal, prior, as_of=AS_OF)


def test_existing_aggregate_contract_rejects_overlapping_contextual_signals() -> None:
    first = derive_team_need_signal(strength(80.0))
    assert first is not None
    duplicate = ContextualValueSignal(
        kind=ContextualValueAdjustmentKind.TEAM_NEED,
        authority_id="decision:another-team-need-path",
        overlap_group=first.overlap_group,
        signal_center=0.10,
        confidence=0.5,
        evidence_ids=("different-evidence",),
        source_model_version="test-v1",
    )
    with pytest.raises(ValueError, match="overlapping adjustments"):
        build_team_owner_adjusted_value(
            team_id="team-a",
            market_baseline=market(),
            signals=(first, duplicate),
            priors=(need_prior(),),
            as_of=AS_OF,
        )
