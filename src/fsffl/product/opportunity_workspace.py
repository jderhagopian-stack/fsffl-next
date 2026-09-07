from __future__ import annotations

from itertools import product

from .runtime import UserRuntimeContext
from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import (
    build_trade_center_browser_view,
    resolve_owned_asset_ref,
)


def _empty_workspace(
    *,
    status: str,
    message: str,
    retryable: bool,
    runtime: UserRuntimeContext,
) -> dict[str, object]:
    league_state = runtime.league_state
    return {
        "status": status,
        "message": message,
        "retryable": retryable,
        "league_state_id": league_state.state_id if league_state is not None else None,
        "as_of": league_state.as_of.isoformat() if league_state is not None else None,
        "focal_team_id": runtime.selected_team_id,
        "focal_team_name": None,
        "requirements": {
            "league_state": league_state is not None,
            "managed_team": runtime.selected_team_id is not None,
            "authoritative_cardinal_value": bool(
                runtime.value_evidence is not None
                and runtime.value_evidence.fsffl_cardinal_values
            ),
            "simulation": runtime.simulation_analytics is not None,
        },
        "trade_discovery": {
            "candidate_count": 0,
            "returned_count": 0,
            "truncated": False,
            "ordering": "authoritative_cardinal_market_distance",
            "bilateral_evaluated_count": 0,
            "bilateral_evaluation_limit": 0,
            "candidates": [],
        },
        "available_players": {"count": 0, "players": []},
        "capabilities": {
            "structural_trade_discovery": False,
            "authoritative_value_ordering": False,
            "bilateral_decision_evaluation": False,
            "behavioral_acceptance": False,
            "waiver_materiality": False,
            "post_transaction_simulation": False,
        },
        "authority": {
            "search_role": "candidate_generation_ordering_and_decision_enrichment",
            "recommendation_authority": False,
            "provisional_value_used": False,
            "bilateral_evaluation_budget_is_product_compute_policy": True,
        },
    }


def _evaluate_structural_trade(
    runtime: UserRuntimeContext,
    row: dict[str, object],
) -> dict[str, object]:
    """Attach NEXT-5 bilateral evidence to one already-generated search row."""

    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return row

    counterparty_team_id = str(row["counterparty_team_id"])
    send = row.get("send") or []
    receive = row.get("receive") or []
    if not send or not receive:
        return row

    focal_assets = tuple(
        resolve_owned_asset_ref(
            league_state,
            team_id=focal_team_id,
            asset_ref=str(item["asset_ref"]),
        )
        for item in send
    )
    counterparty_assets = tuple(
        resolve_owned_asset_ref(
            league_state,
            team_id=counterparty_team_id,
            asset_ref=str(item["asset_ref"]),
        )
        for item in receive
    )
    draft = TradeDraft(
        draft_id=(
            f"opportunity:{league_state.state_id}:{focal_team_id}:"
            f"{counterparty_team_id}:{send[0]['asset_ref']}:{receive[0]['asset_ref']}"
        ),
        focal_team_id=focal_team_id,
        counterparty_team_id=counterparty_team_id,
        focal_side=TradeDraftSide(team_id=focal_team_id, assets=focal_assets),
        counterparty_side=TradeDraftSide(
            team_id=counterparty_team_id,
            assets=counterparty_assets,
        ),
    )
    proposal = submit_trade_draft(draft, as_of=league_state.as_of)
    analysis = build_private_beta_trade_analysis(
        runtime,
        proposal,
        focal_team_id=focal_team_id,
    )

    decision = analysis.get("decision") or {}
    side_a = decision.get("side_a") or {}
    side_b = decision.get("side_b") or {}
    focal_side = side_a if side_a.get("team_id") == focal_team_id else side_b
    counterparty_side = side_a if side_a.get("team_id") == counterparty_team_id else side_b

    evaluation = analysis.get("evaluation") or {}
    eval_a = evaluation.get("side_a") or {}
    eval_b = evaluation.get("side_b") or {}
    focal_eval = eval_a if eval_a.get("team_id") == focal_team_id else eval_b
    counterparty_eval = eval_a if eval_a.get("team_id") == counterparty_team_id else eval_b

    return {
        **row,
        "bilateral_decision_evaluated": decision != {},
        "decision_shape": decision.get("shape"),
        "focal_decision_shape": focal_side.get("shape"),
        "counterparty_decision_shape": counterparty_side.get("shape"),
        "focal_roster_delta": (focal_eval.get("delta") or {}).get("resilience"),
        "counterparty_roster_delta": (counterparty_eval.get("delta") or {}).get("resilience"),
        "behavioral_evidence_attached": bool(
            (analysis.get("availability") or {}).get("behavioral_evidence")
        ),
        "post_trade_simulation_attached": bool(
            (analysis.get("availability") or {}).get("competitive_outcomes")
        ),
        "explanation": (
            "Market-comparable structural trade test enriched with the current "
            "NEXT-5 bilateral roster-consequence view. It remains diagnostic until "
            "materiality, Behavioral evidence, and changed-state competitive outcomes "
            "support stronger authority."
        ),
    }


def build_opportunity_workspace(
    runtime: UserRuntimeContext,
    *,
    candidate_limit: int = 120,
    bilateral_evaluation_limit: int = 24,
) -> dict[str, object]:
    """Build a read-only private-beta Opportunity workspace with explicit readiness.

    Expected product-runtime gaps are represented as structured workspace states
    instead of transport errors. Search itself still runs only after canonical State,
    a managed team, and authoritative Cardinal Value evidence are available.
    """

    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None:
        return _empty_workspace(
            status="needs_league",
            message="Connect a league before running opportunity discovery.",
            retryable=False,
            runtime=runtime,
        )
    if focal_team_id is None:
        return _empty_workspace(
            status="needs_team",
            message="Select the franchise you manage before running opportunity discovery.",
            retryable=False,
            runtime=runtime,
        )

    values = runtime.value_evidence
    cardinal = {
        row.asset_id: row
        for row in (values.fsffl_cardinal_values if values is not None else ())
    }
    if not cardinal:
        return _empty_workspace(
            status="building_intelligence",
            message=(
                "Current FSFFL Value evidence is still being built. Opportunity discovery "
                "will activate automatically when the governed intelligence refresh finishes."
            ),
            retryable=True,
            runtime=runtime,
        )

    try:
        browser = build_trade_center_browser_view(
            league_state,
            focal_team_id=focal_team_id,
        )
    except ValueError as exc:
        return _empty_workspace(
            status="blocked",
            message=f"Canonical roster context is inconsistent: {exc}",
            retryable=True,
            runtime=runtime,
        )

    def option_value(option: object) -> float | None:
        asset_id = getattr(option, "player_id", None) or getattr(option, "pick_id", None)
        row = cardinal.get(asset_id)
        return row.score if row is not None else None

    candidates: list[dict[str, object]] = []
    for counterparty in browser.counterparties:
        for focal_asset, target_asset in product(
            browser.focal_team.assets,
            counterparty.assets,
        ):
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
                    "send": [{
                        "asset_ref": focal_asset.asset_ref,
                        "label": focal_asset.label,
                        "asset_kind": focal_asset.asset_kind,
                        "fsffl_value": focal_value,
                    }],
                    "receive": [{
                        "asset_ref": target_asset.asset_ref,
                        "label": target_asset.label,
                        "asset_kind": target_asset.asset_kind,
                        "fsffl_value": target_value,
                    }],
                    "search_distance": abs(target_value - focal_value),
                    "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
                    "bilateral_decision_evaluated": False,
                    "explanation": (
                        "Market-comparable structural trade test. Decision and acceptance "
                        "evidence are not yet complete enough to recommend action."
                    ),
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
    returned = candidates[: max(candidate_limit, 0)]

    evaluate_count = min(max(bilateral_evaluation_limit, 0), len(returned))
    for index in range(evaluate_count):
        try:
            returned[index] = _evaluate_structural_trade(runtime, returned[index])
        except ValueError as exc:
            returned[index] = {
                **returned[index],
                "bilateral_decision_evaluated": False,
                "decision_error": str(exc),
            }

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
                "explanation": (
                    "Currently unowned in canonical State. Availability is descriptive; "
                    "add/drop materiality has not yet been evaluated."
                ),
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
        "status": "ready",
        "message": "Current opportunity discovery workspace is ready.",
        "retryable": False,
        "league_state_id": league_state.state_id,
        "as_of": league_state.as_of.isoformat(),
        "focal_team_id": focal_team_id,
        "focal_team_name": browser.focal_team.display_name,
        "requirements": {
            "league_state": True,
            "managed_team": True,
            "authoritative_cardinal_value": True,
            "simulation": runtime.simulation_analytics is not None,
        },
        "trade_discovery": {
            "candidate_count": total_candidate_count,
            "returned_count": len(returned),
            "truncated": total_candidate_count > len(returned),
            "ordering": "authoritative_cardinal_market_distance",
            "bilateral_evaluated_count": sum(
                1 for row in returned if row.get("bilateral_decision_evaluated")
            ),
            "bilateral_evaluation_limit": bilateral_evaluation_limit,
            "candidates": returned,
        },
        "available_players": {"count": len(available_players), "players": available_players},
        "capabilities": {
            "structural_trade_discovery": True,
            "authoritative_value_ordering": True,
            "bilateral_decision_evaluation": evaluate_count > 0,
            "behavioral_acceptance": False,
            "waiver_materiality": False,
            "post_transaction_simulation": False,
        },
        "authority": {
            "search_role": "candidate_generation_ordering_and_decision_enrichment",
            "recommendation_authority": False,
            "provisional_value_used": False,
            "bilateral_evaluation_budget_is_product_compute_policy": True,
        },
    }
