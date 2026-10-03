from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Mapping

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, Position
from fsffl.value.career_tail import CareerTailAuthority
from fsffl.value.long_term_intrinsic import (
    LONG_TERM_INTRINSIC_HORIZONS,
    LongTermAnnualAuthority,
    LongTermIntrinsicShadowContract,
)
from fsffl.value.shapley_intrinsic_contract import (
    ShapleyHorizonUncertainty,
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)


CAREER_FORWARD_INTRINSIC_MODEL_VERSION = (
    "holistic-career-forward-intrinsic-shadow-v1"
)
CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION = (
    "holistic-career-forward-contract-v1:raw-y1-y7-plus-tail"
)
CAREER_FORWARD_RAW_QUANTITY = (
    "cumulative_governed_shapley_marginal_fantasy_points_career_forward"
)
CAREER_FORWARD_AGGREGATION = (
    "phi_Y1 + phi_Y2 + phi_Y3 + phi_Y4 + phi_Y5 + phi_Y6 + phi_Y7 + TAIL_Y8_PLUS"
)


class CareerForwardCurrentAnnualContribution(FrozenModel):
    year_index: Annotated[int, Field(ge=1, le=3)]
    target_season: Annotated[int, Field(ge=2000)]
    raw_shapley_contribution: float
    uncertainty: ShapleyHorizonUncertainty


class CareerForwardModelAuthority(FrozenModel):
    low: float
    reference_center: float
    high: float
    width: Annotated[float, Field(ge=0.0)]

    @model_validator(mode="after")
    def validate_bounds(self) -> "CareerForwardModelAuthority":
        if not self.low <= self.reference_center <= self.high:
            raise ValueError("career-forward model-authority bounds are unordered")
        if not math.isclose(
            self.width,
            self.high - self.low,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("career-forward model-authority width does not reconcile")
        return self


class CareerForwardUncertaintyContract(FrozenModel):
    """Keep horizon/model uncertainty distinct; no career-wide variance is claimed."""

    current_y1_y3: tuple[
        CareerForwardCurrentAnnualContribution,
        CareerForwardCurrentAnnualContribution,
        CareerForwardCurrentAnnualContribution,
    ]
    long_horizon_y4_y7: tuple[
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
    ]
    terminal_y8_plus: CareerTailAuthority
    cumulative_outcome_interval_authorized: bool = False
    cumulative_standard_deviation_authorized: bool = False
    cross_horizon_covariance_validated: bool = False
    semantics: str = (
        "Current Y1-Y3 uncertainty, Y4-Y7 annual outcome uncertainty, and terminal "
        "Y8+ residual uncertainty remain separate. The holistic low/high envelope "
        "is model-authority uncertainty only; no cross-horizon probabilistic "
        "aggregation is asserted."
    )

    @model_validator(mode="after")
    def validate_uncertainty(self) -> "CareerForwardUncertaintyContract":
        if self.cumulative_outcome_interval_authorized:
            raise ValueError("career-forward cumulative outcome interval is not authorized")
        if self.cumulative_standard_deviation_authorized:
            raise ValueError("career-forward cumulative standard deviation is not authorized")
        if self.cross_horizon_covariance_validated:
            raise ValueError("career-forward cross-horizon covariance is not validated")
        return self


class CareerForwardIntrinsicPlayerEstimate(FrozenModel):
    player_id: str
    position: Position
    current_intrinsic_raw_y1_y3: float
    long_horizon_raw_y4_y7_reference: float
    terminal_raw_y8_plus_reference: float
    raw_career_forward_reference: float
    model_authority: CareerForwardModelAuthority
    uncertainty: CareerForwardUncertaintyContract
    raw_quantity: str = CAREER_FORWARD_RAW_QUANTITY
    aggregation: str = CAREER_FORWARD_AGGREGATION
    discounting_applied: bool = False
    display_index_arithmetic_used: bool = False
    market_inputs_used: bool = False
    current_intrinsic_replaced: bool = False

    @model_validator(mode="after")
    def validate_economics(self) -> "CareerForwardIntrinsicPlayerEstimate":
        reconstructed = (
            self.current_intrinsic_raw_y1_y3
            + self.long_horizon_raw_y4_y7_reference
            + self.terminal_raw_y8_plus_reference
        )
        if not math.isclose(
            reconstructed,
            self.raw_career_forward_reference,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("career-forward raw reference does not reconcile")
        if self.discounting_applied:
            raise ValueError("holistic career-forward raw economics cannot be discounted")
        if self.display_index_arithmetic_used:
            raise ValueError("display indexes cannot enter holistic career-forward economics")
        if self.market_inputs_used:
            raise ValueError("Market cannot enter universal holistic Intrinsic")
        if self.current_intrinsic_replaced:
            raise ValueError("holistic Long-Term cannot replace Current Intrinsic")
        return self


class CareerForwardIntrinsicShadowContract(FrozenModel):
    evaluation_season: Annotated[int, Field(ge=2000)]
    input_fingerprint: str
    current_intrinsic_contract_version: str
    long_horizon_contract_version: str
    long_horizon_value_model_version: str
    career_tail_model_version: str
    lineup_capacity_signature: str
    estimates: tuple[CareerForwardIntrinsicPlayerEstimate, ...]
    player_count: Annotated[int, Field(ge=1)]
    model_version: str = CAREER_FORWARD_INTRINSIC_MODEL_VERSION
    contract_version: str = CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION
    raw_quantity: str = CAREER_FORWARD_RAW_QUANTITY
    aggregation: str = CAREER_FORWARD_AGGREGATION
    status: Literal["shadow_ready"] = "shadow_ready"
    authoritative_for_current_intrinsic: bool = False
    current_intrinsic_replaced: bool = False
    display_scaling_applied: bool = False
    market_inputs_used: bool = False
    ignored_long_term_residual_rule_stats: tuple[str, ...] = ()
    scoring_coordinate_limitation: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "CareerForwardIntrinsicShadowContract":
        if self.player_count != len(self.estimates):
            raise ValueError("career-forward player_count does not match estimates")
        if len({item.player_id for item in self.estimates}) != len(self.estimates):
            raise ValueError("career-forward player ids must be unique")
        if not self.input_fingerprint.strip():
            raise ValueError("career-forward input fingerprint cannot be blank")
        if self.authoritative_for_current_intrinsic or self.current_intrinsic_replaced:
            raise ValueError("career-forward shadow cannot replace Current Intrinsic")
        if self.display_scaling_applied:
            raise ValueError("career-forward shadow is raw economic authority")
        if self.market_inputs_used:
            raise ValueError("career-forward shadow cannot consume Market")
        if self.ignored_long_term_residual_rule_stats and not (
            self.scoring_coordinate_limitation or ""
        ).strip():
            raise ValueError(
                "career-forward residual omissions require explicit scoring provenance"
            )
        return self


def _semantic_payload(
    current: ShapleyIntrinsicContract,
    long_term: LongTermIntrinsicShadowContract,
    tails: Mapping[str, CareerTailAuthority],
) -> dict[str, object]:
    return {
        "current": {
            "contract_version": current.contract_version,
            "intrinsic_model_version": current.intrinsic_model_version,
            "evaluation_season": current.evaluation_season,
            "estimates": [
                {
                    "player_id": item.player_id,
                    "annual_raw": [
                        {
                            "year_index": row.year_index,
                            "raw_shapley": float(row.raw_shapley_contribution),
                            "uncertainty": row.uncertainty.model_dump(mode="json"),
                        }
                        for row in item.contributions
                    ],
                }
                for item in sorted(current.estimates, key=lambda row: row.player_id)
            ],
        },
        "long_term": {
            "contract_version": long_term.contract_version,
            "value_model_version": long_term.value_model_version,
            "input_fingerprint": long_term.input_fingerprint,
            "estimates": [
                {
                    "player_id": item.player_id,
                    "annual": [
                        row.model_dump(mode="json")
                        for row in item.annual
                    ],
                }
                for item in sorted(long_term.estimates, key=lambda row: row.player_id)
            ],
        },
        "tails": [
            tails[player_id].model_dump(mode="json")
            for player_id in sorted(tails)
        ],
        "aggregation": CAREER_FORWARD_AGGREGATION,
        "model_version": CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
    }


def career_forward_input_fingerprint(
    current: ShapleyIntrinsicContract,
    long_term: LongTermIntrinsicShadowContract,
    tails: Mapping[str, CareerTailAuthority],
) -> str:
    payload = _semantic_payload(current, long_term, tails)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_career_forward_intrinsic_shadow(
    current: ShapleyIntrinsicContract,
    long_term: LongTermIntrinsicShadowContract,
    tails: Mapping[str, CareerTailAuthority],
) -> CareerForwardIntrinsicShadowContract:
    if current.status != ShapleyIntrinsicAvailability.READY:
        raise ValueError("holistic career-forward shadow requires ready Current Intrinsic")
    if long_term.status != "shadow_ready":
        raise ValueError("holistic career-forward shadow requires ready Y4-Y7 component")
    if current.evaluation_season != long_term.evaluation_season:
        raise ValueError("career-forward components must share evaluation season")

    current_by_id = {item.player_id: item for item in current.estimates}
    long_by_id = {item.player_id: item for item in long_term.estimates}
    player_ids = set(current_by_id)
    if not player_ids:
        raise ValueError("career-forward shadow cannot be empty")
    if set(long_by_id) != player_ids or set(tails) != player_ids:
        raise ValueError("career-forward components must cover the identical player cohort")

    estimates: list[CareerForwardIntrinsicPlayerEstimate] = []
    signatures = {tails[player_id].lineup_capacity_signature for player_id in player_ids}
    if len(signatures) != 1:
        raise ValueError("career-forward terminal lineup-capacity signatures must match")
    lineup_signature = next(iter(signatures))

    for player_id in sorted(player_ids):
        current_row = current_by_id[player_id]
        long_row = long_by_id[player_id]
        tail = tails[player_id]
        current_contributions = tuple(
            CareerForwardCurrentAnnualContribution(
                year_index=row.year_index,
                target_season=row.target_season,
                raw_shapley_contribution=float(row.raw_shapley_contribution),
                uncertainty=row.uncertainty,
            )
            for row in current_row.contributions
        )
        if tuple(row.year_index for row in current_contributions) != (1, 2, 3):
            raise ValueError("Current Intrinsic must expose literal raw Y1-Y3 contributions")
        typed_current = (
            current_contributions[0],
            current_contributions[1],
            current_contributions[2],
        )
        if tuple(row.year_index for row in long_row.annual) != LONG_TERM_INTRINSIC_HORIZONS:
            raise ValueError("Long-Term component must expose literal Y4-Y7 annual authority")
        if long_row.position != tail.position:
            raise ValueError("career-forward position must match across Y4-Y7 and terminal")

        current_raw = sum(row.raw_shapley_contribution for row in typed_current)
        long_reference = sum(row.reference_center for row in long_row.annual)
        long_low = sum(row.authority_low for row in long_row.annual)
        long_high = sum(row.authority_high for row in long_row.annual)
        reference = current_raw + long_reference + tail.reference_center
        low = current_raw + long_low + tail.model_authority_low
        high = current_raw + long_high + tail.model_authority_high

        estimates.append(
            CareerForwardIntrinsicPlayerEstimate(
                player_id=player_id,
                position=long_row.position,
                current_intrinsic_raw_y1_y3=current_raw,
                long_horizon_raw_y4_y7_reference=long_reference,
                terminal_raw_y8_plus_reference=tail.reference_center,
                raw_career_forward_reference=reference,
                model_authority=CareerForwardModelAuthority(
                    low=low,
                    reference_center=reference,
                    high=high,
                    width=high - low,
                ),
                uncertainty=CareerForwardUncertaintyContract(
                    current_y1_y3=typed_current,
                    long_horizon_y4_y7=long_row.annual,
                    terminal_y8_plus=tail,
                ),
            )
        )

    return CareerForwardIntrinsicShadowContract(
        evaluation_season=current.evaluation_season,
        input_fingerprint=career_forward_input_fingerprint(
            current,
            long_term,
            tails,
        ),
        current_intrinsic_contract_version=current.contract_version,
        long_horizon_contract_version=long_term.contract_version,
        long_horizon_value_model_version=long_term.value_model_version,
        career_tail_model_version=next(iter(tails.values())).model_version,
        lineup_capacity_signature=lineup_signature,
        estimates=tuple(estimates),
        player_count=len(estimates),
    )
