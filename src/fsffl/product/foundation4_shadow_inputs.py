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
from fsffl.state.models import LeagueRules, Position, ScoringRule
from fsffl.value.career_tail import CareerTailFeatures

from .i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING


FOUNDATION4_CURRENT_BOARD_RUN_ID = 37096263982
FOUNDATION4_CURRENT_BOARD_ARTIFACT_ID = 11263913850
FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256 = (
    "3caddc5c33be83088eaca30d8c1ac7031022f08668a031a0a3b08616aed773c2"
)
FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256 = (
    "ef52ccaaef0749d6d1e5786c351714570c0d0a0ea811cc1cf940fe2adac8c867"
)
FOUNDATION4_LONG_HORIZON_FORECAST_MODEL_VERSION = (
    "y4-y7-frozen-policy-fsffl-direct-materialization-v1"
)
FOUNDATION4_LONG_HORIZON_FORECAST_SOURCE = (
    "fsffl:frozen_cell_routing_fsffl_scoring_recalibration"
)
FOUNDATION4_FSFFL_SCORING_COORDINATE = CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS = (
    "fum_rec",
    "fum_rec_td",
    "st_ff",
    "st_fum_rec",
    "st_td",
)
FOUNDATION4_LONG_TERM_RESIDUAL_OMISSION_POLICY = (
    "rare_unpredictable_residual_bonuses_omitted_from_long_term_intrinsic"
)
# Retained only as provenance for the superseded pre-recalibration board.
FOUNDATION4_FROZEN_STANDARD_SCORING_COORDINATE = (
    "fsffl_frozen_standard_non_ppr_fantasy_points_v1"
)
FOUNDATION4_SCORING_FREEZE_VERSION = (
    "foundation4-fsffl-connected-scoring-direct-recalibration-v1"
)
FOUNDATION4_CURRENT_COHORT_SIZE = 335
FOUNDATION4_LONG_HORIZON_ROW_COUNT = FOUNDATION4_CURRENT_COHORT_SIZE * 4 * 4
FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING = (
    ScoringRule(stat="pass_yd", points=0.04),
    ScoringRule(stat="pass_td", points=4.0),
    ScoringRule(stat="pass_int", points=-1.0),
    ScoringRule(stat="rush_yd", points=0.1),
    ScoringRule(stat="rush_td", points=6.0),
    ScoringRule(stat="rec", points=0.5),
    ScoringRule(stat="rec_yd", points=0.1),
    ScoringRule(stat="rec_td", points=6.0),
    ScoringRule(stat="fum_lost", points=-1.0),
    ScoringRule(stat="pass_2pt", points=2.0),
    ScoringRule(stat="rush_2pt", points=2.0),
    ScoringRule(stat="rec_2pt", points=2.0),
    ScoringRule(stat="fum_rec", points=2.0),
    ScoringRule(stat="fum_rec_td", points=6.0),
    ScoringRule(stat="st_ff", points=1.0),
    ScoringRule(stat="st_fum_rec", points=1.0),
    ScoringRule(stat="st_td", points=6.0),
)


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
    rows = tuple(LongHorizonPolicyForecast.model_validate(row) for row in raw_rows)
    if len({row.player_id for row in rows}) != FOUNDATION4_CURRENT_COHORT_SIZE:
        raise ValueError("Foundation 4 long-horizon board player count is not governed")
    if {row.scoring_coordinate for row in rows} != {
        FOUNDATION4_FSFFL_SCORING_COORDINATE
    }:
        raise ValueError("Foundation 4 long-horizon board scoring coordinate drifted")
    if {row.model_version for row in rows} != {
        FOUNDATION4_LONG_HORIZON_FORECAST_MODEL_VERSION
    }:
        raise ValueError("Foundation 4 long-horizon board model identity drifted")
    if {row.source for row in rows} != {FOUNDATION4_LONG_HORIZON_FORECAST_SOURCE}:
        raise ValueError("Foundation 4 long-horizon board source identity drifted")
    return rows


def provide_foundation4_long_horizon_forecast_contract(
) -> LongHorizonForecastAuthorityContract:
    """Return the frozen board in the coordinate it was actually materialized in."""

    rows = foundation4_long_horizon_rows()
    return LongHorizonForecastAuthorityContract(
        evaluation_season=2026,
        scoring_coordinate=FOUNDATION4_FSFFL_SCORING_COORDINATE,
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
            "source_scoring_coordinate": FOUNDATION4_FSFFL_SCORING_COORDINATE,
            "scoring_freeze_version": FOUNDATION4_SCORING_FREEZE_VERSION,
            "scoring_materialization": "direct_historical_fsffl_target_recalibration",
            "runtime_refit": False,
            "current_named_players_used_for_model_selection": False,
        },
    )


def foundation4_standard_scoring_is_exactly_compatible(rules: LeagueRules) -> bool:
    """Legacy diagnostic for the superseded standard-scoring freeze."""

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


def foundation4_fsffl_scoring_is_compatible(rules: LeagueRules) -> bool:
    """Match the governed player-offense coordinate used to generate the board.

    Kicker/DST rules stay outside this player-offense Intrinsic coordinate. Zero-point
    rules are inert. Material unsupported player-offense rules remain fail-closed.
    Material predictable rules and retained bounded two-point treatment must match
    the frozen recalibration. The explicitly governed rare residual bonuses are
    permitted in the live league but omitted from Foundation 4 Long-Term Intrinsic;
    they are not reconstructed into the historical Y4+ targets.
    """

    coverage = classify_scoring_coverage(rules)
    if coverage.blocks_full_downstream_authority or coverage.unsupported_rule_stats:
        return False
    ignored = set(FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS)
    active_player_stats = (
        set(coverage.supported_rule_stats)
        | set(coverage.provisional_residual_rule_stats)
    ) - ignored
    expected = {
        row.stat: float(row.points)
        for row in FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        if row.stat not in ignored and float(row.points) != 0.0
    }
    actual = {
        row.stat: float(row.points)
        for row in rules.scoring
        if row.stat in active_player_stats and float(row.points) != 0.0
    }
    if actual != expected:
        return False

    # The omission decision is intentionally narrow to the accepted FSFFL residual
    # coefficients (or zero/absent). A materially different coefficient is a new
    # scoring policy question rather than silently inheriting this exception.
    expected_ignored = {
        row.stat: float(row.points)
        for row in FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        if row.stat in ignored
    }
    configured = {row.stat: float(row.points) for row in rules.scoring}
    return all(
        configured.get(stat, 0.0) in (0.0, expected_points)
        for stat, expected_points in expected_ignored.items()
    )


def provide_foundation4_long_horizon_forecast_contract_for_rules(
    rules: LeagueRules,
) -> LongHorizonForecastAuthorityContract:
    """Return the direct FSFFL-scored freeze only for its governed coordinate."""

    if not foundation4_fsffl_scoring_is_compatible(rules):
        raise ValueError(
            "Foundation 4 frozen Y4-Y7 board uses the governed FSFFL connected-"
            "league scoring coordinate; active player-offense scoring is incompatible "
            "with the retained direct recalibration"
        )
    frozen = provide_foundation4_long_horizon_forecast_contract()
    coverage = classify_scoring_coverage(rules)
    return frozen.model_copy(
        update={
            "provenance": {
                **frozen.provenance,
                "coordinate_compatibility": "exact_fsffl_scoring_freeze",
                "coordinate_compatibility_version": FOUNDATION4_SCORING_FREEZE_VERSION,
                "modeled_rule_stats": list(coverage.supported_rule_stats),
                "governed_residual_rule_stats": list(
                    sorted(
                        set(coverage.provisional_residual_rule_stats)
                        - set(FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS)
                    )
                ),
                "intentionally_omitted_immaterial_residual_rule_stats": list(
                    FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS
                ),
                "residual_omission_policy": (
                    FOUNDATION4_LONG_TERM_RESIDUAL_OMISSION_POLICY
                ),
                "current_intrinsic_boundary": (
                    "standalone Current Intrinsic remains unchanged; its Y1-Y3 "
                    "projection may retain bounded provisional residual scoring, "
                    "while Foundation 4 Y4+ omits these immaterial/unpredictable "
                    "bonuses without historical reconstruction"
                ),
                "ignored_non_lineup_rule_stats": list(
                    coverage.ignored_non_lineup_rule_stats
                ),
                "separate_subject_rule_stats": list(
                    coverage.separate_subject_rule_stats
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
    if {
        str(row.get("current_points_coordinate") or "") for row in raw_rows
    } != {FOUNDATION4_FSFFL_SCORING_COORDINATE}:
        raise ValueError("Foundation 4 terminal current-points coordinate drifted")
    if {
        str(row.get("prior_points_coordinate") or "") for row in raw_rows
    } != {FOUNDATION4_FSFFL_SCORING_COORDINATE}:
        raise ValueError("Foundation 4 terminal prior-points coordinate drifted")

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
            live_feature_transport_limitation=(
                str(raw["live_feature_transport_limitation"])
                + "; Foundation 4 Long-Term Intrinsic intentionally omits rare/"
                "unpredictable residual scoring bonuses "
                + ",".join(FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS)
                + "; standalone Current Intrinsic is unchanged"
            ),
        )
    if len(output) != FOUNDATION4_CURRENT_COHORT_SIZE:
        raise ValueError("Foundation 4 terminal feature board is incomplete")
    return output
