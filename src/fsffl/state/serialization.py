from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from .models import LeagueState


def _sorted_payload(state: LeagueState) -> dict[str, Any]:
    payload = state.model_dump(mode="json", exclude_none=False)
    payload["teams"] = sorted(payload["teams"], key=lambda item: item["team_id"])
    payload["team_states"] = sorted(payload["team_states"], key=lambda item: item["team_id"])
    for team_state in payload["team_states"]:
        team_state["roster"] = sorted(
            team_state["roster"], key=lambda item: (item["player_id"], item["slot"])
        )
    payload["players"] = sorted(payload["players"], key=lambda item: item["player_id"])
    payload["player_states"] = sorted(payload["player_states"], key=lambda item: item["player_id"])
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
