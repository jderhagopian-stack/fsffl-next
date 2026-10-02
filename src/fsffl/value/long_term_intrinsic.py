from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.forecast.future_contract import (
    CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE,
)
from fsffl.forecast.long_horizon_contract import (
    LONG_HORIZON_AUTHORITY_MAP_SHA256,
    LONG_HORIZON_AUTHORITY_MAP_VERSION,
    LONG_HORIZON_POLICIES,
    LongHorizonForecastAuthorityContract,
    supported_long_horizon_policies,
)
from fsffl.state.models import FrozenModel, LeagueRules, Position

from .models import ValueScale
from .shapley_intrinsic import (
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)


LONG_TERM_INTRINSIC_MODEL_VERSION = "long-term-intrinsic-shapley-y4-y7-v1"
LONG_TERM_INTRINSIC_CONTRACT_VERSION = (
    "long-term-intrinsic-shadow-contract-v1:authority-envelope"
)
LONG_TERM_INTRINSIC_RAW_QUANTITY = (
    "mean_annual_governed_shapley_marginal_fantasy_points_y4_y7"
)
LONG_TERM_INTRINSIC_SCALE = ValueScale(
    scale_id="fsffl-long-term-intrinsic-index",
    version="long-term-y4-y7-v1",
    unit_label="Long-Term Intrinsic within-lens rank index",
)
LONG_TERM_INTRINSIC_HORIZONS = (4, 5, 6, 7)


class LongTermPolicyContribution(FrozenModel):
    policy_id: str
    central_shapley: float
    lo80_shapley: float
    hi80_shapley: float
    lo90_shapley: float
    hi90_shapley: float
    forecast_model_version: str
    forecast_source: str
    evidence_path: str

    @model_validator(mode="after")
    def validate_intervals(self) -> "LongTermPolicyContribution":
        if not (
            self.lo90_shapley
            <= self.lo80_shapley
            <= self.central_shapley
            <= self.hi80_shapley
            <= self.hi90_shapley
        ):
            raise ValueError("long-term annual Shapley uncertainty must be ordered")
        return self


class LongTermAnnualAuthority(FrozenModel):
    year_index: Annotated[int, Field(ge=4, le=7)]
    target_season: Annotated[int, Field(ge=2000)]
    authority_kind: Literal["exact", "set_valued"]
    supported_policies: tuple[str, ...]
    policy_contributions: tuple[LongTermPolicyContribution, ...]
    authority_low: float
    reference_center: float
    authority_high: float
    combined_lo80: float
    combined_hi80: float
    combined_lo90: float
    combined_hi90: float

    @model_validator(mode="after")
    def validate_authority(self) -> "LongTermAnnualAuthority":
        policies = tuple(sorted(item.policy_id for item in self.policy_contributions))
        if policies != tuple(sorted(self.supported_policies)):
            raise ValueError(
                "annual Long-Term policy contributions must match authority set"
            )
        if self.authority_kind == "exact" and len(self.supported_policies) != 1:
            raise ValueError("exact Long-Term authority requires one supported policy")
        if self.authority_kind == "set_valued" and len(self.supported_policies) <= 1:
            raise ValueError(
                "set-valued Long-Term authority requires multiple policies"
            )
        if not self.authority_low <= self.reference_center <= self.authority_high:
            raise ValueError("Long-Term annual authority bounds are unordered")
        if not (
            self.combined_lo90
            <= self.combined_lo80
            <= self.combined_hi80
            <= self.combined_hi90
        ):
            raise ValueError("Long-Term annual combined uncertainty is unordered")
        return self


class LongTermModelAuthority(FrozenModel):
    low: float
    reference_center: float
    high: float
    width: Annotated[float, Field(ge=0.0)]
    exact_horizons: tuple[int, ...]
    unresolved_horizons: tuple[int, ...]
    policy_sets_by_horizon: dict[str, tuple[str, ...]]

    @model_validator(mode="after")
    def validate_bounds(self) -> "LongTermModelAuthority":
        if not self.low <= self.reference_center <= self.high:
            raise ValueError("Long-Term model-authority bounds are unordered")
        if not math.isclose(
            self.width,
            self.high - self.low,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError("Long-Term model-authority width does not reconcile")
        return self


class LongTermWithinModelUncertainty(FrozenModel):
    """Outcome uncertainty kept distinct from Forecast model-authority disagreement."""

    combined_outer_80: tuple[float, float]
    combined_outer_90: tuple[float, float]
    cross_horizon_covariance_validated: bool = False
    cumulative_standard_deviation_authorized: bool = False
    semantics: str = (
        "Annual within-model residual/conformal scenarios are propagated through "
        "Shapley and then enveloped across the supported Forecast-policy set. "
        "No cross-horizon standard deviation is asserted."
    )

    @model_validator(mode="after")
    def validate_uncertainty(self) -> "LongTermWithinModelUncertainty":
        lo80, hi80 = self.combined_outer_80
        lo90, hi90 = self.combined_outer_90
        if not lo90 <= lo80 <= hi80 <= hi90:
            raise ValueError("Long-Term combined uncertainty bands are unordered")
        if self.cross_horizon_covariance_validated:
            raise ValueError(
                "Long-Term shadow does not authorize cross-horizon covariance"
            )
        if self.cumulative_standard_deviation_authorized:
            raise ValueError(
                "Long-Term shadow does not authorize cumulative standard deviation"
            )
        return self


class LongTermIntrinsicPlayerEstimate(FrozenModel):
    player_id: str
    position: Position
    annual: tuple[
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
        LongTermAnnualAuthority,
    ]
    model_authority: LongTermModelAuthority
    within_model_uncertainty: LongTermWithinModelUncertainty
    percentile_reference: Annotated[float, Field(ge=0.0, le=1.0)]
    value_index_reference_0_10000: Annotated[float, Field(ge=0.0, le=10000.0)]
    raw_quantity: str = LONG_TERM_INTRINSIC_RAW_QUANTITY
    display_scale: ValueScale = LONG_TERM_INTRINSIC_SCALE
    model_version: str = LONG_TERM_INTRINSIC_MODEL_VERSION

    @model_validator(mode="after")
    def validate_player_estimate(self) -> "LongTermIntrinsicPlayerEstimate":
        if not self.player_id.strip():
            raise ValueError("Long-Term Intrinsic player_id cannot be blank")
        if tuple(row.year_index for row in self.annual) != LONG_TERM_INTRINSIC_HORIZONS:
            raise ValueError("Long-Term Intrinsic requires literal Y4-Y7 annual records")
        if self.raw_quantity != LONG_TERM_INTRINSIC_RAW_QUANTITY:
            raise ValueError("Long-Term Intrinsic raw quantity is not governed")
        if self.display_scale != LONG_TERM_INTRINSIC_SCALE:
            raise ValueError("Long-Term Intrinsic display scale is not governed")
        return self


class LongTermIntrinsicShadowContract(FrozenModel):
    evaluation_season: Annotated[int, Field(ge=2000)]
    target_years: tuple[int, int, int, int]
    forecast_contract_version: str
    forecast_model_version: str
    authority_map_version: str = LONG_HORIZON_AUTHORITY_MAP_VERSION
    authority_map_sha256: str = LONG_HORIZON_AUTHORITY_MAP_SHA256
    value_model_version: str = LONG_TERM_INTRINSIC_MODEL_VERSION
    contract_version: str = LONG_TERM_INTRINSIC_CONTRACT_VERSION
    raw_quantity: str = LONG_TERM_INTRINSIC_RAW_QUANTITY
    display_scale: ValueScale = LONG_TERM_INTRINSIC_SCALE
    permutations: Annotated[int, Field(ge=1)]
    base_seed: int
    horizon_seeds: tuple[int, int, int, int]
    input_fingerprint: str
    max_abs_shapley_efficiency_residual: Annotated[float, Field(ge=0.0)]
    estimates: tuple[LongTermIntrinsicPlayerEstimate, ...]
    status: Literal["shadow_ready"] = "shadow_ready"
    authoritative_for_product_ranking: bool = False
    current_intrinsic_replaced: bool = False
    cross_lens_additive: bool = False

    @model_validator(mode="after")
    def validate_shadow(self) -> "LongTermIntrinsicShadowContract":
        if self.target_years != tuple(
            self.evaluation_season + horizon - 1
            for horizon in LONG_TERM_INTRINSIC_HORIZONS
        ):
            raise ValueError("Long-Term target years must align to literal Y4-Y7")
        if self.authority_map_version != LONG_HORIZON_AUTHORITY_MAP_VERSION:
            raise ValueError("Long-Term authority-map version is not governed")
        if self.authority_map_sha256 != LONG_HORIZON_AUTHORITY_MAP_SHA256:
            raise ValueError("Long-Term authority-map hash is not governed")
        if self.value_model_version != LONG_TERM_INTRINSIC_MODEL_VERSION:
            raise ValueError("Long-Term Value model version is not governed")
        if self.permutations != FROZEN_SHAPLEY_PERMUTATIONS:
            raise ValueError("Long-Term shadow requires the governed 2,048 permutations")
        if self.authoritative_for_product_ranking:
            raise ValueError("Long-Term shadow cannot claim product ranking authority")
        if self.current_intrinsic_replaced:
            raise ValueError("Long-Term shadow cannot replace Current Intrinsic")
        if self.cross_lens_additive:
            raise ValueError("Current and Long-Term Intrinsic are not additive")
        if not self.input_fingerprint.strip():
            raise ValueError("Long-Term input fingerprint cannot be blank")
        return self


def _semantic_forecast_payload(
    forecast_contract: LongHorizonForecastAuthorityContract,
) -> dict[str, object]:
    return {
        "contract_version": forecast_contract.contract_version,
        "authority_map_version": forecast_contract.authority_map_version,
        "authority_map_sha256": forecast_contract.authority_map_sha256,
        "evaluation_season": forecast_contract.evaluation_season,
        "scoring_coordinate": forecast_contract.scoring_coordinate,
        "forecast_model_version": forecast_contract.forecast_model_version,
        "forecast_source": forecast_contract.forecast_source,
        "forecasts": [
            row.model_dump(mode="json")
            for row in sorted(
                forecast_contract.forecasts,
                key=lambda item: (
                    item.player_id,
                    int(item.year_index),
                    item.policy_id,
                ),
            )
        ],
    }


def long_term_intrinsic_input_fingerprint(
    forecast_contract: LongHorizonForecastAuthorityContract,
    *,
    rules: LeagueRules,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
    seed: int = FROZEN_SHAPLEY_SEED,
) -> str:
    """Stable semantic identity; audit-only/volatile provenance is excluded."""

    payload = {
        "forecast": _semantic_forecast_payload(forecast_contract),
        "league_rules": rules.model_dump(mode="json"),
        "value_model_version": LONG_TERM_INTRINSIC_MODEL_VERSION,
        "raw_quantity": LONG_TERM_INTRINSIC_RAW_QUANTITY,
        "display_scale": LONG_TERM_INTRINSIC_SCALE.model_dump(mode="json"),
        "permutations": permutations,
        "base_seed": seed,
        "horizon_seed_derivation": "base_seed+literal_year_index",
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _rank_calibration(
    reference_centers: dict[str, float],
) -> dict[str, tuple[float, float]]:
    """Rank-calibrate this lens only; equal raw centers receive equal standing."""

    if not reference_centers:
        return {}
    if len(reference_centers) == 1:
        player_id = next(iter(reference_centers))
        return {player_id: (1.0, 10000.0)}

    values = tuple(reference_centers.values())
    denominator = len(values) - 1
    output: dict[str, tuple[float, float]] = {}
    for player_id, value in reference_centers.items():
        below = sum(candidate < value for candidate in values)
        equal_other = sum(candidate == value for candidate in values) - 1
        percentile = (below + 0.5 * equal_other) / denominator
        percentile = max(0.0, min(1.0, percentile))
        output[player_id] = (percentile, 10000.0 * percentile)
    return output


def build_long_term_intrinsic_shadow(
    forecast_contract: LongHorizonForecastAuthorityContract,
    *,
    rules: LeagueRules,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
    seed: int = FROZEN_SHAPLEY_SEED,
) -> LongTermIntrinsicShadowContract:
    """Build the frozen non-authoritative Y4-Y7 Long-Term Intrinsic consumer."""

    if permutations != FROZEN_SHAPLEY_PERMUTATIONS:
        raise ValueError("Long-Term Intrinsic requires exactly 2,048 Shapley permutations")
    if forecast_contract.scoring_coordinate != CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE:
        raise ValueError("Long-Term Intrinsic requires the connected-league scoring coordinate")

    rows_by_player = {
        player_id: tuple(
            row for row in forecast_contract.forecasts if row.player_id == player_id
        )
        for player_id in forecast_contract.player_ids
    }
    position_by_player: dict[str, Position] = {}
    for player_id, rows in rows_by_player.items():
        positions = {row.position for row in rows}
        if len(positions) != 1:
            raise ValueError("Long-Term Intrinsic requires one stable position per player")
        position_by_player[player_id] = next(iter(positions))

    caps = subset_caps_from_rules(rules)
    policy_contributions: dict[
        tuple[str, int, str], LongTermPolicyContribution
    ] = {}
    max_efficiency_residual = 0.0

    for year_index in LONG_TERM_INTRINSIC_HORIZONS:
        for policy_id in LONG_HORIZON_POLICIES:
            board = tuple(
                sorted(
                    (
                        row
                        for row in forecast_contract.forecasts
                        if int(row.year_index) == year_index
                        and row.policy_id == policy_id
                    ),
                    key=lambda row: row.player_id,
                )
            )
            if len(board) != len(forecast_contract.player_ids):
                raise ValueError(
                    f"Long-Term global policy board incomplete: Y{year_index} {policy_id}"
                )
            players = [
                (
                    row.player_id,
                    row.position.value,
                    float(row.central_expectation),
                )
                for row in board
            ]
            scenarios = {
                row.player_id: (
                    float(row.central_expectation),
                    max(
                        0.0,
                        float(row.central_expectation)
                        - float(row.absolute_error_80),
                    ),
                    float(row.central_expectation) + float(row.absolute_error_80),
                    max(
                        0.0,
                        float(row.central_expectation)
                        - float(row.absolute_error_90),
                    ),
                    float(row.central_expectation) + float(row.absolute_error_90),
                )
                for row in board
            }
            result = monte_carlo_shapley_scenarios(
                players,
                scenarios,
                caps,
                permutations=permutations,
                seed=seed + year_index,
            )
            max_efficiency_residual = max(
                max_efficiency_residual,
                abs(float(result.efficiency_residual)),
            )
            for row in board:
                values = result.estimates[row.player_id]
                policy_contributions[(row.player_id, year_index, policy_id)] = (
                    LongTermPolicyContribution(
                        policy_id=policy_id,
                        central_shapley=float(values[0]),
                        lo80_shapley=float(values[1]),
                        hi80_shapley=float(values[2]),
                        lo90_shapley=float(values[3]),
                        hi90_shapley=float(values[4]),
                        forecast_model_version=row.model_version,
                        forecast_source=row.source,
                        evidence_path=row.evidence_path,
                    )
                )

    annual_by_player: dict[str, tuple[LongTermAnnualAuthority, ...]] = {}
    reference_centers: dict[str, float] = {}
    model_authority_by_player: dict[str, LongTermModelAuthority] = {}
    uncertainty_by_player: dict[str, LongTermWithinModelUncertainty] = {}

    for player_id in forecast_contract.player_ids:
        position = position_by_player[player_id]
        annual: list[LongTermAnnualAuthority] = []
        for year_index in LONG_TERM_INTRINSIC_HORIZONS:
            supported = supported_long_horizon_policies(position, year_index)
            contributions = tuple(
                policy_contributions[(player_id, year_index, policy_id)]
                for policy_id in supported
            )
            central = [item.central_shapley for item in contributions]
            lo80 = [item.lo80_shapley for item in contributions]
            hi80 = [item.hi80_shapley for item in contributions]
            lo90 = [item.lo90_shapley for item in contributions]
            hi90 = [item.hi90_shapley for item in contributions]
            authority_low = min(central)
            authority_high = max(central)
            annual.append(
                LongTermAnnualAuthority(
                    year_index=year_index,
                    target_season=(
                        forecast_contract.evaluation_season + year_index - 1
                    ),
                    authority_kind=(
                        "exact" if len(supported) == 1 else "set_valued"
                    ),
                    supported_policies=tuple(supported),
                    policy_contributions=contributions,
                    authority_low=authority_low,
                    reference_center=(authority_low + authority_high) / 2.0,
                    authority_high=authority_high,
                    combined_lo80=min(lo80),
                    combined_hi80=max(hi80),
                    combined_lo90=min(lo90),
                    combined_hi90=max(hi90),
                )
            )

        annual_tuple = tuple(annual)
        if len(annual_tuple) != 4:
            raise ValueError("Long-Term Intrinsic requires exactly four annual horizons")
        typed_annual = (
            annual_tuple[0],
            annual_tuple[1],
            annual_tuple[2],
            annual_tuple[3],
        )
        low = sum(item.authority_low for item in typed_annual) / 4.0
        high = sum(item.authority_high for item in typed_annual) / 4.0
        center = (low + high) / 2.0
        exact_horizons = tuple(
            item.year_index
            for item in typed_annual
            if item.authority_kind == "exact"
        )
        unresolved_horizons = tuple(
            item.year_index
            for item in typed_annual
            if item.authority_kind == "set_valued"
        )
        annual_by_player[player_id] = typed_annual
        reference_centers[player_id] = center
        model_authority_by_player[player_id] = LongTermModelAuthority(
            low=low,
            reference_center=center,
            high=high,
            width=high - low,
            exact_horizons=exact_horizons,
            unresolved_horizons=unresolved_horizons,
            policy_sets_by_horizon={
                f"Y{item.year_index}": item.supported_policies
                for item in typed_annual
            },
        )
        uncertainty_by_player[player_id] = LongTermWithinModelUncertainty(
            combined_outer_80=(
                sum(item.combined_lo80 for item in typed_annual) / 4.0,
                sum(item.combined_hi80 for item in typed_annual) / 4.0,
            ),
            combined_outer_90=(
                sum(item.combined_lo90 for item in typed_annual) / 4.0,
                sum(item.combined_hi90 for item in typed_annual) / 4.0,
            ),
        )

    rank = _rank_calibration(reference_centers)
    estimates = tuple(
        LongTermIntrinsicPlayerEstimate(
            player_id=player_id,
            position=position_by_player[player_id],
            annual=annual_by_player[player_id],  # type: ignore[arg-type]
            model_authority=model_authority_by_player[player_id],
            within_model_uncertainty=uncertainty_by_player[player_id],
            percentile_reference=rank[player_id][0],
            value_index_reference_0_10000=rank[player_id][1],
        )
        for player_id in forecast_contract.player_ids
    )

    return LongTermIntrinsicShadowContract(
        evaluation_season=forecast_contract.evaluation_season,
        target_years=tuple(
            forecast_contract.evaluation_season + horizon - 1
            for horizon in LONG_TERM_INTRINSIC_HORIZONS
        ),  # type: ignore[arg-type]
        forecast_contract_version=forecast_contract.contract_version,
        forecast_model_version=forecast_contract.forecast_model_version,
        permutations=permutations,
        base_seed=seed,
        horizon_seeds=tuple(
            seed + horizon for horizon in LONG_TERM_INTRINSIC_HORIZONS
        ),  # type: ignore[arg-type]
        input_fingerprint=long_term_intrinsic_input_fingerprint(
            forecast_contract,
            rules=rules,
            permutations=permutations,
            seed=seed,
        ),
        max_abs_shapley_efficiency_residual=max_efficiency_residual,
        estimates=estimates,
    )
