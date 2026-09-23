from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.home_command_center import build_home_command_center_payload
from fsffl.product.runtime import (
    UserRuntimeContext,
    default_live_forecast_loader,
    default_sleeper_state_loader,
)
from fsffl.product.simulation_runtime import build_live_simulation_analytics


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/home_north_star_20260923"
LEAGUE_ID = "1312071960615731200"
MANAGED_TEAM_NAME = "jimmygoodjob"
POSITIONS = ("QB", "RB", "WR", "TE")


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _weakest_position(view):
    rows = [
        row for row in view.position_strengths
        if row.position in POSITIONS
    ]
    if len(rows) != 4:
        raise RuntimeError(
            f"managed team does not expose complete QB/RB/WR/TE strength evidence: {len(rows)} rows"
        )
    order = {position: index for index, position in enumerate(POSITIONS)}
    return sorted(
        rows,
        key=lambda row: (
            -int(row.league_rank),
            float(row.strength_index),
            order[row.position],
        ),
    )[0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    state = default_sleeper_state_loader(LEAGUE_ID)
    state_load_ms = _elapsed_ms(started)

    managed = next(
        (team for team in state.teams if team.display_name == MANAGED_TEAM_NAME),
        None,
    )
    if managed is None:
        raise RuntimeError(
            f"expected managed team {MANAGED_TEAM_NAME!r} in real league"
        )

    forecast_started = time.perf_counter()
    forecast = default_live_forecast_loader(state)
    forecast_load_ms = _elapsed_ms(forecast_started)

    simulation_started = time.perf_counter()
    simulation = build_live_simulation_analytics(
        state,
        forecasts=forecast.league_scored_forecasts,
        forecast_model_version=forecast.model_version,
        simulation_count=50_000,
    )
    simulation_ms = _elapsed_ms(simulation_started)

    runtime = UserRuntimeContext(
        user_id="home-north-star-sanity",
        league_state=state,
        selected_team_id=managed.team_id,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
    )

    compose_started = time.perf_counter()
    home = build_home_command_center_payload(runtime)
    cold_compose_ms = _elapsed_ms(compose_started)

    warm_samples = []
    for _ in range(25):
        started = time.perf_counter()
        repeated = build_home_command_center_payload(runtime)
        warm_samples.append(_elapsed_ms(started))
        if repeated["league_state_id"] != home["league_state_id"]:
            raise RuntimeError("warm Home composition changed State identity")
    warm_median_ms = statistics.median(warm_samples)
    warm_p95_ms = sorted(warm_samples)[max(0, int(len(warm_samples) * 0.95) - 1)]

    view = next(
        item for item in simulation.team_views
        if item.team_id == managed.team_id
    )
    weakest = _weakest_position(view)
    resilience = view.utility.roster_resilience if view.utility is not None else None
    if resilience is None:
        raise RuntimeError("managed team has no governed roster resilience evidence")
    driver_ids = list(resilience.largest_single_player_lineup_drop_player_ids)
    players = {player.player_id: player.full_name for player in view.players}
    driver_names = [players[player_id] for player_id in driver_ids if player_id in players]
    if resilience.largest_single_player_lineup_drop > 0 and not driver_ids:
        raise RuntimeError("nonzero managed-team fragility has no driver identity")
    if len(driver_names) != len(driver_ids):
        raise RuntimeError("a managed-team fragility driver did not resolve to a roster name")

    outcome = next(
        row for row in simulation.simulation_result.outcomes
        if row.team_id == managed.team_id
    )
    finish = next(
        row for row in simulation.simulation_result.finish_distributions
        if row.team_id == managed.team_id
    )
    home_sim = home["simulation"]["team"]
    if home["simulation"]["simulation_count"] != 50_000:
        raise RuntimeError("Home did not preserve the governed 50,000-run Simulation")
    checks = {
        "expected_wins": abs(float(home_sim["expected_wins"]) - float(outcome.expected_wins)) <= 1e-12,
        "playoff_probability": abs(float(home_sim["playoff_probability"]) - float(outcome.playoff_probability)) <= 1e-12,
        "championship_probability": abs(float(home_sim["championship_probability"]) - float(outcome.championship_probability)) <= 1e-12,
        "expected_finish": abs(float(home_sim["expected_finish"]) - float(finish.expected_finish)) <= 1e-12,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Home Simulation summary diverged from authoritative runtime: {checks}")

    standing = home["managed_standing"]
    if standing["team_id"] != managed.team_id:
        raise RuntimeError("Home managed standing is not the managed team")
    if len(home["around_the_league"]) > 3:
        raise RuntimeError("Around-the-league context exceeded the bounded adjacent-team contract")
    if not all(
        abs(int(row["rank"]) - int(standing["rank"])) <= 1
        for row in home["around_the_league"]
    ):
        raise RuntimeError("Around-the-league context contains a non-adjacent standing")

    authority = home["authority"]
    forbidden_authority = [
        key for key, value in authority.items()
        if key.startswith("creates_") and value is not False
    ]
    if forbidden_authority:
        raise RuntimeError(f"Home created prohibited authority: {forbidden_authority}")
    for key in (
        "launches_opportunity_search",
        "launches_decision_evaluation",
        "launches_simulation",
    ):
        if authority[key] is not False:
            raise RuntimeError(f"Home authority flag {key} is not fail-closed")

    manifest = {
        "schema_version": "fsffl-home-north-star-sanity-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "league_id": state.league.league_id,
        "league_name": state.league.name,
        "league_state_id": state.state_id,
        "managed_team_id": managed.team_id,
        "managed_team_name": managed.display_name,
        "managed_record": {
            "wins": standing["wins"],
            "losses": standing["losses"],
            "ties": standing["ties"],
            "rank": standing["rank"],
        },
        "competitive_state": (
            view.utility.calculated_competitive_state.value
            if view.utility is not None
            else None
        ),
        "pressure_point": {
            "position": weakest.position,
            "league_rank": weakest.league_rank,
            "team_count": weakest.team_count,
            "strength_index": weakest.strength_index,
        },
        "simulation": {
            "simulation_count": home["simulation"]["simulation_count"],
            "expected_wins": home_sim["expected_wins"],
            "playoff_probability": home_sim["playoff_probability"],
            "championship_probability": home_sim["championship_probability"],
            "expected_finish": home_sim["expected_finish"],
            "parity_checks": checks,
        },
        "fragility": {
            "largest_single_player_lineup_drop": resilience.largest_single_player_lineup_drop,
            "driver_ids": driver_ids,
            "driver_names": driver_names,
        },
        "around_the_league": home["around_the_league"],
        "forecast_sources": list(forecast.successful_source_ids),
        "forecast_model_version": forecast.model_version,
        "latency_ms": {
            "real_sleeper_state_load": round(state_load_ms, 2),
            "live_forecast_load": round(forecast_load_ms, 2),
            "50k_simulation": round(simulation_ms, 2),
            "home_compose_cold": round(cold_compose_ms, 3),
            "home_compose_warm_median": round(warm_median_ms, 3),
            "home_compose_warm_p95": round(warm_p95_ms, 3),
        },
        "authority": authority,
        "status": "PASS",
        "notes": [
            "Validation constructs one production-equivalent current runtime, then compares Home summaries to the exact same authoritative State, Team Utility, and 50,000-run Simulation evidence.",
            "The Home composition call itself launches no Forecast, Simulation, Search, Decision, or Value work.",
            "The live Forecast/Simulation setup exists only in this validation harness to supply the current governed runtime coordinate.",
        ],
    }
    (OUT / "HOME_NORTH_STAR_SANITY.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
