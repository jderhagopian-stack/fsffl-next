from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.forecast.models import ForecastMetric, ForecastHorizon, ForecastObservation
from fsffl.state.models import Position

from ._selected_future_forecast_package import PACKAGE_JSON
from ._selected_future_forecast_source import SOURCE_CSV

SELECTED_FUTURE_FORECAST_VERSION = "selected-routed-future-forecast-v1:a2-c-d:d0-d1:prior2"
SELECTED_FUTURE_FORECAST_PACKAGE_SHA256 = "ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7"
SELECTED_FUTURE_FORECAST_SOURCE_SHA256 = "eda43a5e297ffe46550af5c3fbf98a1d32545fc15925a9e49c6620427043307a"
SELECTED_FUTURE_FORECAST_IMPLEMENTATION_SHA256 = "1d592e87660565bcda0ca24484568448c4624a4294ecb9ce6183343ee00e693a"

_STATES = ("out", "depth", "usable", "starter", "premium", "elite")
_POSITIVE_STATES = _STATES[1:]
_THRESHOLDS = ("useful", "starter", "premium", "elite")
_SUPPORTED_POSITIONS = {"QB", "RB", "WR", "TE"}


def _verify_embedded_authority() -> None:
    if hashlib.sha256(PACKAGE_JSON.encode("utf-8")).hexdigest() != SELECTED_FUTURE_FORECAST_PACKAGE_SHA256:
        raise ValueError("embedded selected future Forecast package hash mismatch")
    if hashlib.sha256(SOURCE_CSV.encode("utf-8")).hexdigest() != SELECTED_FUTURE_FORECAST_SOURCE_SHA256:
        raise ValueError("embedded selected future Forecast source-coordinate hash mismatch")


_verify_embedded_authority()
_PACKAGE = json.loads(PACKAGE_JSON)
if _PACKAGE.get("schema_version") != "fsffl-redeveloped-forecast-fit-v1":
    raise ValueError("unsupported selected future Forecast package schema")
if _PACKAGE.get("implementation_sha256") != SELECTED_FUTURE_FORECAST_IMPLEMENTATION_SHA256:
    raise ValueError("selected future Forecast implementation provenance mismatch")


@dataclass(frozen=True)
class _SourceRow:
    player_id: str
    position: str
    age: float
    experience: int
    career_stage: str
    age_band: str
    source_points: float
    source_state: str
    prior1_points: float | None
    prior1_coverage: int
    source_role_band: str
    games: float | None
    opportunity_per_game: float | None
    prior_age_state_resid_z: float | None
    prior2_coverage: int
    prior2_mean_age_state_z: float | None
    prior2_gap_age_state_z: float | None
    source_percentile: float
    state_percentile: float


def _nullable_float(value: str | None) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return float(text)


def _load_rows() -> dict[str, _SourceRow]:
    rows: dict[str, _SourceRow] = {}
    for raw in csv.DictReader(io.StringIO(SOURCE_CSV)):
        player_id = str(raw["current_player_id"])
        if player_id in rows:
            raise ValueError(f"duplicate selected Forecast player id: {player_id}")
        position = str(raw["position"])
        if position not in _SUPPORTED_POSITIONS:
            raise ValueError(f"unsupported selected Forecast position: {position}")
        rows[player_id] = _SourceRow(
            player_id=player_id,
            position=position,
            age=float(raw["age"]),
            experience=int(raw["experience"]),
            career_stage=str(raw["career_stage"]),
            age_band=str(raw["age_band"]),
            source_points=float(raw["y1_points"]),
            source_state=str(raw["source_state"]),
            prior1_points=_nullable_float(raw.get("prior1_points")),
            prior1_coverage=int(raw["prior1_coverage"]),
            source_role_band=str(raw.get("source_role_band") or "unknown"),
            games=_nullable_float(raw.get("games")),
            opportunity_per_game=_nullable_float(raw.get("opportunity_per_game")),
            prior_age_state_resid_z=_nullable_float(raw.get("prior_age_state_resid_z")),
            prior2_coverage=int(raw["prior2_coverage"]),
            prior2_mean_age_state_z=_nullable_float(raw.get("prior2_mean_age_state_z")),
            prior2_gap_age_state_z=_nullable_float(raw.get("prior2_gap_age_state_z")),
            source_percentile=float(raw["source_percentile"]),
            state_percentile=float(raw["state_percentile"]),
        )
    if len(rows) != 335:
        raise ValueError(f"selected future Forecast source coordinate must contain 335 players; got {len(rows)}")
    return rows


_ROWS = _load_rows()


def selected_future_source_player_ids() -> tuple[str, ...]:
    return tuple(sorted(_ROWS))


def selected_future_source_row(player_id: str) -> Mapping[str, object]:
    try:
        row = _ROWS[player_id]
    except KeyError as exc:
        raise ValueError(f"selected future Forecast lacks governed source row for {player_id}") from exc
    return dict(row.__dict__)


def _exp_band(experience: int) -> str:
    if experience <= 1:
        return "0_1"
    if experience <= 3:
        return "2_3"
    if experience <= 6:
        return "4_6"
    return "7_plus"


def _prob_features(row: _SourceRow, horizon: int, *, age_mode: str, add_c: bool, add_d: bool) -> dict[str, float]:
    p = row.position
    exp = int(row.experience)
    d: dict[str, float] = {
        f"p={p}": 1.0,
        f"s={row.source_state}": 1.0,
        f"h={horizon}": 1.0,
        f"e={_exp_band(exp)}": 1.0,
        "exp": min(15.0, max(0.0, float(exp))) / 10.0,
    }
    if age_mode == "coarse":
        d[f"a={row.age_band}"] = 1.0
    elif age_mode == "a2":
        age = float(row.age)
        ref = 31.0 if p == "QB" else 27.0
        d[f"age_exact_{p}"] = (age - ref) / 5.0
        if p == "QB":
            d["age_late_QB"] = max(0.0, age - 37.0) / 5.0
        else:
            d[f"age_late_{p}"] = max(0.0, age - 31.0) / 5.0
            if p == "TE":
                d["age_young_TE"] = max(0.0, 24.0 - age) / 5.0
    else:
        raise ValueError(f"unsupported selected Forecast age mode: {age_mode}")

    current = max(0.0, float(row.source_points))
    prior = (
        max(0.0, float(row.prior1_points))
        if row.prior1_coverage and row.prior1_points is not None
        else None
    )
    prior_value = 0.0 if prior is None else prior
    d.update(
        {
            "lp": math.log1p(current) / 6.0,
            "lprev": math.log1p(prior_value) / 6.0,
            "dpts": max(-2.0, min(2.0, (current - prior_value) / 100.0)),
            "prev_cov": 0.0 if prior is None else 1.0,
        }
    )
    role = row.source_role_band
    if (
        role in {"weak", "established"}
        and row.opportunity_per_game is not None
        and row.games is not None
    ):
        d[f"role={role}"] = 1.0
        d["u_cov"] = 1.0
        d["lopg"] = math.log1p(max(0.0, float(row.opportunity_per_game))) / 4.0
        d["lg"] = math.log1p(max(0.0, float(row.games))) / 3.0
    else:
        d.update({"role=unknown": 1.0, "u_cov": 0.0, "lopg": 0.0, "lg": 0.0})
    d.update({"r_cov": 0.0, "i_cov": 0.0, "part_cov": 0.0})

    if add_c:
        supported = p == "QB" and row.age_band in {"prime", "aging"}
        if supported:
            key = f"mem_{p}_{row.age_band}_h{horizon}"
            if row.prior_age_state_resid_z is not None:
                d[key] = float(row.prior_age_state_resid_z)
                d[key + "_cov"] = 1.0
            else:
                d[key] = 0.0
                d[key + "_cov"] = 0.0

    if add_d:
        pct = float(row.state_percentile)
        d[f"pct_{p}"] = (pct - 0.5) * 2.0
        if row.source_state in {"premium", "elite"}:
            d[f"hi_{p}_{row.source_state}"] = max(0.0, (pct - 0.8) / 0.2)
            d[f"lo_{p}_{row.source_state}"] = max(0.0, (0.2 - pct) / 0.2)
    return d


def _dot(coefficients: Iterable[float], features: Iterable[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(coefficients, features, strict=True))


def _vector(feature_map: Mapping[str, float], names: Iterable[str]) -> tuple[float, ...]:
    return tuple(float(feature_map.get(name, 0.0)) for name in names)


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _score_binary(package: Mapping[str, object], feature_map: Mapping[str, float]) -> float:
    intercept = float(package["intercept"][0])  # type: ignore[index]
    coefficients = package["coef"]  # type: ignore[assignment]
    names = package["features"]  # type: ignore[assignment]
    return _sigmoid(intercept + _dot(coefficients, _vector(feature_map, names)))


def _score_probabilities(layer: Mapping[str, object], row: _SourceRow, horizon: int) -> dict[str, float]:
    add_c = bool(layer["add_c"])
    persistence = _score_binary(
        layer["persistence"],  # type: ignore[arg-type]
        _prob_features(row, horizon, age_mode="a2", add_c=add_c, add_d=False),
    )
    ordered_features = _prob_features(row, horizon, age_mode="coarse", add_c=add_c, add_d=True)
    cumulative: list[float] = []
    last = 1.0
    ordered = layer["ordered"]  # type: ignore[assignment]
    for name in _THRESHOLDS:
        q = _score_binary(ordered[name], ordered_features)
        q = min(last, max(0.0, min(1.0, q)))
        cumulative.append(q)
        last = q
    useful, starter, premium, elite = cumulative
    conditional = {
        "depth": 1.0 - useful,
        "usable": useful - starter,
        "starter": starter - premium,
        "premium": premium - elite,
        "elite": elite,
    }
    output = {"out": 1.0 - persistence}
    output.update({state: persistence * conditional[state] for state in _POSITIVE_STATES})
    total = sum(output.values())
    if total <= 0:
        raise ValueError("selected future Forecast probability mass is nonpositive")
    return {state: output[state] / total for state in _STATES}


def _zvalue(package: Mapping[str, object], key: str, value: float) -> float:
    scalers = package["scalers"]  # type: ignore[assignment]
    scaler = scalers[key]
    return (float(value) - float(scaler["mean"])) / float(scaler["sd"])


def _production_features(
    package: Mapping[str, object],
    row: _SourceRow,
    future_state: str | None = None,
) -> dict[str, float]:
    values = {
        "source_log": _zvalue(package, "source_log", math.log1p(max(0.0, float(row.source_points)))),
        "source_pct": _zvalue(package, "source_pct", float(row.source_percentile)),
        "age": _zvalue(package, "age", float(row.age)),
        "experience": _zvalue(package, "experience", min(float(row.experience), 15.0)),
        "prior1_log": (
            _zvalue(package, "prior1_log", math.log1p(max(0.0, float(row.prior1_points))))
            if row.prior1_coverage and row.prior1_points is not None
            else 0.0
        ),
    }
    d: dict[str, float] = {
        f"p={row.position}": 1.0,
        f"src={row.source_state}": 1.0,
        "prior1_cov": float(row.prior1_coverage),
    }
    for key, value in values.items():
        d[key] = value
        d[f"{key}@p={row.position}"] = value

    if package["candidate"] == "D1":
        if future_state is None:
            raise ValueError("D1 selected future Forecast requires a positive future state")
        d[f"future={future_state}"] = 1.0
        d[f"pstate={row.position}|{future_state}"] = 1.0
        d[f"source_log@future={future_state}"] = values["source_log"]
        d[f"source_pct@future={future_state}"] = values["source_pct"]
        if (
            row.prior2_coverage
            and row.prior2_mean_age_state_z is not None
            and row.prior2_gap_age_state_z is not None
        ):
            mean_z = _zvalue(package, "prior2_mean", float(row.prior2_mean_age_state_z))
            gap_z = _zvalue(package, "prior2_gap", float(row.prior2_gap_age_state_z))
        else:
            mean_z = gap_z = 0.0
        d["prior2_cov"] = float(row.prior2_coverage)
        d["prior2_mean_z"] = mean_z
        d["prior2_gap_z"] = gap_z
        d[f"prior2_mean_z@p={row.position}"] = mean_z
        d[f"prior2_gap_z@p={row.position}"] = gap_z
    return d


def _score_production(package: Mapping[str, object], row: _SourceRow, state: str | None = None) -> float:
    features = _production_features(package, row, state)
    value = float(package["intercept"]) + _dot(
        package["coef"],  # type: ignore[arg-type]
        _vector(features, package["features"]),  # type: ignore[arg-type]
    )
    return max(0.0, value)


def _selected_route(horizon: int, row: _SourceRow) -> str:
    try:
        return str(
            _PACKAGE["selection"][str(horizon)]["selected_route"][
                f"{row.position}|{row.career_stage}"
            ]
        )
    except KeyError as exc:
        raise ValueError(
            "selected future Forecast has no governed route for "
            f"h={horizon} position={row.position} career_stage={row.career_stage}"
        ) from exc


class SelectedFutureForecast:
    """Frozen player-identity-aware Y2/Y3 producer.

    The package is a pure scoring artifact: no fit, refit, model selection or
    parameter reconstruction occurs here. A2/C/D own the probability layer.
    D0/D1 own conditional production. Continuous magnitude and prior-two
    information are carried inside the frozen production package exactly once.
    """

    package_sha256 = SELECTED_FUTURE_FORECAST_PACKAGE_SHA256
    source_sha256 = SELECTED_FUTURE_FORECAST_SOURCE_SHA256
    model_version = SELECTED_FUTURE_FORECAST_VERSION

    def assert_standard_year_one(
        self,
        observations: tuple[ForecastObservation, ...],
        *,
        tolerance: float = 1e-9,
    ) -> None:
        seen: set[str] = set()
        for observation in observations:
            if (
                observation.metric != ForecastMetric.FANTASY_POINTS
                or observation.horizon != ForecastHorizon.SEASON
            ):
                continue
            row = _ROWS.get(observation.player_id)
            if row is None:
                raise ValueError(
                    "selected future Forecast lacks a source coordinate for "
                    f"{observation.player_id}"
                )
            if observation.position.value != row.position:
                raise ValueError(
                    "selected future Forecast position mismatch for "
                    f"{observation.player_id}: {observation.position.value} != {row.position}"
                )
            delta = abs(float(observation.distribution.mean) - float(row.source_points))
            if delta > tolerance:
                raise ValueError(
                    "selected future Forecast standard Year-1 coordinate mismatch for "
                    f"{observation.player_id}: delta={delta}"
                )
            seen.add(observation.player_id)
        if not seen:
            raise ValueError("selected future Forecast received no standard Year-1 observations")

    def predict(self, player_id: str, horizon: int) -> I1ForecastResult:
        if horizon not in (2, 3):
            raise ValueError("selected future Forecast only owns direct Y2/Y3 horizons")
        try:
            row = _ROWS[player_id]
        except KeyError as exc:
            raise ValueError(
                f"selected future Forecast lacks governed source row for {player_id}"
            ) from exc
        horizon_package = _PACKAGE["horizons"][str(horizon)]
        layer = horizon_package["state_qb"] if row.position == "QB" else horizon_package["state_nonqb"]
        probabilities = _score_probabilities(layer, row, horizon)
        route = _selected_route(horizon, row)
        production = horizon_package["production_models"].get(route)
        if production is None:
            raise ValueError(
                f"selected future Forecast package lacks required {route} model for horizon {horizon}"
            )

        if route == "D0":
            conditional = _score_production(production, row)
            state_means = {"out": 0.0}
            state_means.update({state: conditional for state in _POSITIVE_STATES})
        elif route == "D1":
            state_means = {"out": 0.0}
            state_means.update(
                {
                    state: _score_production(production, row, state)
                    for state in _POSITIVE_STATES
                }
            )
        else:
            raise ValueError(f"unsupported selected future Forecast route: {route}")

        anticipated = sum(
            float(probabilities[state]) * float(state_means[state])
            for state in _STATES
        )
        return I1ForecastResult(
            probabilities={state: float(probabilities[state]) for state in STATE_NAMES},
            persistence_probability=1.0 - float(probabilities["out"]),
            anticipated_points=max(0.0, float(anticipated)),
            state_means={state: max(0.0, float(state_means[state])) for state in STATE_NAMES},
            evidence_path=f"selected_routed_{route}",
            model_version=f"{SELECTED_FUTURE_FORECAST_VERSION}:{route}",
        )
