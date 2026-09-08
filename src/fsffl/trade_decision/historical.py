from __future__ import annotations

from fsffl.state.historical_trade import HistoricalTradeRecord

from .models import BilateralTradeProposal, TradeLeg


def proposal_from_historical_trade(
    record: HistoricalTradeRecord,
    *,
    model_version: str = "next5-historical-trade-proposal-v1",
) -> BilateralTradeProposal:
    """Bind a reconstructed two-team trade to the authoritative Decision contract.

    This adapter performs no valuation, grading, hindsight adjustment, package
    decomposition, or team-utility computation. It only preserves the completed
    historical package as a BilateralTradeProposal at the original timestamp.
    Multi-team trades fail explicitly because NEXT-5's current proposal contract
    is bilateral; support for multi-team decision evaluation requires a governed
    extension rather than silent reduction to pairs.
    """

    if len(record.legs) != 2:
        raise ValueError("historical Decision adapter currently supports exactly two-team trades")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    side_a, side_b = record.legs
    return BilateralTradeProposal(
        proposal_id=record.transaction_id,
        as_of=record.completed_at,
        side_a=TradeLeg(team_id=side_a.team_id, sends=side_a.sends),
        side_b=TradeLeg(team_id=side_b.team_id, sends=side_b.sends),
        model_version=model_version,
    )
