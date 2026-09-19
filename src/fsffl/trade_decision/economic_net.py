from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.models import ValueScale

from .economics import BilateralTradeEconomics, EconomicConcept, ExpectedPackageValue, TradeLegEconomics


class EconomicNetStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    UNAVAILABLE = "unavailable"


class ExpectedEconomicNetDelta(FrozenModel):
    """Received minus sent expected value for one explicit economic concept."""

    concept: EconomicConcept
    mean_delta: float | None = None
    scale: ValueScale | None = None
    status: EconomicNetStatus
    sent_mean: float | None = None
    received_mean: float | None = None
    missing_asset_ids: tuple[str, ...] = ()
    model_versions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_net(self) -> "ExpectedEconomicNetDelta":
        if self.status == EconomicNetStatus.COMPLETE:
            if self.mean_delta is None or self.scale is None:
                raise ValueError("complete economic net requires value and scale")
            if self.sent_mean is None or self.received_mean is None:
                raise ValueError("complete economic net requires sent and received means")
            if self.missing_asset_ids:
                raise ValueError("complete economic net cannot contain missing assets")
        else:
            if self.mean_delta is not None:
                raise ValueError("incomplete economic net cannot expose a partial net delta")
        return self


class TradeLegEconomicNet(FrozenModel):
    team_id: str
    market: ExpectedEconomicNetDelta
    intrinsic: ExpectedEconomicNetDelta


class BilateralTradeEconomicNet(FrozenModel):
    proposal_id: str
    side_a: TradeLegEconomicNet
    side_b: TradeLegEconomicNet
    model_version: str = "next5-economic-net-v1"

    @model_validator(mode="after")
    def validate_net(self) -> "BilateralTradeEconomicNet":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("economic net identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("bilateral economic net requires distinct teams")
        return self


def _net_same_concept(
    sent: ExpectedPackageValue | None,
    received: ExpectedPackageValue | None,
    *,
    concept: EconomicConcept,
) -> ExpectedEconomicNetDelta:
    if sent is None and received is None:
        return ExpectedEconomicNetDelta(
            concept=concept,
            status=EconomicNetStatus.UNAVAILABLE,
        )

    missing: set[str] = set()
    if sent is not None:
        missing.update(sent.missing_asset_ids)
    if received is not None:
        missing.update(received.missing_asset_ids)

    if sent is None or received is None or missing:
        return ExpectedEconomicNetDelta(
            concept=concept,
            status=EconomicNetStatus.INCOMPLETE,
            sent_mean=sent.mean_value if sent is not None else None,
            received_mean=received.mean_value if received is not None else None,
            missing_asset_ids=tuple(sorted(missing)),
            model_versions=tuple(
                sorted(
                    set(sent.model_versions if sent is not None else ())
                    | set(received.model_versions if received is not None else ())
                )
            ),
        )

    if sent.concept != concept or received.concept != concept:
        raise ValueError("economic net inputs must match requested concept")
    if sent.scale != received.scale:
        raise ValueError("economic net requires identical value scale/version")

    return ExpectedEconomicNetDelta(
        concept=concept,
        mean_delta=received.mean_value - sent.mean_value,
        scale=sent.scale,
        status=EconomicNetStatus.COMPLETE,
        sent_mean=sent.mean_value,
        received_mean=received.mean_value,
        model_versions=tuple(sorted(set(sent.model_versions) | set(received.model_versions))),
    )


def _leg_net(leg: TradeLegEconomics) -> TradeLegEconomicNet:
    return TradeLegEconomicNet(
        team_id=leg.team_id,
        market=_net_same_concept(
            leg.sent_market,
            leg.received_market,
            concept=EconomicConcept.MARKET_PRICE,
        ),
        intrinsic=_net_same_concept(
            leg.sent_intrinsic,
            leg.received_intrinsic,
            concept=EconomicConcept.INTRINSIC_VALUE,
        ),
    )


def calculate_bilateral_economic_net(
    economics: BilateralTradeEconomics,
    *,
    model_version: str = "next5-economic-net-v1",
) -> BilateralTradeEconomicNet:
    """Calculate concept-preserving bilateral economic net deltas.

    This is not franchise utility and not a recommendation. A net delta is
    emitted only when both sent and received packages have complete evidence on
    the same NEXT-3 scale/version. Partial packages remain explicitly incomplete.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    return BilateralTradeEconomicNet(
        proposal_id=economics.proposal_id,
        side_a=_leg_net(economics.side_a),
        side_b=_leg_net(economics.side_b),
        model_version=model_version,
    )
