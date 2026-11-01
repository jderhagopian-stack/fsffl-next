"""Archived provider facts must never be promoted as historical model authority."""
from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from fsffl.state.retrospective_sleeper_replay import replay_archived_sleeper_trade


TRADE_MS = 1696187733375


def fixture(*, count=8, scoring=1, later_waiver=True):
    pick_origin = min(3, count)
    rosters = [
        {"roster_id": i, "players": (['player-b', 'waiver-p'] if later_waiver else ['player-b']) if i == 1
         else ['player-a'] if i == 2 else [],
         "settings": {"waiver_budget_used": 24 if later_waiver and i == 1 else 20 if i == 1 else 5 if i == 2 else 0}}
        for i in range(1, count+1)
    ]
    # 1 sends player-a, pick and $10; 2 sends player-b.
    trade = {"type": "trade", "status": "complete", "transaction_id": "tx",
             "created": TRADE_MS-3600000, "status_updated": TRADE_MS,
             "roster_ids": [1, 2], "adds": {"player-a": 2, "player-b": 1},
             "drops": {"player-a": 1, "player-b": 2},
             "draft_picks": [{"season": "2025", "round": 3, "roster_id": pick_origin,
                              "previous_owner_id": 1, "owner_id": 2}],
             "waiver_budget": [{"sender": 1, "receiver": 2, "amount": 10}]}
    waiver = {"type": "waiver", "status": "complete", "transaction_id": "later-waiver",
              "created": TRADE_MS+1000, "status_updated": TRADE_MS+2000,
              "roster_ids": [1], "adds": {"waiver-p": 1}, "drops": None,
              "settings": {"waiver_bid": 4}, "draft_picks": [], "waiver_budget": []}
    return {"league": {"league_id": f"year-{count}-{scoring}", "season": "2023",
                       "total_rosters": count, "roster_positions": ["QB", "WR", "SUPER_FLEX", "BN"],
                       "settings": {"waiver_budget": 100, "reserve_slots": 2},
                       "scoring_settings": {"fum_lost": scoring}},
            "rosters": rosters, "traded_picks": [
                {"season": "2025", "round": 3, "roster_id": pick_origin, "owner_id": 2}],
            "transactions": [trade, waiver] if later_waiver else [trade]}


@pytest.mark.parametrize("count", [2, 8, 12, 16])
def test_arbitrary_league_sizes_replay_with_readonly_fact_scope(count):
    d = fixture(count=count)
    result = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="immutable-commit")
    assert result.status == "provisionally_consistent"
    assert result.future_completed_events_reversed == 1
    assert result.observed_team_count == count
    assert result.eligible_for_pit_decision_grade is False
    assert result.historical_anchor_independently_verified is False
    assert len(result.transfers) == 3
    assert {(t.asset_kind, t.source_asset_id, t.before_roster_id, t.after_roster_id)
            for t in result.transfers} == {
               ("player", "player-a", "1", "2"), ("player", "player-b", "2", "1"),
               ("pick", f"2025:3:{min(3, count)}", "1", "2")}
    faab = {x.roster_id: x for x in result.faab}
    assert faab["1"].used_before == 10 and faab["1"].used_after == 20
    assert faab["2"].used_before == 15 and faab["2"].used_after == 5
    assert result.trade_created_at < result.trade_completed_at
    assert result.trade_completed_at == datetime.fromtimestamp(TRADE_MS/1000, tz=UTC)
    assert result.ownership_scope == "retrospective_ownership_snapshot_only"
    assert result.roster_slot_coverage == "unknown_at_trade_cutoff"
    before = {row.roster_id: row for row in result.before_ownership}
    after = {row.roster_id: row for row in result.after_ownership}
    assert len(before) == count and len(after) == count
    assert before["1"].player_ids == ("player-a",)
    assert before["2"].player_ids == ("player-b",)
    assert after["1"].player_ids == ("player-b",)
    assert after["2"].player_ids == ("player-a",)
    assert before["1"].pick_ids == (f"2025:3:{min(3, count)}",)
    assert after["2"].pick_ids == (f"2025:3:{min(3, count)}",)
    assert before["1"].faab_used == 10 and after["1"].faab_used == 20
    assert before["2"].faab_used == 15 and after["2"].faab_used == 5
    assert all(row.faab_used is None for row in result.before_ownership if row.roster_id not in {"1", "2"})
    assert all(row.faab_used is None for row in result.after_ownership if row.roster_id not in {"1", "2"})


def test_year_specific_scoring_changes_rules_hash_not_factual_transfer():
    a = replay_archived_sleeper_trade(fixture(scoring=0), transaction_id="tx", source_revision="s")
    b = replay_archived_sleeper_trade(fixture(scoring=5), transaction_id="tx", source_revision="s")
    assert a.league_rules_sha256 != b.league_rules_sha256
    assert a.transfers == b.transfers


def test_other_season_source_cannot_match_transaction_id_or_silent_asof():
    with pytest.raises(ValueError, match="unique completed source record"):
        replay_archived_sleeper_trade(fixture(), transaction_id="unknown", source_revision="s")
    d = fixture()
    d["transactions"][0]["status_updated"] = None
    with pytest.raises(ValueError, match="missing authoritative completion timestamp"):
        replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")


def test_end_roster_player_mismatch_blocks_not_promotes():
    d = fixture()
    d["rosters"][1]["players"] = ["not-player-a"]
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "trade_post_player_owner_mismatch" in r.issues


def test_end_pick_ownership_mismatch_blocks():
    d = fixture()
    d["traded_picks"][0]["owner_id"] = 1
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "trade_post_pick_owner_mismatch" in r.issues


def test_other_completed_roster_transaction_reverses_from_archive():
    d = fixture()
    del d["transactions"][1]["settings"]["waiver_bid"]
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "unverified_waiver_bid_or_roster" in r.issues


def test_faab_unsupported_or_invalid_evidence_blocks():
    d = fixture()
    d["rosters"][0]["settings"]["waiver_budget_used"] = 4
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "reconstructed_faab_balance_out_of_bounds" in r.issues


def test_duplicate_or_inconsistent_end_roster_is_not_accepted():
    d = fixture()
    d["rosters"][0]["players"].append('player-a')
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "end_anchor_duplicate_player_ownership" in r.issues


def test_tied_source_completion_time_fails_closed():
    d = fixture()
    d["transactions"][1]["status_updated"] = TRADE_MS
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "ambiguous_same_timestamp_as_trade" in r.issues


def test_input_is_immutable_and_replay_is_deterministic():
    d = fixture()
    saved = deepcopy(d)
    a = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="original-sha")
    b = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="original-sha")
    assert a == b and d == saved
    assert a.source_season_sha256 == b.source_season_sha256


def test_three_party_trade_is_not_bilateral_assumed():
    d = fixture()
    d["transactions"][0]["roster_ids"] = [1, 2, 3]
    r = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert r.status == "blocked" and "unsupported_trade_participants" in r.issues


def test_independent_tied_waiver_events_are_safe_to_reverse():
    d = fixture()
    another = {"type": "waiver", "status": "complete", "transaction_id": "other-claim",
               "created": TRADE_MS+1000, "status_updated": TRADE_MS+2000,
               "roster_ids": [2], "adds": {"another-claim-p": 2},
               "settings": {"waiver_bid": 1}}
    d["rosters"][1]["players"].append("another-claim-p")
    d["rosters"][1]["settings"]["waiver_budget_used"] += 1
    d["transactions"].append(another)
    x = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert x.status == "provisionally_consistent"


def test_tied_events_touching_same_player_block():
    d = fixture()
    later = {"type": "free_agent", "status": "complete", "transaction_id": "conflicting",
             "created": TRADE_MS+1000, "status_updated": TRADE_MS+2000,
             "roster_ids": [2], "adds": {"waiver-p": 2}, "drops": None}
    d["transactions"].append(later)
    x = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert x.status == "blocked" and "ambiguous_later_event_order" in x.issues


def test_pick_transfer_from_outside_trade_is_never_silently_accepted():
    d = fixture(count=8)
    d["transactions"][0]["draft_picks"][0]["previous_owner_id"] = 5
    x = replay_archived_sleeper_trade(d, transaction_id="tx", source_revision="s")
    assert x.status == "blocked" and "trade_pick_participants_mismatch" in x.issues
