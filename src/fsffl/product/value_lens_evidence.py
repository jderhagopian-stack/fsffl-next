from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)

from .runtime import UserRuntimeContext
from .value_presentation import ValuePresentationCoordinate, build_value_presentation_coordinate


BROAD_MARKET_SCALE_ID = "dynasty-market-percentile"
VALUE_LENS_AVAILABILITY_VERSION = "governed-value-lens-availability-v1"


def percentile_ranks(values: Iterable[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(
        ((asset_id, float(value)) for asset_id, value in values),
        key=lambda item: (item[1], item[0]),
    )
    count = len(ordered)
    if count == 0:
        return {}
    ranks: dict[str, float] = {}
    index = 0
    while index < count:
        end = index + 1
        while end < count and ordered[end][1] == ordered[index][1]:
            end += 1
        average_zero_based_rank = (index + end - 1) / 2.0
        percentile = (average_zero_based_rank + 0.5) / count
        for offset in range(index, end):
            ranks[ordered[offset][0]] = percentile
        index = end
    return ranks


@dataclass(frozen=True)
class GovernedValueLensEvidence:
    status: str
    reason: str | None
    league_state_id: str
    market_percentiles: dict[str, float]
    intrinsic_percentiles: dict[str, float]
    intrinsic_raw: dict[str, float]
    value_coordinate: ValuePresentationCoordinate | None
    value_coordinate_error: str | None
    market_model_version: str | None
    market_context_id: str | None
    intrinsic_contract_version: str | None
    intrinsic_model_version: str | None
    forecast_model_version: str | None

    @property
    def comparable_player_ids(self) -> set[str]:
        return set(self.market_percentiles) & set(self.intrinsic_percentiles)


def build_governed_value_lens_evidence(
    runtime: UserRuntimeContext,
    intrinsic: ShapleyIntrinsicContract | None,
) -> GovernedValueLensEvidence:
    """One readiness contract for every Broad Market vs Intrinsic surface."""

    state = runtime.league_state
    if state is None:
        raise ValueError("governed Value lens evidence requires canonical LeagueState")

    values = runtime.value_evidence
    market = {
        estimate.asset_id: max(0.0, min(1.0, float(estimate.distribution.mean)))
        for estimate in (values.estimates if values is not None else ())
        if estimate.scale.scale_id == BROAD_MARKET_SCALE_ID
    }

    intrinsic_available = bool(
        intrinsic is not None
        and intrinsic.status != ShapleyIntrinsicAvailability.UNAVAILABLE
        and intrinsic.estimates
    )
    intrinsic_raw = (
        {
            estimate.player_id: float(estimate.raw_intrinsic_value)
            for estimate in intrinsic.estimates
        }
        if intrinsic_available and intrinsic is not None
        else {}
    )
    intrinsic_percentiles = percentile_ranks(intrinsic_raw.items())

    coordinate = None
    coordinate_error = None
    if values is not None:
        try:
            coordinate = build_value_presentation_coordinate(
                values.native_magnitude_observations
            )
        except ValueError as exc:
            coordinate_error = str(exc)

    if not market:
        status = "unavailable"
        reason = "Governed Broad Market evidence is unavailable for the current league state."
    elif not intrinsic_percentiles:
        status = "unavailable"
        reason = (
            intrinsic.status_reason
            if intrinsic is not None
            and intrinsic.status == ShapleyIntrinsicAvailability.UNAVAILABLE
            else "Governed FSFFL Intrinsic evidence is unavailable for the current league state."
        )
    elif not (set(market) & set(intrinsic_percentiles)):
        status = "unavailable"
        reason = "Broad Market and Intrinsic have no comparable players in the current league state."
    elif coordinate is None:
        status = "unavailable"
        reason = (
            "Governed Value presentation evidence is unavailable: "
            f"{coordinate_error or 'unknown presentation-coordinate error'}"
        )
    else:
        status = "ready"
        reason = None

    return GovernedValueLensEvidence(
        status=status,
        reason=reason,
        league_state_id=state.state_id,
        market_percentiles=market,
        intrinsic_percentiles=intrinsic_percentiles,
        intrinsic_raw=intrinsic_raw,
        value_coordinate=coordinate,
        value_coordinate_error=coordinate_error,
        market_model_version=(values.model_version if values is not None else None),
        market_context_id=(values.market_context_id if values is not None else None),
        intrinsic_contract_version=(getattr(intrinsic, "contract_version", None) if intrinsic is not None else None),
        intrinsic_model_version=(getattr(intrinsic, "intrinsic_model_version", None) if intrinsic is not None else None),
        forecast_model_version=(getattr(intrinsic, "forecast_model_version", None) if intrinsic is not None else None),
    )
