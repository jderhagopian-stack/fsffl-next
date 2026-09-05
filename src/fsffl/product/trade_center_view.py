from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueState, RosterSlot


class TradeAssetOption(FrozenModel):
    asset_ref: str
    asset_kind: str
    label: str
    detail: str | None = None
    player_id: str | None = None
    pick_id: str | None = None
    roster_slot: RosterSlot | None = None

    @model_validator(mode="after")
    def validate_asset(self) -> "TradeAssetOption":
        if not self.asset_ref.strip() or not self.asset_kind.strip() or not self.label.strip():
            raise ValueError("trade asset option identifiers cannot be blank")
        if self.asset_kind == "player" and self.player_id is None:
            raise ValueError("player trade option requires player_id")
        if self.asset_kind == "pick" and self.pick_id is None:
            raise ValueError("pick trade option requires pick_id")
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
    product_version: str = "next8-trade-browser-v1"


def _team_browser(league_state: LeagueState, team_id: str) -> TeamTradeBrowser:
    team = next((item for item in league_state.teams if item.team_id == team_id), None)
    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team is None or team_state is None:
        raise ValueError("unknown team_id")

    players_by_id = {player.player_id: player for player in league_state.players}
    assets: list[TradeAssetOption] = []
    for entry in team_state.roster:
        player = players_by_id.get(entry.player_id)
        if player is None:
            continue
        assets.append(
            TradeAssetOption(
                asset_ref=f"player:{player.player_id}",
                asset_kind="player",
                label=player.full_name,
                detail=player.position.value,
                player_id=player.player_id,
                roster_slot=entry.slot,
            )
        )

    picks_by_id = {pick.pick_id: pick for pick in league_state.draft_picks}
    for ownership in league_state.pick_ownership:
        if ownership.owner_team_id != team_id:
            continue
        pick = picks_by_id.get(ownership.pick_id)
        if pick is None:
            continue
        original_team = next(
            (item.display_name for item in league_state.teams if item.team_id == pick.original_team_id),
            pick.original_team_id,
        )
        assets.append(
            TradeAssetOption(
                asset_ref=f"pick:{pick.pick_id}",
                asset_kind="pick",
                label=f"{pick.season} Round {pick.round}",
                detail=f"Originally {original_team}",
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
    """Expose only canonically owned assets for visual trade drafting."""

    focal = _team_browser(league_state, focal_team_id)
    counterparties = tuple(
        _team_browser(league_state, team.team_id)
        for team in sorted(league_state.teams, key=lambda item: (item.display_name, item.team_id))
        if team.team_id != focal_team_id
    )
    return TradeCenterBrowserView(
        focal_team=focal,
        counterparties=counterparties,
        state_id=league_state.state_id,
    )
