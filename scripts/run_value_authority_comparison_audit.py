from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.i1_player_scoring import translate_future_i1_result
from fsffl.product.p0_forecast_runtime import frozen_p0_standard_materialization
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
    Team,
    TeamState,
)
from fsffl.value.current_runtime import build_current_market_values
from fsffl.value.models import ValueAssetKind
from fsffl.value.shapley_intrinsic import (
    FutureStateForecast,
    PlayerIntrinsicForecast,
    build_intrinsic_shapley_estimates,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919"
    / "RECONCILED_PRESEASON_SOURCE_335.csv"
)
RULES = (
    ROOT
    / "artifacts/implementation/forecast_source_coordinate_20260919"
    / "CONNECTED_LEAGUE_RULES.json"
)
OUT = ROOT / "artifacts/diagnostics/forecast_value_reconciliation_20260920"

SAMPLE_NAMES = (
    "Josh Allen",
    "Dak Prescott",
    "Jahmyr Gibbs",
    "Tony Pollard",
    "Tyjae Spears",
    "Puka Nacua",
    "CeeDee Lamb",
    "Matthew Golden",
    "Brock Bowers",
    "Kyle Pitts",
    "Dallas Goedert",
)


def _percentile_ranks(values: list[tuple[str, float]]) -> dict[str, float]:
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


def _future(result) -> FutureStateForecast:
    return FutureStateForecast(
        probabilities=result.probabilities,
        state_means=result.state_means,
        anticipated_points=result.anticipated_points,
    )


def _load_source() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _league_state(rows: list[dict[str, str]], rules: LeagueRules) -> LeagueState:
    now = datetime.now(UTC)
    provenance = Provenance(
        source="forecast-value-authority-comparison",
        retrieved_at=now,
        effective_at=now,
        source_version="20260920",
    )
    teams = tuple(
        Team(
            team_id=f"trace-team-{index + 1}",
            league_id="trace:forecast-value-authority",
            display_name=f"Trace Team {index + 1}",
        )
        for index in range(rules.team_count)
    )
    players = []
    player_states = []
    for row in rows:
        current_player_id = row["current_player_id"]
        if not current_player_id.startswith("sleeper:"):
            raise ValueError(f"unexpected current player id {current_player_id}")
        sleeper_id = current_player_id.split(":", 1)[1]
        player_id = current_player_id
        players.append(
            Player(
                player_id=player_id,
                full_name=row["player_name"],
                position=Position(row["position"]),
                provider_refs=(ProviderRef(provider="sleeper", external_id=sleeper_id),),
            )
        )
        player_states.append(
            PlayerState(
                player_id=player_id,
                as_of=now,
                age_years=float(row["age"]) if row.get("age") else None,
                provenance=provenance,
            )
        )
    return LeagueState(
        league=League(
            league_id="trace:forecast-value-authority",
            name="Forecast/Value authority comparison",
            season=2026,
            rules=rules,
        ),
        as_of=now,
        teams=teams,
        team_states=tuple(TeamState(team_id=team.team_id, roster=()) for team in teams),
        players=tuple(players),
        player_states=tuple(player_states),
        provenance=(provenance,),
    )


def _shapley(rows: list[dict[str, str]], rules: LeagueRules):
    p0 = frozen_p0_standard_materialization()
    forecasts: list[PlayerIntrinsicForecast] = []
    metadata: dict[str, dict[str, object]] = {}
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
        metadata[player_id] = {
            "player_name": row["player_name"],
            "position": row["position"],
            "standard_y1": standard_y1,
            "league_y1": league_y1,
        }
    estimates = build_intrinsic_shapley_estimates(tuple(forecasts), rules=rules)
    ranks = _percentile_ranks([(item.player_id, item.value) for item in estimates])
    return {item.player_id: item for item in estimates}, ranks, metadata


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = _load_source()
    rules = LeagueRules.model_validate(json.loads(RULES.read_text(encoding="utf-8")))
    state = _league_state(rows, rules)

    market = build_current_market_values(state)
    shapley, shapley_percentiles, metadata = _shapley(rows, rules)

    broad_market = {item.asset_id: float(item.distribution.mean) for item in market.estimates}
    cardinal = {
        item.asset_id: float(item.score)
        for item in market.fsffl_cardinal_values
        if item.asset_kind == ValueAssetKind.PLAYER
    }

    comparable = sorted(set(broad_market) & set(shapley_percentiles) & set(metadata))
    output_rows = []
    for player_id in comparable:
        meta = metadata[player_id]
        estimate = shapley[player_id]
        market_pct = broad_market[player_id]
        intrinsic_pct = shapley_percentiles[player_id]
        output_rows.append(
            {
                "player_id": player_id,
                "player_name": meta["player_name"],
                "position": meta["position"],
                "broad_market_percentile": market_pct,
                "shapley_intrinsic_raw": float(estimate.value),
                "shapley_intrinsic_percentile": intrinsic_pct,
                "intrinsic_minus_market_pct_points": (intrinsic_pct - market_pct) * 100.0,
                "fsffl_cardinal_market_value": cardinal.get(player_id),
                "league_y1_points": meta["league_y1"],
            }
        )

    output_rows.sort(
        key=lambda row: (
            -abs(float(row["intrinsic_minus_market_pct_points"])),
            str(row["player_name"]),
        )
    )

    with (OUT / "MARKET_SHAPLEY_REAL_PLAYER_COMPARISON.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    sample = [
        row for row in output_rows if str(row["player_name"]) in SAMPLE_NAMES
    ]
    sample.sort(key=lambda row: SAMPLE_NAMES.index(str(row["player_name"])))
    with (OUT / "MARKET_SHAPLEY_NAMED_SAMPLE.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sample[0]))
        writer.writeheader()
        writer.writerows(sample)

    cardinal_consistency = (
        market.cardinal_consistency_audit.model_dump(mode="json")
        if market.cardinal_consistency_audit is not None
        else None
    )
    manifest = {
        "schema_version": "fsffl-market-shapley-authority-comparison-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "population_players": len(rows),
        "broad_market_player_count": len(broad_market),
        "shapley_player_count": len(shapley),
        "comparable_player_count": len(output_rows),
        "cardinal_player_count": len(cardinal),
        "market_context_id": market.market_context_id,
        "market_model_version": market.model_version,
        "successful_market_source_ids": list(market.successful_source_ids),
        "failed_market_source_ids": list(market.failed_sources),
        "market_errors": market.errors_by_source_id,
        "shapley_model_version": (
            next(iter(shapley.values())).model_version if shapley else None
        ),
        "comparison_coordinate": "percentile_rank_presentation_only",
        "raw_value_subtraction_used": False,
        "team_value_created": False,
        "league_market_value_created": False,
        "team_utility_created": False,
        "cardinal_consistency_audit": cardinal_consistency,
        "largest_disagreements": output_rows[:20],
        "named_sample": sample,
    }
    (OUT / "MARKET_SHAPLEY_COMPARISON_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
