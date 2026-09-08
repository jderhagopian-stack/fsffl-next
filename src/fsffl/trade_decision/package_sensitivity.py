from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import Asset, FaabAsset, FrozenModel, PickAsset, PlayerAsset
from fsffl.value.models import AssetValueProfile, ValueScale

from .economics import (
    BilateralTradeEconomics,
    EconomicConcept,
    ExpectedPackageValue,
    MissingEconomicEvidence,
    EconomicFlow,
    TradeLegEconomics,
)
from .models import BilateralTradeProposal, TradeLeg


class PackagePolicyAuthority(StrEnum):
    CHALLENGER_ONLY = "challenger_only"
    GOVERNED = "governed"


class PackageConcentrationPolicy(FrozenModel):
    """Explicit rank-weight policy for package-economics sensitivity analysis.

    The policy does not change any underlying asset value. It represents the
    hypothesis that the second, third, ... asset in a package contributes less
    clearing/decision utility than the best asset. There are deliberately no
    default multipliers and no extrapolation beyond supplied ranks.
    """

    policy_id: str
    model_version: str
    provenance: str
    evidence_through: datetime
    multipliers: tuple[Annotated[float, Field(gt=0, le=1)], ...]
    authority: PackagePolicyAuthority = PackagePolicyAuthority.CHALLENGER_ONLY

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("package policy evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "PackageConcentrationPolicy":
        if any(not value.strip() for value in (self.policy_id, self.model_version, self.provenance)):
            raise ValueError("package policy identifiers/provenance cannot be blank")
        if not self.multipliers:
            raise ValueError("package policy requires at least one rank multiplier")
        if abs(self.multipliers[0] - 1.0) > 1e-12:
            raise ValueError("best package asset must retain multiplier 1.0")
        if any(right > left for left, right in zip(self.multipliers, self.multipliers[1:])):
            raise ValueError("package rank multipliers must be non-increasing")
        return self


def _asset_id(asset: Asset) -> str:
    if isinstance(asset, PlayerAsset):
        return asset.player_id
    if isinstance(asset, PickAsset):
        return asset.pick_id
    if isinstance(asset, FaabAsset):
        return f"faab:{asset.amount}"
    raise TypeError("unsupported trade asset")


def _estimate(profile: AssetValueProfile, concept: EconomicConcept):
    if concept == EconomicConcept.MARKET_PRICE:
        return profile.market_price
    if concept == EconomicConcept.INTRINSIC_VALUE:
        return profile.intrinsic_value if profile.intrinsic_value is not None else profile.pick_value
    if concept == EconomicConcept.ACQUISITION_PRICE:
        return profile.acquisition_price
    if concept == EconomicConcept.SALE_PRICE:
        return profile.sale_price
    raise ValueError("unsupported economic concept")


def _concentrated_package(
    assets: tuple[Asset, ...],
    profiles: Mapping[str, AssetValueProfile],
    *,
    concept: EconomicConcept,
    policy: PackageConcentrationPolicy,
) -> tuple[ExpectedPackageValue | None, tuple[str, ...]]:
    evidenced: list[tuple[str, float, ValueScale, str]] = []
    missing: list[str] = []
    for asset in assets:
        asset_id = _asset_id(asset)
        profile = profiles.get(asset_id)
        estimate = _estimate(profile, concept) if profile is not None else None
        if estimate is None:
            missing.append(asset_id)
            continue
        evidenced.append((asset_id, estimate.distribution.mean, estimate.scale, estimate.model_version))

    if not evidenced:
        return None, tuple(missing)
    if len(evidenced) > len(policy.multipliers):
        raise ValueError("package contains more evidenced assets than policy ranks; extrapolation is forbidden")

    scale = evidenced[0][2]
    if any(item[2] != scale for item in evidenced):
        raise ValueError(f"{concept.value} package contains incompatible value scales")

    # Rank by the same economic concept being summarized. Asset identity/value is
    # unchanged; only its marginal package contribution is varied by the explicit
    # policy. Stable asset-id tie breaking guarantees reproducibility.
    ranked = sorted(evidenced, key=lambda item: (-item[1], item[0]))
    weighted_mean = sum(
        item[1] * policy.multipliers[index]
        for index, item in enumerate(ranked)
    )
    versions = {item[3] for item in ranked}
    versions.add(policy.model_version)
    return (
        ExpectedPackageValue(
            concept=concept,
            mean_value=weighted_mean,
            scale=scale,
            included_asset_ids=tuple(item[0] for item in ranked),
            missing_asset_ids=tuple(missing),
            model_versions=tuple(sorted(versions)),
        ),
        tuple(missing),
    )


def _leg(
    sends: TradeLeg,
    receives: TradeLeg,
    profiles: Mapping[str, AssetValueProfile],
    *,
    policy: PackageConcentrationPolicy,
) -> TradeLegEconomics:
    summaries = {}
    missing_records: list[MissingEconomicEvidence] = []
    requests = (
        ("sent_market", sends.sends, EconomicConcept.MARKET_PRICE, EconomicFlow.SENT),
        ("sent_intrinsic", sends.sends, EconomicConcept.INTRINSIC_VALUE, EconomicFlow.SENT),
        ("sent_sale_price", sends.sends, EconomicConcept.SALE_PRICE, EconomicFlow.SENT),
        ("received_market", receives.sends, EconomicConcept.MARKET_PRICE, EconomicFlow.RECEIVED),
        ("received_intrinsic", receives.sends, EconomicConcept.INTRINSIC_VALUE, EconomicFlow.RECEIVED),
        ("received_acquisition_price", receives.sends, EconomicConcept.ACQUISITION_PRICE, EconomicFlow.RECEIVED),
    )
    for field, assets, concept, flow in requests:
        summary, missing = _concentrated_package(assets, profiles, concept=concept, policy=policy)
        summaries[field] = summary
        missing_records.extend(
            MissingEconomicEvidence(asset_id=asset_id, concept=concept, flow=flow)
            for asset_id in missing
        )
    return TradeLegEconomics(
        team_id=sends.team_id,
        missing_evidence=tuple(missing_records),
        **summaries,
    )


def summarize_package_concentration_scenario(
    proposal: BilateralTradeProposal,
    profiles: Mapping[str, AssetValueProfile],
    *,
    policy: PackageConcentrationPolicy,
) -> BilateralTradeEconomics:
    """Create one explicit package-economics scenario for Decision testing.

    This does not alter NEXT-3 asset values and does not promote a challenger into
    production. Callers can compare additive economics with one or more explicit
    package policies and route resulting scenarios through existing Decision and
    robustness authorities.
    """

    if policy.evidence_through > proposal.as_of:
        raise ValueError("package concentration policy uses evidence unavailable at proposal as_of")
    return BilateralTradeEconomics(
        proposal_id=proposal.proposal_id,
        side_a=_leg(proposal.side_a, proposal.side_b, profiles, policy=policy),
        side_b=_leg(proposal.side_b, proposal.side_a, profiles, policy=policy),
        model_version=f"next5-package-sensitivity:{policy.model_version}",
    )
