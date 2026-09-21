from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)

from .runtime import UserRuntimeContext


LEAGUE_VALUE_LENS_CONTRACT_VERSION = "phase3-league-value-lenses-v1"
BROAD_MARKET_SCALE_ID = "dynasty-market-percentile"
INTRINSIC_PRESENTATION_COORDINATE = "percentile_rank_presentation_only"


def _percentile_ranks(values: Iterable[tuple[str, float]]) -> dict[str, float]:
    """Return centered percentile ranks without pretending raw values share units."""
    ordered = sorted(
        ((asset_id, float(value)) for asset_id, value in values),
        key=lambda item: (item[1], item[0]),
    )
    count = len(ordered)
    if count == 0:
        return {}

    ranks: dict[str, float] = {}
    index = 0
    while index < count:
        end = index + 1
        while end < count and ordered[end][1] == ordered[index][1]:
            end += 1
        average_zero_based_rank = (index + end - 1) / 2.0
        percentile = (average_zero_based_rank + 0.5) / count
        for offset in range(index, end):
            ranks[ordered[offset][0]] = percentile
        index = end
    return ranks


def _ownership(runtime: UserRuntimeContext) -> dict[str, str]:
    state = runtime.league_state
    if state is None:
        return {}
    result: dict[str, str] = {}
    for team_state in state.team_states:
        for entry in team_state.roster:
            prior = result.get(entry.player_id)
            if prior is not None and prior != team_state.team_id:
                raise ValueError(
                    f"canonical State assigns player {entry.player_id} to multiple teams"
                )
            result[entry.player_id] = team_state.team_id
    return result


def build_league_value_lenses(
    runtime: UserRuntimeContext,
    intrinsic: ShapleyIntrinsicContract | None,
    *,
    intrinsic_error: str | None = None,
) -> dict[str, object]:
    """Expose separate Broad Market and Intrinsic player lenses for League Atlas.

    This contract deliberately stops before a team-level value authority. Broad
    Market percentiles are non-additive. Intrinsic raw values live in a different
    coordinate. The Atlas may place the two player-level percentile lenses beside
    each other, but this builder never sums them, substitutes one for the other,
    creates League Market Value, or feeds Team Utility.
    """

    state = runtime.league_state
    if state is None:
        raise ValueError("League value lenses require canonical LeagueState")

    values = runtime.value_evidence
    market = {
        estimate.asset_id: max(0.0, min(1.0, float(estimate.distribution.mean)))
        for estimate in (values.estimates if values is not None else ())
        if estimate.scale.scale_id == BROAD_MARKET_SCALE_ID
    }

    intrinsic_available = bool(
        intrinsic is not None
        and intrinsic.status != ShapleyIntrinsicAvailability.UNAVAILABLE
        and intrinsic.estimates
    )
    intrinsic_raw = (
        {
            estimate.player_id: float(estimate.raw_intrinsic_value)
            for estimate in intrinsic.estimates
        }
        if intrinsic_available and intrinsic is not None
        else {}
    )
    intrinsic_ranks = _percentile_ranks(intrinsic_raw.items())

    owner_by_player = _ownership(runtime)
    team_names = {team.team_id: team.display_name for team in state.teams}
    players = {player.player_id: player for player in state.players}
    player_states = {row.player_id: row for row in state.player_states}

    rostered_ids = sorted(set(owner_by_player) & set(players))
    rows: list[dict[str, object]] = []
    for player_id in rostered_ids:
        player = players[player_id]
        market_percentile = market.get(player_id)
        intrinsic_percentile = intrinsic_ranks.get(player_id)
        gap = (
            intrinsic_percentile - market_percentile
            if market_percentile is not None and intrinsic_percentile is not None
            else None
        )
        player_state = player_states.get(player_id)
        rows.append(
            {
                "player_id": player_id,
                "asset_ref": f"player:{player_id}",
                "full_name": player.full_name,
                "position": player.position.value,
                "age_years": (
                    player_state.age_years if player_state is not None else None
                ),
                "owner_team_id": owner_by_player[player_id],
                "owner_team_name": team_names.get(
                    owner_by_player[player_id], owner_by_player[player_id]
                ),
                "broad_market_percentile": market_percentile,
                "intrinsic_percentile": intrinsic_percentile,
                "percentile_gap": gap,
                "comparison_available": gap is not None,
            }
        )

    by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_team[str(row["owner_team_id"])].append(row)

    teams = []
    for team in sorted(state.teams, key=lambda item: item.team_id):
        team_rows = by_team.get(team.team_id, [])
        teams.append(
            {
                "team_id": team.team_id,
                "team_name": team.display_name,
                "rostered_player_count": len(team_rows),
                "broad_market_covered_players": sum(
                    row["broad_market_percentile"] is not None for row in team_rows
                ),
                "intrinsic_covered_players": sum(
                    row["intrinsic_percentile"] is not None for row in team_rows
                ),
                "comparable_players": sum(
                    row["comparison_available"] is True for row in team_rows
                ),
                "player_ids": [str(row["player_id"]) for row in team_rows],
            }
        )

    market_ready = bool(market)
    intrinsic_status = (
        intrinsic.status.value if intrinsic is not None else "unavailable"
    )
    if market_ready and intrinsic_ranks:
        status = "ready"
    elif market_ready or intrinsic_ranks:
        status = "degraded"
    else:
        status = "unavailable"

    return {
        "status": status,
        "contract_version": LEAGUE_VALUE_LENS_CONTRACT_VERSION,
        "league_state_id": state.state_id,
        "broad_market": {
            "status": "ready" if market_ready else "unavailable",
            "scale_id": BROAD_MARKET_SCALE_ID,
            "player_count": len(market),
            "team_total_authority": False,
            "reason": (
                None
                if market_ready
                else "Governed Broad Market percentile evidence is unavailable."
            ),
        },
        "fsffl_intrinsic": {
            "authority_family": "canonical_shapley_intrinsic",
            "status": intrinsic_status,
            "contract_version": (
                intrinsic.contract_version if intrinsic is not None else None
            ),
            "quantity_semantics": (
                intrinsic.quantity_semantics if intrinsic is not None else None
            ),
            "display_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
            "player_count": len(intrinsic_ranks),
            "team_total_authority": False,
            "reason": (
                intrinsic.status_reason
                if intrinsic is not None
                and intrinsic.status == ShapleyIntrinsicAvailability.UNAVAILABLE
                else intrinsic_error
            ),
        },
        "players": rows,
        "teams": teams,
        "authority": {
            "canonical_fsffl_intrinsic_authority": "shapley_intrinsic",
            "broad_market_and_intrinsic_are_distinct_lenses": True,
            "comparison_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
            "raw_value_subtraction_used": False,
            "team_value_total_created": False,
            "team_value_rank_created": False,
            "league_market_value_available": False,
            "team_utility_included": False,
            "fsffl_cardinal_value_included": False,
            "recommendation_authority": False,
            "acceptance_probability": None,
        },
    }
