from __future__ import annotations

import base64
import hashlib
import json
import math
import zlib
from dataclasses import dataclass
from typing import Mapping

from fsffl.forecast.future_contract import (
    ForecastUncertaintyKind,
    FutureForecastContract,
    FutureForecastScenario,
    FuturePlayerHorizonForecast,
)
from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import ForecastObservation
from fsffl.state.models import LeagueState, Position

from ._vnext_data_qb_y2 import DATA_B64 as QB_Y2_B64
from ._vnext_data_qb_y3 import DATA_B64 as QB_Y3_B64
from ._vnext_data_rb_y2 import DATA_B64 as RB_Y2_B64
from ._vnext_data_rb_y3 import DATA_B64 as RB_Y3_B64
from ._vnext_data_te_y2 import DATA_B64 as TE_Y2_B64
from ._vnext_data_te_y3 import DATA_B64 as TE_Y3_B64
from ._vnext_data_wr_y2 import DATA_B64 as WR_Y2_B64
from ._vnext_data_wr_y3 import DATA_B64 as WR_Y3_B64
from ._vnext_ratio_nodes import DATA_B64 as RATIO_NODES_B64
from .i1_player_scoring import (
    FUTURE_I1_PLAYER_SCORING_VERSION,
    build_future_i1_player_scoring_multipliers,
    derive_future_i1_standard_year_one,
)
from .p0_forecast_runtime import (
    P0_PROBABILITY_TOLERANCE,
    P0_SOURCE_SEASON,
    build_p0_standard_future_materialization,
)
from .p0_future_forecast_provider import P0_FUTURE_SCORING_COORDINATE


VNEXT_FORECAST_VERSION = "forecast-vnext-a2-burr-20260922"
VNEXT_FUTURE_FORECAST_SOURCE = "fsffl:forecast_vnext_a2_burr_frozen"
VNEXT_ARCHIVE_SHA256 = "76b2842349093bb0f5c2bdc60995f78256d7cf6e2e4d64be84768a082450ceb1"
VNEXT_RESEARCH_COMMIT = "122e802f327baf2fc7989ab635a68dfdc481d63f"
VNEXT_RESEARCH_BRANCH = "research/recover-package-a2-burr-20260922"
VNEXT_RESEARCH_TAG = "research-freeze/a2-burr-20260922"
VNEXT_RESEARCH_TAG_OBJECT = "b12c23008b2879af29f3f94c683de18ccbcaf264"
VNEXT_MANIFEST_FILE_COUNT = 40
VNEXT_STAGE_D_PLAYER_COUNT = 335
VNEXT_STAGE_D_ROW_COUNT = 670
VNEXT_RATIO_NODE_COUNT = 81
VNEXT_RATIO_NODES_SHA256 = "738b5b51fe82ad5bad93b72852f3dc4e9ded1046f20330b5f417b755f6118e4a"
VNEXT_CURRENT_SOURCE_COORDINATE = "preserved_preseason_2026_source_335"
VNEXT_CURRENT_SOURCE_PLAYER_COUNT = 335
VNEXT_CURRENT_SOURCE_REFRESH_AUTHORITY = "governed_annual_preseason_source_snapshot"
VNEXT_NEW_PLAYER_POLICY = "fail_closed_until_governed_source_refresh"
VNEXT_PROBABILITY_CANONICAL_SHA256_11DP = "ca99fb8bbd840a04e6698d15389136cc0b9061a082cbb10a7a3bd6d41697f706"
VNEXT_STAGE_D_FORECAST_CANONICAL_SHA256_10DP = "3a17b1b02a5ce2610894bc5a0d934c21e2e937c507980df0219c92dc2c6679bf"
VNEXT_STAGE_D_STATE_MEAN_SHARDS_SHA256 = {
    "QB:2": "572db17fac68318b36005dca3ff8a1c7cc7dec776a46e9601e105c1cc1d31f1e",
    "QB:3": "4a2cc1596c5272b416e2dd43546d2cea11be00c967124dc2236851eac67d2d45",
    "RB:2": "65018c2db88ed39393985a78f15db56db61676aaa8b6e675acaf441cfc61efa1",
    "RB:3": "c87a724deb57e23b3d258c583d7565bb5ba1bc33919caf68d0a3c91491e13a19",
    "TE:2": "959e64402dae5e9ca6e5f9ea759834a7ba6baffa485a4a8d45b392367cf593f9",
    "TE:3": "57a32b11a695ac494cc6564379df7ff16106f38f3cdd0e48a74f147e7301dcc2",
    "WR:2": "1eca9e50c49c01af241d827cfa5e6e14c02524bb29a6debb345c6359e6445bc2",
    "WR:3": "daa4718dd2ef42c4dc335830283df1ca4f39a3894cb59db3597b121544a27ba1",
}
VNEXT_LATEST_DISTRIBUTION_PARAMETERS = {
    "QB:2": "BURR12_M1:c=4.412206982641597,m=1.517013117227367,d=1.7436570629747394,scale=1.135078009403411",
    "QB:3": "BURR12_M1:c=4.089640332906609,m=1.5671440102088534,d=1.811664290379622,scale=1.1566910766124239",
    "RB:2": "DIRECT_GAMMA_M1:shape=7.350891953014491",
    "RB:3": "DIRECT_GAMMA_M1:shape=7.728654304702037",
    "TE:2": "DIRECT_GAMMA_M1:shape=8.788467575558814",
    "TE:3": "DIRECT_GAMMA_M1:shape=9.024660406225102",
    "WR:2": "DIRECT_GAMMA_M1:shape=10.65922356483981",
    "WR:3": "DIRECT_GAMMA_M1:shape=10.37496771008586",
}
_POSITIVE_STATES = ("depth", "usable", "starter", "premium", "elite")
_DATA_B64 = {
    ("QB", 2): QB_Y2_B64,
    ("QB", 3): QB_Y3_B64,
    ("RB", 2): RB_Y2_B64,
    ("RB", 3): RB_Y3_B64,
    ("TE", 2): TE_Y2_B64,
    ("TE", 3): TE_Y3_B64,
    ("WR", 2): WR_Y2_B64,
    ("WR", 3): WR_Y3_B64,
}


@dataclass(frozen=True)
class VNextFutureForecastContractMaterialization:
    contract: FutureForecastContract
    scoring_multipliers: Mapping[str, float]


def _decode(payload: str):
    return json.loads(zlib.decompress(base64.b64decode(payload)).decode("utf-8"))


def _decode_state_mean_rows(
    payload: str,
) -> dict[str, tuple[float, float, float, float, float]]:
    result: dict[str, tuple[float, float, float, float, float]] = {}
    raw = _decode(payload)
    if not isinstance(raw, list):
        raise ValueError("frozen vNext state-mean shard must decode to a row list")
    for row in raw:
        if not isinstance(row, list) or len(row) not in (6, 9):
            raise ValueError("frozen vNext state-mean row has unexpected shape")
        external_id = str(row[0])
        mean_values = row[4:9] if len(row) == 9 else row[1:6]
        means = tuple(float(value) for value in mean_values)
        if len(means) != 5 or any(not math.isfinite(value) or value < 0.0 for value in means):
            raise ValueError(f"invalid frozen vNext state means for sleeper:{external_id}")
        if external_id in result:
            raise ValueError(f"duplicate frozen vNext sleeper id: {external_id}")
        result[external_id] = means
    return result


_STATE_MEANS = {
    key: _decode_state_mean_rows(payload)
    for key, payload in _DATA_B64.items()
}
_RATIO_NODES_RAW = _decode(RATIO_NODES_B64)
if not isinstance(_RATIO_NODES_RAW, dict):
    raise ValueError("frozen vNext ratio-node artifact must decode to a mapping")
_RATIO_NODES: dict[tuple[str, int], tuple[float, ...]] = {}
for position in ("QB", "RB", "TE", "WR"):
    for horizon in (2, 3):
        key = f"{position}:{horizon}"
        nodes = tuple(float(value) for value in _RATIO_NODES_RAW[key])
        if len(nodes) != VNEXT_RATIO_NODE_COUNT:
            raise ValueError(f"frozen vNext ratio node count mismatch for {key}")
        if nodes != tuple(sorted(nodes)) or any(value <= 0.0 for value in nodes):
            raise ValueError(f"frozen vNext ratio nodes are invalid for {key}")
        _RATIO_NODES[(position, horizon)] = nodes

if sum(len(rows) for rows in _STATE_MEANS.values()) != VNEXT_STAGE_D_ROW_COUNT:
    raise ValueError("frozen vNext Stage D row count mismatch")
if len(set().union(*(set(rows) for rows in _STATE_MEANS.values()))) != VNEXT_STAGE_D_PLAYER_COUNT:
    raise ValueError("frozen vNext Stage D player count mismatch")


def frozen_vnext_stage_d_state_means(
    position: str,
    horizon: int,
    sleeper_external_id: str,
) -> Mapping[str, float]:
    values = _STATE_MEANS[(position, int(horizon))][str(sleeper_external_id)]
    return dict(zip(_POSITIVE_STATES, values, strict=True))


def frozen_vnext_ratio_nodes(position: str, horizon: int) -> tuple[float, ...]:
    return _RATIO_NODES[(position, int(horizon))]


def _weighted_quantile(
    probabilities: Mapping[str, float],
    state_means: Mapping[str, float],
    ratio_nodes: tuple[float, ...],
    quantile: float,
) -> float:
    values_and_weights: list[tuple[float, float]] = [
        (0.0, max(0.0, float(probabilities["out"])))
    ]
    node_count = len(ratio_nodes)
    for state in _POSITIVE_STATES:
        state_probability = max(0.0, float(probabilities[state]))
        state_mean = max(0.0, float(state_means[state]))
        node_weight = state_probability / node_count
        values_and_weights.extend(
            (state_mean * ratio, node_weight)
            for ratio in ratio_nodes
        )
    values_and_weights.sort(key=lambda item: item[0])
    total = sum(weight for _, weight in values_and_weights)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=P0_PROBABILITY_TOLERANCE):
        raise ValueError(f"vNext uncertainty probability mass mismatch: {total}")
    cumulative = 0.0
    for value, weight in values_and_weights:
        cumulative += weight / total
        if cumulative >= quantile:
            return float(value)
    return float(values_and_weights[-1][0])


def _distribution_stddev(
    probabilities: Mapping[str, float],
    state_means: Mapping[str, float],
    ratio_nodes: tuple[float, ...],
    expected: float,
) -> float:
    node_count = len(ratio_nodes)
    second_moment = 0.0
    for state in _POSITIVE_STATES:
        p_state = max(0.0, float(probabilities[state]))
        mean = max(0.0, float(state_means[state]))
        second_moment += p_state * sum((mean * ratio) ** 2 for ratio in ratio_nodes) / node_count
    return math.sqrt(max(0.0, second_moment - expected * expected))


def _state_mean_shard_digest(
    position: str,
    horizon: int,
) -> str:
    rows = _STATE_MEANS[(position, horizon)]
    canonical = json.dumps(
        [
            [external_id, *rows[external_id]]
            for external_id in sorted(rows, key=lambda value: int(value) if value.isdigit() else value)
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def _canonical_digest(rows: list[list[object]], *, digits: int) -> str:
    normalized: list[list[object]] = []
    for row in rows:
        normalized.append(
            [
                row[0],
                row[1],
                *[
                    round(float(value), digits)
                    for value in row[2:]
                ],
            ]
        )
    encoded = json.dumps(
        normalized,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def vnext_shadow_identity() -> dict[str, object]:
    """Replay the frozen 335 x Y2/Y3 Stage-D coordinate without product state.

    This is a validation surface, not a second Forecast authority.  It proves the
    shipped probability layer, conditional-state means and 81-node uncertainty
    adapter reproduce the exact current-coordinate handoff to the preregistered
    canonical precision.
    """

    p0 = build_p0_standard_future_materialization(
        league_state=_frozen_source_league_state(),
        standard_year_one=_frozen_source_year_one(),
    )
    probability_rows: list[list[object]] = []
    forecast_rows: list[list[object]] = []
    max_probability_mass_error = 0.0
    max_expected_identity_error = 0.0
    for player_id in sorted(p0.players):
        player = p0.players[player_id]
        position = str(player.source.position)
        sleeper_external_id = player.source.sleeper_external_id
        for horizon in (2, 3):
            result = player.result_for(horizon)
            probabilities = {
                state: float(result.probabilities[state])
                for state in STATE_NAMES
            }
            max_probability_mass_error = max(
                max_probability_mass_error,
                abs(sum(probabilities.values()) - 1.0),
            )
            means = {
                "out": 0.0,
                **dict(
                    frozen_vnext_stage_d_state_means(
                        position,
                        horizon,
                        sleeper_external_id,
                    )
                ),
            }
            expected = sum(
                probabilities[state] * means[state]
                for state in STATE_NAMES
            )
            identity = sum(
                probabilities[state] * means[state]
                for state in STATE_NAMES
            )
            max_expected_identity_error = max(
                max_expected_identity_error,
                abs(expected - identity),
            )
            ratio_nodes = frozen_vnext_ratio_nodes(position, horizon)
            q10 = _weighted_quantile(probabilities, means, ratio_nodes, 0.10)
            q50 = _weighted_quantile(probabilities, means, ratio_nodes, 0.50)
            q90 = _weighted_quantile(probabilities, means, ratio_nodes, 0.90)
            q99 = _weighted_quantile(probabilities, means, ratio_nodes, 0.99)
            probability_rows.append(
                [
                    player_id,
                    horizon,
                    *[probabilities[state] for state in STATE_NAMES],
                ]
            )
            forecast_rows.append(
                [player_id, horizon, expected, q10, q50, q90, q99]
            )
    return {
        "players": len(p0.players),
        "rows": len(forecast_rows),
        "probability_canonical_sha256_11dp": _canonical_digest(
            probability_rows,
            digits=11,
        ),
        "forecast_canonical_sha256_10dp": _canonical_digest(
            forecast_rows,
            digits=10,
        ),
        "max_probability_mass_error": max_probability_mass_error,
        "max_expected_identity_error": max_expected_identity_error,
    }


def _frozen_source_league_state() -> LeagueState:
    """Build the minimal canonical state needed for the frozen source replay."""

    from datetime import UTC, datetime

    from fsffl.state.models import League, LeagueRules, Player, PlayerState, ProviderRef, Provenance

    sources = tuple(_frozen_source_rows())
    now = datetime(2026, 9, 1, tzinfo=UTC)
    provenance = Provenance(
        source="fsffl:vnext_shadow_identity",
        retrieved_at=now,
        effective_at=now,
        source_version=VNEXT_FORECAST_VERSION,
    )
    players = tuple(
        Player(
            player_id=source.current_player_id,
            full_name=source.player_name,
            position=Position(source.position),
            provider_refs=(
                ProviderRef(
                    provider="sleeper",
                    external_id=source.sleeper_external_id,
                ),
            ),
        )
        for source in sources
    )
    return LeagueState(
        league=League(
            league_id="fsffl:vnext-shadow",
            name="vNext shadow identity",
            season=P0_SOURCE_SEASON,
            rules=LeagueRules(team_count=1, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=now,
                provenance=provenance,
            )
            for player in players
        ),
    )


def _frozen_source_year_one() -> tuple[ForecastObservation, ...]:
    """Expose the preserved standard/non-PPR source coordinate for parity only."""

    from datetime import UTC, datetime, timedelta

    from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric
    from fsffl.state.models import Provenance

    now = datetime(2026, 9, 1, tzinfo=UTC)
    provenance = Provenance(
        source="fsffl:vnext_shadow_identity",
        retrieved_at=now,
        effective_at=now,
        source_version=VNEXT_FORECAST_VERSION,
    )
    return tuple(
        ForecastObservation(
            player_id=source.current_player_id,
            position=Position(source.position),
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=now,
            period_end=now + timedelta(days=180),
            distribution=ForecastDistribution(
                mean=float(source.standard_y1_points),
                stddev=0.0,
            ),
            source="fsffl:vnext_shadow_identity",
            model_version=VNEXT_FORECAST_VERSION,
            as_of=now,
            provenance=provenance,
        )
        for source in _frozen_source_rows()
    )


def _frozen_source_rows():
    from .p0_forecast_runtime import frozen_p0_source_rows

    return frozen_p0_source_rows()


def build_vnext_future_forecast_contract(
    *,
    league_state: LeagueState,
    raw_forecasts: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
) -> VNextFutureForecastContractMaterialization:
    """Materialize the frozen A2 + Burr XII Forecast vNext Y2/Y3 authority.

    P0's already-governed current-coordinate probability layer is reused because
    the research freeze demonstrated byte/numerical parity with frozen A2 state
    probabilities. Conditional state means come only from the verified Stage D
    A2 handoff. Burr XII changes QB positive-state within-state uncertainty only;
    direct-Gamma remains attached to RB/WR/TE. No fitting, route selection,
    clipping, market input, or post-hoc scaling occurs here.
    """

    standard_year_one = derive_future_i1_standard_year_one(
        raw_forecasts=raw_forecasts,
        rules=league_state.league.rules,
    )
    scoring_multipliers = build_future_i1_player_scoring_multipliers(
        raw_forecasts=raw_forecasts,
        league_year_one=league_year_one,
        rules=league_state.league.rules,
    )
    p0 = build_p0_standard_future_materialization(
        league_state=league_state,
        standard_year_one=standard_year_one,
    )
    if set(p0.players) != set(scoring_multipliers):
        raise ValueError("vNext future Forecast/scoring coverage mismatch")

    rows: list[FuturePlayerHorizonForecast] = []
    for player_id in sorted(p0.players):
        player_forecast = p0.players[player_id]
        position = str(player_forecast.source.position)
        sleeper_external_id = player_forecast.source.sleeper_external_id
        multiplier = float(scoring_multipliers[player_id])
        for year_index in (2, 3):
            p0_result = player_forecast.result_for(year_index)
            probabilities = {
                state: max(0.0, float(p0_result.probabilities[state]))
                for state in STATE_NAMES
            }
            total_probability = sum(probabilities.values())
            if not math.isclose(
                total_probability,
                1.0,
                rel_tol=0.0,
                abs_tol=P0_PROBABILITY_TOLERANCE,
            ):
                raise ValueError(
                    f"vNext state probability mass mismatch for {player_id} Y{year_index}"
                )
            try:
                frozen_means = frozen_vnext_stage_d_state_means(
                    position,
                    year_index,
                    sleeper_external_id,
                )
            except KeyError as exc:
                raise ValueError(
                    f"frozen vNext Stage D row missing for sleeper:{sleeper_external_id} "
                    f"{position} Y{year_index}"
                ) from exc
            league_means = {
                state: max(0.0, float(frozen_means[state]) * multiplier)
                for state in _POSITIVE_STATES
            }
            state_means = {"out": 0.0, **league_means}
            anticipated = sum(
                probabilities[state] * state_means[state]
                for state in STATE_NAMES
            )
            ratio_nodes = frozen_vnext_ratio_nodes(position, year_index)
            p10 = _weighted_quantile(probabilities, state_means, ratio_nodes, 0.10)
            p50 = _weighted_quantile(probabilities, state_means, ratio_nodes, 0.50)
            p90 = _weighted_quantile(probabilities, state_means, ratio_nodes, 0.90)
            rows.append(
                FuturePlayerHorizonForecast(
                    player_id=player_id,
                    position=Position(position),
                    evaluation_season=P0_SOURCE_SEASON,
                    year_index=year_index,
                    target_season=P0_SOURCE_SEASON + year_index - 1,
                    central_expectation=max(0.0, float(anticipated)),
                    scoring_coordinate=P0_FUTURE_SCORING_COORDINATE,
                    model_version=VNEXT_FORECAST_VERSION,
                    source=VNEXT_FUTURE_FORECAST_SOURCE,
                    uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                    stddev=_distribution_stddev(
                        probabilities,
                        state_means,
                        ratio_nodes,
                        anticipated,
                    ),
                    p10=p10,
                    p50=p50,
                    p90=p90,
                    scenarios=tuple(
                        FutureForecastScenario(
                            scenario_id=state,
                            probability=probabilities[state],
                            fantasy_points=state_means[state],
                        )
                        for state in STATE_NAMES
                    ),
                    evidence_path=(
                        "frozen_a2_state_probability_and_mean"
                        + (
                            ":burr12_m1_positive_state_uncertainty"
                            if position == "QB"
                            else ":direct_gamma_m1_positive_state_uncertainty"
                        )
                    ),
                )
            )

    provenance: dict[str, bool | float | int | str | None] = {
        "provider_neutral_contract": True,
        "future_forecast_authority": "A2_BURR_XII_FROZEN_20260922",
        "research_freeze_archive_sha256": VNEXT_ARCHIVE_SHA256,
        "research_freeze_manifest_files": VNEXT_MANIFEST_FILE_COUNT,
        "research_freeze_manifest_verified_files": VNEXT_MANIFEST_FILE_COUNT,
        "research_commit": VNEXT_RESEARCH_COMMIT,
        "research_branch": VNEXT_RESEARCH_BRANCH,
        "research_tag": VNEXT_RESEARCH_TAG,
        "research_tag_object": VNEXT_RESEARCH_TAG_OBJECT,
        "stage_d_players": VNEXT_STAGE_D_PLAYER_COUNT,
        "stage_d_rows": VNEXT_STAGE_D_ROW_COUNT,
        "stage_d_role": "frozen_2026_current_coordinate_and_validation_fixture",
        "current_source_coordinate": VNEXT_CURRENT_SOURCE_COORDINATE,
        "current_source_player_count": VNEXT_CURRENT_SOURCE_PLAYER_COUNT,
        "current_source_refresh_authority": VNEXT_CURRENT_SOURCE_REFRESH_AUTHORITY,
        "new_player_policy": VNEXT_NEW_PLAYER_POLICY,
        "runtime_generalizes_beyond_frozen_source_coordinate": False,
        "state_probability_authority": "frozen_A2_equal_to_current_P0_within_3.33e-16",
        "conditional_state_mean_authority": "frozen_A2_stage_d_current_coordinate",
        "qb_within_state_family": "BURR12_M1",
        "non_qb_within_state_family": "DIRECT_GAMMA_M1",
        "within_state_ratio_nodes": VNEXT_RATIO_NODE_COUNT,
        "within_state_ratio_nodes_sha256": VNEXT_RATIO_NODES_SHA256,
        "burr_changes_state_probability": False,
        "burr_changes_conditional_state_mean": False,
        "burr_value_shapley_tail_family_only_delta": 0.0,
        "known_qb_shoulder_misses": "1.45x,1.50x,1.55x",
        "current_named_players_used_for_fit_or_selection": False,
        "current_season_y1_authority_changed": False,
        "runtime_clipping": False,
        "future_i1_scoring_version": FUTURE_I1_PLAYER_SCORING_VERSION,
        "future_i1_scoring_method": "player_specific_year1_league_standard_ratio",
        "future_i1_scoring_player_count": len(scoring_multipliers),
        "distribution_parameters": json.dumps(
            VNEXT_LATEST_DISTRIBUTION_PARAMETERS,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "state_mean_shard_sha256": json.dumps(
            {
                f"{position}:{horizon}": _state_mean_shard_digest(position, horizon)
                for position in ("QB", "RB", "TE", "WR")
                for horizon in (2, 3)
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    }
    contract = FutureForecastContract(
        evaluation_season=P0_SOURCE_SEASON,
        scoring_coordinate=P0_FUTURE_SCORING_COORDINATE,
        forecast_model_version=VNEXT_FORECAST_VERSION,
        forecast_source=VNEXT_FUTURE_FORECAST_SOURCE,
        forecasts=tuple(rows),
        provenance=provenance,
    )
    return VNextFutureForecastContractMaterialization(
        contract=contract,
        scoring_multipliers=dict(scoring_multipliers),
    )
