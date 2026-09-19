from datetime import UTC, datetime

import pytest

from fsffl.state.models import PickAsset
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.trade_decision.package_sensitivity import (
    PackageConcentrationPolicy,
    PackagePolicyAuthority,
    summarize_package_concentration_scenario,
)
from fsffl.value.models import AssetValueProfile, PickValueEstimate, ValueAssetKind, ValueDistribution, ValueScale


SCALE = ValueScale(scale_id="dynasty", version="1", unit_label="units")
AS_OF = datetime(2026, 7, 11, tzinfo=UTC)


def profile(asset_id: str, mean: float) -> AssetValueProfile:
    return AssetValueProfile(
        asset_id=asset_id,
        asset_kind=ValueAssetKind.PICK,
        pick_value=PickValueEstimate(
            asset_id=asset_id,
            distribution=ValueDistribution(mean=mean, stddev=10),
            scale=SCALE,
            as_of=AS_OF,
            draft_season=2026,
            round=2 if asset_id == "late-second" else 3,
            model_version="pick-v1",
            class_strength_model_version="class-v1",
            slot_uncertainty_model_version="exact-slot",
        ),
    )


def proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="pick-package",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(PickAsset(pick_id="late-second"),)),
        side_b=TradeLeg(
            team_id="B",
            sends=(PickAsset(pick_id="third-a"), PickAsset(pick_id="third-b")),
        ),
    )


def policy(*multipliers: float, evidence_through=AS_OF) -> PackageConcentrationPolicy:
    return PackageConcentrationPolicy(
        policy_id="research-package",
        model_version="research-package-v1",
        provenance="chronological historical package challenger",
        evidence_through=evidence_through,
        multipliers=multipliers,
        authority=PackagePolicyAuthority.CHALLENGER_ONLY,
    )


def test_package_policy_has_no_implicit_curve_and_requires_best_asset_at_one():
    with pytest.raises(ValueError, match="at least one"):
        policy()
    with pytest.raises(ValueError, match="retain multiplier 1.0"):
        policy(0.9, 0.7)
    with pytest.raises(ValueError, match="non-increasing"):
        policy(1.0, 0.6, 0.7)


def test_challenger_reduces_only_marginal_package_contribution_not_asset_values():
    profiles = {
        "late-second": profile("late-second", 2500),
        "third-a": profile("third-a", 2300),
        "third-b": profile("third-b", 2200),
    }
    result = summarize_package_concentration_scenario(
        proposal(),
        profiles,
        policy=policy(1.0, 0.5),
    )

    # Side B sends the two thirds. Their intrinsic package contribution is
    # 2300 + 0.5*2200 = 3400, while the one-asset side remains 2500.
    assert result.side_b.sent_intrinsic is not None
    assert result.side_b.sent_intrinsic.mean_value == pytest.approx(3400)
    assert result.side_a.sent_intrinsic is not None
    assert result.side_a.sent_intrinsic.mean_value == pytest.approx(2500)
    assert profiles["third-b"].pick_value.distribution.mean == pytest.approx(2200)
    assert "research-package-v1" in result.side_b.sent_intrinsic.model_versions


def test_policy_cannot_use_future_evidence_for_historical_trade():
    future = datetime(2026, 7, 12, tzinfo=UTC)
    profiles = {
        "late-second": profile("late-second", 2500),
        "third-a": profile("third-a", 2300),
        "third-b": profile("third-b", 2200),
    }
    with pytest.raises(ValueError, match="unavailable"):
        summarize_package_concentration_scenario(
            proposal(),
            profiles,
            policy=policy(1.0, 0.5, evidence_through=future),
        )


def test_policy_refuses_to_extrapolate_to_more_assets_than_calibrated():
    p = BilateralTradeProposal(
        proposal_id="three-asset-package",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(PickAsset(pick_id="late-second"),)),
        side_b=TradeLeg(
            team_id="B",
            sends=(PickAsset(pick_id="third-a"), PickAsset(pick_id="third-b"), PickAsset(pick_id="third-c")),
        ),
    )
    profiles = {
        "late-second": profile("late-second", 2500),
        "third-a": profile("third-a", 2300),
        "third-b": profile("third-b", 2200),
        "third-c": profile("third-c", 2100),
    }
    with pytest.raises(ValueError, match="extrapolation is forbidden"):
        summarize_package_concentration_scenario(p, profiles, policy=policy(1.0, 0.5))
