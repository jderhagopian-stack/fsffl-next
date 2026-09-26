from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Mapping

from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import LeagueState, Position

from .future_state_primitive_assets import (
    FUTURE_STATE_ORIGIN_PACKAGE_SHA256,
    FUTURE_STATE_PACKAGE_JSON,
    FUTURE_STATE_PACKAGE_SHA256,
    FUTURE_STATE_SOURCE_CSV,
    FUTURE_STATE_SOURCE_CSV_SHA256,
)


FUTURE_STATE_PRIMITIVE_VERSION = (
    "future-state-probability-primitive-v1:"
    + FUTURE_STATE_ORIGIN_PACKAGE_SHA256[:12]
)
FUTURE_STATE_SOURCE_SEASON = 2026
FUTURE_STATE_SOURCE_ROW_COUNT = 335
FUTURE_STATE_STANDARD_PARITY_TOLERANCE = 1e-9
FUTURE_STATE_PROBABILITY_TOLERANCE = 1e-10
_POSITIVE_STATES = ("depth", "usable", "starter", "premium", "elite")
_THRESHOLDS = ("useful", "starter", "premium", "elite")


@dataclass(frozen=True)
class FutureStateSourceRow:
    """Frozen source identity/features for the validated state-probability primitive.

    These records originated in the P0 research package, but this Forecast-owned
    primitive exposes only the empirically retained identity/current-state features.
    P0 route selection and P0 conditional production scoring are intentionally absent.
    """

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
class FutureStateProbabilityPlayer:
    player_id: str
    source: FutureStateSourceRow
    probabilities: Mapping[int, Mapping[str, float]]

    def probabilities_for(self, horizon: int) -> Mapping[str, float]:
        return self.probabilities[int(horizon)]


@dataclass(frozen=True)
class FutureStateProbabilityMaterialization:
    """Model-neutral probability primitive consumed by promoted Forecast adapters."""

    players: Mapping[str, FutureStateProbabilityPlayer]
    primitive_version: str = FUTURE_STATE_PRIMITIVE_VERSION
    origin_package_sha256: str = FUTURE_STATE_ORIGIN_PACKAGE_SHA256
    primitive_package_sha256: str = FUTURE_STATE_PACKAGE_SHA256
    source_sha256: str = FUTURE_STATE_SOURCE_CSV_SHA256
    source_season: int = FUTURE_STATE_SOURCE_SEASON

    @property
    def player_count(self) -> int:
        return len(self.players)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if _sha256(FUTURE_STATE_PACKAGE_JSON) != FUTURE_STATE_PACKAGE_SHA256:
    raise ValueError("embedded future-state fitted package byte hash mismatch")
if _sha256(FUTURE_STATE_SOURCE_CSV) != FUTURE_STATE_SOURCE_CSV_SHA256:
    raise ValueError("embedded future-state source coordinate byte hash mismatch")

_PACKAGE = json.loads(FUTURE_STATE_PACKAGE_JSON)
if _PACKAGE.get("schema_version") != "fsffl-future-state-probability-primitive-v1":
    raise ValueError("embedded future-state primitive schema mismatch")
if _PACKAGE.get("origin_schema_version") != "fsffl-redeveloped-forecast-fit-v1":
    raise ValueError("embedded future-state origin schema mismatch")

# The charter-correct primitive deliberately retains only the fitted state layer.
# P0 production models, D0/D1 routes, and conditional point scorers are not exposed
# or consulted by this module.
_STATE_LAYERS = {
    horizon: {
        "QB": _PACKAGE["horizons"][str(horizon)]["state_qb"],
        "NON_QB": _PACKAGE["horizons"][str(horizon)]["state_nonqb"],
    }
    for horizon in (2, 3)
}


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _load_source_rows() -> tuple[FutureStateSourceRow, ...]:
    rows: list[FutureStateSourceRow] = []
    for raw in csv.DictReader(io.StringIO(FUTURE_STATE_SOURCE_CSV)):
        rows.append(
            FutureStateSourceRow(
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
                prior_age_state_resid_z=_optional_float(
                    raw.get("prior_age_state_resid_z")
                ),
                prior2_coverage=int(raw["prior2_coverage"]),
                prior2_mean_age_state_z=_optional_float(
                    raw.get("prior2_mean_age_state_z")
                ),
                prior2_gap_age_state_z=_optional_float(
                    raw.get("prior2_gap_age_state_z")
                ),
                source_percentile=float(raw["source_percentile"]),
                state_percentile=float(raw["state_percentile"]),
            )
        )
    if len(rows) != FUTURE_STATE_SOURCE_ROW_COUNT:
        raise ValueError(
            "embedded future-state source row count mismatch: "
            f"{len(rows)} != {FUTURE_STATE_SOURCE_ROW_COUNT}"
        )
    current_ids = [row.current_player_id for row in rows]
    sleeper_ids = [row.sleeper_external_id for row in rows]
    if len(set(current_ids)) != len(rows) or len(set(sleeper_ids)) != len(rows):
        raise ValueError("embedded future-state source identity is not unique")
    return tuple(rows)


_SOURCE_ROWS = _load_source_rows()
_SOURCE_BY_CURRENT_ID = {row.current_player_id: row for row in _SOURCE_ROWS}
_SOURCE_BY_PLAYER_ID = {row.player_id: row for row in _SOURCE_ROWS}
_SOURCE_BY_SLEEPER_EXTERNAL_ID = {
    row.sleeper_external_id: row for row in _SOURCE_ROWS
}


def frozen_future_state_source_rows() -> tuple[FutureStateSourceRow, ...]:
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
    return sum(
        float(c) * float(feat.get(name, 0.0))
        for c, name in zip(coef, names, strict=True)
    )


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _score_bin(package: Mapping[str, object], feat: Mapping[str, float]) -> float:
    intercept = package["intercept"]
    if not isinstance(intercept, list) or not intercept:
        raise ValueError("future-state binary package lacks intercept")
    return _sigmoid(
        float(intercept[0])
        + _dot(
            [float(value) for value in package["coef"]],
            [str(value) for value in package["features"]],
            feat,
        )
    )


def _prob_features(
    row: SimpleNamespace,
    *,
    age_mode: str,
    add_c: bool,
    add_d: bool,
) -> dict[str, float]:
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
        raise ValueError(f"unknown future-state age mode: {age_mode}")

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
    if (
        role in ("weak", "established")
        and _finite(row.opportunity_per_game)
        and _finite(row.games)
    ):
        feat[f"role={role}"] = 1.0
        feat["u_cov"] = 1.0
        feat["lopg"] = (
            math.log1p(max(0.0, float(row.opportunity_per_game))) / 4.0
        )
        feat["lg"] = math.log1p(max(0.0, float(row.games))) / 3.0
    else:
        feat.update(
            {
                "role=unknown": 1.0,
                "u_cov": 0.0,
                "lopg": 0.0,
                "lg": 0.0,
            }
        )
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
            feat[f"hi_{position}_{row.source_state}"] = max(
                0.0,
                (percentile - 0.8) / 0.2,
            )
            feat[f"lo_{position}_{row.source_state}"] = max(
                0.0,
                (0.2 - percentile) / 0.2,
            )
    return feat


def _score_prob(
    layer_package: Mapping[str, object],
    row: SimpleNamespace,
) -> dict[str, float]:
    add_c = bool(layer_package["add_c"])
    persistence = _score_bin(
        layer_package["persistence"],
        _prob_features(row, age_mode="a2", add_c=add_c, add_d=False),
    )
    ordered_feat = _prob_features(
        row,
        age_mode="coarse",
        add_c=add_c,
        add_d=True,
    )
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
    result.update(
        {
            state: persistence * conditional[state]
            for state in _POSITIVE_STATES
        }
    )
    total = sum(result.values())
    if total <= 0:
        raise ValueError("future-state probability mass is nonpositive")
    normalized = {
        state: float(result[state] / total)
        for state in STATE_NAMES
    }
    if (
        abs(sum(normalized.values()) - 1.0)
        > FUTURE_STATE_PROBABILITY_TOLERANCE
    ):
        raise ValueError("future-state probabilities do not sum to one")
    return normalized


def _source_for_player(
    league_state: LeagueState,
    player_id: str,
) -> FutureStateSourceRow:
    direct = _SOURCE_BY_CURRENT_ID.get(player_id) or _SOURCE_BY_PLAYER_ID.get(
        player_id
    )
    candidates: dict[str, FutureStateSourceRow] = {}
    if direct is not None:
        candidates[direct.current_player_id] = direct

    by_player = {player.player_id: player for player in league_state.players}
    player = by_player.get(player_id)
    if player is None:
        raise ValueError(
            f"future-state source cannot find canonical player {player_id}"
        )
    for ref in player.provider_refs:
        provider = str(ref.provider).strip().lower()
        if "sleeper" not in provider:
            continue
        source = _SOURCE_BY_SLEEPER_EXTERNAL_ID.get(str(ref.external_id))
        if source is not None:
            candidates[source.current_player_id] = source

    if len(candidates) != 1:
        raise ValueError(
            "future-state source mapping is not unique for "
            f"{player_id}: {sorted(candidates)}"
        )
    return next(iter(candidates.values()))


def governed_future_state_source_row(
    league_state: LeagueState,
    player_id: str,
) -> FutureStateSourceRow:
    """Return the unique frozen governed source row for one current canonical subject.

    This is an identity/read-only primitive. It does not broaden the frozen source
    cohort and raises when the current subject cannot be uniquely reconciled through
    the accepted canonical/Sleeper identity mapping.
    """

    return _source_for_player(league_state, player_id)


def governed_future_state_player_ids(
    league_state: LeagueState,
) -> tuple[str, ...]:
    """Canonical current ids represented by the validated frozen source cohort."""

    governed: list[str] = []
    for player in league_state.players:
        try:
            _source_for_player(league_state, player.player_id)
        except ValueError:
            continue
        governed.append(player.player_id)
    return tuple(sorted(set(governed)))


def _year_one_index(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    result: dict[str, ForecastObservation] = {}
    for observation in observations:
        if (
            observation.horizon != ForecastHorizon.SEASON
            or observation.position
            not in {Position.QB, Position.RB, Position.WR, Position.TE}
        ):
            continue
        if observation.player_id in result:
            raise ValueError(
                "duplicate future-state standard Year-1 observation for "
                f"{observation.player_id}"
            )
        result[observation.player_id] = observation
    return result


def build_future_state_probability_materialization(
    *,
    league_state: LeagueState,
    standard_year_one: tuple[ForecastObservation, ...],
) -> FutureStateProbabilityMaterialization:
    """Materialize only the empirically retained identity/probability primitive."""

    year_one = _year_one_index(standard_year_one)
    if not year_one:
        raise ValueError(
            "future-state primitive requires a non-empty standard/non-PPR "
            "Year-1 coordinate"
        )

    players: dict[str, FutureStateProbabilityPlayer] = {}
    for player_id, observation in sorted(year_one.items()):
        source = _source_for_player(league_state, player_id)
        if observation.position.value != source.position:
            raise ValueError(
                "future-state source position mismatch for "
                f"{player_id}: {observation.position.value} != {source.position}"
            )
        actual = float(observation.distribution.mean)
        expected = float(source.standard_y1_points)
        if not math.isclose(
            actual,
            expected,
            rel_tol=0.0,
            abs_tol=FUTURE_STATE_STANDARD_PARITY_TOLERANCE,
        ):
            raise ValueError(
                "future-state standard/non-PPR Year-1 parity failure for "
                f"{player_id}: {actual} != {expected}"
            )

        probabilities: dict[int, Mapping[str, float]] = {}
        for horizon in (2, 3):
            row = SimpleNamespace(
                position=source.position,
                horizon=horizon,
                experience=source.experience,
                source_state=source.source_state,
                age_band=source.age_band,
                age=source.age,
                source_points=actual,
                prior1_points=source.prior1_points,
                prior1_coverage=source.prior1_coverage,
                source_role_band=source.source_role_band,
                games=source.games,
                opportunity_per_game=source.opportunity_per_game,
                prior_age_state_resid_z=source.prior_age_state_resid_z,
                state_percentile=source.state_percentile,
            )
            family = "QB" if source.position == "QB" else "NON_QB"
            probabilities[horizon] = _score_prob(
                _STATE_LAYERS[horizon][family],
                row,
            )

        players[player_id] = FutureStateProbabilityPlayer(
            player_id=player_id,
            source=source,
            probabilities=probabilities,
        )

    return FutureStateProbabilityMaterialization(players=players)
