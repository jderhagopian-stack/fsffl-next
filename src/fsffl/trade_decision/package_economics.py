from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .package_concentration import (
    BilateralPackageConcentration,
    PackageConcentrationSide,
    PackageConcentrationStatus,
)


_PACKAGE_PRIOR_EVIDENCE_THROUGH = datetime(2026, 9, 1, tzinfo=UTC)


class PackageEconomicStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class PackageEconomicResolution(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    SINGLETON_UNDERPAID = "singleton_underpaid"
    WITHIN_PROVISIONAL_BAND = "within_provisional_band"
    PACKAGE_CLEARS_UPPER_BOUND = "package_clears_upper_bound"
    INCOMPLETE = "incomplete"


class BoundedPackagePremiumPrior(FrozenModel):
    """Explicit interval prior for unresolved one-for-many transaction economics.

    This is not added to market Value, Team Utility, roster-cut cost, or Simulation.
    It exists only as a Decision-layer robustness guard until the multi-asset
    transaction benchmark can empirically replace the interval.
    """

    lower_ratio: float = Field(ge=0.0, le=1.0)
    upper_ratio: float = Field(ge=0.0, le=1.0)
    evidence_through: datetime
    provenance: str
    authority_status: str = "bounded_provisional_prior"
    update_mode: str = "evidence_updating"
    model_version: str = "next5-package-premium-prior-v1"

    @model_validator(mode="after")
    def validate_prior(self) -> "BoundedPackagePremiumPrior":
        if self.lower_ratio > self.upper_ratio:
            raise ValueError("package premium lower bound cannot exceed upper bound")
        if self.evidence_through.tzinfo is None:
            raise ValueError("package premium evidence_through must be timezone-aware")
        if not self.provenance.strip() or not self.model_version.strip():
            raise ValueError("package premium prior metadata cannot be blank")
        if self.authority_status != "bounded_provisional_prior":
            raise ValueError("package premium v1 must remain explicitly provisional")
        return self


class PackageEconomicAssessment(FrozenModel):
    proposal_id: str
    singleton_sender_team_id: str | None = None
    package_sender_team_id: str | None = None
    singleton_market_value: float | None = Field(default=None, ge=0.0)
    package_market_value: float | None = Field(default=None, ge=0.0)
    package_largest_asset_share: float | None = Field(default=None, ge=0.0, le=1.0)
    premium_lower_value: float | None = Field(default=None, ge=0.0)
    premium_upper_value: float | None = Field(default=None, ge=0.0)
    package_surplus_vs_lower: float | None = None
    package_surplus_vs_upper: float | None = None
    status: PackageEconomicStatus
    resolution: PackageEconomicResolution
    prior_model_version: str
    model_version: str = "next5-package-economic-assessment-v1"

    @model_validator(mode="after")
    def validate_assessment(self) -> "PackageEconomicAssessment":
        if not self.proposal_id.strip() or not self.prior_model_version.strip() or not self.model_version.strip():
            raise ValueError("package economic assessment identifiers cannot be blank")
        if self.status == PackageEconomicStatus.COMPLETE:
            required = (
                self.singleton_sender_team_id,
                self.package_sender_team_id,
                self.singleton_market_value,
                self.package_market_value,
                self.premium_lower_value,
                self.premium_upper_value,
                self.package_surplus_vs_lower,
                self.package_surplus_vs_upper,
            )
            if any(value is None for value in required):
                raise ValueError("complete package economic assessment requires full evidence")
        return self


def live_bounded_package_premium_prior(*, as_of: datetime) -> BoundedPackagePremiumPrior:
    """Return the private-beta interval prior without pretending to know a point estimate.

    The lower bound is zero: NEXT does not assume a residual premium exists merely
    because a trade is one-for-many. The 15% upper bound is an explicit conservative
    research prior used only to test whether a conclusion is robust while the new
    historical package benchmark is populated. It must be replaced or narrowed by
    empirical package evidence rather than becoming a permanent coefficient.
    """

    if as_of.tzinfo is None:
        raise ValueError("package premium prior request must be timezone-aware")
    if as_of < _PACKAGE_PRIOR_EVIDENCE_THROUGH:
        raise ValueError("live package premium prior is unavailable before its evidence cutoff")
    return BoundedPackagePremiumPrior(
        lower_ratio=0.0,
        upper_ratio=0.15,
        evidence_through=_PACKAGE_PRIOR_EVIDENCE_THROUGH,
        provenance=(
            "bounded 0%-15% residual transaction-premium interval for private-beta robustness testing; "
            "does not include roster-cut cost, lineup impact, Simulation outcomes, or Behavioral evidence; "
            "replace with point-in-time multi-asset transaction calibration"
        ),
    )


def _one_for_many_sides(
    concentration: BilateralPackageConcentration,
) -> tuple[PackageConcentrationSide, PackageConcentrationSide] | None:
    a, b = concentration.side_a, concentration.side_b
    if a.asset_count == 1 and b.asset_count >= 2:
        return a, b
    if b.asset_count == 1 and a.asset_count >= 2:
        return b, a
    return None


def assess_package_economics(
    concentration: BilateralPackageConcentration,
    *,
    prior: BoundedPackagePremiumPrior,
    model_version: str = "next5-package-economic-assessment-v1",
) -> PackageEconomicAssessment:
    """Assess whether a one-for-many conclusion is robust to the bounded residual prior.

    The guard applies only when the singleton is individually more valuable than
    every component of the opposing package. Otherwise there is no elite-asset
    concentration question for this provisional model. No numeric adjustment is
    added to Value or utility; the interval only classifies transaction robustness.
    """

    if prior.evidence_through.tzinfo is None:
        raise ValueError("package economic prior must be point-in-time safe")
    sides = _one_for_many_sides(concentration)
    if sides is None:
        return PackageEconomicAssessment(
            proposal_id=concentration.proposal_id,
            status=PackageEconomicStatus.NOT_APPLICABLE,
            resolution=PackageEconomicResolution.NOT_APPLICABLE,
            prior_model_version=prior.model_version,
            model_version=model_version,
        )

    singleton, package = sides
    if (
        singleton.status != PackageConcentrationStatus.COMPLETE
        or package.status != PackageConcentrationStatus.COMPLETE
        or singleton.total_market_value is None
        or package.total_market_value is None
        or package.largest_asset_market_value is None
        or package.largest_asset_share is None
    ):
        return PackageEconomicAssessment(
            proposal_id=concentration.proposal_id,
            singleton_sender_team_id=singleton.team_id,
            package_sender_team_id=package.team_id,
            status=PackageEconomicStatus.INCOMPLETE,
            resolution=PackageEconomicResolution.INCOMPLETE,
            prior_model_version=prior.model_version,
            model_version=model_version,
        )

    singleton_value = singleton.total_market_value
    package_value = package.total_market_value
    if singleton_value <= package.largest_asset_market_value:
        return PackageEconomicAssessment(
            proposal_id=concentration.proposal_id,
            status=PackageEconomicStatus.NOT_APPLICABLE,
            resolution=PackageEconomicResolution.NOT_APPLICABLE,
            prior_model_version=prior.model_version,
            model_version=model_version,
        )

    lower_value = singleton_value * prior.lower_ratio
    upper_value = singleton_value * prior.upper_ratio
    surplus_lower = package_value - (singleton_value + lower_value)
    surplus_upper = package_value - (singleton_value + upper_value)
    if surplus_lower < 0:
        resolution = PackageEconomicResolution.SINGLETON_UNDERPAID
    elif surplus_upper >= 0:
        resolution = PackageEconomicResolution.PACKAGE_CLEARS_UPPER_BOUND
    else:
        resolution = PackageEconomicResolution.WITHIN_PROVISIONAL_BAND

    return PackageEconomicAssessment(
        proposal_id=concentration.proposal_id,
        singleton_sender_team_id=singleton.team_id,
        package_sender_team_id=package.team_id,
        singleton_market_value=singleton_value,
        package_market_value=package_value,
        package_largest_asset_share=package.largest_asset_share,
        premium_lower_value=lower_value,
        premium_upper_value=upper_value,
        package_surplus_vs_lower=surplus_lower,
        package_surplus_vs_upper=surplus_upper,
        status=PackageEconomicStatus.COMPLETE,
        resolution=resolution,
        prior_model_version=prior.model_version,
        model_version=model_version,
    )
