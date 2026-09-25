from __future__ import annotations

from bisect import bisect_left
from itertools import combinations
from typing import Mapping

from fsffl.state.models import LeagueState, Position
from fsffl.team_utility.position_strength import LeagueRelativePositionStrength
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_SKILL_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)
_MAX_DISCOVERY_PACKAGE_SIZE = 3
_PACKAGE_NEIGHBORHOOD_PER_SIZE = 3

PackageCatalog = dict[int, tuple[tuple[float, tuple[str, ...], tuple[TradeAssetOption, ...]], ...]]


def _player_position(league_state: LeagueState, option: TradeAssetOption) -> Position | None:
    if option.asset_kind != "player" or option.player_id is None:
        return None
    player = next((row for row in league_state.players if row.player_id == option.player_id), None)
    return player.position if player is not None else None


def _position_strengths(runtime: UserRuntimeContext) -> dict[str, dict[Position, LeagueRelativePositionStrength]]:
    """Consume already-published league-relative position strength evidence.

    Search does not rebuild this derived truth; it only consumes the common
    Analytics/Simulation position-strength rows for exploration context.
    """

    simulation = runtime.simulation_analytics
    if simulation is None:
        return {}
    result: dict[str, dict[Position, LeagueRelativePositionStrength]] = {}
    for view in simulation.team_views:
        for row in view.position_strengths:
            if row.position in _SKILL_POSITIONS:
                result.setdefault(view.team_id, {})[row.position] = row
    return result


def _asset_value(option: TradeAssetOption, cardinal: Mapping[str, FSFFLCardinalValueScore]) -> float | None:
    asset_id = option.player_id or option.pick_id
    row = cardinal.get(asset_id or "")
    return row.score if row is not None else None


def _asset_payload(option: TradeAssetOption, value: float) -> dict[str, object]:
    """Publish existing canonical asset metadata without creating new Search truth."""

    return {
        "asset_ref": option.asset_ref,
        "label": option.label,
        "asset_kind": option.asset_kind,
        "detail": option.detail,
        "age_years": option.age_years,
        "roster_slot": option.roster_slot.value if option.roster_slot is not None else None,
        "fsffl_value": value,
    }


def _relative_market_gap(receive_value: float, send_total: float) -> float:
    denominator = max(abs(receive_value), abs(send_total))
    return abs(receive_value - send_total) / denominator if denominator > 0.0 else 0.0


def _weakest_receive_fit(
    *,
    league_state: LeagueState,
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
    team_id: str,
    send_assets: tuple[TradeAssetOption, ...],
) -> LeagueRelativePositionStrength | None:
    positions = [
        position
        for option in send_assets
        if (position := _player_position(league_state, option)) is not None
    ]
    rows = [strengths.get(team_id, {}).get(position) for position in positions]
    resolved = [row for row in rows if row is not None]
    if not resolved:
        return None
    return min(
        resolved,
        key=lambda row: (
            row.strength_index if row.strength_index is not None else 100.0,
            -row.league_rank,
            row.position.value,
        ),
    )


def _candidate(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    send_assets: tuple[TradeAssetOption, ...],
    receive_asset: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
) -> dict[str, object] | None:
    receive_value = _asset_value(receive_asset, cardinal)
    send_values = tuple(_asset_value(option, cardinal) for option in send_assets)
    if receive_value is None or any(value is None for value in send_values):
        return None
    resolved_send_values = tuple(float(value) for value in send_values if value is not None)
    send_total = sum(resolved_send_values)
    target_position = _player_position(league_state, receive_asset)
    focal_strength = strengths.get(focal_team_id, {}).get(target_position) if target_position is not None else None
    counterparty_fit = _weakest_receive_fit(
        league_state=league_state,
        strengths=strengths,
        team_id=counterparty_team_id,
        send_assets=send_assets,
    )
    shape = {1: "one_for_one", 2: "two_for_one", 3: "three_for_one"}.get(
        len(send_assets), f"{len(send_assets)}_for_one"
    )
    context: list[str] = []
    if focal_strength is not None:
        strength_text = f"{focal_strength.strength_index:.0f}" if focal_strength.strength_index is not None else "unavailable"
        context.append(
            f"Target addresses {target_position.value}: strength index {strength_text} "
            f"(league average 100), rank #{focal_strength.league_rank}."
        )
    if counterparty_fit is not None:
        strength_text = f"{counterparty_fit.strength_index:.0f}" if counterparty_fit.strength_index is not None else "unavailable"
        context.append(
            f"Assets sent include {counterparty_fit.position.value}, where the other team has "
            f"strength index {strength_text} and rank #{counterparty_fit.league_rank}."
        )
    if len(send_assets) > 1:
        context.append(
            f"Consolidation structure: {len(send_assets)} focal assets for one target. Search does not "
            "award a consolidation premium; NEXT-5 Decision owns package economics."
        )
    return {
        "kind": "trade",
        "discovery_status": "structurally_valid",
        "action_authority": "diagnostic_only",
        "evidence_completeness": "partial",
        "counterparty_team_id": counterparty_team_id,
        "counterparty_name": counterparty_name,
        "send": [
            _asset_payload(option, value)
            for option, value in zip(send_assets, resolved_send_values, strict=True)
        ],
        "receive": [_asset_payload(receive_asset, receive_value)],
        "package_shape": shape,
        "target_position": target_position.value if target_position is not None else None,
        "target_fsffl_value": float(receive_value),
        "focal_position_strength_rank": focal_strength.league_rank if focal_strength is not None else None,
        "focal_position_strength_index": focal_strength.strength_index if focal_strength is not None else None,
        "counterparty_receive_position_rank": counterparty_fit.league_rank if counterparty_fit is not None else None,
        "counterparty_receive_position_strength_index": counterparty_fit.strength_index if counterparty_fit is not None else None,
        "search_distance": abs(receive_value - send_total),
        "market_gap_ratio": _relative_market_gap(receive_value, send_total),
        "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
        "search_context": context,
        "bilateral_decision_evaluated": False,
        "explanation": (
            "Broad structural trade search. Cardinal Value is one market-plausibility coordinate, "
            "not the definition of the best opportunity; Decision and acceptance evidence remain incomplete."
        ),
    }


def _build_package_catalog(
    focal_assets: tuple[TradeAssetOption, ...],
    cardinal: Mapping[str, FSFFLCardinalValueScore],
) -> PackageCatalog:
    """Enumerate the focal package universe once, not once per opposing target.

    With the discovery cap at three assets this is O(focal_assets^3) once per
    workspace. Target lookup then uses a binary search over package totals, avoiding
    the previous O(targets × focal_assets^3) synchronous path.
    """

    valued_focal = tuple(
        (asset, float(value))
        for asset in focal_assets
        if (value := _asset_value(asset, cardinal)) is not None
    )
    catalog: PackageCatalog = {}
    max_size = min(_MAX_DISCOVERY_PACKAGE_SIZE, len(valued_focal))
    for size in range(1, max_size + 1):
        entries: list[tuple[float, tuple[str, ...], tuple[TradeAssetOption, ...]]] = []
        for package in combinations(valued_focal, size):
            assets = tuple(asset for asset, _ in package)
            total = sum(value for _, value in package)
            refs = tuple(sorted(asset.asset_ref for asset in assets))
            entries.append((total, refs, assets))
        entries.sort(key=lambda item: (item[0], item[1]))
        catalog[size] = tuple(entries)
    return catalog


def _nearest_packages(
    catalog: PackageCatalog,
    *,
    size: int,
    target_value: float,
    limit: int = _PACKAGE_NEIGHBORHOOD_PER_SIZE,
) -> tuple[tuple[TradeAssetOption, ...], ...]:
    """Return a bounded Cardinal neighborhood without creating a package score.

    Search deliberately keeps several nearby structures so the single closest
    additive package cannot monopolize the path before Decision-owned economics
    and bilateral screening run. The neighborhood size is product compute policy,
    not Value or Decision authority.
    """

    entries = catalog.get(size) or ()
    if not entries or limit <= 0:
        return ()
    totals = [item[0] for item in entries]
    insertion = bisect_left(totals, target_value)
    radius = max(limit * 2, 4)
    start = max(0, insertion - radius)
    end = min(len(entries), insertion + radius + 1)
    ordered = sorted(
        entries[start:end],
        key=lambda item: (abs(item[0] - target_value), item[1]),
    )
    return tuple(item[2] for item in ordered[:limit])


def _nearest_packages_for_target(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    package_catalog: PackageCatalog,
    target: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
) -> tuple[dict[str, object], ...]:
    """Generate a bounded structural neighborhood for every target.

    Keep the nearest Cardinal package at each supported size instead of allowing
    the best single asset to veto all package complexity. This expands premium-target
    access without inventing a consolidation coefficient or acceptance rule.
    """

    target_value = _asset_value(target, cardinal)
    if target_value is None:
        return ()
    rows: list[dict[str, object]] = []
    for size in sorted(package_catalog):
        packages = _nearest_packages(
            package_catalog,
            size=size,
            target_value=float(target_value),
        )
        for variant_rank, package in enumerate(packages, start=1):
            row = _candidate(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty_team_id,
                counterparty_name=counterparty_name,
                send_assets=package,
                receive_asset=target,
                cardinal=cardinal,
                strengths=strengths,
            )
            if row is not None:
                row["package_variant_rank"] = variant_rank
                row["search_context"] = [
                    *(row.get("search_context") or []),
                    f"Search retained bounded governed {size}-asset market-neighborhood variant "
                    f"#{variant_rank} for this target. Package size and neighborhood rank are "
                    "exploratory product policy; Decision owns whether the structure is actually good.",
                ]
                rows.append(row)
    return tuple(rows)


def _strength(row: dict[str, object], key: str) -> float:
    value = row.get(key)
    return float(value) if value is not None else float("inf")


def _target_value(row: dict[str, object]) -> float:
    value = row.get("target_fsffl_value")
    return float(value) if value is not None else float("-inf")


def _multi_lane_search_order(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    """Interleave distinct Search lenses before the workspace truncates candidates.

    The first row remains the closest market match. Subsequent rows are admitted in
    round-robin order from market fit, premium target value, focal roster need,
    counterparty fit, and package complexity. No metrics are blended into a score.
    """

    if not candidates:
        return []
    indices = range(len(candidates))
    lanes = (
        sorted(indices, key=lambda i: (float(candidates[i]["market_gap_ratio"]), float(candidates[i]["search_distance"]), i)),
        sorted(indices, key=lambda i: (-_target_value(candidates[i]), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (_strength(candidates[i], "focal_position_strength_index"), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (_strength(candidates[i], "counterparty_receive_position_strength_index"), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (-len(candidates[i].get("send") or []), float(candidates[i]["market_gap_ratio"]), i)),
    )
    ordered: list[int] = []
    seen: set[int] = set()
    cursors = [0] * len(lanes)
    while len(ordered) < len(candidates):
        progressed = False
        for lane_index, lane in enumerate(lanes):
            while cursors[lane_index] < len(lane) and lane[cursors[lane_index]] in seen:
                cursors[lane_index] += 1
            if cursors[lane_index] >= len(lane):
                continue
            candidate_index = lane[cursors[lane_index]]
            cursors[lane_index] += 1
            seen.add(candidate_index)
            ordered.append(candidate_index)
            progressed = True
        if not progressed:
            break
    return [candidates[index] for index in ordered]


def _target_path_family_key(row: dict[str, object]) -> tuple[str, tuple[str, ...]]:
    return (
        str(row.get("counterparty_team_id") or ""),
        tuple(
            sorted(
                str(item.get("asset_ref") or "")
                for item in (row.get("receive") or [])
                if isinstance(item, dict) and item.get("asset_ref")
            )
        ),
    )


def _family_first_search_order(
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Preserve target/path diversity before the workspace candidate bound.

    Multi-lane Search still determines the first appearance and within-family
    ordering. This second pass changes only admission order: every distinct
    target/counterparty path family gets one row before any family gets a second
    package variant. It prevents package-neighborhood repetition from consuming
    the bounded workspace before Opportunity/Decision screening.
    """

    ordered = _multi_lane_search_order(candidates)
    families: dict[
        tuple[str, tuple[str, ...]],
        list[dict[str, object]],
    ] = {}
    family_order: list[tuple[str, tuple[str, ...]]] = []
    for row in ordered:
        key = _target_path_family_key(row)
        if key not in families:
            families[key] = []
            family_order.append(key)
        families[key].append(row)

    result: list[dict[str, object]] = []
    depth = 0
    while len(result) < len(ordered):
        progressed = False
        for key in family_order:
            rows = families[key]
            if depth >= len(rows):
                continue
            result.append(rows[depth])
            progressed = True
        if not progressed:
            break
        depth += 1
    return result


def build_roster_aware_trade_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
) -> list[dict[str, object]]:
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return []
    strengths = _position_strengths(runtime)
    package_catalog = _build_package_catalog(browser.focal_team.assets, cardinal)
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for counterparty in browser.counterparties:
        player_targets = tuple(asset for asset in counterparty.assets if asset.asset_kind == "player")
        for target in player_targets:
            for row in _nearest_packages_for_target(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty.team_id,
                counterparty_name=counterparty.display_name,
                package_catalog=package_catalog,
                target=target,
                cardinal=cardinal,
                strengths=strengths,
            ):
                key = (
                    counterparty.team_id,
                    tuple(sorted(str(item["asset_ref"]) for item in row["send"])),
                    str(row["receive"][0]["asset_ref"]),
                )
                if key not in seen:
                    seen.add(key)
                    candidates.append(row)
    return _family_first_search_order(candidates)
