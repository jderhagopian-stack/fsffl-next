from __future__ import annotations

import hashlib
import json
import math
from importlib.resources import files
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, Position
from fsffl.value.shapley_intrinsic import subset_caps_from_rules


CAREER_TAIL_VALUE_CONSUMER_VERSION = "career-tail-value-consumer-v1"
CAREER_TAIL_RAW_QUANTITY = (
    "cumulative_governed_shapley_marginal_fantasy_points_y8_plus"
)
CAREER_TAIL_AUTHORITY = "coarse_set_valued_terminal"
CAREER_TAIL_SUPPORTED_MODELS = ("direct_ridge", "two_part_state")
CAREER_TAIL_FEATURES = (
    "age_years",
    "experience_years",
    "log_current_points",
    "log_prior_points",
    "prior_missing",
)
CAREER_TAIL_LEGACY_RESEARCH_LINEUP_CAPACITY_SIGNATURE = (
    "fe6d07a77a7f11cd61e1af476e9d6b3fe89b7e59c6aecdeab5eb61c991b21349"
)
CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE = (
    "a4d9a532c477b9fb2114a33009b94adbe15823748efec46d9701bdcddc8f5363"
)
CAREER_TAIL_RUNTIME_PACKAGE_SEMANTIC_SHA256 = (
    "33158a26d50e71809cf0f38a7d479fda05ccbaa9fbd5703ba894c1cba4560537"
)
CAREER_TAIL_RESEARCH_ARTIFACT_ID = 11263913850


def _canonical_package_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_fsffl_runtime_package() -> dict[str, object]:
    resource = files("fsffl.value").joinpath(
        "data/foundation4_career_tail_fsffl_2026.json"
    )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Foundation 4 career-tail runtime package is not an object")
    declared = str(payload.get("semantic_sha256") or "")
    semantic_payload = {
        key: value for key, value in payload.items() if key != "semantic_sha256"
    }
    actual = _canonical_package_digest(semantic_payload)
    if declared != CAREER_TAIL_RUNTIME_PACKAGE_SEMANTIC_SHA256 or actual != declared:
        raise ValueError("Foundation 4 career-tail runtime package semantic digest mismatch")
    if tuple(payload.get("supported_models") or ()) != CAREER_TAIL_SUPPORTED_MODELS:
        raise ValueError("Foundation 4 career-tail supported model set is not governed")
    if payload.get("lineup_capacity_signature") != CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE:
        raise ValueError("Foundation 4 career-tail lineup-capacity signature drifted")
    if payload.get("scoring_coordinate") != "connected_league_fantasy_points":
        raise ValueError("Foundation 4 career-tail scoring coordinate drifted")
    aggregation = payload.get("aggregation_semantics")
    if (
        not isinstance(aggregation, dict)
        or aggregation.get("cumulative_outcome_sd_authorized") is not False
        or aggregation.get("current_intrinsic_replaced") is not False
        or aggregation.get("discounting") != "none"
        or aggregation.get("display_indexes_combined") is not False
    ):
        raise ValueError("Foundation 4 career-tail aggregation semantics drifted")
    return payload


_CAREER_TAIL_RUNTIME_PACKAGE = _load_fsffl_runtime_package()
CAREER_TAIL_TARGET_VERSION = str(_CAREER_TAIL_RUNTIME_PACKAGE["target_version"])
CAREER_TAIL_MODEL_VERSION = str(_CAREER_TAIL_RUNTIME_PACKAGE["model_version"])
CAREER_TAIL_SCORING_COORDINATE = str(
    _CAREER_TAIL_RUNTIME_PACKAGE["scoring_coordinate"]
)
CAREER_TAIL_RESEARCH_RUN_ID = int(_CAREER_TAIL_RUNTIME_PACKAGE["research_run_id"])
# The retained workflow artifact packages the exact runtime JSON plus its generating
# evidence. The runtime provenance pins the semantic JSON identity directly.
CAREER_TAIL_RESEARCH_ARTIFACT_SHA256 = CAREER_TAIL_RUNTIME_PACKAGE_SEMANTIC_SHA256
CAREER_TAIL_SHAPLEY_PERMUTATIONS = int(
    _CAREER_TAIL_RUNTIME_PACKAGE["shapley_permutations"]
)
CAREER_TAIL_SHAPLEY_SEED = int(_CAREER_TAIL_RUNTIME_PACKAGE["shapley_seed"])


def _normalized_frozen_models() -> dict[str, dict[Position, dict[str, object]]]:
    raw_models = _CAREER_TAIL_RUNTIME_PACKAGE["fitted_models"]
    if not isinstance(raw_models, dict):
        raise ValueError("Foundation 4 career-tail fitted models are missing")
    output: dict[str, dict[Position, dict[str, object]]] = {}
    for model_id in CAREER_TAIL_SUPPORTED_MODELS:
        raw_by_position = raw_models.get(model_id)
        if not isinstance(raw_by_position, dict):
            raise ValueError(f"Foundation 4 career-tail model missing: {model_id}")
        typed: dict[Position, dict[str, object]] = {}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE):
            row = raw_by_position.get(position.value)
            if not isinstance(row, dict):
                raise ValueError(
                    f"Foundation 4 career-tail model missing {model_id}/{position.value}"
                )
            if model_id == "direct_ridge":
                typed[position] = {
                    "scaler_mean": tuple(row["scaler_mean"]),
                    "scaler_scale": tuple(row["scaler_scale"]),
                    "intercept": row["ridge_intercept"],
                    "coefficients": tuple(row["ridge_coefficients"]),
                    "smearing": row["smearing_factor"],
                }
            else:
                typed[position] = {
                    "scaler_mean": tuple(row["scaler_mean"]),
                    "scaler_scale": tuple(row["scaler_scale"]),
                    "logit_intercept": row["logit_intercept"],
                    "logit_coefficients": tuple(row["logit_coefficients"]),
                    "positive_intercept": row["positive_ridge_intercept"],
                    "positive_coefficients": tuple(
                        row["positive_ridge_coefficients"]
                    ),
                    "positive_smearing": row["positive_smearing_factor"],
                }
        output[model_id] = typed
    return output


def _normalized_residual_bands() -> dict[
    str, dict[Position, tuple[int, float, float]]
]:
    raw_bands = _CAREER_TAIL_RUNTIME_PACKAGE["residual_bands"]
    if not isinstance(raw_bands, dict):
        raise ValueError("Foundation 4 career-tail residual bands are missing")
    output: dict[str, dict[Position, tuple[int, float, float]]] = {}
    for model_id in CAREER_TAIL_SUPPORTED_MODELS:
        raw_by_position = raw_bands.get(model_id)
        if not isinstance(raw_by_position, dict):
            raise ValueError(
                f"Foundation 4 career-tail residual model missing: {model_id}"
            )
        output[model_id] = {}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE):
            row = raw_by_position.get(position.value)
            if not isinstance(row, dict):
                raise ValueError(
                    f"Foundation 4 career-tail residual missing {model_id}/{position.value}"
                )
            output[model_id][position] = (
                int(row["n"]),
                float(row["q80"]),
                float(row["q90"]),
            )
    return output


_FROZEN_MODELS = _normalized_frozen_models()
_RESIDUAL_BANDS = _normalized_residual_bands()

class CareerTailFeatures(FrozenModel):
    player_id: str
    position: Position
    age_years: Annotated[float, Field(ge=0.0)]
    experience_years: Annotated[float, Field(ge=0.0)]
    current_points: Annotated[float, Field(ge=0.0)]
    prior_points: Annotated[float | None, Field(ge=0.0)] = None
    current_points_coordinate: str = (
        "retrospective_completed_base_season_fantasy_production"
    )
    prior_points_coordinate: str = "retrospective_completed_prior_season_fantasy_production"
    live_feature_transport_limitation: str | None = None

    @model_validator(mode="after")
    def validate_feature_transport(self) -> "CareerTailFeatures":
        if not self.player_id.strip():
            raise ValueError("career-tail player_id cannot be blank")
        if not self.current_points_coordinate.strip() or not self.prior_points_coordinate.strip():
            raise ValueError("career-tail production coordinate identifiers cannot be blank")
        return self

    @property
    def feature_vector(self) -> tuple[float, float, float, float, float]:
        prior_missing = 1.0 if self.prior_points is None else 0.0
        return (
            float(self.age_years),
            float(self.experience_years),
            math.log1p(float(self.current_points)),
            math.log1p(float(self.prior_points or 0.0)),
            prior_missing,
        )


class CareerTailModelPrediction(FrozenModel):
    model_id: Literal["direct_ridge", "two_part_state"]
    central: Annotated[float, Field(ge=0.0)]
    outcome_lo80: Annotated[float, Field(ge=0.0)]
    outcome_hi80: Annotated[float, Field(ge=0.0)]
    outcome_lo90: Annotated[float, Field(ge=0.0)]
    outcome_hi90: Annotated[float, Field(ge=0.0)]
    residual_sample_n: Annotated[int, Field(ge=1)]
    residual_q80: Annotated[float, Field(ge=0.0)]
    residual_q90: Annotated[float, Field(ge=0.0)]

    @model_validator(mode="after")
    def validate_bands(self) -> "CareerTailModelPrediction":
        if not (
            self.outcome_lo90
            <= self.outcome_lo80
            <= self.central
            <= self.outcome_hi80
            <= self.outcome_hi90
        ):
            raise ValueError("career-tail outcome bands are unordered")
        return self


class CareerTailAuthority(FrozenModel):
    player_id: str
    position: Position
    features: CareerTailFeatures
    model_predictions: tuple[CareerTailModelPrediction, CareerTailModelPrediction]
    model_authority_low: Annotated[float, Field(ge=0.0)]
    reference_center: Annotated[float, Field(ge=0.0)]
    model_authority_high: Annotated[float, Field(ge=0.0)]
    outcome_outer_80: tuple[float, float]
    outcome_outer_90: tuple[float, float]
    lineup_capacity_signature: str = CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE
    raw_quantity: str = CAREER_TAIL_RAW_QUANTITY
    authority: Literal["coarse_set_valued_terminal"] = CAREER_TAIL_AUTHORITY
    target_version: str = CAREER_TAIL_TARGET_VERSION
    model_version: str = CAREER_TAIL_MODEL_VERSION
    value_consumer_version: str = CAREER_TAIL_VALUE_CONSUMER_VERSION
    research_run_id: int = CAREER_TAIL_RESEARCH_RUN_ID
    research_artifact_id: int = CAREER_TAIL_RESEARCH_ARTIFACT_ID
    research_artifact_sha256: str = CAREER_TAIL_RESEARCH_ARTIFACT_SHA256
    cumulative_outcome_sd_authorized: bool = False

    @model_validator(mode="after")
    def validate_authority(self) -> "CareerTailAuthority":
        if self.features.player_id != self.player_id or self.features.position != self.position:
            raise ValueError("career-tail feature identity must match estimate")
        ids = tuple(row.model_id for row in self.model_predictions)
        if ids != CAREER_TAIL_SUPPORTED_MODELS:
            raise ValueError("career-tail supported model set is not governed")
        if not self.model_authority_low <= self.reference_center <= self.model_authority_high:
            raise ValueError("career-tail model-authority bounds are unordered")
        lo80, hi80 = self.outcome_outer_80
        lo90, hi90 = self.outcome_outer_90
        if not lo90 <= lo80 <= self.reference_center <= hi80 <= hi90:
            raise ValueError("career-tail outer outcome bands are unordered")
        if self.cumulative_outcome_sd_authorized:
            raise ValueError("career-tail cumulative outcome standard deviation is not authorized")
        return self


def lineup_capacity_signature(rules: LeagueRules) -> str:
    # The Shapley economy consumes capacities, not the provider's source ordering
    # of lineup rows.  Hash only the semantic capacity coordinate so equivalent
    # Sleeper/canonical lineups receive the same identity.
    payload = {
        "team_count": rules.team_count,
        "caps": subset_caps_from_rules(rules),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _standardize(values: tuple[float, ...], model: dict[str, object]) -> tuple[float, ...]:
    means = tuple(float(value) for value in model["scaler_mean"])  # type: ignore[index]
    scales = tuple(float(value) for value in model["scaler_scale"])  # type: ignore[index]
    return tuple(
        (value - mean) / (scale if scale != 0.0 else 1.0)
        for value, mean, scale in zip(values, means, scales, strict=True)
    )


def _linear(intercept: float, coefficients: object, z: tuple[float, ...]) -> float:
    coefs = tuple(float(value) for value in coefficients)  # type: ignore[arg-type]
    return float(intercept) + sum(
        coefficient * value
        for coefficient, value in zip(coefs, z, strict=True)
    )


def _predict(model_id: str, position: Position, values: tuple[float, ...]) -> float:
    model = _FROZEN_MODELS[model_id][position]
    z = _standardize(values, model)
    if model_id == "direct_ridge":
        log_tail = _linear(float(model["intercept"]), model["coefficients"], z)
        return max(0.0, math.exp(log_tail) * float(model["smearing"]) - 1.0)

    logits = _linear(float(model["logit_intercept"]), model["logit_coefficients"], z)
    probability = 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, logits))))
    positive_log_tail = _linear(
        float(model["positive_intercept"]),
        model["positive_coefficients"],
        z,
    )
    positive_mean = max(
        0.0,
        math.exp(positive_log_tail) * float(model["positive_smearing"]) - 1.0,
    )
    return probability * positive_mean


def build_career_tail_authority(
    features: CareerTailFeatures,
    *,
    rules: LeagueRules,
) -> CareerTailAuthority:
    if (
        features.current_points_coordinate != CAREER_TAIL_SCORING_COORDINATE
        or features.prior_points_coordinate != CAREER_TAIL_SCORING_COORDINATE
    ):
        raise ValueError(
            "career-tail terminal features are outside the governed FSFFL scoring coordinate"
        )
    signature = lineup_capacity_signature(rules)
    if signature != CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE:
        raise ValueError(
            "career-tail terminal artifact is unavailable for this lineup-capacity signature"
        )

    predictions: list[CareerTailModelPrediction] = []
    for model_id in CAREER_TAIL_SUPPORTED_MODELS:
        central = _predict(model_id, features.position, features.feature_vector)
        sample_n, q80, q90 = _RESIDUAL_BANDS[model_id][features.position]
        predictions.append(
            CareerTailModelPrediction(
                model_id=model_id,  # type: ignore[arg-type]
                central=central,
                outcome_lo80=max(0.0, central - q80),
                outcome_hi80=central + q80,
                outcome_lo90=max(0.0, central - q90),
                outcome_hi90=central + q90,
                residual_sample_n=sample_n,
                residual_q80=q80,
                residual_q90=q90,
            )
        )

    typed_predictions = (predictions[0], predictions[1])
    central_values = [row.central for row in typed_predictions]
    low = min(central_values)
    high = max(central_values)
    return CareerTailAuthority(
        player_id=features.player_id,
        position=features.position,
        features=features,
        model_predictions=typed_predictions,
        model_authority_low=low,
        reference_center=(low + high) / 2.0,
        model_authority_high=high,
        outcome_outer_80=(
            min(row.outcome_lo80 for row in typed_predictions),
            max(row.outcome_hi80 for row in typed_predictions),
        ),
        outcome_outer_90=(
            min(row.outcome_lo90 for row in typed_predictions),
            max(row.outcome_hi90 for row in typed_predictions),
        ),
    )
