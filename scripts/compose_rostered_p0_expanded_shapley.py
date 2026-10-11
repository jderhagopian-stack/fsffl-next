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


def compose_saved_rostered_p0(
    *,
    artifact_path: Path,
    frozen_board_path: Path,
    frozen_shapley_path: Path,
    rules_path: Path,
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
    year_one_points = artifact["year_one_points"]
    for player_id in sorted(candidate_ids):
        points = year_one_points[player_id].get("league")
        if points is None:
            raise ValueError(f"complete governed Year-1 league points missing for {player_id}")
        source_row = source_rows[player_id]
        observations.append(_make_observation(
            player_id=player_id,
            position=str(source_row["position"]),
            points=float(points),
            as_of=evaluation_as_of,
            source="fsffl:p0_live_rostered_candidate",
            model_version=str(source_row["evidence_source_version"]),
        ))

    future_rows = _base_future_rows(base) + _candidate_future_rows(artifact)
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
    calendar = compose_live_intrinsic_calendar_from_forecast_contract(
        live_year_one_forecasts=tuple(observations),
        future_contract=contract,
    )
    rules = LeagueRules.model_validate_json(rules_path.read_text())
    current = build_shapley_intrinsic_contract(
        build_live_calendar_shapley_estimates(calendar, rules=rules)
    )

    frozen_rows = {row["player_id"]: row for row in _read_csv(frozen_shapley_path)}
    if set(frozen_rows) != base_ids:
        raise ValueError("frozen Shapley fixture identity set differs from frozen P0 board")
    actual_by_id = {row.player_id: row for row in current.estimates}
    if len(actual_by_id) != 345:
        raise ValueError(f"full-cohort Shapley expected 345 players, got {len(actual_by_id)}")
    max_base_delta = 0.0
    for player_id in sorted(base_ids):
        actual = actual_by_id[player_id]
        reference = frozen_rows[player_id]
        for component, column in zip(
            actual.contributions,
            ("year1_shapley", "year2_expected_shapley", "year3_expected_shapley"),
            strict=True,
        ):
            delta = abs(float(component.raw_shapley_contribution) - float(reference[column]))
            max_base_delta = max(max_base_delta, delta)
    candidate_estimates = []
    for player_id in sorted(candidate_ids):
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
        "candidate_count": len(candidate_ids),
        "candidate_ids": sorted(candidate_ids),
        "frozen_base_max_abs_component_delta": max_base_delta,
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
