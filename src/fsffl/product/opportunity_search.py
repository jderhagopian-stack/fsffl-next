from __future__ import annotations

from itertools import combinations
from typing import Mapping

from fsffl.state.models import LeagueState, Position
from fsffl.team_utility.position_strength import summarize_lineup_by_position
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_SKILL_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def _player_position(league_state: LeagueState, option: TradeAssetOption) -> Position | None:
    if option.asset_kind != "player" or option.player_id is None:
        return None
    player = next((row for row in league_state.players if row.player_id == option.player_id), None)
    return player.position if player is not None else None


def _position_strength_ranks(runtime: UserRuntimeContext) -> dict[str, dict[Position, int]]:
    """Return 1=strongest league rank for optimized starter production by position.

    This is a search-order diagnostic only. It does not create a Team Utility score
    and does not alter Forecast, Value, Decision, or Simulation authority.
    """

    simulation = runtime.simulation_analytics
    if simulation is None:
        return {}
    by_position: dict[Position, list[tuple[str, float]]] = {position: [] for position in _SKILL_POSITIONS}
    for view in simulation.team_views:
        if view.optimized_lineup is None:
            continue
        strengths = {row.position: row.expected_points for row in summarize_lineup_by_position(view.optimized_lineup)}
        for position in _SKILL_POSITIONS:
            by_position[position].append((view.team_id, strengths.get(position, 0.0)))
    result: dict[str, dict[Position, int]] = {}
    for position, rows in by_position.items():
        ordered = sorted(rows, key=lambda item: (-item[1], item[0]))
        for rank, (team_id, _value) in enumerate(ordered, start=1):
            result.setdefault(team_id, {})[position] = rank
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


def _counterparty_receive_need_rank(
    *,
    league_state: LeagueState,
    ranks: dict[str, dict[Position, int]],
    team_id: str,
    send_assets: tuple[TradeAssetOption, ...],
) -> int:
    player_positions = [
        position
        for option in send_assets
        if (position := _player_position(league_state, option)) is not None
    ]
    if not player_positions:
        return 0
    return max(ranks.get(team_id, {}).get(position, 0) for position in player_positions)


def _candidate(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    send_assets: tuple[TradeAssetOption, ...],
    receive_asset: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    ranks: dict[str, dict[Position, int]],
) -> dict[str, object] | None:
    receive_value = _asset_value(receive_asset, cardinal)
    send_values = tuple(_asset_value(option, cardinal) for option in send_assets)
    if receive_value is None or any(value is None for value in send_values):
        return None
    resolved_send_values = tuple(float(value) for value in send_values if value is not None)
    send_total = sum(resolved_send_values)
    target_position = _player_position(league_state, receive_asset)
    focal_need_rank = ranks.get(focal_team_id, {}).get(target_position, 0) if target_position is not None else 0
    counterparty_need_rank = _counterparty_receive_need_rank(
        league_state=league_state,
        ranks=ranks,
        team_id=counterparty_team_id,
        send_assets=send_assets,
    )
    shape = "two_for_one" if len(send_assets) == 2 else "one_for_one"
    context: list[str] = []
    if target_position is not None and focal_need_rank:
        context.append(f"Target addresses {target_position.value}, currently league rank #{focal_need_rank} by optimized starter production.")
    if counterparty_need_rank:
        context.append(f"Assets sent include a position where the other team ranks as low as #{counterparty_need_rank} by optimized starter production.")
    if shape == "two_for_one":
        context.append("Consolidation structure: two focal assets for one target asset.")
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
        "focal_position_strength_rank": focal_need_rank or None,
        "counterparty_receive_position_rank": counterparty_need_rank or None,
        "search_distance": abs(receive_value - send_total),
        "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
        "search_context": context,
        "bilateral_decision_evaluated": False,
        "explanation": (
            "Roster-aware structural trade test. Position context and Cardinal Value "
            "order Search only; Decision and acceptance evidence remain incomplete."
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
    ranks: dict[str, dict[Position, int]],
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
    nearest_single = min(
        valued_focal,
        key=lambda item: (abs(float(item[1]) - target_value), item[0].asset_ref),
    )[0]
    rows: list[dict[str, object]] = []
    single = _candidate(
        league_state=league_state,
        focal_team_id=focal_team_id,
        counterparty_team_id=counterparty_team_id,
        counterparty_name=counterparty_name,
        send_assets=(nearest_single,),
        receive_asset=target,
        cardinal=cardinal,
        ranks=ranks,
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
        package = _candidate(
            league_state=league_state,
            focal_team_id=focal_team_id,
            counterparty_team_id=counterparty_team_id,
            counterparty_name=counterparty_name,
            send_assets=(pair[0][0], pair[1][0]),
            receive_asset=target,
            cardinal=cardinal,
            ranks=ranks,
        )
        if package is not None:
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
    ranks = _position_strength_ranks(runtime)
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
                ranks=ranks,
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
    # Weak focal positions (higher league rank number) come first, followed by
    # structures that plausibly address a weak position for the other team, then
    # Cardinal distance. Packages do not receive artificial value premiums here.
    candidates.sort(
        key=lambda row: (
            -int(row.get("focal_position_strength_rank") or 0),
            -int(row.get("counterparty_receive_position_rank") or 0),
            0 if row.get("package_shape") == "two_for_one" else 1,
            float(row["search_distance"]),
            str(row["counterparty_name"]),
            str(row["receive"][0]["label"]),
        )
    )
    return candidates
