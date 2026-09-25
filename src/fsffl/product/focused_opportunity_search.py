from __future__ import annotations

from typing import Mapping

from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .opportunity_posture import (
    apply_search_posture,
    calculated_competitive_state,
    resolve_search_posture,
)
from .opportunity_search import (
    SearchCandidateCollection,
    _player_position,
    _position_strengths,
    actionable_need_positions,
    build_roster_aware_trade_candidates,
    build_scoped_trade_candidates,
)
from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_VALID_INTENTS = {"", "position", "shop", "target", "owner", "consolidate"}


def _row_has_ref(row: dict[str, object], side: str, asset_ref: str) -> bool:
    return any(str(item.get("asset_ref")) == asset_ref for item in (row.get(side) or []))


def candidate_matches_focus(
    row: dict[str, object],
    *,
    intent: str,
    intent_value: str,
) -> bool:
    """Return whether a candidate satisfies the explicit user-selected Market task."""

    normalized_intent = intent if intent in _VALID_INTENTS else ""
    if normalized_intent in {"position", "target", "owner", "shop"} and not intent_value:
        return False
    if normalized_intent == "position":
        return str(row.get("target_position") or "") == intent_value
    if normalized_intent == "target":
        return _row_has_ref(row, "receive", intent_value)
    if normalized_intent == "owner":
        return str(row.get("counterparty_team_id") or "") == intent_value
    if normalized_intent == "shop":
        return _row_has_ref(row, "send", intent_value)
    if normalized_intent == "consolidate":
        return len(row.get("send") or []) > 1
    return True


def build_focused_trade_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    canonical_candidates: list[dict[str, object]] | None = None,
    requested_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED,
    intent: str = "",
    intent_value: str = "",
) -> SearchCandidateCollection:
    """Apply explicit Market intent before target/package generation.

    Specific intents construct their own strategically constrained candidate
    neighborhood instead of filtering a generic value-nearest catalog after the
    fact. Strategic posture remains ordering-only and cannot rewrite upstream
    State, Value, Team Utility, Decision or acceptance truth.
    """

    normalized_intent = intent if intent in _VALID_INTENTS else ""
    strengths = _position_strengths(runtime)
    focal_team_id = str(runtime.selected_team_id or "")
    focal_needs = actionable_need_positions(
        runtime,
        focal_team_id,
        strengths=strengths,
    ) if focal_team_id else ()
    need_filter = frozenset(focal_needs) if focal_needs else None

    if not normalized_intent:
        raw = (
            canonical_candidates
            if canonical_candidates is not None
            else build_roster_aware_trade_candidates(runtime, browser, cardinal)
        )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    elif normalized_intent == "position":
        try:
            requested_position = Position(intent_value)
        except ValueError:
            raw = SearchCandidateCollection(
                [],
                diagnostics={
                    "scope_label": "intent:position",
                    "admission_rejection_reasons": {"invalid_position": 1},
                },
            )
        else:
            raw = build_scoped_trade_candidates(
                runtime,
                browser,
                cardinal,
                target_positions=frozenset({requested_position}),
                require_counterparty_supply=False,
                scope_label=f"intent:position:{requested_position.value}",
            )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    elif normalized_intent == "target":
        raw = build_scoped_trade_candidates(
            runtime,
            browser,
            cardinal,
            target_asset_refs=(frozenset({intent_value}) if intent_value else frozenset()),
            require_counterparty_supply=False,
            scope_label=f"intent:target:{intent_value or 'missing'}",
        )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    elif normalized_intent == "owner":
        raw = build_scoped_trade_candidates(
            runtime,
            browser,
            cardinal,
            counterparty_team_ids=(frozenset({intent_value}) if intent_value else frozenset()),
            target_positions=need_filter,
            require_counterparty_supply=False,
            scope_label=f"intent:owner:{intent_value or 'missing'}",
        )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    elif normalized_intent == "shop":
        selected = next(
            (
                asset
                for asset in browser.focal_team.assets
                if asset.asset_ref == intent_value
            ),
            None,
        )
        selected_position = (
            _player_position(runtime.league_state, selected)
            if runtime.league_state is not None and selected is not None
            else None
        )
        raw = build_scoped_trade_candidates(
            runtime,
            browser,
            cardinal,
            target_positions=need_filter,
            require_counterparty_supply=True,
            required_send_asset_ref=intent_value or "__missing__",
            required_counterparty_need_position=selected_position,
            scope_label=f"intent:shop:{intent_value or 'missing'}",
        )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    elif normalized_intent == "consolidate":
        raw = build_scoped_trade_candidates(
            runtime,
            browser,
            cardinal,
            target_positions=need_filter,
            require_counterparty_supply=True,
            minimum_send_count=2,
            scope_label="intent:consolidate",
        )
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)
    else:
        raw = build_roster_aware_trade_candidates(runtime, browser, cardinal)
        diagnostics = dict(getattr(raw, "diagnostics", {}) or {})
        rows = list(raw)

    if normalized_intent:
        rows = [
            row
            for row in rows
            if candidate_matches_focus(
                row,
                intent=normalized_intent,
                intent_value=intent_value,
            )
        ]
        for row in rows:
            row["search_context"] = [
                *list(row.get("search_context") or []),
                (
                    "Explicit Market intent constrained discovery before package generation. "
                    "Value and Decision authority are unchanged."
                ),
            ]

    effective = resolve_search_posture(
        requested_posture,
        calculated_competitive_state(runtime),
    )
    ordered = apply_search_posture(rows, effective)
    return SearchCandidateCollection(
        ordered,
        diagnostics={
            **diagnostics,
            "intent": normalized_intent,
            "intent_value": intent_value,
            "focused_candidates_after_intent_validation": len(ordered),
        },
    )
