from __future__ import annotations

from itertools import combinations
from typing import Mapping

from fsffl.state.models import LeagueState, Position
from fsffl.team_utility.position_strength import LeagueRelativePositionStrength
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_SKILL_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def _player_position(league_state: LeagueState, option: TradeAssetOption) -> Position | None:
    if option.asset_kind != "player" or option.player_id is None:
        return None
    player = next((row for row in league_state.players if row.player_id == option.player_id), None)
    return player.position if player is not None else None


def _position_strengths(
    runtime: UserRuntimeContext,
) -> dict[str, dict[Position, LeagueRelativePositionStrength]]:
    """Consume the published league-relative positional-production evidence.

    Search does not rebuild this derived truth. NEXT-4/Analytics publishes the
    common 100-based position-strength rows once; Search only indexes those rows
    for candidate ordering and explanatory context.
    """

    simulation = runtime.simulation_analytics
    if simulation is None:
        return {}
    result: dict[str, dict[Position, LeagueRelativePositionStrength]] = {}
    for view in simulation.team_views:
        for row in view.position_strengths:
            if row.position not in _SKILL_POSITIONS:
                continue
            result.setdefault(view.team_id, {})[row.position] = row
    return result


def _asset_value(option: TradeAssetOption, cardinal: Mapping[str, FSFFLCardinalValueScore]) -> float | None:
    asset_id = option.player_id or option.pick_id
    row = cardinal.get(asset_id or "")
    return row.score if row is not None else None


def _asset_payload(option: TradeAssetOption, value: float) -> dict[str, object]:
    return {
        "asset_ref": option.asset_ref,
        "label": option.label,
        "asset_kind": option.asset_kind,
        "fsffl_value": value,
    }


def _weakest_receive_fit(
    *,
    league_state: LeagueState,
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
    team_id: str,
    send_assets: tuple[TradeAssetOption, ...],
) -> LeagueRelativePositionStrength | None:
    player_positions = [
        position
        for option in send_assets
        if (position := _player_position(league_state, option)) is not None
    ]
    rows = [
        strengths.get(team_id, {}).get(position)
        for position in player_positions
    ]
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
    focal_strength = (
        strengths.get(focal_team_id, {}).get(target_position)
        if target_position is not None
        else None
    )
    counterparty_fit = _weakest_receive_fit(
        league_state=league_state,
        strengths=strengths,
        team_id=counterparty_team_id,
        send_assets=send_assets,
    )
    shape = "two_for_one" if len(send_assets) == 2 else "one_for_one"
    context: list[str] = []
    if focal_strength is not None:
        strength_text = (
            f"{focal_strength.strength_index:.0f}"
            if focal_strength.strength_index is not None
            else "unavailable"
        )
        context.append(
            f"Target addresses {target_position.value}: strength index {strength_text} "
            f"(league average 100), rank #{focal_strength.league_rank}."
        )
    if counterparty_fit is not None:
        strength_text = (
            f"{counterparty_fit.strength_index:.0f}"
            if counterparty_fit.strength_index is not None
            else "unavailable"
        )
        context.append(
            f"Assets sent include {counterparty_fit.position.value}, where the other team has "
            f"strength index {strength_text} and rank #{counterparty_fit.league_rank}."
        )
    if shape == "two_for_one":
        context.append(
            "Consolidation structure: two focal assets for one target asset. Search does not "
            "award a package premium; Decision owns package economics."
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
        "focal_position_strength_rank": focal_strength.league_rank if focal_strength is not None else None,
        "focal_position_strength_index": focal_strength.strength_index if focal_strength is not None else None,
        "counterparty_receive_position_rank": counterparty_fit.league_rank if counterparty_fit is not None else None,
        "counterparty_receive_position_strength_index": counterparty_fit.strength_index if counterparty_fit is not None else None,
        "search_distance": abs(receive_value - send_total),
        "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
        "search_context": context,
        "bilateral_decision_evaluated": False,
        "explanation": (
            "Roster-aware structural trade test. League-relative positional production "
            "and Cardinal Value order Search only; Decision and acceptance evidence remain incomplete."
        ),
    }


def _best_single_and_pair_for_target(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    focal_assets: tuple[TradeAssetOption, ...],
    target: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
) -> tuple[dict[str, object], ...]:
    target_value = _asset_value(target, cardinal)
    if target_value is None:
        return ()
    valued_focal = tuple(
        (asset, value)
        for asset in focal_assets
        if (value := _asset_value(asset, cardinal)) is not None
    )
    if not valued_focal:
        return ()
    nearest_single, nearest_single_value = min(
        valued_focal,
        key=lambda item: (abs(float(item[1]) - target_value), item[0].asset_ref),
    )
    single_distance = abs(float(nearest_single_value) - target_value)
    rows: list[dict[str, object]] = []
    single = _candidate(
        league_state=league_state,
        focal_team_id=focal_team_id,
        counterparty_team_id=counterparty_team_id,
        counterparty_name=counterparty_name,
        send_assets=(nearest_single,),
        receive_asset=target,
        cardinal=cardinal,
        strengths=strengths,
    )
    if single is not None:
        rows.append(single)
    if len(valued_focal) >= 2:
        pair = min(
            combinations(valued_focal, 2),
            key=lambda items: (
                abs(float(items[0][1]) + float(items[1][1]) - target_value),
                items[0][0].asset_ref,
                items[1][0].asset_ref,
            ),
        )
        pair_total = float(pair[0][1]) + float(pair[1][1])
        pair_distance = abs(pair_total - target_value)
        # Structural realism guard: Search may only add package complexity when it
        # improves the governed market-value match over every available single asset.
        # This is parameter-free and does not attempt to estimate a consolidation
        # premium; NEXT-5 Decision remains authoritative for package economics.
        if pair_distance < single_distance:
            package = _candidate(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty_team_id,
                counterparty_name=counterparty_name,
                send_assets=(pair[0][0], pair[1][0]),
                receive_asset=target,
                cardinal=cardinal,
                strengths=strengths,
            )
            if package is not None:
                package["search_context"] = [
                    *(package.get("search_context") or []),
                    "Two-asset package retained because it is a closer Cardinal market-value match "
                    "than every available single focal asset.",
                ]
                rows.append(package)
    return tuple(rows)


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
    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    for counterparty in browser.counterparties:
        player_targets = tuple(asset for asset in counterparty.assets if asset.asset_kind == "player")
        for target in player_targets:
            for row in _best_single_and_pair_for_target(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty.team_id,
                counterparty_name=counterparty.display_name,
                focal_assets=browser.focal_team.assets,
                target=target,
                cardinal=cardinal,
                strengths=strengths,
            ):
                key = (
                    counterparty.team_id,
                    tuple(sorted(str(item["asset_ref"]) for item in row["send"])),
                    str(row["receive"][0]["asset_ref"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(row)
    # Lexicographic, explainable ordering rather than a hidden weighted score.
    # The weakest focal position relative to league-average optimized production
    # comes first, then structures that plausibly address a weak position for the
    # other team, then Cardinal distance. Search does not award a package-shape
    # preference; the simpler one-for-one wins only an exact-distance tie.
    candidates.sort(
        key=lambda row: (
            float(row.get("focal_position_strength_index") or 100.0),
            float(row.get("counterparty_receive_position_strength_index") or 100.0),
            float(row["search_distance"]),
            0 if row.get("package_shape") == "one_for_one" else 1,
            str(row["counterparty_name"]),
            str(row["receive"][0]["label"]),
        )
    )
    return candidates
