from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import Asset, FaabAsset, FrozenModel, PickAsset, PlayerAsset
from fsffl.value.models import AssetValueProfile, ValueScale

from .models import BilateralTradeProposal, TradeLeg


class EconomicConcept(StrEnum):
    MARKET_PRICE = "market_price"
    INTRINSIC_VALUE = "intrinsic_value"
    ACQUISITION_PRICE = "acquisition_price"
    SALE_PRICE = "sale_price"


class ExpectedPackageValue(FrozenModel):
    """Expected package value for one explicit NEXT-3 concept and scale.

    Expected values may be summed without assuming independence. Uncertainty is
    intentionally not aggregated here because package covariance is not yet an
    authoritative NEXT concept.
    """

    concept: EconomicConcept
    mean_value: float
    scale: ValueScale
    included_asset_ids: tuple[str, ...]
    missing_asset_ids: tuple[str, ...] = ()
    model_versions: tuple[str, ...]

    @model_validator(mode="after")
    def validate_summary(self) -> "ExpectedPackageValue":
        if not self.included_asset_ids:
            raise ValueError("package summary must include at least one evidenced asset")
        if not self.model_versions or any(not value.strip() for value in self.model_versions):
            raise ValueError("package summary must record contributing model versions")
        return self


class TradeLegEconomics(FrozenModel):
    team_id: str
    sent_market: ExpectedPackageValue | None = None
    sent_intrinsic: ExpectedPackageValue | None = None
    sent_sale_price: ExpectedPackageValue | None = None
    received_market: ExpectedPackageValue | None = None
    received_intrinsic: ExpectedPackageValue | None = None
    received_acquisition_price: ExpectedPackageValue | None = None


class BilateralTradeEconomics(FrozenModel):
    proposal_id: str
    side_a: TradeLegEconomics
    side_b: TradeLegEconomics
    model_version: str = "next5-trade-economics-v1"

    @model_validator(mode="after")
    def validate_economics(self) -> "BilateralTradeEconomics":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("trade economics identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("bilateral economics requires distinct teams")
        return self


def _asset_id(asset: Asset) -> str:
    if isinstance(asset, PlayerAsset):
        return asset.player_id
    if isinstance(asset, PickAsset):
        return asset.pick_id
    if isinstance(asset, FaabAsset):
        # FAAB is amount-bearing rather than identity-bearing. NEXT-3 may later
        # provide a governed FAAB conversion; until then missing evidence remains visible.
        return f"faab:{asset.amount}"
    raise TypeError("unsupported trade asset")


def _extract_estimate(profile: AssetValueProfile, concept: EconomicConcept):
    if concept == EconomicConcept.MARKET_PRICE:
        return profile.market_price
    if concept == EconomicConcept.INTRINSIC_VALUE:
        return profile.intrinsic_value if profile.intrinsic_value is not None else profile.pick_value
    if concept == EconomicConcept.ACQUISITION_PRICE:
        return profile.acquisition_price
    if concept == EconomicConcept.SALE_PRICE:
        return profile.sale_price
    raise ValueError("unsupported economic concept")


def _summarize_package(
    assets: tuple[Asset, ...],
    profiles: Mapping[str, AssetValueProfile],
    *,
    concept: EconomicConcept,
) -> ExpectedPackageValue | None:
    included: list[str] = []
    missing: list[str] = []
    means: list[float] = []
    scale: ValueScale | None = None
    versions: set[str] = set()

    for asset in assets:
        asset_id = _asset_id(asset)
        profile = profiles.get(asset_id)
        if profile is None:
            missing.append(asset_id)
            continue
        estimate = _extract_estimate(profile, concept)
        if estimate is None:
            missing.append(asset_id)
            continue
        estimate_scale = estimate.scale
        if scale is None:
            scale = estimate_scale
        elif estimate_scale != scale:
            raise ValueError(f"{concept.value} package contains incompatible value scales")
        included.append(asset_id)
        means.append(estimate.distribution.mean)
        versions.add(estimate.model_version)

    if not included:
        return None
    assert scale is not None
    return ExpectedPackageValue(
        concept=concept,
        mean_value=sum(means),
        scale=scale,
        included_asset_ids=tuple(included),
        missing_asset_ids=tuple(missing),
        model_versions=tuple(sorted(versions)),
    )


def _leg_economics(
    leg: TradeLeg,
    receives: TradeLeg,
    profiles: Mapping[str, AssetValueProfile],
) -> TradeLegEconomics:
    return TradeLegEconomics(
        team_id=leg.team_id,
        sent_market=_summarize_package(leg.sends, profiles, concept=EconomicConcept.MARKET_PRICE),
        sent_intrinsic=_summarize_package(leg.sends, profiles, concept=EconomicConcept.INTRINSIC_VALUE),
        sent_sale_price=_summarize_package(leg.sends, profiles, concept=EconomicConcept.SALE_PRICE),
        received_market=_summarize_package(receives.sends, profiles, concept=EconomicConcept.MARKET_PRICE),
        received_intrinsic=_summarize_package(receives.sends, profiles, concept=EconomicConcept.INTRINSIC_VALUE),
        received_acquisition_price=_summarize_package(
            receives.sends,
            profiles,
            concept=EconomicConcept.ACQUISITION_PRICE,
        ),
    )


def summarize_bilateral_trade_economics(
    proposal: BilateralTradeProposal,
    profiles: Mapping[str, AssetValueProfile],
    *,
    model_version: str = "next5-trade-economics-v1",
) -> BilateralTradeEconomics:
    """Bind typed NEXT-3 economics to a proposal without creating utility.

    Market price, intrinsic value, acquisition price, and sale price remain
    distinct concepts. Missing evidence is surfaced. Expected means are additive;
    package uncertainty is deliberately left unaggregated until covariance has an
    authoritative model.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    return BilateralTradeEconomics(
        proposal_id=proposal.proposal_id,
        side_a=_leg_economics(proposal.side_a, proposal.side_b, profiles),
        side_b=_leg_economics(proposal.side_b, proposal.side_a, profiles),
        model_version=model_version,
    )
