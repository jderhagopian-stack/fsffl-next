from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.league_atlas import build_league_atlas_payload
from fsffl.product.runtime import (
    UserRuntimeContext,
    default_live_forecast_loader,
    default_sleeper_state_loader,
)
from fsffl.product.simulation_runtime import build_live_simulation_analytics


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/league_atlas_final_acceptance_20260923"
LEAGUE_ID = "1312071960615731200"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    state = default_sleeper_state_loader(LEAGUE_ID)
    forecast = default_live_forecast_loader(state)
    simulation = build_live_simulation_analytics(
        state,
        forecasts=forecast.league_scored_forecasts,
        forecast_model_version=forecast.model_version,
        simulation_count=50_000,
    )
    runtime = UserRuntimeContext(
        user_id="league-atlas-final-acceptance",
        league_state=state,
        selected_team_id=state.teams[0].team_id if state.teams else None,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
    )
    atlas = build_league_atlas_payload(runtime)

    team_rows = []
    failures = []
    for view in simulation.team_views:
        players = {row.player_id: row.full_name for row in view.players}
        resilience = view.utility.roster_resilience if view.utility is not None else None
        if resilience is None:
            failures.append(f"{view.team_id}: resilience unavailable")
            continue
        driver_ids = list(resilience.largest_single_player_lineup_drop_player_ids)
        driver_names = [players[player_id] for player_id in driver_ids if player_id in players]
        if resilience.largest_single_player_lineup_drop > 0:
            if not driver_ids:
                failures.append(f"{view.team_id}: nonzero drop without driver IDs")
            if len(driver_names) != len(driver_ids):
                failures.append(f"{view.team_id}: driver ID did not resolve to rostered player name")
        team_rows.append(
            {
                "team_id": view.team_id,
                "team_name": view.display_name,
                "largest_single_player_lineup_drop": resilience.largest_single_player_lineup_drop,
                "driver_ids": driver_ids,
                "driver_names": driver_names,
                "resilience_model_version": resilience.model_version,
                "team_utility_model_version": view.utility.model_version if view.utility is not None else None,
            }
        )

    if simulation.simulation_result.simulation_count != 50_000:
        failures.append(
            f"simulation_count={simulation.simulation_result.simulation_count}, expected 50000"
        )
    if len(team_rows) != 12:
        failures.append(f"team_rows={len(team_rows)}, expected 12")
    if len(atlas["standings"]) != 12:
        failures.append(f"atlas standings={len(atlas['standings'])}, expected 12")
    if atlas["simulation"]["simulation_count"] != 50_000:
        failures.append("Atlas did not expose the matching 50,000-run Simulation")

    manifest = {
        "schema_version": "fsffl-league-atlas-live-fragility-acceptance-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "league_id": state.league.league_id,
        "league_state_id": state.state_id,
        "forecast_sources": list(forecast.successful_source_ids),
        "forecast_model_version": forecast.model_version,
        "simulation_count": simulation.simulation_result.simulation_count,
        "simulation_model_version": simulation.model_version,
        "team_count": len(team_rows),
        "nonzero_drop_team_count": sum(
            row["largest_single_player_lineup_drop"] > 0 for row in team_rows
        ),
        "resolved_driver_team_count": sum(
            bool(row["driver_ids"]) and len(row["driver_ids"]) == len(row["driver_names"])
            for row in team_rows
            if row["largest_single_player_lineup_drop"] > 0
        ),
        "teams": team_rows,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "notes": [
            "This diagnostic uses the real live Sleeper league and current governed Forecast acquisition.",
            "It runs the unmodified governed 50,000-run current Simulation on the exact candidate code.",
            "Driver IDs are read from Team Utility roster resilience and names are resolved from the same team-view payload consumed by League Atlas.",
        ],
    }
    (OUT / "LIVE_FRAGILITY_DRIVER_ACCEPTANCE.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
