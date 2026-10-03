from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Literal, Mapping

from pydantic import Field

from fsffl.state.models import FrozenModel, LeagueRules, Position

from .long_term_intrinsic import (
    LongTermIntrinsicPlayerEstimate,
    LongTermIntrinsicShadowContract,
)
from .shapley_intrinsic import subset_caps_from_rules
from .shapley_intrinsic_contract import (
    ShapleyIntrinsicContract,
    ShapleyIntrinsicPlayerEstimate,
)


FOUNDATION4_TERMINAL_ARTIFACT_PATH = Path(__file__).with_name(
    "foundation4_career_tail_artifact.json"
)
FOUNDATION4_TERMINAL_ARTIFACT_SHA256 = (
    "ab2390ef8bb77d14f958781bd7ac3d87b1baffadf805768ef156ce818cc97e81"
)
FOUNDATION4_HOLISTIC_MODEL_VERSION = (
    "foundation4-career-forward-shadow-v1:raw-y1-y7-plus-governed-y8plus"
)
FOUNDATION4_HOLISTIC_ENDPOINT_PATH = "/api/value/long-term-intrinsic-shadow-v1"

_TERMINAL_ARTIFACT = json.loads(
    FOUNDATION4_TERMINAL_ARTIFACT_PATH.read_text(encoding="utf-8")
)
_ARTIFACT_CANONICAL = json.dumps(
    _TERMINAL_ARTIFACT, sort_keys=True, separators=(",", ":")
).encode()
if hashlib.sha256(_ARTIFACT_CANONICAL).hexdigest() != FOUNDATION4_TERMINAL_ARTIFACT_SHA256:
    raise ValueError("Foundation 4 terminal artifact semantic hash mismatch")


class CareerTailPlayerFeatures(FrozenModel):
    player_id: str
    position: Position
    age_years: float = Field(ge=0)
    experience_years: float = Field(ge=0)
    current_points: float = Field(ge=0)
    prior_points: float | None = Field(default=None, ge=0)


class CareerTailModelPrediction(FrozenModel):
    model_id: Literal["direct_ridge", "two_part_state"]
    expected_tail_y8_plus: float = Field(ge=0)
    residual_q80: float = Field(ge=0)
    residual_q90: float = Field(ge=0)
    residual_n: int = Field(ge=1)
    historical_outer80_label_coverage: float = Field(ge=0, le=1)
    historical_outer90_label_coverage: float = Field(ge=0, le=1)
    outer80_is_calibrated_product_interval: bool = False
    outer90_is_calibrated_product_interval: bool = False


class CareerTailModelAuthority(FrozenModel):
    authority_kind: Literal["coarse_set_valued"] = "coarse_set_valued"
    low: float = Field(ge=0)
    reference_center: float = Field(ge=0)
    high: float = Field(ge=0)
    width: float = Field(ge=0)
    supported_models: tuple[str, ...]


class CareerTailOutcomeUncertainty(FrozenModel):
    semantics: Literal[
        "historical_absolute_residual_evidence_not_product_interval"
    ] = "historical_absolute_residual_evidence_not_product_interval"
    model_residuals: tuple[CareerTailModelPrediction, ...]
    corrected_holdout_outer80_coverage: float = Field(ge=0, le=1)
    corrected_holdout_outer90_coverage: float = Field(ge=0, le=1)


class CareerTailEstimate(FrozenModel):
    player_id: str
    position: Position
    lineup_capacity_signature: str
    terminal_model_version: str
    terminal_target_version: str
    artifact_id: int
    artifact_digest: str
    input_features: CareerTailPlayerFeatures
    model_predictions: tuple[CareerTailModelPrediction, ...]
    model_authority: CareerTailModelAuthority
    outcome_uncertainty: CareerTailOutcomeUncertainty


class HolisticCareerModelAuthority(FrozenModel):
    low: float
    reference_center: float
    high: float
    width: float
    y1_y3_raw_exact: float
    y4_y7_authority_low: float
    y4_y7_reference_center: float
    y4_y7_authority_high: float
    tail_authority_low: float
    tail_reference_center: float
    tail_authority_high: float
    semantics: Literal[
        "arithmetic_sum_of_compatible_raw_shapley_authority_coordinates"
    ] = "arithmetic_sum_of_compatible_raw_shapley_authority_coordinates"
    probabilistic_confidence_interval: bool = False


class HolisticOutcomeUncertainty(FrozenModel):
    current_intrinsic_horizon_uncertainty: tuple[Mapping[str, object], ...]
    y4_y7_within_model_uncertainty: Mapping[str, object]
    terminal_residual_evidence: CareerTailOutcomeUncertainty
    cumulative_career_standard_deviation: None = None
    covariance_authorized: bool = False


class HolisticCareerForwardPlayerEstimate(FrozenModel):
    player_id: str
    position: Position
    career_forward_raw_reference: float
    annual_raw_y1_y3: tuple[float, float, float]
    annual_y4_y7: tuple[Mapping[str, object], ...]
    tail_y8_plus: CareerTailEstimate
    model_authority: HolisticCareerModelAuthority
    outcome_uncertainty: HolisticOutcomeUncertainty
    current_intrinsic_raw_discounted_scalar: float
    current_intrinsic_kept_separate: bool = True
    display_indexes_combined: bool = False


class HolisticCareerForwardCoverage(FrozenModel):
    player_count: int = Field(ge=0)
    current_intrinsic_players: int = Field(ge=0)
    y4_y7_players: int = Field(ge=0)
    terminal_players: int = Field(ge=0)
    fully_materialized_players: int = Field(ge=0)
    missing_player_ids: tuple[str, ...] = ()


class HolisticCareerForwardShadow(FrozenModel):
    model_version: str = FOUNDATION4_HOLISTIC_MODEL_VERSION
    endpoint_path: str = FOUNDATION4_HOLISTIC_ENDPOINT_PATH
    evaluation_season: int
    lineup_capacity_signature: str
    current_intrinsic_contract_version: str
    y4_y7_contract_version: str
    terminal_model_version: str
    terminal_artifact_digest: str
    quantity_semantics: Literal[
        "sum_raw_shapley_y1_y7_plus_direct_cumulative_y8plus_tail"
    ] = "sum_raw_shapley_y1_y7_plus_direct_cumulative_y8plus_tail"
    current_intrinsic_replaced: bool = False
    display_scaling_applied: bool = False
    market_inputs_used: bool = False
    discounting_applied_to_holistic_raw: bool = False
    cumulative_outcome_sd_authorized: bool = False
    coverage: HolisticCareerForwardCoverage
    estimates: tuple[HolisticCareerForwardPlayerEstimate, ...]
    semantic_fingerprint: str


def lineup_capacity_signature(rules: LeagueRules) -> str:
    payload = {
        "team_count": rules.team_count,
        "lineup": [
            {"slot": row.slot.value, "count": row.count}
            for row in rules.lineup
        ],
        "caps": subset_caps_from_rules(rules),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _feature_vector(features: CareerTailPlayerFeatures) -> tuple[float, ...]:
    prior = 0.0 if features.prior_points is None else float(features.prior_points)
    return (
        float(features.age_years),
        float(features.experience_years),
        math.log1p(float(features.current_points)),
        math.log1p(prior),
        1.0 if features.prior_points is None else 0.0,
    )


def _standardize(model: Mapping[str, object], values: tuple[float, ...]) -> tuple[float, ...]:
    means = tuple(float(x) for x in model["scaler_mean"])  # type: ignore[index]
    scales = tuple(float(x) for x in model["scaler_scale"])  # type: ignore[index]
    if len(values) != len(means) or len(values) != len(scales):
        raise ValueError("terminal feature/scaler dimension mismatch")
    return tuple(
        (value - mean) / (scale if scale != 0.0 else 1.0)
        for value, mean, scale in zip(values, means, scales, strict=True)
    )


def _linear(intercept: float, coefficients: object, values: tuple[float, ...]) -> float:
    coefs = tuple(float(x) for x in coefficients)  # type: ignore[arg-type]
    if len(coefs) != len(values):
        raise ValueError("terminal coefficient dimension mismatch")
    return float(intercept) + sum(
        coefficient * value for coefficient, value in zip(coefs, values, strict=True)
    )


def _predict_one(model: Mapping[str, object], features: CareerTailPlayerFeatures) -> float:
    z = _standardize(model, _feature_vector(features))
    if str(model["kind"]) == "direct_ridge":
        log_tail = _linear(float(model["ridge_intercept"]), model["ridge_coefficients"], z)
        return max(
            0.0,
            math.exp(log_tail) * float(model["smearing_factor"]) - 1.0,
        )

    logit = _linear(float(model["logit_intercept"]), model["logit_coefficients"], z)
    probability = 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, logit))))
    positive_log_tail = _linear(
        float(model["positive_ridge_intercept"]),
        model["positive_ridge_coefficients"],
        z,
    )
    conditional = max(
        0.0,
        math.exp(positive_log_tail)
        * float(model["positive_smearing_factor"])
        - 1.0,
    )
    return probability * conditional


def build_career_tail_estimate(
    features: CareerTailPlayerFeatures,
    *,
    rules: LeagueRules,
) -> CareerTailEstimate:
    signature = lineup_capacity_signature(rules)
    expected = str(_TERMINAL_ARTIFACT["lineup_capacity_signature"])
    if signature != expected:
        raise ValueError(
            "Foundation 4 terminal artifact lineup-capacity signature mismatch: "
            f"{signature} != {expected}"
        )
    position = features.position.value
    supported = tuple(str(x) for x in _TERMINAL_ARTIFACT["supported_models"])
    predictions: list[CareerTailModelPrediction] = []
    for model_id in supported:
        model = _TERMINAL_ARTIFACT["fitted_models"][model_id][position]
        residual = _TERMINAL_ARTIFACT["residual_bands"][model_id][position]
        predictions.append(
            CareerTailModelPrediction(
                model_id=model_id,  # type: ignore[arg-type]
                expected_tail_y8_plus=_predict_one(model, features),
                residual_q80=float(residual["q80"]),
                residual_q90=float(residual["q90"]),
                residual_n=int(residual["n"]),
                historical_outer80_label_coverage=float(
                    _TERMINAL_ARTIFACT["final_holdout"][
                        "combined_outer_80_coverage"
                    ]
                ),
                historical_outer90_label_coverage=float(
                    _TERMINAL_ARTIFACT["final_holdout"][
                        "combined_outer_90_coverage"
                    ]
                ),
                outer80_is_calibrated_product_interval=False,
                outer90_is_calibrated_product_interval=False,
            )
        )
    values = tuple(row.expected_tail_y8_plus for row in predictions)
    low, high = min(values), max(values)
    center = (low + high) / 2.0
    uncertainty = CareerTailOutcomeUncertainty(
        model_residuals=tuple(predictions),
        corrected_holdout_outer80_coverage=float(
            _TERMINAL_ARTIFACT["final_holdout"]["combined_outer_80_coverage"]
        ),
        corrected_holdout_outer90_coverage=float(
            _TERMINAL_ARTIFACT["final_holdout"]["combined_outer_90_coverage"]
        ),
    )
    return CareerTailEstimate(
        player_id=features.player_id,
        position=features.position,
        lineup_capacity_signature=signature,
        terminal_model_version=str(_TERMINAL_ARTIFACT["model_version"]),
        terminal_target_version=str(_TERMINAL_ARTIFACT["target_version"]),
        artifact_id=int(_TERMINAL_ARTIFACT["artifact_id"]),
        artifact_digest=str(_TERMINAL_ARTIFACT["artifact_digest"]),
        input_features=features,
        model_predictions=tuple(predictions),
        model_authority=CareerTailModelAuthority(
            low=low,
            reference_center=center,
            high=high,
            width=high - low,
            supported_models=supported,
        ),
        outcome_uncertainty=uncertainty,
    )


def _semantic_fingerprint(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _holistic_semantic_payload(
    *,
    model_version: str,
    evaluation_season: int,
    lineup_capacity_signature_value: str,
    current_intrinsic_contract_version: str,
    y4_y7_contract_version: str,
    terminal_artifact_digest: str,
    estimates: tuple[HolisticCareerForwardPlayerEstimate, ...] | list[HolisticCareerForwardPlayerEstimate],
) -> dict[str, object]:
    return {
        "model_version": model_version,
        "evaluation_season": evaluation_season,
        "lineup_capacity_signature": lineup_capacity_signature_value,
        "current_intrinsic_contract_version": current_intrinsic_contract_version,
        "y4_y7_contract_version": y4_y7_contract_version,
        "terminal_artifact_digest": terminal_artifact_digest,
        "estimates": [
            {
                "player_id": row.player_id,
                "raw_reference": row.career_forward_raw_reference,
                "authority": row.model_authority.model_dump(mode="json"),
            }
            for row in estimates
        ],
    }


def holistic_shadow_semantic_fingerprint(
    shadow: HolisticCareerForwardShadow,
) -> str:
    """Recompute the persisted Foundation 4 semantic identity from served output."""

    return _semantic_fingerprint(
        _holistic_semantic_payload(
            model_version=shadow.model_version,
            evaluation_season=shadow.evaluation_season,
            lineup_capacity_signature_value=shadow.lineup_capacity_signature,
            current_intrinsic_contract_version=(
                shadow.current_intrinsic_contract_version
            ),
            y4_y7_contract_version=shadow.y4_y7_contract_version,
            terminal_artifact_digest=shadow.terminal_artifact_digest,
            estimates=shadow.estimates,
        )
    )


def build_holistic_career_forward_shadow(
    current_intrinsic: ShapleyIntrinsicContract,
    y4_y7: LongTermIntrinsicShadowContract,
    terminal_features: Mapping[str, CareerTailPlayerFeatures],
    *,
    rules: LeagueRules,
) -> HolisticCareerForwardShadow:
    signature = lineup_capacity_signature(rules)
    expected = str(_TERMINAL_ARTIFACT["lineup_capacity_signature"])
    if signature != expected:
        raise ValueError(
            "Foundation 4 holistic shadow requires the governed lineup-capacity "
            f"signature {expected}; received {signature}"
        )
    if current_intrinsic.evaluation_season != y4_y7.evaluation_season:
        raise ValueError("Y1-Y3 and Y4-Y7 evaluation seasons must match")

    current_by_id = {row.player_id: row for row in current_intrinsic.estimates}
    long_by_id = {row.player_id: row for row in y4_y7.estimates}
    all_ids = set(current_by_id) | set(long_by_id) | set(terminal_features)
    common_ids = set(current_by_id) & set(long_by_id) & set(terminal_features)
    missing = tuple(sorted(all_ids - common_ids))
    if missing:
        raise ValueError(
            "Foundation 4 holistic shadow requires full coordinate coverage; "
            f"missing/incompatible players={missing[:10]}"
        )

    estimates: list[HolisticCareerForwardPlayerEstimate] = []
    for player_id in sorted(common_ids):
        current = current_by_id[player_id]
        long = long_by_id[player_id]
        features = terminal_features[player_id]
        if long.position != features.position:
            raise ValueError(f"terminal/Y4-Y7 position mismatch for {player_id}")
        tail = build_career_tail_estimate(features, rules=rules)
        near = tuple(
            float(item.raw_shapley_contribution) for item in current.contributions
        )
        y4_y7_low = sum(float(item.authority_low) for item in long.annual)
        y4_y7_center = sum(float(item.reference_center) for item in long.annual)
        y4_y7_high = sum(float(item.authority_high) for item in long.annual)
        near_raw = sum(near)
        low = near_raw + y4_y7_low + tail.model_authority.low
        center = (
            near_raw
            + y4_y7_center
            + tail.model_authority.reference_center
        )
        high = near_raw + y4_y7_high + tail.model_authority.high
        estimates.append(
            HolisticCareerForwardPlayerEstimate(
                player_id=player_id,
                position=long.position,
                career_forward_raw_reference=center,
                annual_raw_y1_y3=near,  # type: ignore[arg-type]
                annual_y4_y7=tuple(
                    item.model_dump(mode="json") for item in long.annual
                ),
                tail_y8_plus=tail,
                model_authority=HolisticCareerModelAuthority(
                    low=low,
                    reference_center=center,
                    high=high,
                    width=high - low,
                    y1_y3_raw_exact=near_raw,
                    y4_y7_authority_low=y4_y7_low,
                    y4_y7_reference_center=y4_y7_center,
                    y4_y7_authority_high=y4_y7_high,
                    tail_authority_low=tail.model_authority.low,
                    tail_reference_center=tail.model_authority.reference_center,
                    tail_authority_high=tail.model_authority.high,
                ),
                outcome_uncertainty=HolisticOutcomeUncertainty(
                    current_intrinsic_horizon_uncertainty=tuple(
                        item.uncertainty.model_dump(mode="json")
                        for item in current.contributions
                    ),
                    y4_y7_within_model_uncertainty=(
                        long.within_model_uncertainty.model_dump(mode="json")
                    ),
                    terminal_residual_evidence=tail.outcome_uncertainty,
                ),
                current_intrinsic_raw_discounted_scalar=float(
                    current.raw_intrinsic_value
                ),
            )
        )

    fingerprint_payload = _holistic_semantic_payload(
        model_version=FOUNDATION4_HOLISTIC_MODEL_VERSION,
        evaluation_season=current_intrinsic.evaluation_season,
        lineup_capacity_signature_value=signature,
        current_intrinsic_contract_version=current_intrinsic.contract_version,
        y4_y7_contract_version=y4_y7.contract_version,
        terminal_artifact_digest=str(_TERMINAL_ARTIFACT["artifact_digest"]),
        estimates=estimates,
    )
    return HolisticCareerForwardShadow(
        evaluation_season=current_intrinsic.evaluation_season,
        lineup_capacity_signature=signature,
        current_intrinsic_contract_version=current_intrinsic.contract_version,
        y4_y7_contract_version=y4_y7.contract_version,
        terminal_model_version=str(_TERMINAL_ARTIFACT["model_version"]),
        terminal_artifact_digest=str(_TERMINAL_ARTIFACT["artifact_digest"]),
        coverage=HolisticCareerForwardCoverage(
            player_count=len(estimates),
            current_intrinsic_players=len(current_by_id),
            y4_y7_players=len(long_by_id),
            terminal_players=len(terminal_features),
            fully_materialized_players=len(estimates),
            missing_player_ids=(),
        ),
        estimates=tuple(estimates),
        semantic_fingerprint=_semantic_fingerprint(fingerprint_payload),
    )


def terminal_artifact_metadata() -> Mapping[str, object]:
    return {
        "artifact_id": _TERMINAL_ARTIFACT["artifact_id"],
        "artifact_digest": _TERMINAL_ARTIFACT["artifact_digest"],
        "workflow_run_id": _TERMINAL_ARTIFACT["workflow_run_id"],
        "model_version": _TERMINAL_ARTIFACT["model_version"],
        "target_version": _TERMINAL_ARTIFACT["target_version"],
        "authority": _TERMINAL_ARTIFACT["authority"],
        "lineup_capacity_signature": _TERMINAL_ARTIFACT[
            "lineup_capacity_signature"
        ],
        "corrected_holdout_outer80_coverage": _TERMINAL_ARTIFACT[
            "final_holdout"
        ]["combined_outer_80_coverage"],
        "corrected_holdout_outer90_coverage": _TERMINAL_ARTIFACT[
            "final_holdout"
        ]["combined_outer_90_coverage"],
    }
