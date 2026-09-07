from datetime import UTC, datetime

import pytest

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.trade_decision import AcceptanceEvidenceKind, AcceptanceModelStatus, bind_owner_behavior_evidence
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg


NOW = datetime(2026, 9, 6, tzinfo=UTC)


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="proposal:behavior",
        as_of=NOW,
        side_a=TradeLeg(team_id="team:a", player_ids=("player:a",)),
        side_b=TradeLeg(team_id="team:b", player_ids=("player:b",)),
    )


def _profile(as_of: datetime = NOW) -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="sleeper-family:test",
        owner_id="owner:b",
        as_of=as_of,
        first_observed_at=datetime(2024, 1, 1, tzinfo=UTC),
        event_count=12,
        trade_count=5,
        waiver_count=4,
        free_agent_count=3,
        acquired_player_count=8,
        disposed_player_count=7,
        acquired_pick_count=2,
        disposed_pick_count=1,
        consolidation_trade_count=2,
        diversification_trade_count=1,
        balanced_trade_count=2,
        acquired_positions={"RB": 4, "WR": 4},
        disposed_positions={"RB": 3, "WR": 4},
        seasons_observed=(2024, 2025, 2026),
    )


def test_owner_profile_binds_as_unestimated_behavioral_evidence() -> None:
    view = bind_owner_behavior_evidence(
        _proposal(), accepting_team_id="team:b", profile=_profile()
    )
    assert view.status == AcceptanceModelStatus.NOT_ESTIMATED
    assert view.estimate is None
    assert len(view.evidence.items) == 1
    item = view.evidence.items[0]
    assert item.kind == AcceptanceEvidenceKind.OWNER_BEHAVIOR
    assert "5 completed trades" in item.description
    assert "2 consolidation" in item.description
    assert view.evidence.counterparty_team_id == "team:b"


def test_owner_behavior_binding_rejects_future_profile() -> None:
    future = datetime(2026, 9, 7, tzinfo=UTC)
    with pytest.raises(ValueError, match="after proposal cutoff"):
        bind_owner_behavior_evidence(
            _proposal(), accepting_team_id="team:b", profile=_profile(future)
        )
