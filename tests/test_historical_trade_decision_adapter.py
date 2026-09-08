from datetime import UTC, datetime

import pytest

from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import PickAsset, PlayerAsset, Provenance
from fsffl.trade_decision.historical import proposal_from_historical_trade


def provenance() -> Provenance:
    when = datetime(2025, 10, 1, tzinfo=UTC)
    return Provenance(source="fixture", retrieved_at=when, effective_at=when)


def test_historical_trade_reuses_bilateral_decision_proposal_contract():
    record = HistoricalTradeRecord(
        transaction_id="tx-1",
        league_id="league-x",
        completed_at=datetime(2025, 10, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(
                team_id="team-a",
                sends=(PlayerAsset(player_id="player-a"), PickAsset(pick_id="pick-a")),
            ),
            HistoricalTradeLeg(
                team_id="team-b",
                sends=(PlayerAsset(player_id="player-b"),),
            ),
        ),
        provenance=provenance(),
    )

    proposal = proposal_from_historical_trade(record)

    assert proposal.proposal_id == "tx-1"
    assert proposal.as_of == record.completed_at
    assert proposal.side_a.team_id == "team-a"
    assert proposal.side_a.sends == record.legs[0].sends
    assert proposal.side_b.team_id == "team-b"
    assert proposal.side_b.sends == record.legs[1].sends


def test_multi_team_historical_trade_is_not_silently_reduced_to_bilateral_pairs():
    record = HistoricalTradeRecord(
        transaction_id="tx-3way",
        league_id="league-x",
        completed_at=datetime(2025, 10, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="team-a", sends=(PlayerAsset(player_id="a"),)),
            HistoricalTradeLeg(team_id="team-b", sends=(PlayerAsset(player_id="b"),)),
            HistoricalTradeLeg(team_id="team-c", sends=(PlayerAsset(player_id="c"),)),
        ),
        provenance=provenance(),
    )

    with pytest.raises(ValueError, match="exactly two-team"):
        proposal_from_historical_trade(record)
