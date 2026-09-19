from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.historical_trade import HistoricalTradeRecord
from fsffl.state.models import FaabAsset, FrozenModel, PickAsset, PlayerAsset


class HistoricalTradeCompositionClass(StrEnum):
    PLAYER_ONLY = "player_only"
    PICK_ONLY = "pick_only"
    FAAB_ONLY = "faab_only"
    PLAYERS_AND_PICKS = "players_and_picks"
    PLAYERS_AND_FAAB = "players_and_faab"
    PICKS_AND_FAAB = "picks_and_faab"
    MIXED = "mixed"


class HistoricalTradeComposition(FrozenModel):
    transaction_id: str
    team_count: int
    player_count: int
    pick_count: int
    faab_transfer_count: int
    composition_class: HistoricalTradeCompositionClass

    @model_validator(mode="after")
    def validate_counts(self) -> "HistoricalTradeComposition":
        if not self.transaction_id.strip():
            raise ValueError("historical trade composition transaction_id cannot be blank")
        if self.team_count < 2:
            raise ValueError("historical trade composition requires at least two teams")
        if min(self.player_count, self.pick_count, self.faab_transfer_count) < 0:
            raise ValueError("historical trade composition counts cannot be negative")
        if self.player_count + self.pick_count + self.faab_transfer_count <= 0:
            raise ValueError("historical trade composition requires at least one asset")
        return self


def classify_historical_trade_composition(record: HistoricalTradeRecord) -> HistoricalTradeComposition:
    """Profile asset families without assigning value, quality, or recommendation.

    This generic Runtime helper lets batch orchestration prioritize clean research
    cases (for example player-only or pick-only) for any league. It does not decide
    whether FAAB is incidental, infer economics, or exclude any trade.
    """

    players = 0
    picks = 0
    faab = 0
    for leg in record.legs:
        for asset in leg.sends:
            if isinstance(asset, PlayerAsset):
                players += 1
            elif isinstance(asset, PickAsset):
                picks += 1
            elif isinstance(asset, FaabAsset):
                faab += 1
            else:
                raise TypeError(f"unsupported historical trade asset type: {type(asset).__name__}")

    present = (players > 0, picks > 0, faab > 0)
    composition = {
        (True, False, False): HistoricalTradeCompositionClass.PLAYER_ONLY,
        (False, True, False): HistoricalTradeCompositionClass.PICK_ONLY,
        (False, False, True): HistoricalTradeCompositionClass.FAAB_ONLY,
        (True, True, False): HistoricalTradeCompositionClass.PLAYERS_AND_PICKS,
        (True, False, True): HistoricalTradeCompositionClass.PLAYERS_AND_FAAB,
        (False, True, True): HistoricalTradeCompositionClass.PICKS_AND_FAAB,
        (True, True, True): HistoricalTradeCompositionClass.MIXED,
    }[present]

    return HistoricalTradeComposition(
        transaction_id=record.transaction_id,
        team_count=len(record.legs),
        player_count=players,
        pick_count=picks,
        faab_transfer_count=faab,
        composition_class=composition,
    )


def prioritize_historical_trade_research_cases(
    records: tuple[HistoricalTradeRecord, ...],
) -> tuple[HistoricalTradeComposition, ...]:
    """Return deterministic composition profiles ordered from simpler to mixed.

    Ordering is an orchestration convenience only. It never changes eligibility,
    evidence requirements, valuation, or grading authority.
    """

    priority = {
        HistoricalTradeCompositionClass.PLAYER_ONLY: 0,
        HistoricalTradeCompositionClass.PICK_ONLY: 1,
        HistoricalTradeCompositionClass.PLAYERS_AND_PICKS: 2,
        HistoricalTradeCompositionClass.PLAYERS_AND_FAAB: 3,
        HistoricalTradeCompositionClass.PICKS_AND_FAAB: 4,
        HistoricalTradeCompositionClass.FAAB_ONLY: 5,
        HistoricalTradeCompositionClass.MIXED: 6,
    }
    profiles = tuple(classify_historical_trade_composition(record) for record in records)
    return tuple(sorted(profiles, key=lambda row: (priority[row.composition_class], row.transaction_id)))
