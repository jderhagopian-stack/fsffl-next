from __future__ import annotations

from itertools import product

from .runtime import UserRuntimeContext
from .trade_center_view import build_trade_center_browser_view


def build_opportunity_workspace(runtime: UserRuntimeContext, *, candidate_limit: int = 120) -> dict[str, object]:
    """Build a read-only private-beta Opportunity workspace.

    Search may consume authoritative Value to order structural candidates, but it
    does not grant action authority. Until acceptance/materiality and changed-state
    competitive evidence are attached, trade rows remain diagnostic market tests.
    The retired provisional Value challenger is deliberately excluded.
    """

    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None:
        raise ValueError("No league is loaded")
    if focal_team_id is None:
        raise ValueError("No managed team is selected")

    browser = build_trade_center_browser_view(league_state, focal_team_id=focal_team_id)
    values = runtime.value_evidence
    cardinal = {
        row.asset_id: row
        for row in (values.fsffl_cardinal_values if values is not None else ())
    }

    def option_value(option: object) -> float | None:
        asset_id = getattr(option, "player_id", None) or getattr(option, "pick_id", None)
        row = cardinal.get(asset_id)
        return row.score if row is not None else None

    candidates: list[dict[str, object]] = []
    for counterparty in browser.counterparties:
        for focal_asset, target_asset in product(browser.focal_team.assets, counterparty.assets):
            focal_value = option_value(focal_asset)
            target_value = option_value(target_asset)
            if focal_value is None or target_value is None:
                continue
            candidates.append(
                {
                    "kind": "trade",
                    "discovery_status": "structurally_valid",
                    "action_authority": "diagnostic_only",
                    "evidence_completeness": "partial",
                    "counterparty_team_id": counterparty.team_id,
                    "counterparty_name": counterparty.display_name,
                    "send": [
                        {
                            "asset_ref": focal_asset.asset_ref,
                            "label": focal_asset.label,
                            "asset_kind": focal_asset.asset_kind,
                            "fsffl_value": focal_value,
                        }
                    ],
                    "receive": [
                        {
                            "asset_ref": target_asset.asset_ref,
                            "label": target_asset.label,
                            "asset_kind": target_asset.asset_kind,
                            "fsffl_value": target_value,
                        }
                    ],
                    "search_distance": abs(target_value - focal_value),
                    "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
                    "explanation": "Market-comparable structural trade test. Decision and acceptance evidence are not yet complete enough to recommend action.",
                }
            )

    candidates.sort(
        key=lambda row: (
            float(row["search_distance"]),
            str(row["counterparty_name"]),
            str(row["receive"][0]["label"]),
        )
    )
    total_candidate_count = len(candidates)
    candidates = candidates[: max(candidate_limit, 0)]

    rostered_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    states = {row.player_id: row for row in league_state.player_states}
    available_players = []
    for player in league_state.players:
        if player.player_id in rostered_ids:
            continue
        player_state = states.get(player.player_id)
        value_row = cardinal.get(player.player_id)
        available_players.append(
            {
                "player_id": player.player_id,
                "full_name": player.full_name,
                "position": player.position.value,
                "nfl_team": player.nfl_team,
                "age_years": player_state.age_years if player_state is not None else None,
                "status": player_state.status.value if player_state is not None else "unknown",
                "fsffl_value": value_row.score if value_row is not None else None,
                "action_authority": "diagnostic_only",
                "explanation": "Currently unowned in canonical State. Availability is descriptive; add/drop materiality has not yet been evaluated.",
            }
        )
    available_players.sort(
        key=lambda row: (
            row["fsffl_value"] is None,
            -(row["fsffl_value"] or 0.0),
            str(row["full_name"]),
        )
    )

    return {
        "league_state_id": league_state.state_id,
        "as_of": league_state.as_of.isoformat(),
        "focal_team_id": focal_team_id,
        "focal_team_name": browser.focal_team.display_name,
        "trade_discovery": {
            "candidate_count": total_candidate_count,
            "returned_count": len(candidates),
            "truncated": total_candidate_count > len(candidates),
            "ordering": "authoritative_cardinal_market_distance",
            "candidates": candidates,
        },
        "available_players": {
            "count": len(available_players),
            "players": available_players,
        },
        "capabilities": {
            "structural_trade_discovery": True,
            "authoritative_value_ordering": values is not None and bool(cardinal),
            "bilateral_decision_evaluation": False,
            "behavioral_acceptance": False,
            "waiver_materiality": False,
            "post_transaction_simulation": False,
        },
        "authority": {
            "search_role": "candidate_generation_and_ordering_only",
            "recommendation_authority": False,
            "provisional_value_used": False,
        },
    }
