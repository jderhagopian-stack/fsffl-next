from datetime import UTC, datetime

from fsffl.runtime.historical_trade_composition import (
    HistoricalTradeCompositionClass,
    classify_historical_trade_composition,
    prioritize_historical_trade_research_cases,
)
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset, Provenance


def provenance() -> Provenance:
    at = datetime(2024, 1, 1, tzinfo=UTC)
    return Provenance(source="test", retrieved_at=at, effective_at=at)


def record(transaction_id: str, left, right) -> HistoricalTradeRecord:
    return HistoricalTradeRecord(
        transaction_id=transaction_id,
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=tuple(left)),
            HistoricalTradeLeg(team_id="B", sends=tuple(right)),
        ),
        provenance=provenance(),
    )


def test_classifies_player_pick_faab_compositions_without_economics() -> None:
    player_only = classify_historical_trade_composition(
        record("p", (PlayerAsset(player_id="p1"),), (PlayerAsset(player_id="p2"),))
    )
    assert player_only.composition_class == HistoricalTradeCompositionClass.PLAYER_ONLY
    assert player_only.player_count == 2

    pick_only = classify_historical_trade_composition(
        record("k", (PickAsset(pick_id="k1"),), (PickAsset(pick_id="k2"), PickAsset(pick_id="k3")))
    )
    assert pick_only.composition_class == HistoricalTradeCompositionClass.PICK_ONLY
    assert pick_only.pick_count == 3

    mixed = classify_historical_trade_composition(
        record(
            "m",
            (PlayerAsset(player_id="p1"), FaabAsset(amount=10)),
            (PickAsset(pick_id="k1"),),
        )
    )
    assert mixed.composition_class == HistoricalTradeCompositionClass.MIXED
    assert mixed.faab_transfer_count == 1


def test_research_priority_is_generic_and_does_not_drop_complex_trades() -> None:
    rows = (
        record("mixed", (PlayerAsset(player_id="p1"), FaabAsset(amount=5)), (PickAsset(pick_id="k1"),)),
        record("pick", (PickAsset(pick_id="k2"),), (PickAsset(pick_id="k3"),)),
        record("player", (PlayerAsset(player_id="p2"),), (PlayerAsset(player_id="p3"),)),
    )
    profiles = prioritize_historical_trade_research_cases(rows)
    assert [row.transaction_id for row in profiles] == ["player", "pick", "mixed"]
    assert len(profiles) == len(rows)
