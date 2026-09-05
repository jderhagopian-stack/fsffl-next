from datetime import UTC, datetime

from fsffl.value.transaction_evidence import normalize_sleeper_one_for_one_trades


AS_OF = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def test_imports_only_clean_one_for_one_player_trade() -> None:
    payload = '''
    [
      {
        "type": "trade",
        "status": "complete",
        "transaction_id": "t1",
        "status_updated": 1788600000000,
        "roster_ids": [2, 1],
        "adds": {"p1": 2, "p2": 1},
        "draft_picks": [],
        "waiver_budget": [],
        "creator": "u1"
      },
      {
        "type": "trade",
        "status": "complete",
        "transaction_id": "package",
        "status_updated": 1788600000000,
        "roster_ids": [1, 2],
        "adds": {"p1": 2, "p2": 1},
        "draft_picks": [{"season": "2027", "round": 1}],
        "waiver_budget": []
      }
    ]
    '''
    result = normalize_sleeper_one_for_one_trades(
        payload,
        league_id="league-1",
        format_context_id="dynasty:sf:12:half",
        asset_id_by_sleeper_id={"p1": "player:1", "p2": "player:2"},
        as_of=AS_OF,
    )

    assert result.transactions_seen == 2
    assert result.completed_trades_seen == 2
    assert result.imported == 1
    assert result.skipped_non_one_for_one == 1
    trade = result.observations[0]
    assert trade.transaction_id == "t1"
    assert trade.format_context_id == "dynasty:sf:12:half"
    assert trade.roster_a_id == 1
    assert trade.asset_a_id == "player:2"
    assert trade.roster_b_id == 2
    assert trade.asset_b_id == "player:1"


def test_skips_trade_if_either_player_identity_is_unmapped() -> None:
    payload = '''
    [{
      "type": "trade",
      "status": "complete",
      "transaction_id": "t1",
      "status_updated": 1788600000000,
      "roster_ids": [1, 2],
      "adds": {"p1": 2, "missing": 1},
      "draft_picks": [],
      "waiver_budget": []
    }]
    '''
    result = normalize_sleeper_one_for_one_trades(
        payload,
        league_id="league-1",
        format_context_id="dynasty:sf",
        asset_id_by_sleeper_id={"p1": "player:1"},
        as_of=AS_OF,
    )
    assert result.imported == 0
    assert result.skipped_unmapped == 1
