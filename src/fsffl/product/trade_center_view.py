from __future__ import annotations

from pydantic import model_validator

from fsffl.state.settled_draft_order import settled_origin_order
from fsffl.state.models import Asset, FrozenModel, LeagueState, PickAsset, PlayerAsset, RosterSlot


class TradeAssetOption(FrozenModel):
    available: bool = True
    asset_ref: str
    asset_kind: str
    label: str
    detail: str | None = None
    player_id: str | None = None
    pick_id: str | None = None
    rule_slot: int | None = None
    official_slot: int | None = None
    slot_disagreement: bool = False
    roster_slot: RosterSlot | None = None
    age_years: float | None = None

    @model_validator(mode="after")
    def validate_asset(self) -> "TradeAssetOption":
        if not self.asset_ref.strip() or not self.asset_kind.strip() or not self.label.strip():
            raise ValueError("trade asset option identifiers cannot be blank")
        if self.asset_kind == "player" and self.player_id is None:
            raise ValueError("player trade option requires player_id")
        if self.asset_kind == "pick" and self.pick_id is None:
            raise ValueError("pick trade option requires pick_id")
        if self.asset_kind != "player" and self.age_years is not None:
            raise ValueError("only player trade options may expose age")
        return self


class TeamTradeBrowser(FrozenModel):
    team_id: str
    display_name: str
    assets: tuple[TradeAssetOption, ...]
    faab_balance: int


class TradeCenterBrowserView(FrozenModel):
    focal_team: TeamTradeBrowser
    counterparties: tuple[TeamTradeBrowser, ...]
    state_id: str
    pick_window_notice: str | None = None
    product_version: str = "next8-trade-browser-v2:player-state-age"


def _team_browser(league_state: LeagueState, team_id: str, orders) -> TeamTradeBrowser:
    team = next((item for item in league_state.teams if item.team_id == team_id), None)
    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team is None or team_state is None:
        raise ValueError("unknown team_id")

    players_by_id = {player.player_id: player for player in league_state.players}
    player_states_by_id = {state.player_id: state for state in league_state.player_states}
    assets: list[TradeAssetOption] = []
    for entry in team_state.roster:
        player = players_by_id.get(entry.player_id)
        if player is None:
            continue
        player_state = player_states_by_id.get(player.player_id)
        assets.append(
            TradeAssetOption(
                asset_ref=f"player:{player.player_id}",
                asset_kind="player",
                label=player.full_name,
                detail=player.position.value,
                player_id=player.player_id,
                roster_slot=entry.slot,
                age_years=player_state.age_years if player_state is not None else None,
            )
        )

    picks_by_id = {pick.pick_id: pick for pick in league_state.draft_picks}
    unconfirmed = league_state.unconfirmed_pick_ids()
    for ownership in league_state.pick_ownership:
        if ownership.owner_team_id != team_id:
            continue
        pick = picks_by_id.get(ownership.pick_id)
        if pick is None:
            continue
        order = orders.get(pick.season, {}).get(pick.original_team_id)
        rule_slot = order.slot if order else None
        slot = pick.verified_slot or rule_slot
        conflict = bool(order and order.conflicts(pick.verified_slot))
        notes = [order.reason] if order else []
        if pick.verified_slot:
            notes.append(f"Sleeper board slot {pick.verified_slot}")
        if conflict:
            notes.append(f"Conflicting league-rule slot {rule_slot}; exact valuation withheld")
        original_team = next(
            (item.display_name for item in league_state.teams if item.team_id == pick.original_team_id),
            pick.original_team_id,
        )
        assets.append(
            TradeAssetOption(
                asset_ref=f"pick:{pick.pick_id}",
                asset_kind="pick",
                label=(f"{pick.season} {pick.round}.{slot:02d}" if slot
                       else f"{pick.season} Round {pick.round}"),
                available=pick.pick_id not in unconfirmed,
                rule_slot=rule_slot, official_slot=pick.verified_slot, slot_disagreement=conflict,
                detail=" · ".join([f"Originally {original_team}", *notes]) + (" · Awaiting draft update" if pick.pick_id in unconfirmed else ""),
                pick_id=pick.pick_id,
            )
        )

    assets.sort(key=lambda item: (item.asset_kind != "player", item.label, item.asset_ref))
    return TeamTradeBrowser(
        team_id=team.team_id,
        display_name=team.display_name,
        assets=tuple(assets),
        faab_balance=team_state.faab_balance,
    )


def build_trade_center_browser_view(
    league_state: LeagueState,
    *,
    focal_team_id: str,
) -> TradeCenterBrowserView:
    """Expose canonically owned assets and descriptive State metadata for drafting.

    This view does not calculate Value, forecasts, lineup optimization, decision
    utility, or action authority. Player age is copied from canonical point-in-time
    State so product surfaces can share one ownership-aware asset catalog.
    """

    orders = {year: settled_origin_order(league_state, year) for year in {p.season for p in league_state.draft_picks}}
    focal = _team_browser(league_state, focal_team_id, orders)
    counterparties = tuple(
        _team_browser(league_state, team.team_id, orders)
        for team in sorted(league_state.teams, key=lambda item: (item.display_name, item.team_id))
        if team.team_id != focal_team_id
    )
    return TradeCenterBrowserView(
        focal_team=focal,
        counterparties=counterparties,
        state_id=league_state.state_id,
        pick_window_notice=league_state.rookie_pick_window.notice if league_state.rookie_pick_window else None,
    )


def asset_from_trade_option(option: TradeAssetOption) -> Asset:
    """Convert one already ownership-validated browser option to canonical Asset."""

    if not option.available:
        raise ValueError("Pick use is awaiting a draft update")
    if option.asset_kind == "player" and option.player_id is not None:
        return PlayerAsset(player_id=option.player_id)
    if option.asset_kind == "pick" and option.pick_id is not None:
        return PickAsset(pick_id=option.pick_id)
    raise ValueError("unsupported trade asset option")


def owned_asset_index(view: TradeCenterBrowserView) -> dict[tuple[str, str], Asset]:
    """Index exact canonical ownership once for request-local trade evaluation reuse."""

    teams = (view.focal_team, *view.counterparties)
    return {
        (team.team_id, option.asset_ref): asset_from_trade_option(option)
        for team in teams
        for option in team.assets if option.available
    }


def resolve_owned_asset_ref(
    league_state: LeagueState,
    *,
    team_id: str,
    asset_ref: str,
) -> Asset:
    """Resolve one submitted UI asset ref against current canonical ownership."""

    browser = _team_browser(league_state, team_id, {})
    option = next((item for item in browser.assets if item.asset_ref == asset_ref), None)
    if option is None:
        raise ValueError("submitted asset is not currently owned by the specified team")
    return asset_from_trade_option(option)
