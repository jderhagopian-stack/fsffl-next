from datetime import UTC, datetime
import json

import pytest

from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    Team,
    TeamState,
)
from fsffl.value.cardinal_authority import (
    FSFFLCardinalValueScore,
    build_authoritative_pick_scores_from_trade_evaluation,
)
from fsffl.value.models import ValueAssetKind
from fsffl.value.portfolio import build_team_cardinal_portfolios


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
SF_CONTEXT = "dynasty:12t:sf:0.5ppr"


def _pick() -> DraftPick:
    return DraftPick(
        pick_id="canonical-pick",
        league_id="league",
        season=2027,
        round=1,
        original_team_id="team-a",
    )


def test_trade_evaluation_pick_requires_sf_response_format_for_sf_context() -> None:
    payload = {
        "format": "sf_dynasty",
        "asOf": NOW.isoformat(),
        "sideA": {
            "assets": [
                {"id": "pick:2027:1", "type": "pick", "found": True, "value": 3100},
            ]
        },
        "sideB": {"assets": []},
    }
    scores = build_authoritative_pick_scores_from_trade_evaluation(
        json.dumps(payload),
        draft_picks=(_pick(),),
        market_context_id=SF_CONTEXT,
        retrieved_at=NOW,
    )
    assert scores[0].score == 3100
    assert scores[0].market_context_id == SF_CONTEXT


def test_trade_evaluation_pick_rejects_1qb_response_for_sf_context() -> None:
    payload = {
        "format": "non_sf_dynasty",
        "asOf": NOW.isoformat(),
        "sideA": {
            "assets": [
                {"id": "pick:2027:1", "type": "pick", "found": True, "value": 2100},
            ]
        },
        "sideB": {"assets": []},
    }
    with pytest.raises(ValueError, match="format does not match market context"):
        build_authoritative_pick_scores_from_trade_evaluation(
            json.dumps(payload),
            draft_picks=(_pick(),),
            market_context_id=SF_CONTEXT,
            retrieved_at=NOW,
        )


def _empty_state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id="league",
            name="League",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="team-a", league_id="league", display_name="A"),
            Team(team_id="team-b", league_id="league", display_name="B"),
        ),
        team_states=(
            TeamState(team_id="team-a", roster=()),
            TeamState(team_id="team-b", roster=()),
        ),
    )


def test_team_portfolio_refuses_mixed_market_contexts_even_on_same_scale() -> None:
    scores = (
        FSFFLCardinalValueScore(
            asset_id="p1",
            asset_kind=ValueAssetKind.PLAYER,
            score=5000,
            as_of=NOW,
            market_context_id=SF_CONTEXT,
        ),
        FSFFLCardinalValueScore(
            asset_id="p2",
            asset_kind=ValueAssetKind.PLAYER,
            score=5000,
            as_of=NOW,
            market_context_id="dynasty:12t:1qb:0.5ppr",
        ),
    )
    with pytest.raises(ValueError, match="cannot mix market contexts"):
        build_team_cardinal_portfolios(_empty_state(), scores)
