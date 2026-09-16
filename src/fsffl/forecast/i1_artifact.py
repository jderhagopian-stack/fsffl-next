from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from fsffl.state.models import Position

from .i1_config import FROZEN_I1_REGULARIZATION
from .integrated_i1 import (
    I1_MODEL_VERSION,
    I1ForecastInput,
    I1ForecastResult,
    IntegratedI1Model,
    STATE_NAMES,
    feature_vector_for_validation,
)

I1_ARTIFACT_SCHEMA_VERSION = "i1-frozen-artifact-v1"


@dataclass(frozen=True)
class FrozenLogit:
    intercept: float
    coefficients: Mapping[str, float]

    def probability(self, features: Mapping[str, object]) -> float:
        z = float(self.intercept)
        for key, value in features.items():
            coefficient = self.coefficients.get(str(key))
            if coefficient is not None:
                z += float(coefficient) * float(value)
        z = max(-40.0, min(40.0, z))
        return 1.0 / (1.0 + math.exp(-z))


@dataclass(frozen=True)
class FrozenPath:
    persistence: FrozenLogit | None
    ordered: tuple[FrozenLogit | None, ...]

    def predict(self, features: Mapping[str, object]) -> dict[str, float] | None:
        if self.persistence is None or len(self.ordered) != 4 or any(item is None for item in self.ordered):
            return None
        persist = self.persistence.probability(features)
        cumulative: list[float] = []
        last = 1.0
        for model in self.ordered:
            assert model is not None
            value = min(last, max(0.0, min(1.0, model.probability(features))))
            cumulative.append(value)
            last = value
        useful, starter, premium, elite = cumulative
        conditional = {
            "depth": 1.0 - useful,
            "usable": useful - starter,
            "starter": starter - premium,
            "premium": premium - elite,
            "elite": elite,
        }
        probabilities = {"out": 1.0 - persist}
        probabilities.update({state: persist * conditional[state] for state in STATE_NAMES[1:]})
        total = sum(probabilities.values())
        if total <= 0:
            return None
        return {state: value / total for state, value in probabilities.items()}


@dataclass(frozen=True)
class FrozenStateMeans:
    """Only supported cells are serialized, preserving I1's frozen fallback minima."""

    position_horizon_state: Mapping[str, float]
    position_state: Mapping[str, float]
    horizon_state: Mapping[str, float]
    state: Mapping[str, float]

    @staticmethod
    def _key(*parts: object) -> str:
        return "|".join(str(part) for part in parts)

    def get(self, position: Position, horizon: int, state: str) -> float:
        keys = (
            (self.position_horizon_state, self._key(position.value, horizon, state)),
            (self.position_state, self._key(position.value, state)),
            (self.horizon_state, self._key(horizon, state)),
            (self.state, self._key(state)),
        )
        for table, key in keys:
            if key in table:
                return max(0.0, float(table[key]))
        return 0.0


@dataclass(frozen=True)
class FrozenI1Artifact:
    artifact_schema_version: str
    model_version: str
    regularization_policy_version: str
    regularization_default_c: float
    evidence_source_seasons: tuple[int, int]
    rich: FrozenPath
    reduced: FrozenPath
    state_means: FrozenStateMeans
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.artifact_schema_version != I1_ARTIFACT_SCHEMA_VERSION:
            raise ValueError("unsupported I1 artifact schema")
        if self.regularization_policy_version != FROZEN_I1_REGULARIZATION.version:
            raise ValueError("I1 artifact regularization policy version does not match production governance")
        if abs(float(self.regularization_default_c) - FROZEN_I1_REGULARIZATION.default_c) > 1e-15:
            raise ValueError("I1 artifact C does not match governed production candidate")
        if self.evidence_source_seasons != (2012, 2022):
            raise ValueError("I1 artifact must preserve the frozen 2012-2022 calibration source era")

    def predict(
        self,
        item: I1ForecastInput,
        *,
        fallback_probabilities: Mapping[str, float] | None = None,
    ) -> I1ForecastResult:
        rich = item.evidence is not None and item.evidence.rich_roster_evidence_available
        path_name = "rich" if rich else "reduced"
        features = feature_vector_for_validation(item, rich=rich)
        probabilities = (self.rich if rich else self.reduced).predict(features)
        if probabilities is None:
            if fallback_probabilities is None:
                raise ValueError("frozen I1 path unavailable and no governed fallback was supplied")
            probabilities = _normalize(fallback_probabilities)
            path_name = "legacy_fallback"
        means = {
            state: self.state_means.get(item.position, item.horizon, state)
            for state in STATE_NAMES
        }
        anticipated = max(
            0.0,
            sum(float(probabilities[state]) * means[state] for state in STATE_NAMES),
        )
        return I1ForecastResult(
            probabilities=probabilities,
            persistence_probability=1.0 - probabilities["out"],
            anticipated_points=anticipated,
            state_means=means,
            evidence_path=path_name,
            model_version=self.model_version,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_schema_version": self.artifact_schema_version,
            "model_version": self.model_version,
            "regularization_policy_version": self.regularization_policy_version,
            "regularization_default_c": self.regularization_default_c,
            "evidence_source_seasons": list(self.evidence_source_seasons),
            "rich": _path_dict(self.rich),
            "reduced": _path_dict(self.reduced),
            "state_means": {
                "position_horizon_state": dict(self.state_means.position_horizon_state),
                "position_state": dict(self.state_means.position_state),
                "horizon_state": dict(self.state_means.horizon_state),
                "state": dict(self.state_means.state),
            },
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "FrozenI1Artifact":
        state_means = raw["state_means"]
        if not isinstance(state_means, Mapping):
            raise ValueError("I1 artifact state_means must be a mapping")
        seasons = raw["evidence_source_seasons"]
        if not isinstance(seasons, (list, tuple)) or len(seasons) != 2:
            raise ValueError("I1 artifact evidence_source_seasons must contain two seasons")
        rich = raw["rich"]
        reduced = raw["reduced"]
        if not isinstance(rich, Mapping) or not isinstance(reduced, Mapping):
            raise ValueError("I1 artifact paths must be mappings")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("I1 artifact metadata must be a mapping")
        return cls(
            artifact_schema_version=str(raw["artifact_schema_version"]),
            model_version=str(raw["model_version"]),
            regularization_policy_version=str(raw["regularization_policy_version"]),
            regularization_default_c=float(raw["regularization_default_c"]),
            evidence_source_seasons=(int(seasons[0]), int(seasons[1])),
            rich=_path_from_dict(rich),
            reduced=_path_from_dict(reduced),
            state_means=FrozenStateMeans(
                position_horizon_state=_float_map(state_means.get("position_horizon_state", {})),
                position_state=_float_map(state_means.get("position_state", {})),
                horizon_state=_float_map(state_means.get("horizon_state", {})),
                state=_float_map(state_means.get("state", {})),
            ),
            metadata=metadata,
        )

    @classmethod
    def load(cls, path: Path) -> "FrozenI1Artifact":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("I1 artifact must be a JSON object")
        return cls.from_dict(raw)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def freeze_i1_model(
    model: IntegratedI1Model,
    *,
    evidence_source_seasons: tuple[int, int] = (2012, 2022),
    metadata: Mapping[str, object] | None = None,
) -> FrozenI1Artifact:
    """Serialize a fitted production I1 model without changing its semantics."""

    return FrozenI1Artifact(
        artifact_schema_version=I1_ARTIFACT_SCHEMA_VERSION,
        model_version=I1_MODEL_VERSION,
        regularization_policy_version=FROZEN_I1_REGULARIZATION.version,
        regularization_default_c=FROZEN_I1_REGULARIZATION.default_c,
        evidence_source_seasons=evidence_source_seasons,
        rich=_freeze_path(model.rich),
        reduced=_freeze_path(model.reduced),
        state_means=FrozenStateMeans(
            position_horizon_state=_mean_table(model.means.by_position_horizon_state, minimum=10),
            position_state=_mean_table(model.means.by_position_state, minimum=10),
            horizon_state=_mean_table(model.means.by_horizon_state, minimum=10),
            state=_mean_table(model.means.by_state, minimum=5),
        ),
        metadata=dict(metadata or {}),
    )


def _freeze_binary(model) -> FrozenLogit | None:
    if not model.fitted:
        return None
    names = model.vectorizer.get_feature_names_out()
    coefficients = model.model.coef_[0]
    return FrozenLogit(
        intercept=float(model.model.intercept_[0]),
        coefficients={str(name): float(value) for name, value in zip(names, coefficients, strict=True)},
    )


def _freeze_path(path) -> FrozenPath:
    return FrozenPath(
        persistence=_freeze_binary(path.persistence),
        ordered=tuple(_freeze_binary(model) for model in path.positive_states.models),
    )


def _mean_table(
    table: Mapping[tuple[object, ...], list[float]],
    *,
    minimum: int,
) -> dict[str, float]:
    output: dict[str, float] = {}
    for key, values in table.items():
        if len(values) >= minimum:
            output["|".join(str(part) for part in key)] = sum(float(value) for value in values) / len(values)
    return output


def _normalize(probabilities: Mapping[str, float]) -> dict[str, float]:
    output = {state: max(0.0, float(probabilities.get(state, 0.0))) for state in STATE_NAMES}
    total = sum(output.values())
    if total <= 0:
        raise ValueError("career-state fallback probabilities must contain positive mass")
    return {state: output[state] / total for state in STATE_NAMES}


def _float_map(raw: object) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise ValueError("I1 artifact mean table must be a mapping")
    return {str(key): float(value) for key, value in raw.items()}


def _logit_dict(model: FrozenLogit | None) -> dict[str, object] | None:
    if model is None:
        return None
    return {"intercept": model.intercept, "coefficients": dict(model.coefficients)}


def _logit_from_dict(raw: object) -> FrozenLogit | None:
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("frozen logit must be a mapping")
    coefficients = raw.get("coefficients", {})
    if not isinstance(coefficients, Mapping):
        raise ValueError("frozen logit coefficients must be a mapping")
    return FrozenLogit(
        intercept=float(raw["intercept"]),
        coefficients={str(key): float(value) for key, value in coefficients.items()},
    )


def _path_dict(path: FrozenPath) -> dict[str, object]:
    return {
        "persistence": _logit_dict(path.persistence),
        "ordered": [_logit_dict(model) for model in path.ordered],
    }


def _path_from_dict(raw: Mapping[str, object]) -> FrozenPath:
    ordered = raw.get("ordered", ())
    if not isinstance(ordered, (list, tuple)):
        raise ValueError("frozen I1 ordered models must be a sequence")
    return FrozenPath(
        persistence=_logit_from_dict(raw.get("persistence")),
        ordered=tuple(_logit_from_dict(item) for item in ordered),
    )
