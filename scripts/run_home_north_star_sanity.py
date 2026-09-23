from __future__ import annotations

import json
import time
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
OUT = ROOT / "artifacts/diagnostics/home_north_star_20260923"
LEAGUE_ID = "1312071960615731200"
HOME_JS = ROOT / "src/fsffl/product/static/home_dashboard.js"
SHELL_JS = ROOT / "src/fsffl/product/static/product_shell.js"
LEAGUE_JS = ROOT / "src/fsffl/product/static/league_comparison.js"
MARKET_JS = ROOT / "src/fsffl/product/static/opportunities.js"


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _managed_team(state):
    preferred = next(
        (team for team in state.teams if team.display_name.casefold() == "jimmygoodjob"),
        None,
    )
    return preferred or sorted(state.teams, key=lambda team: team.display_name)[0]


def _weakest_position(view):
    positions = {"QB": 0, "RB": 1, "WR": 2, "TE": 3}
    rows = [
        row
        for row in view.position_strengths
        if row.position in positions
    ]
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: (
            -int(row.league_rank),
            float(row.strength_index),
            positions[row.position],
        ),
    )[0]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    state = default_sleeper_state_loader(LEAGUE_ID)
    state_load_ms = _elapsed_ms(started)
    managed = _managed_team(state)

    started = time.perf_counter()
    forecast = default_live_forecast_loader(state)
    forecast_load_ms = _elapsed_ms(started)
    if len(forecast.successful_source_ids) < 2:
        raise RuntimeError(
            "Home real-league sanity requires the existing two-independent-source "
            f"Forecast authority; healthy={forecast.successful_source_ids}"
        )
    if not forecast.uncertainty_ready:
        raise RuntimeError("current Forecast uncertainty is not ready for governed Simulation")

    started = time.perf_counter()
    simulation = build_live_simulation_analytics(
        state,
        forecasts=forecast.league_scored_forecasts,
        forecast_model_version=forecast.model_version,
        simulation_count=50_000,
    )
    simulation_ms = _elapsed_ms(started)

    runtime = UserRuntimeContext(
        user_id="home-north-star-sanity",
        league_state=state,
        selected_team_id=managed.team_id,
        forecast_evidence=forecast,
        simulation_analytics=simulation,
    )
    atlas = build_league_atlas_payload(
        runtime,
        preseason_reason="Home sanity intentionally ignores preseason reconstruction.",
    )
    view = next(item for item in simulation.team_views if item.team_id == managed.team_id)
    standing = next(item for item in atlas["standings"] if item["team_id"] == managed.team_id)
    sim_row = next(
        item for item in atlas["simulation"]["teams"]
        if item["team_id"] == managed.team_id
    )
    outcome = next(
        item for item in simulation.simulation_result.outcomes
        if item.team_id == managed.team_id
    )
    finish = next(
        item for item in simulation.simulation_result.finish_distributions
        if item.team_id == managed.team_id
    )
    weakest = _weakest_position(view)
    resilience = view.utility.roster_resilience if view.utility is not None else None
    players = {player.player_id: player for player in view.players}
    driver_ids = (
        list(resilience.largest_single_player_lineup_drop_player_ids)
        if resilience is not None
        else []
    )
    driver_names = [
        players[player_id].full_name for player_id in driver_ids
        if player_id in players
    ]

    failures: list[str] = []
    if len(state.teams) != 12:
        failures.append(f"expected 12 teams, found {len(state.teams)}")
    if simulation.simulation_result.simulation_count != 50_000:
        failures.append("Simulation is not the governed 50,000-run coordinate")
    if atlas["league_state_id"] != state.state_id:
        failures.append("Atlas and Home State identities diverge")
    if atlas["simulation"]["simulation_count"] != 50_000:
        failures.append("Atlas does not expose the same 50,000-run Simulation")
    if abs(float(sim_row["expected_wins"]) - float(outcome.expected_wins)) > 1e-12:
        failures.append("expected wins diverge from Simulation authority")
    if abs(float(sim_row["playoff_probability"]) - float(outcome.playoff_probability)) > 1e-12:
        failures.append("playoff probability diverges from Simulation authority")
    if abs(float(sim_row["championship_probability"]) - float(outcome.championship_probability)) > 1e-12:
        failures.append("championship probability diverges from Simulation authority")
    if abs(float(sim_row["expected_finish"]) - float(finish.expected_finish)) > 1e-12:
        failures.append("expected finish diverges from Simulation authority")
    if weakest is None:
        failures.append("managed team has no comparable QB/RB/WR/TE position-strength evidence")
    if resilience is None:
        failures.append("managed team has no governed roster-resilience evidence")
    elif resilience.largest_single_player_lineup_drop > 0:
        if not driver_ids:
            failures.append("nonzero fragility has no governed driver ID")
        if len(driver_names) != len(driver_ids):
            failures.append("fragility driver ID does not resolve to team-view player identity")

    standings = sorted(atlas["standings"], key=lambda row: int(row["rank"]))
    managed_index = next(
        index for index, row in enumerate(standings)
        if row["team_id"] == managed.team_id
    )
    adjacent = standings[
        max(0, managed_index - 1): min(len(standings), managed_index + 2)
    ]
    if not any(row["team_id"] == managed.team_id for row in adjacent):
        failures.append("around-the-league slice does not retain managed team")

    home_js = HOME_JS.read_text(encoding="utf-8")
    shell_js = SHELL_JS.read_text(encoding="utf-8")
    league_js = LEAGUE_JS.read_text(encoding="utf-8")
    market_js = MARKET_JS.read_text(encoding="utf-8")
    for token in (
        "What matters right now",
        "Season outlook · current Simulation",
        "Your roster at a glance",
        "Also worth knowing",
        "Around the league",
        "api('/api/home')",
    ):
        if token not in home_js:
            failures.append(f"Home presentation missing required token: {token}")
    for forbidden in (
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center",
        "/api/what-if",
        "/api/league/value-lenses",
    ):
        if forbidden in home_js:
            failures.append(f"Home cold-load source contains forbidden deep-work call: {forbidden}")
    for token in (
        "fsfflNavigateTo",
        "fsfflConsumeDeepLinkIntent",
    ):
        if token not in shell_js:
            failures.append(f"shell missing deep-link mechanism: {token}")
    if "laConsumeDeepLinkIntent" not in league_js:
        failures.append("League Atlas does not consume Home contextual intents")
    if "oppConsumeHomeIntent" not in market_js:
        failures.append("Market does not consume Home pressure-point intent")

    manifest = {
        "schema_version": "fsffl-home-north-star-real-league-sanity-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "league_id": state.league.league_id,
        "league_state_id": state.state_id,
        "team_count": len(state.teams),
        "managed_team": {
            "team_id": managed.team_id,
            "team_name": managed.display_name,
            "record": {
                "wins": standing["wins"],
                "losses": standing["losses"],
                "ties": standing["ties"],
            },
            "current_rank": standing["rank"],
            "competitive_state": (
                view.utility.calculated_competitive_state.value
                if view.utility is not None
                else "unknown"
            ),
        },
        "pressure_point": (
            {
                "position": weakest.position,
                "league_rank": weakest.league_rank,
                "team_count": weakest.team_count,
                "strength_index": weakest.strength_index,
            }
            if weakest is not None
            else None
        ),
        "simulation": {
            "simulation_count": simulation.simulation_result.simulation_count,
            "expected_wins": sim_row["expected_wins"],
            "playoff_probability": sim_row["playoff_probability"],
            "championship_probability": sim_row["championship_probability"],
            "expected_finish": sim_row["expected_finish"],
            "model_version": atlas["simulation"]["model_version"],
        },
        "position_strip": [
            {
                "position": row.position,
                "league_rank": row.league_rank,
                "team_count": row.team_count,
                "strength_index": row.strength_index,
            }
            for row in view.position_strengths
            if row.position in {"QB", "RB", "WR", "TE"}
        ],
        "fragility": (
            {
                "largest_single_player_lineup_drop": resilience.largest_single_player_lineup_drop,
                "driver_ids": driver_ids,
                "driver_names": driver_names,
            }
            if resilience is not None
            else None
        ),
        "around_the_league": [
            {
                "team_id": row["team_id"],
                "team_name": row["team_name"],
                "rank": row["rank"],
                "wins": row["wins"],
                "losses": row["losses"],
                "ties": row["ties"],
            }
            for row in adjacent
        ],
        "forecast_sources": list(forecast.successful_source_ids),
        "latency_ms": {
            "state_load": round(state_load_ms, 2),
            "forecast_load": round(forecast_load_ms, 2),
            "simulation_50000": round(simulation_ms, 2),
        },
        "authority": {
            "home_specific_forecast": False,
            "home_specific_simulation": False,
            "home_specific_value": False,
            "home_master_score": False,
            "home_search_on_load": False,
        },
    }
    (OUT / "HOME_NORTH_STAR_REAL_LEAGUE_SANITY.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
