from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from .models import LeagueState


def _sorted_payload(state: LeagueState) -> dict[str, Any]:
    payload = state.model_dump(mode="json", exclude_none=False)
    if state.final_regular_totals_week is None:
        payload.pop("final_regular_totals_week")
    if state.rookie_pick_window is None:
        payload.pop("rookie_pick_window")
    for pick in payload["draft_picks"]:
        if pick["verified_slot"] is None:
            pick.pop("verified_slot")
    if not state.winners_bracket:
        payload.pop("winners_bracket", None)
    # Existing provider snapshots retain their exact identity. Personal rules are
    # an explicit, isolated derived State, never a mutation of provider evidence.
    if payload.get("rule_configuration") is None:
        payload.pop("rule_configuration", None)
    # Additive matchup-completion evidence must remain backward-compatible with
    # durable snapshots written before the field existed. Omitting only the new
    # unset coordinate preserves their deterministic State identity; a governed
    # non-null coordinate remains canonical State evidence and changes identity.
    if payload.get("completed_through_week") is None:
        payload.pop("completed_through_week", None)
    # Preserve identity for durable snapshots written before exact weekly
    # availability evidence existed. Pop only the empty additive coordinate.
    if not payload.get("player_week_availability"):
        payload.pop("player_week_availability", None)
    else:
        payload["player_week_availability"] = sorted(
            payload["player_week_availability"],
            key=lambda item: (item["week"], item["player_id"]),
        )
    # Draft-order policy evidence is an additive State coordinate. Omit only the
    # empty coordinate so snapshots written before item 5 keep their State ID.
    if not payload.get("draft_order_policies"):
        payload.pop("draft_order_policies", None)
    else:
        payload["draft_order_policies"] = sorted(
            payload["draft_order_policies"],
            key=lambda item: (
                item["draft_season"],
                item["policy_id"],
                item["version"],
                item["effective_at"],
                item["available_at"],
            ),
        )
        for policy in payload["draft_order_policies"]:
            policy["parameters"] = sorted(
                policy["parameters"],
                key=lambda item: item["name"],
            )
    payload["teams"] = sorted(payload["teams"], key=lambda item: item["team_id"])
    payload["team_states"] = sorted(payload["team_states"], key=lambda item: item["team_id"])
    for team_state in payload["team_states"]:
        if team_state["final_regular_record"] is None:
            team_state.pop("final_regular_record")
        # Preserve identity for durable snapshots written before Max PF existed.
        if team_state.get("max_points_for") is None:
            team_state.pop("max_points_for", None)
            team_state.pop("max_points_for_provenance", None)
        team_state["roster"] = sorted(
            team_state["roster"], key=lambda item: (item["player_id"], item["slot"])
        )
    payload["players"] = sorted(payload["players"], key=lambda item: item["player_id"])
    payload["player_states"] = sorted(payload["player_states"], key=lambda item: item["player_id"])
    for player_state in payload["player_states"]:
        # Unknown additive NFL reserve evidence must not re-key saved States.
        if player_state.get("nfl_injured_reserve") is None:
            player_state.pop("nfl_injured_reserve", None)
    payload["draft_picks"] = sorted(payload["draft_picks"], key=lambda item: item["pick_id"])
    payload["pick_ownership"] = sorted(payload["pick_ownership"], key=lambda item: item["pick_id"])
    payload["provenance"] = sorted(
        payload["provenance"],
        key=lambda item: (
            item["source"],
            item["effective_at"],
            item["retrieved_at"],
            (item.get("provider_ref") or {}).get("external_id", ""),
        ),
    )
    return payload


def canonical_state_json(state: LeagueState) -> str:
    return json.dumps(
        _sorted_payload(state),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def deterministic_state_id(state: LeagueState) -> str:
    return sha256(canonical_state_json(state).encode("utf-8")).hexdigest()


def load_state_json(raw: str) -> LeagueState:
    return LeagueState.model_validate_json(raw)
