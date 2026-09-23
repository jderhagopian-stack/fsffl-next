from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from fsffl.product.league_atlas import build_league_atlas_payload
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.simulation_runtime import LiveSimulationAnalyticsResult
from fsffl.state.models import LeagueState


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/home_north_star_20260923"
LEAGUE_ID = "sleeper:1312071960615731200"
HOME_JS = ROOT / "src/fsffl/product/static/home_dashboard.js"
SHELL_JS = ROOT / "src/fsffl/product/static/product_shell.js"
LEAGUE_JS = ROOT / "src/fsffl/product/static/league_comparison.js"
MARKET_JS = ROOT / "src/fsffl/product/static/opportunities.js"


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _managed_team(state: LeagueState):
    preferred = next(
        (team for team in state.teams if team.display_name.casefold() == "jimmygoodjob"),
        None,
    )
    return preferred or sorted(state.teams, key=lambda team: team.display_name)[0]


def _weakest_position(view):
    positions = {"QB": 0, "RB": 1, "WR": 2, "TE": 3}
    rows = [row for row in view.position_strengths if row.position in positions]
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


def _load_exact_persisted_coordinate():
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "FSFFL_DATABASE_URL is required for the exact persisted Home sanity coordinate"
        )
    started = time.perf_counter()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    s.state_hash,
                    s.as_of,
                    s.payload,
                    a.model_version,
                    a.computed_at,
                    a.payload
                from fsffl.derived_artifact a
                join fsffl.state_snapshot_history s
                  on s.state_hash = a.scope_id
                where a.artifact_kind = 'live_simulation_analytics'
                  and s.league_id = %s
                  and s.season = 2026
                  and a.invalidated_at is null
                order by a.computed_at desc
                limit 1
                """,
                (LEAGUE_ID,),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError(
                    "no persisted production Simulation coordinate exists for the real league"
                )
            (
                state_hash,
                state_as_of,
                state_payload,
                simulation_model_version,
                simulation_computed_at,
                simulation_payload,
            ) = row
            cursor.execute(
                """
                select payload
                from fsffl.derived_artifact
                where artifact_kind = 'current_forecast_evidence'
                  and scope_id = %s
                  and invalidated_at is null
                order by computed_at desc
                limit 1
                """,
                (state_hash,),
            )
            forecast_row = cursor.fetchone()
    state = LeagueState.model_validate(state_payload)
    simulation = LiveSimulationAnalyticsResult.model_validate(simulation_payload)
    forecast_payload = forecast_row[0] if forecast_row is not None else {}
    return {
        "state": state,
        "simulation": simulation,
        "state_hash": state_hash,
        "state_as_of": state_as_of,
        "simulation_model_version": simulation_model_version,
        "simulation_computed_at": simulation_computed_at,
        "forecast_sources": list(forecast_payload.get("successful_source_ids") or []),
        "load_ms": _elapsed_ms(started),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    persisted = _load_exact_persisted_coordinate()
    state = persisted["state"]
    simulation = persisted["simulation"]
    managed = _managed_team(state)

    if state.state_id != persisted["state_hash"]:
        raise RuntimeError("persisted State payload identity does not match artifact scope")
    if simulation.league_view.context.league_state_id != state.state_id:
        raise RuntimeError("persisted Simulation does not match the exact persisted State")

    runtime = UserRuntimeContext(
        user_id="home-north-star-sanity",
        league_state=state,
        selected_team_id=managed.team_id,
        simulation_analytics=simulation,
    )
    started = time.perf_counter()
    atlas = build_league_atlas_payload(
        runtime,
        preseason_reason="Home sanity intentionally ignores preseason reconstruction.",
    )
    compose_ms = _elapsed_ms(started)

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
    for token in ("fsfflNavigateTo", "fsfflConsumeDeepLinkIntent"):
        if token not in shell_js:
            failures.append(f"shell missing deep-link mechanism: {token}")
    if "laConsumeDeepLinkIntent" not in league_js:
        failures.append("League Atlas does not consume Home contextual intents")
    if "oppConsumeHomeIntent" not in market_js:
        failures.append("Market does not consume Home pressure-point intent")

    manifest = {
        "schema_version": "fsffl-home-north-star-real-league-sanity-v2",
        "run_at": datetime.now(UTC).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "coordinate": {
            "league_id": state.league.league_id,
            "league_state_id": state.state_id,
            "state_as_of": persisted["state_as_of"].isoformat(),
            "simulation_computed_at": persisted["simulation_computed_at"].isoformat(),
            "simulation_model_version": persisted["simulation_model_version"],
            "forecast_sources": persisted["forecast_sources"],
        },
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
            if weakest is not None else None
        ),
        "simulation": {
            "simulation_count": simulation.simulation_result.simulation_count,
            "expected_wins": sim_row["expected_wins"],
            "playoff_probability": sim_row["playoff_probability"],
            "championship_probability": sim_row["championship_probability"],
            "expected_finish": sim_row["expected_finish"],
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
            if resilience is not None else None
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
        "latency_ms": {
            "persisted_coordinate_load": round(persisted["load_ms"], 2),
            "home_atlas_compose": round(compose_ms, 3),
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
