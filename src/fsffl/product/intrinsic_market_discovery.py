from __future__ import annotations

from collections import defaultdict

from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)

from .runtime import UserRuntimeContext
from .value_lens_evidence import build_governed_value_lens_evidence


INTRINSIC_MARKET_DISCOVERY_VERSION = "phase3-intrinsic-market-discovery-v2:value-index"
MARKET_PERCENTILE_SCALE_ID = "dynasty-market-percentile"


def _ownership(runtime: UserRuntimeContext) -> dict[str, str]:
    state = runtime.league_state
    if state is None:
        return {}
    owner_by_player: dict[str, str] = {}
    for team_state in state.team_states:
        for entry in team_state.roster:
            prior = owner_by_player.get(entry.player_id)
            if prior is not None and prior != team_state.team_id:
                raise ValueError(
                    f"canonical State assigns player {entry.player_id} to multiple teams"
                )
            owner_by_player[entry.player_id] = team_state.team_id
    return owner_by_player


def _unavailable(
    runtime: UserRuntimeContext,
    *,
    reason: str,
    intrinsic: ShapleyIntrinsicContract | None,
) -> dict[str, object]:
    state = runtime.league_state
    return {
        "status": "unavailable",
        "message": reason,
        "model_version": INTRINSIC_MARKET_DISCOVERY_VERSION,
        "league_state_id": state.state_id if state is not None else None,
        "focal_team_id": runtime.selected_team_id,
        "minimum_percentile_gap": 0.10,
        "comparable_player_count": 0,
        "disagreement_count": 0,
        "rows": [],
        "authority": {
            "discovery_lens_only": True,
            "recommendation_authority": False,
            "acceptance_probability": None,
            "league_market_value_available": False,
            "team_utility_included": False,
            "raw_value_subtraction_used": False,
            "intrinsic_status": (
                intrinsic.status.value if intrinsic is not None else "unavailable"
            ),
        },
    }


def build_intrinsic_market_discovery(
    runtime: UserRuntimeContext,
    intrinsic: ShapleyIntrinsicContract,
    *,
    minimum_percentile_gap: float = 0.10,
    limit: int = 24,
) -> dict[str, object]:
    """Build a discovery-only Intrinsic-vs-Broad-Market disagreement lens.

    This is presentation/search context, not a new value coordinate. Broad Market
    and Intrinsic retain separate units. The only comparison is percentile rank.
    No Team Utility, League Market Value, acceptance probability, or action
    authority is inferred here.
    """

    if not 0.0 <= minimum_percentile_gap <= 1.0:
        raise ValueError("minimum_percentile_gap must be between zero and one")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    state = runtime.league_state
    if state is None:
        return _unavailable(
            runtime,
            reason="Connect a league before requesting value disagreement discovery.",
            intrinsic=intrinsic,
        )
    if runtime.selected_team_id is None:
        return _unavailable(
            runtime,
            reason="Select the franchise you manage before requesting value disagreement discovery.",
            intrinsic=intrinsic,
        )
    lens_evidence = build_governed_value_lens_evidence(runtime, intrinsic)
    if lens_evidence.status != "ready":
        return _unavailable(
            runtime,
            reason=lens_evidence.reason or "Governed Value lens evidence is unavailable.",
            intrinsic=intrinsic,
        )

    market = lens_evidence.market_percentiles
    intrinsic_values = lens_evidence.intrinsic_raw
    intrinsic_ranks = lens_evidence.intrinsic_percentiles
    value_coordinate = lens_evidence.value_coordinate
    assert value_coordinate is not None
    owner_by_player = _ownership(runtime)
    teams = {team.team_id: team.display_name for team in state.teams}
    players = {player.player_id: player for player in state.players}
    player_states = {item.player_id: item for item in state.player_states}

    comparable_ids = sorted(
        set(market)
        & set(intrinsic_ranks)
        & set(owner_by_player)
        & set(players)
    )
    if not comparable_ids:
        return _unavailable(
            runtime,
            reason=(
                "Broad Market and Intrinsic evidence have no comparable canonically "
                "rostered players in the current state."
            ),
            intrinsic=intrinsic,
        )

    rows: list[dict[str, object]] = []
    for player_id in comparable_ids:
        market_percentile = market[player_id]
        intrinsic_percentile = intrinsic_ranks[player_id]
        gap = intrinsic_percentile - market_percentile
        market_index = value_coordinate.index_for_percentile(market_percentile)
        intrinsic_index = value_coordinate.index_for_percentile(intrinsic_percentile)
        display_gap = (
            intrinsic_index - market_index
            if market_index is not None and intrinsic_index is not None
            else None
        )
        if abs(gap) < minimum_percentile_gap:
            continue

        player = players[player_id]
        owner_team_id = owner_by_player[player_id]
        owned_by_focal = owner_team_id == runtime.selected_team_id
        direction = "intrinsic_higher" if gap > 0 else "market_higher"
        if direction == "intrinsic_higher":
            read = (
                "FSFFL Intrinsic ranks this player materially higher than the broad "
                "dynasty market. Investigate the price and team context; this is not "
                "an automatic acquisition signal."
            )
        else:
            read = (
                "The broad dynasty market ranks this player materially higher than "
                "FSFFL Intrinsic. Investigate current market demand and team context; "
                "this is not an automatic sale signal."
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
                "owner_team_id": owner_team_id,
                "owner_team_name": teams.get(owner_team_id, owner_team_id),
                "owned_by_focal": owned_by_focal,
                "market_percentile": market_percentile,
                "intrinsic_percentile": intrinsic_percentile,
                "market_value_index": market_index,
                "intrinsic_value_index": intrinsic_index,
                "value_index_gap": display_gap,
                "percentile_gap": gap,
                "absolute_percentile_gap": abs(gap),
                "direction": direction,
                "read": read,
                "focus_intent": "shop" if owned_by_focal else "target",
                "focus_value": f"player:{player_id}",
                "action_authority": "diagnostic_only",
                "acceptance_probability": None,
            }
        )

    rows.sort(
        key=lambda row: (
            -float(row["absolute_percentile_gap"]),
            str(row["full_name"]),
            str(row["player_id"]),
        )
    )
    returned = rows[:limit]
    return {
        "status": "ready",
        "message": (
            "Governed Intrinsic-vs-Broad-Market disagreement discovery is ready."
        ),
        "model_version": INTRINSIC_MARKET_DISCOVERY_VERSION,
        "league_state_id": state.state_id,
        "focal_team_id": runtime.selected_team_id,
        "market_context_id": lens_evidence.market_context_id,
        "market_model_version": lens_evidence.market_model_version,
        "intrinsic_contract_version": lens_evidence.intrinsic_contract_version,
        "intrinsic_model_version": lens_evidence.intrinsic_model_version,
        "forecast_model_version": lens_evidence.forecast_model_version,
        "value_presentation": {
            "status": "ready",
            **value_coordinate.summary_payload(),
        },
        "intrinsic_status": intrinsic.status.value,
        "minimum_percentile_gap": minimum_percentile_gap,
        "comparable_player_count": len(comparable_ids),
        "disagreement_count": len(rows),
        "returned_count": len(returned),
        "truncated": len(rows) > len(returned),
        "rows": returned,
        "authority": {
            "discovery_lens_only": True,
            "recommendation_authority": False,
            "acceptance_probability": None,
            "league_market_value_available": False,
            "team_utility_included": False,
            "raw_value_subtraction_used": False,
            "comparison_coordinate": "percentile_rank_presentation_only",
            "shared_value_index_presentation_only": True,
            "display_value_index_subtraction_allowed": True,
        },
    }
