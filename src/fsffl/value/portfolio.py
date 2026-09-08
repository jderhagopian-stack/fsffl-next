from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueState

from .cardinal_authority import FSFFL_CARDINAL_SCALE, FSFFLCardinalValueScore
from .models import ValueAssetKind, ValueScale


class TeamCardinalPortfolio(FrozenModel):
    """Additive current market portfolio on the governed FSFFL Cardinal scale.

    This is a portfolio accounting view, not Team Utility or Decision authority.
    Owned player and pick scores may be summed because every included asset is on
    the exact same explicit Cardinal scale. Coverage remains visible so a partial
    portfolio is never mistaken for a complete team valuation.
    """

    team_id: str
    total_value: float | None = None
    player_value: float | None = None
    pick_value: float | None = None
    owned_player_count: int
    valued_player_count: int
    owned_pick_count: int
    valued_pick_count: int
    scale: ValueScale = FSFFL_CARDINAL_SCALE
    model_version: str = "next3-team-cardinal-portfolio-v1"

    @property
    def owned_asset_count(self) -> int:
        return self.owned_player_count + self.owned_pick_count

    @property
    def valued_asset_count(self) -> int:
        return self.valued_player_count + self.valued_pick_count

    @property
    def coverage(self) -> float:
        if self.owned_asset_count == 0:
            return 0.0
        return self.valued_asset_count / self.owned_asset_count

    @model_validator(mode="after")
    def validate_portfolio(self) -> "TeamCardinalPortfolio":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("team Cardinal portfolio identifiers cannot be blank")
        if self.scale != FSFFL_CARDINAL_SCALE:
            raise ValueError("team Cardinal portfolio must use the governed FSFFL Cardinal scale")
        counts = (
            self.owned_player_count,
            self.valued_player_count,
            self.owned_pick_count,
            self.valued_pick_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("team Cardinal portfolio counts cannot be negative")
        if self.valued_player_count > self.owned_player_count or self.valued_pick_count > self.owned_pick_count:
            raise ValueError("valued asset counts cannot exceed owned counts")
        if self.valued_asset_count == 0 and self.total_value is not None:
            raise ValueError("portfolio with no valued assets cannot expose a total")
        return self


def build_team_cardinal_portfolios(
    league_state: LeagueState,
    scores: tuple[FSFFLCardinalValueScore, ...],
) -> tuple[TeamCardinalPortfolio, ...]:
    score_by_asset = {row.asset_id: row for row in scores}
    team_state_by_id = {row.team_id: row for row in league_state.team_states}
    owned_picks_by_team: dict[str, list[str]] = {team.team_id: [] for team in league_state.teams}
    for ownership in league_state.pick_ownership:
        owned_picks_by_team.setdefault(ownership.owner_team_id, []).append(ownership.pick_id)

    portfolios: list[TeamCardinalPortfolio] = []
    for team in sorted(league_state.teams, key=lambda row: row.team_id):
        team_state = team_state_by_id.get(team.team_id)
        player_ids = [entry.player_id for entry in team_state.roster] if team_state is not None else []
        pick_ids = owned_picks_by_team.get(team.team_id, [])
        valued_players = [
            score_by_asset[player_id].score
            for player_id in player_ids
            if player_id in score_by_asset and score_by_asset[player_id].asset_kind == ValueAssetKind.PLAYER
        ]
        valued_picks = [
            score_by_asset[pick_id].score
            for pick_id in pick_ids
            if pick_id in score_by_asset and score_by_asset[pick_id].asset_kind == ValueAssetKind.PICK
        ]
        player_value = sum(valued_players) if valued_players else None
        pick_value = sum(valued_picks) if valued_picks else (0.0 if not pick_ids else None)
        valued_total = valued_players + valued_picks
        portfolios.append(
            TeamCardinalPortfolio(
                team_id=team.team_id,
                total_value=sum(valued_total) if valued_total else None,
                player_value=player_value,
                pick_value=pick_value,
                owned_player_count=len(player_ids),
                valued_player_count=len(valued_players),
                owned_pick_count=len(pick_ids),
                valued_pick_count=len(valued_picks),
            )
        )
    return tuple(portfolios)
