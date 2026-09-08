from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueState

from .cardinal_authority import FSFFL_CARDINAL_SCALE, FSFFLCardinalValueScore
from .models import MarketPriceEstimate, ValueAssetKind, ValueScale


class PortfolioCoverageStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class TeamMarketValuePortfolio(FrozenModel):
    """Team accounting over an explicitly promoted additive Market Value scale.

    Market Percentile is deliberately not additive. A team Market Value total may
    be exposed only when Value authority explicitly supplies a compatible additive
    market scale. Missing authority or missing assets remain visible instead of
    being filled from Cardinal, Intrinsic, or Presentation-side arithmetic.
    """

    team_id: str
    total_value: float | None = None
    player_value: float | None = None
    pick_value: float | None = None
    owned_player_count: int
    valued_player_count: int
    owned_pick_count: int
    valued_pick_count: int
    scale: ValueScale | None = None
    market_context_id: str | None = None
    as_of: datetime | None = None
    availability_reason: str | None = None
    model_version: str = "next3-team-market-portfolio-v2"

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

    @property
    def coverage_status(self) -> PortfolioCoverageStatus:
        if self.valued_asset_count == 0:
            return PortfolioCoverageStatus.UNAVAILABLE
        if self.valued_asset_count == self.owned_asset_count:
            return PortfolioCoverageStatus.COMPLETE
        return PortfolioCoverageStatus.PARTIAL

    @model_validator(mode="after")
    def validate_portfolio(self) -> "TeamMarketValuePortfolio":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("team Market Value portfolio identifiers cannot be blank")
        counts = (
            self.owned_player_count,
            self.valued_player_count,
            self.owned_pick_count,
            self.valued_pick_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("team Market Value portfolio counts cannot be negative")
        if self.valued_player_count > self.owned_player_count or self.valued_pick_count > self.owned_pick_count:
            raise ValueError("valued asset counts cannot exceed owned counts")
        if self.availability_reason is not None and not self.availability_reason.strip():
            raise ValueError("team Market Value availability reason cannot be blank")
        if self.valued_asset_count == 0:
            if any(value is not None for value in (self.total_value, self.player_value, self.pick_value)):
                raise ValueError("portfolio with no valued assets cannot expose market totals")
            if any(value is not None for value in (self.scale, self.market_context_id, self.as_of)):
                raise ValueError("portfolio with no valued assets cannot claim a market snapshot")
            if self.owned_asset_count > 0 and self.availability_reason is None:
                raise ValueError("unavailable team Market Value requires an explicit reason")
        else:
            if self.total_value is None or self.scale is None or self.market_context_id is None or self.as_of is None:
                raise ValueError("valued market portfolio requires total, scale, context, and as_of")
            if not self.market_context_id.strip():
                raise ValueError("team Market Value portfolio context cannot be blank")
        return self


class TeamCardinalPortfolio(FrozenModel):
    """Additive current market-cardinal portfolio on the FSFFL Cardinal scale.

    This is a Value-layer portfolio accounting view, not Team Utility or Decision
    authority. It must remain labeled separately from external/ensemble Market
    Value in product presentation even though both live in the Value layer.
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


def _owned_asset_ids(league_state: LeagueState) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    team_state_by_id = {row.team_id: row for row in league_state.team_states}
    players_by_team: dict[str, list[str]] = {}
    picks_by_team: dict[str, list[str]] = {team.team_id: [] for team in league_state.teams}
    for team in league_state.teams:
        team_state = team_state_by_id.get(team.team_id)
        players_by_team[team.team_id] = (
            [entry.player_id for entry in team_state.roster]
            if team_state is not None
            else []
        )
    for ownership in league_state.pick_ownership:
        picks_by_team.setdefault(ownership.owner_team_id, []).append(ownership.pick_id)
    return players_by_team, picks_by_team


def build_team_market_value_portfolios(
    league_state: LeagueState,
    estimates: tuple[MarketPriceEstimate, ...],
    *,
    additive_scale: ValueScale | None,
    unavailable_reason: str = (
        "No separate additive Market Value scale is promoted. Current market estimates "
        "are relative Market Percentiles and cannot be summed."
    ),
) -> tuple[TeamMarketValuePortfolio, ...]:
    """Aggregate Market Value only after Value authority promotes an additive scale.

    Merely sharing a ValueScale is insufficient: percentile/rank scales can be
    mutually compatible yet still be non-additive. The caller must explicitly
    supply the promoted additive scale. Passing ``None`` fails closed and returns
    typed unavailable portfolios with ownership coverage and a reason.
    """

    owned_players_by_team, owned_picks_by_team = _owned_asset_ids(league_state)
    if additive_scale is None:
        return tuple(
            TeamMarketValuePortfolio(
                team_id=team.team_id,
                owned_player_count=len(owned_players_by_team.get(team.team_id, [])),
                valued_player_count=0,
                owned_pick_count=len(owned_picks_by_team.get(team.team_id, [])),
                valued_pick_count=0,
                availability_reason=unavailable_reason,
            )
            for team in sorted(league_state.teams, key=lambda row: row.team_id)
        )

    asset_ids = [row.asset_id for row in estimates]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("team Market Value portfolios require unique asset estimates")
    if any(row.scale != additive_scale for row in estimates):
        raise ValueError("team Market Value portfolios require the explicitly promoted additive scale")

    if estimates:
        contexts = {row.market_context_id for row in estimates}
        snapshots = {row.as_of for row in estimates}
        if len(contexts) != 1:
            raise ValueError("team Market Value portfolios cannot mix market contexts")
        if len(snapshots) != 1:
            raise ValueError("team Market Value portfolios cannot mix as-of snapshots")
        market_context_id = next(iter(contexts))
        as_of = next(iter(snapshots))
    else:
        market_context_id = None
        as_of = None

    estimate_by_asset = {row.asset_id: row for row in estimates}
    portfolios: list[TeamMarketValuePortfolio] = []
    for team in sorted(league_state.teams, key=lambda row: row.team_id):
        player_ids = owned_players_by_team.get(team.team_id, [])
        pick_ids = owned_picks_by_team.get(team.team_id, [])
        valued_players = [
            estimate_by_asset[player_id].distribution.mean
            for player_id in player_ids
            if player_id in estimate_by_asset
            and estimate_by_asset[player_id].asset_kind == ValueAssetKind.PLAYER
        ]
        valued_picks = [
            estimate_by_asset[pick_id].distribution.mean
            for pick_id in pick_ids
            if pick_id in estimate_by_asset
            and estimate_by_asset[pick_id].asset_kind == ValueAssetKind.PICK
        ]
        valued_total = valued_players + valued_picks
        missing_assets = len(player_ids) + len(pick_ids) - len(valued_total)
        portfolios.append(
            TeamMarketValuePortfolio(
                team_id=team.team_id,
                total_value=sum(valued_total) if valued_total else None,
                player_value=sum(valued_players) if valued_players else None,
                pick_value=sum(valued_picks) if valued_picks else (0.0 if not pick_ids and valued_total else None),
                owned_player_count=len(player_ids),
                valued_player_count=len(valued_players),
                owned_pick_count=len(pick_ids),
                valued_pick_count=len(valued_picks),
                scale=additive_scale if valued_total else None,
                market_context_id=market_context_id if valued_total else None,
                as_of=as_of if valued_total else None,
                availability_reason=(
                    f"{missing_assets} owned asset(s) lack a compatible additive Market Value estimate."
                    if missing_assets > 0
                    else None
                ),
            )
        )
    return tuple(portfolios)


def build_team_cardinal_portfolios(
    league_state: LeagueState,
    scores: tuple[FSFFLCardinalValueScore, ...],
) -> tuple[TeamCardinalPortfolio, ...]:
    """Sum only one coherent Cardinal context into team portfolio accounting."""

    asset_ids = [row.asset_id for row in scores]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("team Cardinal portfolios require unique asset scores")
    contexts = {row.market_context_id for row in scores}
    if len(contexts) > 1:
        raise ValueError("team Cardinal portfolios cannot mix market contexts")
    if any(row.scale != FSFFL_CARDINAL_SCALE for row in scores):
        raise ValueError("team Cardinal portfolios require the governed Cardinal scale")

    score_by_asset = {row.asset_id: row for row in scores}
    owned_players_by_team, owned_picks_by_team = _owned_asset_ids(league_state)

    portfolios: list[TeamCardinalPortfolio] = []
    for team in sorted(league_state.teams, key=lambda row: row.team_id):
        player_ids = owned_players_by_team.get(team.team_id, [])
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
