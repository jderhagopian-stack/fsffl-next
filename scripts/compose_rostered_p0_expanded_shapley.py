"""Compose saved roster P0 packets with the frozen full Shapley cohort.

This utility is nonproduction. It reads sanitized frozen-board data and a private
P0 JSON artifact, computes Shapley for the complete 335 + candidate cohort, then
emits only the candidate Y1-Y3 components. It never computes candidate-alone
Shapley values and never rewrites the frozen reference.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource

from fsffl.forecast.future_contract import (
    ForecastUncertaintyKind,
    FutureForecastContract,
    FutureForecastScenario,
    FuturePlayerHorizonForecast,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import LeagueRules, Position, Provenance
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar_from_forecast_contract,
)
from fsffl.value.shapley_intrinsic_contract import build_shapley_intrinsic_contract

STATE_NAMES = ("out", "depth", "usable", "starter", "premium", "elite")
BOARD_STATES = ("out", "depth", "usable", "starter", "premium", "elite")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _make_observation(
    *,
    player_id: str,
    position: str,
    points: float,
    as_of: datetime,
    source: str,
    model_version: str,
) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=Position(position),
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=timezone.utc),
        period_end=datetime(2027, 1, 10, tzinfo=timezone.utc),
        distribution=ForecastDistribution(mean=float(points), stddev=0.0),
        source=source,
        model_version=model_version,
        as_of=as_of,
        provenance=Provenance(
            source=source,
            retrieved_at=as_of,
            effective_at=as_of,
            source_version=model_version,
        ),
    )


def _base_future_rows(board: list[dict[str, str]]) -> list[FuturePlayerHorizonForecast]:
    output: list[FuturePlayerHorizonForecast] = []
    for row in board:
        player_id = row["current_player_id"]
        position = Position(row["position"])
        for year_index in (2, 3):
            prefix = f"y{year_index}_"
            probabilities = [
                float(row[prefix + f"p_{state}"])
                for state in STATE_NAMES
            ]
            means = [0.0] + [
                float(row[prefix + f"player_league_mean_{state}"])
                for state in STATE_NAMES[1:]
            ]
            # Reconcile to the canonical P0 expected points already accepted
            # in the reference board before constructing typed contracts.
            expectation = sum(p * m for p, m in zip(probabilities, means, strict=True))
            accepted = float(row[prefix + "player_league_expected_points"])
            if abs(expectation - accepted) > 1e-7:
                raise ValueError(
                    f"frozen board scenario expectation mismatch for {player_id} Y{year_index}"
                )
            scenarios = tuple(
                FutureForecastScenario(
                    scenario_id=state,
                    probability=probability,
                    fantasy_points=mean,
                )
                for state, probability, mean in zip(
                    STATE_NAMES, probabilities, means, strict=True
                )
            )
            output.append(FuturePlayerHorizonForecast(
                player_id=player_id,
                position=position,
                evaluation_season=2026,
                year_index=year_index,
                target_season=2026 + year_index - 1,
                central_expectation=expectation,
                scoring_coordinate="connected_league_fantasy_points",
                model_version="frozen-p0-board-2026",
                source="fsffl:frozen_p0_future_forecast",
                uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                scenarios=scenarios,
                evidence_path="accepted/final-connected-league-board-335",
            ))
    return output


def _candidate_future_rows(artifact: dict[str, object]) -> list[FuturePlayerHorizonForecast]:
    output = []
    for row in artifact["future_forecasts"]:
        scenario_rows = row.get("scenarios")
        if not isinstance(scenario_rows, list):
            raise ValueError(f"missing discrete scenarios for {row['player_id']}")
        scenario_map = {str(item["scenario_id"]): item for item in scenario_rows}
        if set(scenario_map) != set(STATE_NAMES) or len(scenario_rows) != len(STATE_NAMES):
            raise ValueError(f"state geometry mismatch for {row['player_id']} Y{row['year_index']}")
        scenarios = tuple(
            FutureForecastScenario(
                scenario_id=state,
                probability=float(scenario_map[state]["probability"]),
                fantasy_points=float(scenario_map[state]["fantasy_points"]),
            )
            for state in STATE_NAMES
        )
        output.append(FuturePlayerHorizonForecast(
            player_id=str(row["player_id"]),
            position=Position(str(row["position"])),
            evaluation_season=2026,
            year_index=int(row["year_index"]),
            target_season=int(row["target_season"]),
            central_expectation=float(row["central_expectation"]),
            scoring_coordinate=str(row["scoring_coordinate"]),
            model_version=str(row["model_version"]),
            source=str(row["source"]),
            uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
            scenarios=scenarios,
            evidence_path=(
                "private-p0-artifact:"
                + str(artifact["saved_state_hash"])
                + ":"
                + str(artifact["evaluation_as_of"])
            ),
        ))
    return output



def _candidate_year_one_index(
    observations: tuple[ForecastObservation, ...],
    *,
    candidate_ids: set[str],
    expected_positions: dict[str, str],
) -> tuple[dict[str, ForecastObservation], dict[str, str]]:
    """Index full-season Year-1 points from completed actuals plus regular ROS."""
    indexed: dict[str, ForecastObservation] = {}
    failures: dict[str, str] = {}
    for observation in observations:
        player_id = str(observation.player_id)
        if player_id not in candidate_ids:
            continue
        if player_id in indexed or player_id in failures:
            indexed.pop(player_id, None)
            failures[player_id] = "duplicate_full_season_year_one_input"
            continue
        if observation.horizon != ForecastHorizon.SEASON:
            failures[player_id] = "year_one_input_is_not_full_season"
        elif observation.metric != ForecastMetric.FANTASY_POINTS:
            failures[player_id] = "year_one_input_metric_is_not_fantasy_points"
        elif observation.position.value != expected_positions.get(player_id):
            failures[player_id] = "year_one_input_position_mismatch_exact_state"
        elif not math.isfinite(float(observation.distribution.mean)):
            failures[player_id] = "year_one_full_season_points_are_not_finite"
        elif observation.source not in {
            "fsffl:completed-actuals-plus-ros",
            "fsffl:completed-actuals-only",
        }:
            failures[player_id] = "year_one_input_not_governed_actuals_plus_ros"
        elif not observation.model_version:
            failures[player_id] = "year_one_input_model_provenance_missing"
        else:
            indexed[player_id] = observation
    for player_id in candidate_ids:
        if player_id not in indexed and player_id not in failures:
            failures[player_id] = "full_season_year_one_input_missing"
    return indexed, failures


def _candidate_future_rows_per_player(
    artifact: dict[str, object],
    *,
    candidate_ids: set[str],
) -> tuple[list[FuturePlayerHorizonForecast], dict[str, str]]:
    """Validate Y2/Y3 state distributions independently for each candidate."""
    valid_rows: list[FuturePlayerHorizonForecast] = []
    failures: dict[str, str] = {}
    all_rows = artifact.get("future_forecasts", [])
    if not isinstance(all_rows, list):
        return [], {player_id: "future_forecast_rows_invalid" for player_id in candidate_ids}
    for player_id in sorted(candidate_ids):
        player_rows = [
            row for row in all_rows
            if isinstance(row, dict) and str(row.get("player_id")) == player_id
        ]
        try:
            years = [int(row.get("year_index", -1)) for row in player_rows]
        except (TypeError, ValueError):
            failures[player_id] = "accepted_future_year_identity_invalid"
            continue
        if len(player_rows) != 2 or sorted(years) != [2, 3]:
            failures[player_id] = "accepted_future_years_y2_y3_missing_or_duplicated"
            continue
        try:
            converted = _candidate_future_rows({
                "saved_state_hash": artifact.get("saved_state_hash", ""),
                "evaluation_as_of": artifact.get("evaluation_as_of", ""),
                "future_forecasts": player_rows,
            })
        except Exception as exc:
            failures[player_id] = f"{type(exc).__name__}: {exc}"
            continue
        valid_rows.extend(converted)
    return valid_rows, failures


def compose_saved_rostered_p0(
    *,
    artifact_path: Path,
    frozen_board_path: Path,
    frozen_shapley_path: Path,
    rules_path: Path,
    candidate_year_one_forecasts: tuple[ForecastObservation, ...] | None = None,
) -> dict[str, object]:
    artifact_bytes = artifact_path.read_bytes()
    artifact = json.loads(artifact_bytes)
    if artifact.get("schema_version") != "fsffl.rostered-p0-batch.v1":
        raise ValueError("unsupported roster P0 artifact schema")
    source_rows = artifact.get("candidate_source_rows")
    candidate_ids = set(source_rows or {})
    failure_ids = set((artifact.get("failures") or {}).keys())
    if not candidate_ids or candidate_ids & failure_ids:
        raise ValueError("P0 artifact success/failure identities overlap or are empty")
    if candidate_ids | failure_ids != set(artifact.get("candidate_ids", ())):
        raise ValueError("P0 artifact does not account for every selected roster candidate")
    base = _read_csv(frozen_board_path)
    base_ids = {row["current_player_id"] for row in base}
    if len(base_ids) != 335 or len(base) != 335:
        raise ValueError("frozen P0 reference must contain exactly 335 unique players")
    if candidate_ids & base_ids:
        raise ValueError("dynamic candidate overlaps frozen 335 reference")

    state_as_of = datetime.fromisoformat(
        str(artifact["saved_state_as_of"]).replace("Z", "+00:00")
    )
    evaluation_as_of = datetime.fromisoformat(
        str(artifact["evaluation_as_of"]).replace("Z", "+00:00")
    )
    if state_as_of.tzinfo is None or evaluation_as_of.tzinfo is None:
        raise ValueError("artifact State/evaluation timestamps must be timezone-aware")
    observations = [
        _make_observation(
            player_id=row["current_player_id"],
            position=row["position"],
            points=float(row["league_y1_points"]),
            as_of=state_as_of,
            source="fsffl:frozen_p0_year_one",
            model_version="accepted-frozen-p0-2026",
        )
        for row in base
    ]
    if candidate_year_one_forecasts is not None:
        candidate_year_one_by_id, year_one_failures = _candidate_year_one_index(
            candidate_year_one_forecasts,
            candidate_ids=candidate_ids,
            expected_positions={
                player_id: str(source_rows[player_id]["position"])
                for player_id in candidate_ids
            },
        )
        composed_candidate_ids = set(candidate_year_one_by_id)
        observations.extend(
            candidate_year_one_by_id[player_id]
            for player_id in sorted(composed_candidate_ids)
        )
    else:
        # Compatibility path for saved governed P0 artifacts. The regular runtime
        # passes its in-memory completed-actuals + ROS season outlook above and does
        # not require a separate full-season projection artifact.
        year_one_points = artifact.get("year_one_points", {})
        year_one_failures = {}
        candidate_year_one_by_id = {}
        for player_id in sorted(candidate_ids):
            source_row = source_rows[player_id]
            points = (
                year_one_points.get(player_id, {}).get("league")
                if isinstance(year_one_points, dict)
                else None
            )
            if points is None:
                points = source_row.get("connected_league_y1_points")
            try:
                points = float(points)
                if not math.isfinite(points):
                    raise ValueError("non_finite")
            except (TypeError, ValueError):
                year_one_failures[player_id] = "full_season_year_one_input_missing_or_invalid"
                continue
            observation = _make_observation(
                player_id=player_id,
                position=str(source_row["position"]),
                points=points,
                as_of=evaluation_as_of,
                source="fsffl:p0_live_rostered_candidate",
                model_version=str(source_row.get("evidence_source_version") or "accepted-p0"),
            )
            candidate_year_one_by_id[player_id] = observation
        composed_candidate_ids = set(candidate_year_one_by_id)
        observations.extend(candidate_year_one_by_id[player_id] for player_id in sorted(composed_candidate_ids))

    candidate_future_rows, future_failures = _candidate_future_rows_per_player(
        artifact,
        candidate_ids=composed_candidate_ids,
    )
    year_one_failures.update(future_failures)
    composed_candidate_ids.difference_update(future_failures)
    candidate_year_one_by_id = {
        player_id: forecast
        for player_id, forecast in candidate_year_one_by_id.items()
        if player_id in composed_candidate_ids
    }
    observations = observations[: len(base)]
    observations.extend(
        candidate_year_one_by_id[player_id]
        for player_id in sorted(composed_candidate_ids)
    )
    future_rows = _base_future_rows(base) + [
        row for row in candidate_future_rows
        if row.player_id in composed_candidate_ids
    ]
    contract = FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate="connected_league_fantasy_points",
        forecast_model_version="frozen-reference-plus-saved-rostered-p0",
        forecast_source="accepted-p0-composition-inputs",
        forecasts=tuple(future_rows),
        provenance={
            "frozen_reference_players": 335,
            "dynamic_rostered_candidates": len(candidate_ids),
            "saved_state_hash": str(artifact["saved_state_hash"]),
            "saved_state_as_of": str(artifact["saved_state_as_of"]),
            "evaluation_as_of": str(artifact["evaluation_as_of"]),
        },
    )
    rules = LeagueRules.model_validate_json(rules_path.read_text())
    frozen_rows = {row["player_id"]: row for row in _read_csv(frozen_shapley_path)}
    if set(frozen_rows) != base_ids:
        raise ValueError("frozen Shapley fixture identity set differs from frozen P0 board")

    # First prove the frozen input base reproduces the accepted 335 reference.
    # Then expand the composer context for candidate values. Shapley reallocates
    # among members when the game expands; those diagnostic base changes are not
    # allowed to replace the accepted frozen Career values.
    base_contract = FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate="connected_league_fantasy_points",
        forecast_model_version="accepted-frozen-p0-335",
        forecast_source="frozen-base-parity",
        forecasts=tuple(_base_future_rows(base)),
    )
    base_calendar = compose_live_intrinsic_calendar_from_forecast_contract(
        live_year_one_forecasts=tuple(observations[: len(base)]),
        future_contract=base_contract,
    )
    base_current = build_shapley_intrinsic_contract(
        build_live_calendar_shapley_estimates(base_calendar, rules=rules)
    )
    base_by_id = {row.player_id: row for row in base_current.estimates}
    if set(base_by_id) != base_ids:
        raise ValueError("frozen-base Shapley output differs from its 335 identities")
    max_frozen_base_delta = 0.0
    for player_id in sorted(base_ids):
        actual = base_by_id[player_id]
        reference = frozen_rows[player_id]
        for component, column in zip(
            actual.contributions,
            ("year1_shapley", "year2_expected_shapley", "year3_expected_shapley"),
            strict=True,
        ):
            delta = abs(float(component.raw_shapley_contribution) - float(reference[column]))
            max_frozen_base_delta = max(max_frozen_base_delta, delta)
    if max_frozen_base_delta > 1e-9:
        raise ValueError(
            f"frozen 335 Shapley parity failed: max component delta={max_frozen_base_delta}"
        )

    expanded_contract = FutureForecastContract(
        evaluation_season=contract.evaluation_season,
        scoring_coordinate=contract.scoring_coordinate,
        forecast_model_version=contract.forecast_model_version,
        forecast_source=contract.forecast_source,
        forecasts=tuple(future_rows),
        provenance=contract.provenance,
    )
    calendar = compose_live_intrinsic_calendar_from_forecast_contract(
        live_year_one_forecasts=tuple(observations),
        future_contract=expanded_contract,
    )
    current = build_shapley_intrinsic_contract(
        build_live_calendar_shapley_estimates(calendar, rules=rules)
    )
    actual_by_id = {row.player_id: row for row in current.estimates}
    expected_expanded_count = len(base_ids) + len(composed_candidate_ids)
    if len(actual_by_id) != expected_expanded_count:
        raise ValueError(
            f"full-cohort Shapley expected {expected_expanded_count} players, got {len(actual_by_id)}"
        )
    candidate_estimates = []
    for player_id in sorted(composed_candidate_ids):
        estimate = actual_by_id[player_id]
        candidate_estimates.append({
            "player_id": player_id,
            "current_intrinsic_raw_y1_y3": estimate.raw_intrinsic_value,
            "contributions": [
                {
                    "year_index": row.year_index,
                    "target_season": row.target_season,
                    "raw_shapley_contribution": row.raw_shapley_contribution,
                    "discount_factor": row.discount_factor,
                    "discounted_contribution": row.discounted_contribution,
                    "uncertainty": row.uncertainty.model_dump(mode="json"),
                }
                for row in estimate.contributions
            ],
        })
    return {
        "schema_version": "fsffl-rostered-p0-expanded-shapley-v1",
        "saved_state_hash": artifact["saved_state_hash"],
        "saved_state_as_of": artifact["saved_state_as_of"],
        "evaluation_as_of": artifact["evaluation_as_of"],
        "p0_artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "frozen_board_sha256": _sha256(frozen_board_path),
        "frozen_shapley_sha256": _sha256(frozen_shapley_path),
        "frozen_reference_count": len(base_ids),
        "expanded_full_cohort_count": len(actual_by_id),
        "candidate_count": len(composed_candidate_ids),
        "candidate_ids": sorted(composed_candidate_ids),
        "year_one_failures": year_one_failures,
        "frozen_base_max_abs_component_delta": max_frozen_base_delta,
        "frozen_base_preserved_in_outputs": True,
        "candidate_current_y1_y3": candidate_estimates,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "candidate_alone_shapley_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p0-artifact", required=True, type=Path)
    parser.add_argument("--frozen-board", required=True, type=Path)
    parser.add_argument("--frozen-shapley", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compose_saved_rostered_p0(
        artifact_path=args.p0_artifact,
        frozen_board_path=args.frozen_board,
        frozen_shapley_path=args.frozen_shapley,
        rules_path=args.rules,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        key: result[key] for key in (
            "candidate_count", "expanded_full_cohort_count",
            "frozen_base_max_abs_component_delta", "max_rss_kib",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
