from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from fsffl.analytics.team import TeamAnalyticsView
from fsffl.state.matchups import completed_matchups, completed_through_week
from fsffl.state.models import LeagueState

from .runtime import UserRuntimeContext


LEAGUE_ATLAS_CONTRACT_VERSION = "phase3-league-atlas-v1:north-star"


def _team_names(state: LeagueState) -> dict[str, str]:
    return {team.team_id: team.display_name for team in state.teams}


def _current_standings(state: LeagueState) -> tuple[dict[str, object], ...]:
    names = _team_names(state)
    records: dict[str, dict[str, float | int]] = {
        team.team_id: {
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "points_for": 0.0,
            "points_against": 0.0,
            "games": 0,
        }
        for team in state.teams
    }
    completed_weeks: set[int] = set()
    for matchup in completed_matchups(state):
        completed_weeks.add(matchup.week)
        a = records[matchup.team_a_id]
        b = records[matchup.team_b_id]
        a["games"] = int(a["games"]) + 1
        b["games"] = int(b["games"]) + 1
        a["points_for"] = float(a["points_for"]) + float(matchup.team_a_points)
        a["points_against"] = float(a["points_against"]) + float(matchup.team_b_points)
        b["points_for"] = float(b["points_for"]) + float(matchup.team_b_points)
        b["points_against"] = float(b["points_against"]) + float(matchup.team_a_points)
        if matchup.team_a_points > matchup.team_b_points:
            a["wins"] = int(a["wins"]) + 1
            b["losses"] = int(b["losses"]) + 1
        elif matchup.team_b_points > matchup.team_a_points:
            b["wins"] = int(b["wins"]) + 1
            a["losses"] = int(a["losses"]) + 1
        else:
            a["ties"] = int(a["ties"]) + 1
            b["ties"] = int(b["ties"]) + 1

    rows: list[dict[str, object]] = []
    for team in state.teams:
        raw = records[team.team_id]
        games = int(raw["games"])
        pct = (
            (int(raw["wins"]) + 0.5 * int(raw["ties"])) / games
            if games > 0
            else 0.0
        )
        rows.append(
            {
                "team_id": team.team_id,
                "team_name": names[team.team_id],
                "wins": int(raw["wins"]),
                "losses": int(raw["losses"]),
                "ties": int(raw["ties"]),
                "games": games,
                "win_percentage": pct,
                "points_for": float(raw["points_for"]),
                "points_against": float(raw["points_against"]),
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["win_percentage"]),
            -float(row["points_for"]),
            str(row["team_name"]),
            str(row["team_id"]),
        )
    )
    return tuple({**row, "rank": rank} for rank, row in enumerate(rows, start=1))


def _simulation_rows(
    runtime: UserRuntimeContext,
    standings: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    simulation = runtime.simulation_analytics
    if simulation is None:
        return ()
    current_rank = {str(row["team_id"]): int(row["rank"]) for row in standings}
    outcome_by_team = {
        row.team_id: row for row in simulation.simulation_result.outcomes
    }
    finish_by_team = {
        row.team_id: row for row in simulation.simulation_result.finish_distributions
    }
    state_by_team = {
        view.team_id: (
            view.utility.calculated_competitive_state.value
            if view.utility is not None
            else "unknown"
        )
        for view in simulation.team_views
    }

    fallback_order = sorted(
        outcome_by_team.values(),
        key=lambda row: (-row.expected_wins, row.team_id),
    )
    fallback_rank = {
        row.team_id: rank for rank, row in enumerate(fallback_order, start=1)
    }

    rows: list[dict[str, object]] = []
    for team_id, outcome in outcome_by_team.items():
        finish = finish_by_team.get(team_id)
        projected_rank = (
            float(finish.expected_finish)
            if finish is not None
            else float(fallback_rank[team_id])
        )
        current = current_rank.get(team_id)
        rows.append(
            {
                "team_id": team_id,
                "expected_wins": outcome.expected_wins,
                "wins_stddev": outcome.wins_stddev,
                "playoff_probability": outcome.playoff_probability,
                "first_place_probability": outcome.first_place_probability,
                "championship_probability": outcome.championship_probability,
                "simulation_count": outcome.simulation_count,
                "simulation_model_version": outcome.simulation_model_version,
                "expected_finish": projected_rank,
                "current_rank": current,
                "movement_vs_current_rank": (
                    float(current) - projected_rank if current is not None else None
                ),
                "competitive_state": state_by_team.get(team_id, "unknown"),
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["expected_finish"]),
            -float(row["playoff_probability"]),
            str(row["team_id"]),
        )
    )
    return tuple(rows)


def _preseason_rows(
    state: LeagueState,
    team_views: Iterable[TeamAnalyticsView] | None,
) -> tuple[dict[str, object], ...]:
    if team_views is None:
        return ()
    names = _team_names(state)
    rows: list[dict[str, object]] = []
    for view in team_views:
        lineup = view.optimized_lineup
        if lineup is None:
            continue
        projected_points = sum(
            float(assignment.expected_points)
            for assignment in lineup.assignments
        )
        rows.append(
            {
                "team_id": view.team_id,
                "team_name": names.get(view.team_id, view.display_name),
                "projected_starter_points": projected_points,
                "starter_count": len(lineup.assignments),
                "lineup_model_version": lineup.model_version,
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["projected_starter_points"]),
            str(row["team_name"]),
            str(row["team_id"]),
        )
    )
    return tuple({**row, "rank": rank} for rank, row in enumerate(rows, start=1))


def _pick_map(state: LeagueState) -> dict[str, object]:
    names = _team_names(state)
    owner_by_pick = {
        ownership.pick_id: ownership.owner_team_id
        for ownership in state.pick_ownership
    }
    picks = {pick.pick_id: pick for pick in state.draft_picks}
    seasons = sorted({pick.season for pick in state.draft_picks})
    rounds = sorted({pick.round for pick in state.draft_picks})

    owned_by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    traded_away_by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    for pick_id, pick in picks.items():
        owner_team_id = owner_by_pick.get(pick_id)
        if owner_team_id is None:
            continue
        status = "own" if owner_team_id == pick.original_team_id else "acquired"
        row = {
            "pick_id": pick.pick_id,
            "season": pick.season,
            "round": pick.round,
            "original_team_id": pick.original_team_id,
            "original_team_name": names.get(pick.original_team_id, pick.original_team_id),
            "owner_team_id": owner_team_id,
            "owner_team_name": names.get(owner_team_id, owner_team_id),
            "status": status,
        }
        owned_by_team[owner_team_id].append(row)
        if owner_team_id != pick.original_team_id:
            traded_away_by_team[pick.original_team_id].append(
                {**row, "status": "traded_away"}
            )

    teams: list[dict[str, object]] = []
    for team in sorted(state.teams, key=lambda item: item.display_name):
        owned = sorted(
            owned_by_team.get(team.team_id, []),
            key=lambda row: (
                int(row["season"]),
                int(row["round"]),
                str(row["original_team_name"]),
            ),
        )
        traded = sorted(
            traded_away_by_team.get(team.team_id, []),
            key=lambda row: (
                int(row["season"]),
                int(row["round"]),
                str(row["owner_team_name"]),
            ),
        )
        by_year: list[dict[str, object]] = []
        for season in seasons:
            year_owned = [row for row in owned if int(row["season"]) == season]
            counts = {
                str(round_number): sum(
                    int(row["round"]) == round_number for row in year_owned
                )
                for round_number in rounds
            }
            by_year.append(
                {
                    "season": season,
                    "total_picks": len(year_owned),
                    "round_counts": counts,
                    "first_round_count": counts.get("1", 0),
                }
            )
        teams.append(
            {
                "team_id": team.team_id,
                "team_name": team.display_name,
                "total_owned_picks": len(owned),
                "first_round_count": sum(int(row["round"]) == 1 for row in owned),
                "owned": owned,
                "traded_away_original_picks": traded,
                "by_year": by_year,
            }
        )
    return {
        "seasons": seasons,
        "rounds": rounds,
        "teams": teams,
        "ownership_semantics": "canonical State draft_picks + pick_ownership; no pick-value score",
    }


def build_league_atlas_payload(
    runtime: UserRuntimeContext,
    *,
    preseason_team_views: Iterable[TeamAnalyticsView] | None = None,
    preseason_as_of: str | None = None,
    preseason_reason: str | None = None,
) -> dict[str, object]:
    state = runtime.league_state
    if state is None:
        raise ValueError("League Atlas requires canonical LeagueState")

    standings = _current_standings(state)
    simulation_rows = _simulation_rows(runtime, standings)
    preseason_rows = _preseason_rows(state, preseason_team_views)
    if preseason_rows:
        preseason = {
            "status": "ready",
            "as_of": preseason_as_of,
            "basis": (
                "preserved preseason full-season Forecast joined to a compatible "
                "point-in-time preseason State snapshot; optimized starter production "
                "is shown as expectation context, not as a current power score"
            ),
            "teams": list(preseason_rows),
        }
    else:
        preseason = {
            "status": "unavailable",
            "as_of": preseason_as_of,
            "basis": None,
            "reason": (
                preseason_reason
                or "A compatible frozen preseason team-State expectation is unavailable."
            ),
            "teams": [],
        }

    simulation = runtime.simulation_analytics
    return {
        "status": "ready",
        "contract_version": LEAGUE_ATLAS_CONTRACT_VERSION,
        "league_state_id": state.state_id,
        "league_id": state.league.league_id,
        "league_name": state.league.name,
        "season": state.league.season,
        "as_of": state.as_of.isoformat(),
        "last_completed_week": completed_through_week(state),
        "managed_team_id": runtime.selected_team_id,
        "standings": list(standings),
        "simulation": {
            "status": "ready" if simulation_rows else "unavailable",
            "teams": list(simulation_rows),
            "simulation_count": (
                simulation.simulation_result.simulation_count
                if simulation is not None
                else None
            ),
            "model_version": (
                simulation.simulation_result.model_version
                if simulation is not None
                else None
            ),
            "reason": (
                None
                if simulation_rows
                else "Matching governed Simulation evidence is not yet available."
            ),
        },
        "preseason_expectation": preseason,
        "pick_map": _pick_map(state),
        "authority": {
            "state": "canonical point-in-time LeagueState",
            "simulation": "governed 50,000-run Simulation when already available",
            "competitive_state": "existing Team Utility calculated competitive state",
            "pick_ownership": "canonical State",
            "presentation_creates_model_truth": False,
            "team_intrinsic_total_created": False,
            "summed_market_percentiles_created": False,
            "league_market_value_available": False,
            "power_score_created": False,
            "recommendation_strength_created": False,
            "acceptance_probability_created": False,
        },
    }
