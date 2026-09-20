from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Mapping

from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Position

from .p0_frozen_assets import (
    P0_CONNECTED_LEAGUE_Y1_BOARD_SHA256,
    P0_CORRECTED_BOARD_SHA256,
    P0_CURRENT_SOURCE_CSV,
    P0_CURRENT_SOURCE_CSV_SHA256,
    P0_PACKAGE_JSON,
    P0_PACKAGE_SHA256,
    P0_STANDARD_Y1_BOARD_SHA256,
)

P0_FITTED_PACKAGE_VERSION = "p0-redeveloped-v1:" + P0_PACKAGE_SHA256[:12]
P0_FINAL_ROUTE_AUTHORITY = {
    "2": {
        "QB|developmental": "D1",
        "QB|established": "D1",
        "QB|veteran": "D1",
        "RB|developmental": "D1",
        "RB|established": "D1",
        "RB|veteran": "D1",
        "TE|developmental": "D1",
        "TE|established": "D1",
        "TE|veteran": "D1",
        "WR|developmental": "D1",
        "WR|established": "D1",
        "WR|veteran": "D1",
    },
    "3": {
        "QB|developmental": "D1",
        "QB|established": "D1",
        "QB|veteran": "D1",
        "RB|developmental": "D1",
        "RB|established": "D1",
        "RB|veteran": "D0",
        "TE|developmental": "D1",
        "TE|established": "D1",
        "TE|veteran": "D0",
        "WR|developmental": "D1",
        "WR|established": "D1",
        "WR|veteran": "D0",
    },
}
P0_FINAL_ROUTE_AUTHORITY_JSON = json.dumps(
    P0_FINAL_ROUTE_AUTHORITY,
    sort_keys=True,
    separators=(",", ":"),
)
P0_FINAL_ROUTE_AUTHORITY_SHA256 = hashlib.sha256(
    P0_FINAL_ROUTE_AUTHORITY_JSON.encode("utf-8")
).hexdigest()
P0_FINAL_ROUTE_AUTHORITY_VERSION = (
    "p0-final-route-authority-v1:" + P0_FINAL_ROUTE_AUTHORITY_SHA256[:12]
)
P0_FORECAST_VERSION = (
    f"{P0_FITTED_PACKAGE_VERSION}:{P0_FINAL_ROUTE_AUTHORITY_VERSION}"
)
P0_SOURCE_SEASON = 2026
P0_STANDARD_PARITY_TOLERANCE = 1e-9
P0_PROBABILITY_TOLERANCE = 1e-10
P0_POINT_REPLAY_TOLERANCE = 1e-8
_POSITIVE_STATES = ("depth", "usable", "starter", "premium", "elite")
_THRESHOLDS = ("useful", "starter", "premium", "elite")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if _sha256(P0_PACKAGE_JSON) != P0_PACKAGE_SHA256:
    raise ValueError("embedded P0 fitted package byte hash mismatch")
if _sha256(P0_CURRENT_SOURCE_CSV) != P0_CURRENT_SOURCE_CSV_SHA256:
    raise ValueError("embedded P0 current-source coordinate byte hash mismatch")

_PACKAGE = json.loads(P0_PACKAGE_JSON)
if _PACKAGE.get("schema_version") != "fsffl-redeveloped-forecast-fit-v1":
    raise ValueError("embedded P0 package schema mismatch")


def _validate_final_route_authority() -> None:
    expected_overrides = {
        ("3", "QB|developmental", "D0", "D1"),
        ("3", "RB|established", "D0", "D1"),
    }
    observed_overrides: set[tuple[str, str, str, str]] = set()
    for horizon in ("2", "3"):
        embedded = _PACKAGE["selection"][horizon]["selected_route"]
        final = P0_FINAL_ROUTE_AUTHORITY[horizon]
        if set(final) != set(embedded):
            raise ValueError(f"final route authority cell mismatch for horizon {horizon}")
        for cell, final_route in final.items():
            embedded_route = str(embedded[cell])
            if final_route not in _PACKAGE["horizons"][horizon]["production_models"]:
                raise ValueError(
                    f"final route authority references missing model: {horizon} {cell} {final_route}"
                )
            if embedded_route != final_route:
                observed_overrides.add((horizon, cell, embedded_route, final_route))
    if observed_overrides != expected_overrides:
        raise ValueError(
            "final route authority differs from the frozen package outside the two "
            f"research-earned cells: {sorted(observed_overrides)}"
        )


_validate_final_route_authority()


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    result = float(value)
    return result if math.isfinite(result) else None


@dataclass(frozen=True)
class P0SourceRow:
    player_id: str
    current_player_id: str
    player_name: str
    position: str
    age: float
    experience: int
    career_stage: str
    age_band: str
    mapping_status: str
    historical_gsis_id: str | None
    history_status: str
    standard_y1_points: float
    connected_league_y1_points: float
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

    @property
    def sleeper_external_id(self) -> str:
        return self.current_player_id.rsplit(":", 1)[-1]


@dataclass(frozen=True)
class P0PlayerForecast:
    player_id: str
    source: P0SourceRow
    routes: Mapping[int, str]
    results: Mapping[int, I1ForecastResult]

    def result_for(self, horizon: int) -> I1ForecastResult:
        return self.results[int(horizon)]

    def route_for(self, horizon: int) -> str:
        return self.routes[int(horizon)]


@dataclass(frozen=True)
class P0FutureMaterialization:
    players: Mapping[str, P0PlayerForecast]
    package_sha256: str = P0_PACKAGE_SHA256
    source_sha256: str = P0_CURRENT_SOURCE_CSV_SHA256
    route_authority_sha256: str = P0_FINAL_ROUTE_AUTHORITY_SHA256
    source_season: int = P0_SOURCE_SEASON

    @property
    def player_count(self) -> int:
        return len(self.players)


def _load_source_rows() -> tuple[P0SourceRow, ...]:
    rows: list[P0SourceRow] = []
    for raw in csv.DictReader(io.StringIO(P0_CURRENT_SOURCE_CSV)):
        rows.append(
            P0SourceRow(
                player_id=str(raw["player_id"]),
                current_player_id=str(raw["current_player_id"]),
                player_name=str(raw["player_name"]),
                position=str(raw["position"]),
                age=float(raw["age"]),
                experience=int(raw["experience"]),
                career_stage=str(raw["career_stage"]),
                age_band=str(raw["age_band"]),
                mapping_status=str(raw["mapping_status"]),
                historical_gsis_id=str(raw["historical_gsis_id"]) or None,
                history_status=str(raw["history_status"]),
                standard_y1_points=float(raw["y1_points"]),
                connected_league_y1_points=float(raw["league_y1_points"]),
                source_state=str(raw["source_state"]),
                prior1_points=_optional_float(raw.get("prior1_points")),
                prior1_coverage=int(raw["prior1_coverage"]),
                source_role_band=str(raw["source_role_band"]),
                games=_optional_float(raw.get("games")),
                opportunity_per_game=_optional_float(raw.get("opportunity_per_game")),
                prior_age_state_resid_z=_optional_float(raw.get("prior_age_state_resid_z")),
                prior2_coverage=int(raw["prior2_coverage"]),
                prior2_mean_age_state_z=_optional_float(raw.get("prior2_mean_age_state_z")),
                prior2_gap_age_state_z=_optional_float(raw.get("prior2_gap_age_state_z")),
                source_percentile=float(raw["source_percentile"]),
                state_percentile=float(raw["state_percentile"]),
            )
        )
    if len(rows) != 335:
        raise ValueError(f"embedded P0 current-source row count mismatch: {len(rows)}")
    ids = [row.current_player_id for row in rows]
    external = [row.sleeper_external_id for row in rows]
    if len(set(ids)) != len(rows) or len(set(external)) != len(rows):
        raise ValueError("embedded P0 current-source identity is not unique")
    return tuple(rows)


_SOURCE_ROWS = _load_source_rows()
_SOURCE_BY_CURRENT_ID = {row.current_player_id: row for row in _SOURCE_ROWS}
_SOURCE_BY_PLAYER_ID = {row.player_id: row for row in _SOURCE_ROWS}
_SOURCE_BY_SLEEPER_EXTERNAL_ID = {row.sleeper_external_id: row for row in _SOURCE_ROWS}


def frozen_p0_source_rows() -> tuple[P0SourceRow, ...]:
    return _SOURCE_ROWS


def _finite(value: object) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _exp_band(experience: int) -> str:
    if experience <= 1:
        return "0_1"
    if experience <= 3:
        return "2_3"
    if experience <= 6:
        return "4_6"
    return "7_plus"


def _dot(coef: list[float], names: list[str], feat: Mapping[str, float]) -> float:
    return sum(float(c) * float(feat.get(name, 0.0)) for c, name in zip(coef, names, strict=True))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _score_bin(package: Mapping[str, object], feat: Mapping[str, float]) -> float:
    intercept = package["intercept"]
    if not isinstance(intercept, list) or not intercept:
        raise ValueError("P0 binary package lacks intercept")
    return _sigmoid(
        float(intercept[0])
        + _dot(
            [float(value) for value in package["coef"]],
            [str(value) for value in package["features"]],
            feat,
        )
    )


def _prob_features(row: SimpleNamespace, *, age_mode: str, add_c: bool, add_d: bool) -> dict[str, float]:
    position = str(row.position)
    horizon = int(row.horizon)
    experience = int(row.experience)
    feat: dict[str, float] = {
        f"p={position}": 1.0,
        f"s={row.source_state}": 1.0,
        f"h={horizon}": 1.0,
        f"e={_exp_band(experience)}": 1.0,
        "exp": min(15.0, max(0.0, float(experience))) / 10.0,
    }
    if age_mode == "coarse":
        feat[f"a={row.age_band}"] = 1.0
    elif age_mode == "a2":
        age = float(row.age)
        reference = 31.0 if position == "QB" else 27.0
        feat[f"age_exact_{position}"] = (age - reference) / 5.0
        if position == "QB":
            feat["age_late_QB"] = max(0.0, age - 37.0) / 5.0
        else:
            feat[f"age_late_{position}"] = max(0.0, age - 31.0) / 5.0
            if position == "TE":
                feat["age_young_TE"] = max(0.0, 24.0 - age) / 5.0
    else:
        raise ValueError(f"unknown P0 age mode: {age_mode}")

    current = max(0.0, float(row.source_points))
    prior = (
        max(0.0, float(row.prior1_points))
        if int(row.prior1_coverage) and _finite(row.prior1_points)
        else None
    )
    prior_value = 0.0 if prior is None else prior
    feat.update(
        {
            "lp": math.log1p(current) / 6.0,
            "lprev": math.log1p(prior_value) / 6.0,
            "dpts": max(-2.0, min(2.0, (current - prior_value) / 100.0)),
            "prev_cov": 0.0 if prior is None else 1.0,
        }
    )
    role = str(row.source_role_band) if row.source_role_band else "unknown"
    if role in ("weak", "established") and _finite(row.opportunity_per_game) and _finite(row.games):
        feat[f"role={role}"] = 1.0
        feat["u_cov"] = 1.0
        feat["lopg"] = math.log1p(max(0.0, float(row.opportunity_per_game))) / 4.0
        feat["lg"] = math.log1p(max(0.0, float(row.games))) / 3.0
    else:
        feat.update({"role=unknown": 1.0, "u_cov": 0.0, "lopg": 0.0, "lg": 0.0})
    feat.update({"r_cov": 0.0, "i_cov": 0.0, "part_cov": 0.0})

    if add_c:
        supported = position == "QB" and row.age_band in ("prime", "aging")
        if supported:
            key = f"mem_{position}_{row.age_band}_h{horizon}"
            if _finite(row.prior_age_state_resid_z):
                feat[key] = float(row.prior_age_state_resid_z)
                feat[key + "_cov"] = 1.0
            else:
                feat[key] = 0.0
                feat[key + "_cov"] = 0.0

    if add_d and _finite(row.state_percentile):
        percentile = float(row.state_percentile)
        feat[f"pct_{position}"] = (percentile - 0.5) * 2.0
        if row.source_state in ("premium", "elite"):
            feat[f"hi_{position}_{row.source_state}"] = max(0.0, (percentile - 0.8) / 0.2)
            feat[f"lo_{position}_{row.source_state}"] = max(0.0, (0.2 - percentile) / 0.2)
    return feat


def _score_prob(layer_package: Mapping[str, object], row: SimpleNamespace) -> dict[str, float]:
    add_c = bool(layer_package["add_c"])
    persistence = _score_bin(
        layer_package["persistence"],
        _prob_features(row, age_mode="a2", add_c=add_c, add_d=False),
    )
    ordered_feat = _prob_features(row, age_mode="coarse", add_c=add_c, add_d=True)
    cumulative: list[float] = []
    last = 1.0
    ordered = layer_package["ordered"]
    for name in _THRESHOLDS:
        probability = _score_bin(ordered[name], ordered_feat)
        probability = min(last, max(0.0, min(1.0, probability)))
        cumulative.append(probability)
        last = probability

    useful, starter, premium, elite = cumulative
    conditional = {
        "depth": 1.0 - useful,
        "usable": useful - starter,
        "starter": starter - premium,
        "premium": premium - elite,
        "elite": elite,
    }
    result = {"out": 1.0 - persistence}
    result.update({state: persistence * conditional[state] for state in _POSITIVE_STATES})
    total = sum(result.values())
    if total <= 0:
        raise ValueError("P0 state probability mass is nonpositive")
    normalized = {state: float(result[state] / total) for state in STATE_NAMES}
    if abs(sum(normalized.values()) - 1.0) > P0_PROBABILITY_TOLERANCE:
        raise ValueError("P0 state probabilities do not sum to one")
    return normalized


def _zvalue(package: Mapping[str, object], key: str, value: float) -> float:
    scaler = package["scalers"][key]
    sd = float(scaler["sd"])
    if abs(sd) < 1e-15:
        raise ValueError(f"P0 production scaler is degenerate: {key}")
    return (float(value) - float(scaler["mean"])) / sd


def _production_features(
    package: Mapping[str, object],
    row: SimpleNamespace,
    state: str | None = None,
) -> dict[str, float]:
    values = {
        "source_log": _zvalue(package, "source_log", math.log1p(max(0.0, float(row.source_points)))),
        "source_pct": _zvalue(package, "source_pct", float(row.source_percentile)),
        "age": _zvalue(package, "age", float(row.age)),
        "experience": _zvalue(package, "experience", min(float(row.experience), 15.0)),
        "prior1_log": (
            _zvalue(package, "prior1_log", math.log1p(max(0.0, float(row.prior1_points))))
            if int(row.prior1_coverage) and _finite(row.prior1_points)
            else 0.0
        ),
    }
    feat: dict[str, float] = {
        f"p={row.position}": 1.0,
        f"src={row.source_state}": 1.0,
        "prior1_cov": float(int(row.prior1_coverage)),
    }
    for key, value in values.items():
        feat[key] = value
        feat[f"{key}@p={row.position}"] = value

    if package["candidate"] == "D1":
        future_state = state or str(row.source_state)
        feat[f"future={future_state}"] = 1.0
        feat[f"pstate={row.position}|{future_state}"] = 1.0
        feat[f"source_log@future={future_state}"] = values["source_log"]
        feat[f"source_pct@future={future_state}"] = values["source_pct"]
        if (
            int(row.prior2_coverage)
            and _finite(row.prior2_mean_age_state_z)
            and _finite(row.prior2_gap_age_state_z)
        ):
            mean_z = _zvalue(package, "prior2_mean", float(row.prior2_mean_age_state_z))
            gap_z = _zvalue(package, "prior2_gap", float(row.prior2_gap_age_state_z))
        else:
            mean_z = gap_z = 0.0
        feat["prior2_cov"] = float(int(row.prior2_coverage))
        feat["prior2_mean_z"] = mean_z
        feat["prior2_gap_z"] = gap_z
        feat[f"prior2_mean_z@p={row.position}"] = mean_z
        feat[f"prior2_gap_z@p={row.position}"] = gap_z
    return feat


def _score_production(
    package: Mapping[str, object],
    row: SimpleNamespace,
    state: str | None = None,
) -> float:
    prediction = float(package["intercept"]) + _dot(
        [float(value) for value in package["coef"]],
        [str(value) for value in package["features"]],
        _production_features(package, row, state),
    )
    return max(0.0, prediction)


def _score_source(
    source: P0SourceRow,
    *,
    player_id: str,
    standard_y1_points: float,
) -> P0PlayerForecast:
    routes: dict[int, str] = {}
    results: dict[int, I1ForecastResult] = {}
    for horizon in (2, 3):
        horizon_package = _PACKAGE["horizons"][str(horizon)]
        row = SimpleNamespace(
            position=source.position,
            horizon=horizon,
            experience=source.experience,
            source_state=source.source_state,
            age_band=source.age_band,
            age=source.age,
            source_points=float(standard_y1_points),
            prior1_points=source.prior1_points,
            prior1_coverage=source.prior1_coverage,
            source_role_band=source.source_role_band,
            games=source.games,
            opportunity_per_game=source.opportunity_per_game,
            prior_age_state_resid_z=source.prior_age_state_resid_z,
            state_percentile=source.state_percentile,
            source_percentile=source.source_percentile,
            prior2_coverage=source.prior2_coverage,
            prior2_mean_age_state_z=source.prior2_mean_age_state_z,
            prior2_gap_age_state_z=source.prior2_gap_age_state_z,
        )
        layer = horizon_package["state_qb"] if source.position == "QB" else horizon_package["state_nonqb"]
        probabilities = _score_prob(layer, row)
        route_cell = f"{source.position}|{source.career_stage}"
        route = P0_FINAL_ROUTE_AUTHORITY[str(horizon)][route_cell]
        model = horizon_package["production_models"][route]
        if route == "D0":
            conditional = _score_production(model, row)
            state_means = {"out": 0.0, **{state: conditional for state in _POSITIVE_STATES}}
            anticipated = (1.0 - probabilities["out"]) * conditional
        elif route == "D1":
            positive_means = {
                state: _score_production(model, row, state)
                for state in _POSITIVE_STATES
            }
            state_means = {"out": 0.0, **positive_means}
            anticipated = sum(probabilities[state] * positive_means[state] for state in _POSITIVE_STATES)
        else:
            raise ValueError(f"unknown frozen P0 route: {route}")
        persistence = 1.0 - probabilities["out"]
        results[horizon] = I1ForecastResult(
            probabilities=probabilities,
            persistence_probability=persistence,
            anticipated_points=max(0.0, float(anticipated)),
            state_means=state_means,
            evidence_path="rich",
            model_version=f"{P0_FORECAST_VERSION}:{route}:h{horizon}",
        )
        routes[horizon] = route
    return P0PlayerForecast(player_id=player_id, source=source, routes=routes, results=results)


def frozen_p0_standard_materialization() -> P0FutureMaterialization:
    players = {
        source.current_player_id: _score_source(
            source,
            player_id=source.current_player_id,
            standard_y1_points=source.standard_y1_points,
        )
        for source in _SOURCE_ROWS
    }
    return P0FutureMaterialization(players=players)


def _year_one_index(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    result: dict[str, ForecastObservation] = {}
    for observation in observations:
        if (
            observation.metric != ForecastMetric.FANTASY_POINTS
            or observation.horizon != ForecastHorizon.SEASON
            or observation.position not in {Position.QB, Position.RB, Position.WR, Position.TE}
        ):
            continue
        if observation.player_id in result:
            raise ValueError(f"duplicate P0 standard Year-1 observation for {observation.player_id}")
        result[observation.player_id] = observation
    return result


def _source_for_player(league_state: LeagueState, player_id: str) -> P0SourceRow:
    direct = _SOURCE_BY_CURRENT_ID.get(player_id) or _SOURCE_BY_PLAYER_ID.get(player_id)
    candidates: dict[str, P0SourceRow] = {}
    if direct is not None:
        candidates[direct.current_player_id] = direct

    by_player = {player.player_id: player for player in league_state.players}
    player = by_player.get(player_id)
    if player is None:
        raise ValueError(f"P0 current source cannot find canonical player {player_id}")
    for ref in player.provider_refs:
        provider = str(ref.provider).strip().lower()
        if "sleeper" not in provider:
            continue
        source = _SOURCE_BY_SLEEPER_EXTERNAL_ID.get(str(ref.external_id))
        if source is not None:
            candidates[source.current_player_id] = source

    if len(candidates) != 1:
        raise ValueError(
            f"P0 current source mapping is not unique for {player_id}: {sorted(candidates)}"
        )
    return next(iter(candidates.values()))


def build_p0_standard_future_materialization(
    *,
    league_state: LeagueState,
    standard_year_one: tuple[ForecastObservation, ...],
) -> P0FutureMaterialization:
    year_one = _year_one_index(standard_year_one)
    if not year_one:
        raise ValueError("P0 requires a non-empty frozen standard/non-PPR Year-1 coordinate")

    players: dict[str, P0PlayerForecast] = {}
    for player_id, observation in sorted(year_one.items()):
        source = _source_for_player(league_state, player_id)
        if observation.position.value != source.position:
            raise ValueError(
                f"P0 current source position mismatch for {player_id}: "
                f"{observation.position.value} != {source.position}"
            )
        actual = float(observation.distribution.mean)
        expected = float(source.standard_y1_points)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=P0_STANDARD_PARITY_TOLERANCE):
            raise ValueError(
                f"P0 standard/non-PPR Year-1 parity failure for {player_id}: "
                f"{actual} != {expected}"
            )
        players[player_id] = _score_source(
            source,
            player_id=player_id,
            standard_y1_points=actual,
        )
    return P0FutureMaterialization(players=players)
