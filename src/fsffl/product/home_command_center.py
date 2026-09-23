from __future__ import annotations

from .league_atlas import build_league_atlas_payload
from .runtime import UserRuntimeContext


HOME_COMMAND_CENTER_CONTRACT_VERSION = "home-north-star-v1"


def build_home_command_center_payload(runtime: UserRuntimeContext) -> dict[str, object]:
    """Compose Home from existing governed runtime evidence without launching new work."""

    if runtime.league_state is None:
        raise ValueError("Home requires canonical LeagueState")
    if runtime.selected_team_id is None:
        raise ValueError("Home requires a managed team")

    atlas = build_league_atlas_payload(
        runtime,
        preseason_reason=(
            "Home intentionally does not request or reconstruct preseason evidence."
        ),
    )
    standings = list(atlas["standings"])
    managed_id = runtime.selected_team_id
    managed = next(
        (row for row in standings if row["team_id"] == managed_id),
        None,
    )
    if managed is None:
        raise ValueError("Managed team is not present in canonical standings")

    simulation_rows = list(atlas["simulation"]["teams"])
    managed_simulation = next(
        (row for row in simulation_rows if row["team_id"] == managed_id),
        None,
    )

    rank = int(managed["rank"])
    adjacent_ranks = {rank - 1, rank, rank + 1}
    around = [
        row for row in standings
        if int(row["rank"]) in adjacent_ranks
    ]

    return {
        "status": "ready",
        "contract_version": HOME_COMMAND_CENTER_CONTRACT_VERSION,
        "league_state_id": atlas["league_state_id"],
        "league_id": atlas["league_id"],
        "league_name": atlas["league_name"],
        "season": atlas["season"],
        "as_of": atlas["as_of"],
        "managed_team_id": managed_id,
        "last_completed_week": atlas["last_completed_week"],
        "managed_standing": managed,
        "around_the_league": around,
        "simulation": {
            "status": (
                "ready"
                if managed_simulation is not None
                and atlas["simulation"]["status"] == "ready"
                else "unavailable"
            ),
            "team": managed_simulation,
            "simulation_count": atlas["simulation"]["simulation_count"],
            "model_version": atlas["simulation"]["model_version"],
            "reason": atlas["simulation"]["reason"],
        },
        "authority": {
            "presentation_only": True,
            "state": atlas["authority"]["state"],
            "simulation": atlas["authority"]["simulation"],
            "position_strength": "existing Team Analytics optimized-starter position strength",
            "fragility": "existing Team Utility roster resilience",
            "launches_opportunity_search": False,
            "launches_decision_evaluation": False,
            "launches_simulation": False,
            "creates_master_score": False,
            "creates_recommendation_authority": False,
            "creates_value_blend": False,
        },
    }
