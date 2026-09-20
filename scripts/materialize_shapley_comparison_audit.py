from __future__ import annotations

import csv
import json
from pathlib import Path

from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.state.models import LeagueRules, Position
from fsffl.product.i1_player_scoring import translate_future_i1_result
from fsffl.product.p0_forecast_runtime import frozen_p0_standard_materialization
from fsffl.value.shapley_intrinsic import (
    FutureStateForecast,
    PlayerIntrinsicForecast,
    build_intrinsic_shapley_estimates,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/RECONCILED_PRESEASON_SOURCE_335.csv"
RULES = ROOT / "artifacts/implementation/forecast_source_coordinate_20260919/CONNECTED_LEAGUE_RULES.json"
OUT = ROOT / "artifacts/diagnostics/forecast_value_reconciliation_20260920"


def _centered_percentile(values: list[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(values, key=lambda item: (item[1], item[0]))
    n = len(ordered)
    result: dict[str, float] = {}
    i = 0
    while i < n:
        end = i + 1
        while end < n and ordered[end][1] == ordered[i][1]:
            end += 1
        percentile = (((i + end - 1) / 2.0) + 0.5) / n
        for j in range(i, end):
            result[ordered[j][0]] = percentile
        i = end
    return result


def _future(result):
    return FutureStateForecast(
        probabilities=result.probabilities,
        state_means=result.state_means,
        anticipated_points=result.anticipated_points,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rules = LeagueRules.model_validate(json.loads(RULES.read_text(encoding="utf-8")))
    p0 = frozen_p0_standard_materialization()

    forecasts: list[PlayerIntrinsicForecast] = []
    names: dict[str, tuple[str, str, float, float]] = {}
    for row in rows:
        player_id = row["current_player_id"]
        standard_y1 = float(row["y1_points"])
        league_y1 = float(row["league_y1_points"])
        if standard_y1 <= 0.0:
            raise ValueError(f"nonpositive frozen standard Y1 for {player_id}")
        multiplier = league_y1 / standard_y1
        player = p0.players[player_id]
        y2 = translate_future_i1_result(player.result_for(2), multiplier=multiplier)
        y3 = translate_future_i1_result(player.result_for(3), multiplier=multiplier)
        forecasts.append(
            PlayerIntrinsicForecast(
                player_id=player_id,
                position=Position(row["position"]),
                current_points=league_y1,
                year_2=_future(y2),
                year_3=_future(y3),
            )
        )
        names[player_id] = (row["player_name"], row["position"], standard_y1, league_y1)

    estimates = build_intrinsic_shapley_estimates(tuple(forecasts), rules=rules)
    percentiles = _centered_percentile([(item.player_id, item.value) for item in estimates])
    out_rows = []
    for item in estimates:
        name, position, standard_y1, league_y1 = names[item.player_id]
        out_rows.append(
            {
                "player_id": item.player_id,
                "player_name": name,
                "position": position,
                "standard_y1": standard_y1,
                "league_y1": league_y1,
                "raw_shapley_intrinsic": item.value,
                "intrinsic_percentile": percentiles[item.player_id],
                "year1_shapley": item.year_1_shapley,
                "year2_expected_shapley": item.year_2_expected_shapley,
                "year3_expected_shapley": item.year_3_expected_shapley,
                "model_version": item.model_version,
            }
        )
    out_rows.sort(key=lambda row: (-float(row["raw_shapley_intrinsic"]), str(row["player_id"])))
    with (OUT / "SHAPLEY_CURRENT_BOARD_335.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    print(json.dumps({
        "status": "PASS",
        "players": len(out_rows),
        "model_version": out_rows[0]["model_version"],
        "rules_team_count": rules.team_count,
        "lineup": [{"slot": item.slot.value, "count": item.count} for item in rules.lineup],
        "output": str(OUT / "SHAPLEY_CURRENT_BOARD_335.csv"),
    }, indent=2))


if __name__ == "__main__":
    main()
