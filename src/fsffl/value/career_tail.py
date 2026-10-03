from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, Position
from fsffl.value.shapley_intrinsic import subset_caps_from_rules


CAREER_TAIL_TARGET_VERSION = "career-tail-y8plus-shapley-v1"
CAREER_TAIL_MODEL_VERSION = "career-tail-two-family-v1"
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
CAREER_TAIL_LINEUP_CAPACITY_SIGNATURE = (
    "fe6d07a77a7f11cd61e1af476e9d6b3fe89b7e59c6aecdeab5eb61c991b21349"
)
CAREER_TAIL_RESEARCH_RUN_ID = 37086000162
CAREER_TAIL_RESEARCH_ARTIFACT_ID = 11260487964
CAREER_TAIL_RESEARCH_ARTIFACT_SHA256 = (
    "505ba72e71ddcb868c1673386f2a516d64e1a087fe2d8d9807572cb24cd99aa6"
)
CAREER_TAIL_SHAPLEY_PERMUTATIONS = 2048
CAREER_TAIL_SHAPLEY_SEED = 20260915


_FROZEN_MODELS: dict[str, dict[Position, dict[str, object]]] = {
    "direct_ridge": {
        Position.QB: {
            "scaler_mean": (28.803876324880406, 5.356495468277946, 3.511842268797386, 2.717757830611865, 0.3041289023162135),
            "scaler_scale": (4.431663955616934, 4.335827069762098, 1.823394446901083, 2.29236652094665, 0.46003751270102805),
            "intercept": 1.2283121227444938,
            "coefficients": (-0.631120117879448, -0.0349363638331627, 0.6189339479451728, 0.45573020081039944, 0.2834387805166698),
            "smearing": 17.785726797864225,
        },
        Position.RB: {
            "scaler_mean": (26.446119243073518, 3.3187006145741877, 3.258621524096676, 2.4792941232192245, 0.3033362598770852),
            "scaler_scale": (2.9956102140741643, 2.9688626539834, 1.4515225139049912, 1.9877815685307816, 0.45969922049190665),
            "intercept": 0.35157613656646186,
            "coefficients": (-0.47679187718439486, 0.2073978927358479, 0.28358249582935796, 0.0333389320603864, 0.09983730080563974),
            "smearing": 4.219669476417952,
        },
        Position.TE: {
            "scaler_mean": (26.833764997511917, 3.590778097982709, 2.735706087234454, 2.091439522476457, 0.30331412103746397),
            "scaler_scale": (3.176887641570353, 3.1670086477568997, 1.3258534483109514, 1.7247006489117755, 0.45968974865308304),
            "intercept": 0.49799809830993824,
            "coefficients": (-0.8810841951050555, 0.5345999563133221, 0.32233412789615234, 0.1812757454569877, 0.18501773413551179),
            "smearing": 3.952764083190802,
        },
        Position.WR: {
            "scaler_mean": (26.563471165689833, 3.480561122244489, 3.3603344560811936, 2.5911821808837825, 0.30741482965931866),
            "scaler_scale": (3.3835115146817025, 3.292720288693026, 1.4310345997196248, 2.0148172452027997, 0.4614227477756712),
            "intercept": 0.5839569381740273,
            "coefficients": (-0.4338939777803942, 0.022867042210151338, 0.4587911770313252, 0.17592847224056934, 0.22558938376396662),
            "smearing": 5.98962368603483,
        },
    },
    "two_part_state": {
        Position.QB: {
            "scaler_mean": (28.803876324880406, 5.356495468277946, 3.511842268797386, 2.717757830611865, 0.3041289023162135),
            "scaler_scale": (4.431663955616934, 4.335827069762098, 1.823394446901083, 2.29236652094665, 0.46003751270102805),
            "logit_intercept": -1.3370797927178728,
            "logit_coefficients": (-0.9031414222261018, -0.22228528207029108, 0.8158210628123791, 0.7300437304431165, 0.5435084302879836),
            "positive_intercept": 3.792212904779314,
            "positive_coefficients": (-0.4866895224383592, 0.044130021866585684, 0.5781321392300057, 0.3496546695474597, 0.186927595499223),
            "positive_smearing": 5.384051324661913,
        },
        Position.RB: {
            "scaler_mean": (26.446119243073518, 3.3187006145741877, 3.258621524096676, 2.4792941232192245, 0.3033362598770852),
            "scaler_scale": (2.9956102140741643, 2.9688626539834, 1.4515225139049912, 1.9877815685307816, 0.45969922049190665),
            "logit_intercept": -2.7837281719188276,
            "logit_coefficients": (-1.1256159411873277, -0.27636517419647216, 0.7566448985844114, 0.2957989796055362, 0.31043440242362935),
            "positive_intercept": 1.9831540848102254,
            "positive_coefficients": (-0.8100174943229401, 0.17084783201092973, 0.8780232808523023, 0.3435193083941179, 0.45086936506113967),
            "positive_smearing": 2.478633059336131,
        },
        Position.TE: {
            "scaler_mean": (26.833764997511917, 3.590778097982709, 2.735706087234454, 2.091439522476457, 0.30331412103746397),
            "scaler_scale": (3.176887641570353, 3.1670086477568997, 1.3258534483109514, 1.7247006489117755, 0.45968974865308304),
            "logit_intercept": -2.280761936565817,
            "logit_coefficients": (-1.9426786477737537, 0.4647224118120708, 0.6962119097035886, 0.581791544443871, 0.4839577611546206),
            "positive_intercept": 1.9432626034802627,
            "positive_coefficients": (-0.8353646377345334, 0.19990138007722777, 0.7321443809387594, 0.6233801584272495, 0.5726883577200316),
            "positive_smearing": 2.6562617306187666,
        },
        Position.WR: {
            "scaler_mean": (26.563471165689833, 3.480561122244489, 3.3603344560811936, 2.5911821808837825, 0.30741482965931866),
            "scaler_scale": (3.3835115146817025, 3.292720288693026, 1.4310345997196248, 2.0148172452027997, 0.4614227477756712),
            "logit_intercept": -2.35517010847703,
            "logit_coefficients": (-1.055629198033804, -0.24368524967577615, 1.192580425047812, 0.576283811092281, 0.6405058363445538),
            "positive_intercept": 3.090267205473738,
            "positive_coefficients": (-0.316020846799795, -0.04522266361834543, 0.5935020684190871, 0.29254885113199774, 0.27018414522008083),
            "positive_smearing": 2.668002204652552,
        },
    },
}

_RESIDUAL_BANDS: dict[str, dict[Position, tuple[int, float, float]]] = {
    "direct_ridge": {
        Position.QB: (375, 15.481068218339349, 345.5562915380326),
        Position.RB: (871, 1.88484674375667, 2.522184862983338),
        Position.TE: (533, 0.5495474486221303, 17.469520907368903),
        Position.WR: (973, 2.7556657684374324, 14.64075741251873),
    },
    "two_part_state": {
        Position.QB: (375, 32.64468555050439, 347.3900064829445),
        Position.RB: (871, 1.8044198948495225, 8.726198481184156),
        Position.TE: (533, 0.8652072144681578, 16.777141550961982),
        Position.WR: (973, 3.700848985805659, 18.45716314184871),
    },
}


class CareerTailFeatures(FrozenModel):
    player_id: str
    position: Position
    age_years: Annotated[float, Field(ge=0.0)]
    experience_years: Annotated[float, Field(ge=0.0)]
    current_points: Annotated[float, Field(ge=0.0)]
    prior_points: Annotated[float | None, Field(ge=0.0)] = None

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
