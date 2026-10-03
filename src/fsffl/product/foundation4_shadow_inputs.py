from __future__ import annotations

import gzip
import hashlib
import json
import math
from importlib.resources import files
from typing import Any

from fsffl.forecast.future_contract import CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
from fsffl.forecast.league_scoring import classify_scoring_coverage
from fsffl.forecast.long_horizon_contract import (
    LONG_HORIZON_AUTHORITY_MAP_SHA256,
    LONG_HORIZON_AUTHORITY_MAP_VERSION,
    LongHorizonForecastAuthorityContract,
    LongHorizonPolicyForecast,
)
from fsffl.state.models import LeagueRules, Position
from fsffl.value.career_tail import CareerTailFeatures

from .i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING


FOUNDATION4_CURRENT_BOARD_RUN_ID = 37090518110
FOUNDATION4_CURRENT_BOARD_ARTIFACT_ID = 11262018062
FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256 = (
    "dad883347facaccbf98bdfc86835b8e650ddfc2789c1ebb95de31ec4a6640f71"
)
FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256 = (
    "be5c6b8d5523c0c3af70aaf0eace0bc268d97b97efa4191482a522252933b81b"
)
FOUNDATION4_LONG_HORIZON_FORECAST_MODEL_VERSION = (
    "y4-y7-frozen-policy-materialization-v1"
)
FOUNDATION4_LONG_HORIZON_FORECAST_SOURCE = (
    "fsffl:frozen_cell_routing_current_coordinate"
)
FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE = (
    "fsffl_frozen_standard_non_ppr_fantasy_points_v1"
)
FOUNDATION4_SCORING_EQUIVALENCE_VERSION = (
    "foundation4-exact-standard-scoring-equivalence-v1"
)
FOUNDATION4_CURRENT_COHORT_SIZE = 335
FOUNDATION4_LONG_HORIZON_ROW_COUNT = FOUNDATION4_CURRENT_COHORT_SIZE * 4 * 4


def _canonical_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_gzip_json(package: str, relative_path: str) -> list[dict[str, Any]]:
    resource = files(package).joinpath(relative_path)
    with resource.open("rb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="rb") as archive:
            decoded = json.loads(archive.read().decode("utf-8"))
    if not isinstance(decoded, list) or not all(isinstance(row, dict) for row in decoded):
        raise ValueError(f"Foundation 4 frozen board is not a row list: {relative_path}")
    return decoded


def foundation4_long_horizon_rows() -> tuple[LongHorizonPolicyForecast, ...]:
    raw_rows = _load_gzip_json(
        "fsffl.forecast",
        "data/foundation4_long_horizon_board_2026.json.gz",
    )
    if len(raw_rows) != FOUNDATION4_LONG_HORIZON_ROW_COUNT:
        raise ValueError("Foundation 4 long-horizon board row count is not governed")
    if _canonical_digest(raw_rows) != FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256:
        raise ValueError("Foundation 4 long-horizon board semantic digest mismatch")
    rows = tuple(
        LongHorizonPolicyForecast.model_validate(
            {
                **row,
                "scoring_coordinate": FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE,
            }
        )
        for row in raw_rows
    )
    if len({row.player_id for row in rows}) != FOUNDATION4_CURRENT_COHORT_SIZE:
        raise ValueError("Foundation 4 long-horizon board player count is not governed")
    return rows


def provide_foundation4_long_horizon_forecast_contract(
) -> LongHorizonForecastAuthorityContract:
    """Return the frozen board in the coordinate it was actually materialized in."""

    rows = foundation4_long_horizon_rows()
    return LongHorizonForecastAuthorityContract(
        evaluation_season=2026,
        scoring_coordinate=FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE,
        authority_map_version=LONG_HORIZON_AUTHORITY_MAP_VERSION,
        authority_map_sha256=LONG_HORIZON_AUTHORITY_MAP_SHA256,
        forecast_model_version=FOUNDATION4_LONG_HORIZON_FORECAST_MODEL_VERSION,
        forecast_source=FOUNDATION4_LONG_HORIZON_FORECAST_SOURCE,
        forecasts=rows,
        provenance={
            "current_board_run_id": FOUNDATION4_CURRENT_BOARD_RUN_ID,
            "current_board_artifact_id": FOUNDATION4_CURRENT_BOARD_ARTIFACT_ID,
            "current_board_semantic_sha256": FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256,
            "rolling_route_run_id": 36271080037,
            "rolling_route_artifact_id": 10916355135,
            "authority_map_sha256": LONG_HORIZON_AUTHORITY_MAP_SHA256,
            "source_scoring_coordinate": FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE,
            "runtime_refit": False,
            "current_named_players_used_for_model_selection": False,
        },
    )


def foundation4_standard_scoring_is_exactly_compatible(rules: LeagueRules) -> bool:
    """True only when active player-offense scoring equals the frozen standard unit."""

    coverage = classify_scoring_coverage(rules)
    if (
        coverage.blocks_full_downstream_authority
        or coverage.provisional_residual_rule_stats
        or coverage.unsupported_rule_stats
    ):
        return False

    expected = {
        row.stat: float(row.points)
        for row in FROZEN_I1_STANDARD_SCORING
        if float(row.points) != 0.0
    }
    supported = set(coverage.supported_rule_stats)
    actual = {
        row.stat: float(row.points)
        for row in rules.scoring
        if row.stat in supported and float(row.points) != 0.0
    }
    return actual == expected


def provide_foundation4_long_horizon_forecast_contract_for_rules(
    rules: LeagueRules,
) -> LongHorizonForecastAuthorityContract:
    """Relabel only an exactly equivalent standard-scoring league coordinate.

    No multiplier or approximation is authorized for Foundation 4.  Non-standard
    leagues must fail closed until a separately governed Y4-Y7/tail transform exists.
    """

    if not foundation4_standard_scoring_is_exactly_compatible(rules):
        raise ValueError(
            "Foundation 4 frozen Y4-Y7 board uses the standard/non-PPR scoring "
            "coordinate; connected-league scoring is incompatible and no governed "
            "Foundation 4 scoring transform is authorized"
        )

    frozen = provide_foundation4_long_horizon_forecast_contract()
    rows = tuple(
        row.model_copy(
            update={"scoring_coordinate": CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE}
        )
        for row in frozen.forecasts
    )
    return frozen.model_copy(
        update={
            "scoring_coordinate": CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE,
            "forecast_model_version": (
                f"{frozen.forecast_model_version}:"
                f"{FOUNDATION4_SCORING_EQUIVALENCE_VERSION}"
            ),
            "forecasts": rows,
            "provenance": {
                **frozen.provenance,
                "coordinate_equivalence": "exact_frozen_standard_scoring_match",
                "coordinate_equivalence_version": (
                    FOUNDATION4_SCORING_EQUIVALENCE_VERSION
                ),
            },
        }
    )


def provide_foundation4_terminal_features() -> dict[str, CareerTailFeatures]:
    raw_rows = _load_gzip_json(
        "fsffl.value",
        "data/foundation4_terminal_features_2026.json.gz",
    )
    if len(raw_rows) != FOUNDATION4_CURRENT_COHORT_SIZE:
        raise ValueError("Foundation 4 terminal feature player count is not governed")
    if _canonical_digest(raw_rows) != FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256:
        raise ValueError("Foundation 4 terminal feature semantic digest mismatch")

    output: dict[str, CareerTailFeatures] = {}
    for raw in raw_rows:
        player_id = str(raw["player_id"])
        if player_id in output:
            raise ValueError("Foundation 4 terminal feature board has duplicate player_id")
        prior = raw.get("prior_points")
        prior_value = None if prior is None else float(prior)
        if prior_value is not None and not math.isfinite(prior_value):
            prior_value = None
        output[player_id] = CareerTailFeatures(
            player_id=player_id,
            position=Position(str(raw["position"])),
            age_years=float(raw["age_years"]),
            experience_years=float(raw["experience_years"]),
            current_points=float(raw["current_points"]),
            prior_points=prior_value,
            current_points_coordinate=str(raw["current_points_coordinate"]),
            prior_points_coordinate=str(raw["prior_points_coordinate"]),
            live_feature_transport_limitation=str(
                raw["live_feature_transport_limitation"]
            ),
        )
    if len(output) != FOUNDATION4_CURRENT_COHORT_SIZE:
        raise ValueError("Foundation 4 terminal feature board is incomplete")
    return output
