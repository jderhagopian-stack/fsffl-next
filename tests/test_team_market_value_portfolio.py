from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    PickOwnership,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.models import MarketPriceEstimate, ValueAssetKind, ValueDistribution, ValueScale
from fsffl.value.portfolio import PortfolioCoverageStatus, build_team_market_value_portfolios


def _state(as_of: datetime) -> LeagueState:
    league_id = "league:test"
    provenance = Provenance(source="test", retrieved_at=as_of, effective_at=as_of)
    players = (
        Player(player_id="p1", full_name="Alpha QB", position=Position.QB),
        Player(player_id="p2", full_name="Beta RB", position=Position.RB),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Test League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                rookie_draft_rounds=1,
                lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
                scoring=(ScoringRule(stat="rec", points=0.5),),
            ),
        ),
        as_of=as_of,
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(
            TeamState(team_id="t1", roster=(RosterEntry(player_id="p1", slot=RosterSlot.QB),)),
            TeamState(team_id="t2", roster=(RosterEntry(player_id="p2", slot=RosterSlot.RB),)),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=as_of,
                status=PlayerStatus.ACTIVE,
                provenance=provenance,
            )
            for player in players
        ),
        draft_picks=(
            DraftPick(
                pick_id="pick-2027-r1-t1",
                league_id=league_id,
                season=2027,
                round=1,
                original_team_id="t1",
            ),
        ),
        pick_ownership=(PickOwnership(pick_id="pick-2027-r1-t1", owner_team_id="t1"),),
        provenance=(provenance,),
    )


def _estimate(
    *,
    asset_id: str,
    asset_kind: ValueAssetKind,
    value: float,
    as_of: datetime,
    scale: ValueScale,
) -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id=asset_id,
        asset_kind=asset_kind,
        distribution=ValueDistribution(mean=value),
        scale=scale,
        as_of=as_of,
        market_context_id="dynasty:2t:sf:0.5ppr",
        model_version="test-market-v1",
    )


def test_team_market_portfolio_exposes_partial_pick_coverage_without_cross_scale_fill() -> None:
    now = datetime.now(UTC)
    state = _state(now)
    scale = ValueScale(
        scale_id="dynasty-market-percentile",
        version="next3-v1",
        unit_label="market percentile",
    )
    portfolios = build_team_market_value_portfolios(
        state,
        (
            _estimate(asset_id="p1", asset_kind=ValueAssetKind.PLAYER, value=0.8, as_of=now, scale=scale),
            _estimate(asset_id="p2", asset_kind=ValueAssetKind.PLAYER, value=0.4, as_of=now, scale=scale),
        ),
    )
    by_team = {row.team_id: row for row in portfolios}

    assert by_team["t1"].total_value == pytest.approx(0.8)
    assert by_team["t1"].player_value == pytest.approx(0.8)
    assert by_team["t1"].pick_value is None
    assert by_team["t1"].coverage == pytest.approx(0.5)
    assert by_team["t1"].coverage_status == PortfolioCoverageStatus.PARTIAL
    assert by_team["t1"].scale == scale

    assert by_team["t2"].total_value == pytest.approx(0.4)
    assert by_team["t2"].pick_value == pytest.approx(0.0)
    assert by_team["t2"].coverage == pytest.approx(1.0)
    assert by_team["t2"].coverage_status == PortfolioCoverageStatus.COMPLETE


def test_team_market_portfolio_includes_pick_only_on_same_market_scale() -> None:
    now = datetime.now(UTC)
    state = _state(now)
    scale = ValueScale(scale_id="market-index", version="v1", unit_label="market units")
    portfolios = build_team_market_value_portfolios(
        state,
        (
            _estimate(asset_id="p1", asset_kind=ValueAssetKind.PLAYER, value=80.0, as_of=now, scale=scale),
            _estimate(asset_id="p2", asset_kind=ValueAssetKind.PLAYER, value=40.0, as_of=now, scale=scale),
            _estimate(
                asset_id="pick-2027-r1-t1",
                asset_kind=ValueAssetKind.PICK,
                value=30.0,
                as_of=now,
                scale=scale,
            ),
        ),
    )
    t1 = next(row for row in portfolios if row.team_id == "t1")

    assert t1.total_value == pytest.approx(110.0)
    assert t1.player_value == pytest.approx(80.0)
    assert t1.pick_value == pytest.approx(30.0)
    assert t1.coverage == pytest.approx(1.0)
    assert t1.coverage_status == PortfolioCoverageStatus.COMPLETE


def test_team_market_portfolio_rejects_mixed_value_scales() -> None:
    now = datetime.now(UTC)
    state = _state(now)
    scale_a = ValueScale(scale_id="market-index", version="v1", unit_label="market units")
    scale_b = ValueScale(scale_id="market-index", version="v2", unit_label="market units")

    with pytest.raises(ValueError, match="cannot mix ValueScale versions"):
        build_team_market_value_portfolios(
            state,
            (
                _estimate(asset_id="p1", asset_kind=ValueAssetKind.PLAYER, value=80.0, as_of=now, scale=scale_a),
                _estimate(asset_id="p2", asset_kind=ValueAssetKind.PLAYER, value=40.0, as_of=now, scale=scale_b),
            ),
        )
