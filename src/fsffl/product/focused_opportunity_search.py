from __future__ import annotations

from itertools import combinations
from typing import Mapping

from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .opportunity_posture import (
    apply_search_posture,
    calculated_competitive_state,
    resolve_search_posture,
)
from .opportunity_search import (
    _asset_value,
    _candidate,
    _position_strengths,
    build_roster_aware_trade_candidates,
)
from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_VALID_INTENTS = {"", "position", "shop", "target", "consolidate"}


def _row_has_ref(row: dict[str, object], side: str, asset_ref: str) -> bool:
    return any(str(item.get("asset_ref")) == asset_ref for item in (row.get(side) or []))


def _shop_catalog(
    focal_assets: tuple[TradeAssetOption, ...],
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    shop_asset_ref: str,
) -> dict[int, tuple[tuple[float, tuple[TradeAssetOption, ...]], ...]]:
    valued = tuple(
        (asset, float(value))
        for asset in focal_assets
        if (value := _asset_value(asset, cardinal)) is not None
    )
    selected = next((asset for asset, _ in valued if asset.asset_ref == shop_asset_ref), None)
    if selected is None:
        return {}
    result: dict[int, tuple[tuple[float, tuple[TradeAssetOption, ...]], ...]] = {}
    for size in range(1, min(3, len(valued)) + 1):
        rows: list[tuple[float, tuple[TradeAssetOption, ...]]] = []
        for package in combinations(valued, size):
            assets = tuple(asset for asset, _ in package)
            if all(asset.asset_ref != shop_asset_ref for asset in assets):
                continue
            rows.append((sum(value for _, value in package), assets))
        rows.sort(key=lambda item: (item[0], tuple(asset.asset_ref for asset in item[1])))
        result[size] = tuple(rows)
    return result


def _nearest_shop_package(
    catalog: dict[int, tuple[tuple[float, tuple[TradeAssetOption, ...]], ...]],
    *,
    size: int,
    target_value: float,
) -> tuple[TradeAssetOption, ...] | None:
    rows = catalog.get(size) or ()
    if not rows:
        return None
    return min(
        rows,
        key=lambda item: (
            abs(item[0] - target_value),
            tuple(asset.asset_ref for asset in item[1]),
        ),
    )[1]


def _shop_focused_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    shop_asset_ref: str,
) -> list[dict[str, object]]:
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return []
    catalog = _shop_catalog(
        browser.focal_team.assets,
        cardinal,
        shop_asset_ref=shop_asset_ref,
    )
    if not catalog:
        return []
    strengths = _position_strengths(runtime)
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for counterparty in browser.counterparties:
        for target in (asset for asset in counterparty.assets if asset.asset_kind == "player"):
            target_value = _asset_value(target, cardinal)
            if target_value is None:
                continue
            for size in sorted(catalog):
                package = _nearest_shop_package(
                    catalog,
                    size=size,
                    target_value=float(target_value),
                )
                if package is None:
                    continue
                row = _candidate(
                    league_state=league_state,
                    focal_team_id=focal_team_id,
                    counterparty_team_id=counterparty.team_id,
                    counterparty_name=counterparty.display_name,
                    send_assets=package,
                    receive_asset=target,
                    cardinal=cardinal,
                    strengths=strengths,
                )
                if row is None:
                    continue
                key = (
                    counterparty.team_id,
                    tuple(sorted(str(item["asset_ref"]) for item in row["send"])),
                    str(row["receive"][0]["asset_ref"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                row["search_context"] = [
                    *(row.get("search_context") or []),
                    "Market Focus rebuilt the package neighborhood around the player you chose to shop. "
                    "Value and Decision authority are unchanged.",
                ]
                candidates.append(row)
    return sorted(
        candidates,
        key=lambda row: (
            float(row.get("market_gap_ratio") or 0.0),
            float(row.get("search_distance") or 0.0),
            str(row.get("counterparty_team_id") or ""),
        ),
    )


def build_focused_trade_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    canonical_candidates: list[dict[str, object]] | None = None,
    requested_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED,
    intent: str = "",
    intent_value: str = "",
) -> list[dict[str, object]]:
    """Apply explicit Market Focus before the product candidate limit.

    Position, target and consolidation focus narrow the full structural catalog.
    Shopping a player rebuilds package neighborhoods constrained to include that asset,
    so it is not merely a browser filter over previously returned rows. Strategic
    posture changes Search ordering only and never rewrites State, Value or Decision.
    """

    normalized_intent = intent if intent in _VALID_INTENTS else ""
    if normalized_intent == "shop" and intent_value:
        rows = _shop_focused_candidates(
            runtime,
            browser,
            cardinal,
            shop_asset_ref=intent_value,
        )
    else:
        rows = list(
            canonical_candidates
            if canonical_candidates is not None
            else build_roster_aware_trade_candidates(runtime, browser, cardinal)
        )
        if normalized_intent == "position" and intent_value:
            rows = [row for row in rows if str(row.get("target_position") or "") == intent_value]
        elif normalized_intent == "target" and intent_value:
            rows = [row for row in rows if _row_has_ref(row, "receive", intent_value)]
        elif normalized_intent == "consolidate":
            rows = [row for row in rows if len(row.get("send") or []) > 1]

    effective = resolve_search_posture(
        requested_posture,
        calculated_competitive_state(runtime),
    )
    return apply_search_posture(rows, effective)
