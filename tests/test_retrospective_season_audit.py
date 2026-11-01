"""Provider-edge historical ledger audit: intentionally not canonical PIT State."""
from __future__ import annotations
from copy import deepcopy
import pytest

from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season
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



def audit(d):
    return audit_retrospective_sleeper_season(d, source_revision="immutable-provider-snapshot")


@pytest.mark.parametrize("size", [2, 8, 12, 16])
def test_consistent_retro_archive_does_not_promote_historical_state(size):
    d=fixture(count=size)
    orig=deepcopy(d)
    a=audit(d)
    assert a.status=="retrospective_ledger_consistent"
    assert not a.issues
    assert a.team_count==size
    assert a.completed_events_examined==2
    assert a.completed_trades_examined==1
    assert a.player_movements_examined==5
    assert a.pick_movements_examined==1
    assert a.faab_transfers_examined==1
    assert a.waiver_bids_examined==1
    assert a.source_provides_contemporaneous_state is False
    assert a.eligible_for_pit_decision_grade is False
    assert a.historically_validated_faab_balances is False
    assert d == orig and a == audit(d)


def test_original_rule_drift_changes_digest_without_changing_facts():
    a=fixture(scoring=1)
    b=fixture(scoring=3)
    x=audit(a)
    y=audit(b)
    assert x.original_rules_sha256 != y.original_rules_sha256
    assert x.issues == y.issues


def test_missing_unrecorded_departure_detected_as_gap_not_invented_drop():
    d=fixture()
    d["rosters"][0]["players"].remove("waiver-p")
    x=audit(d)
    assert x.status=="incomplete_source_history"
    assert [v.code for v in x.issues]==["post_event_player_missing"]
    assert x.issues[0].transaction_id=="later-waiver"
    assert x.issues[0].event_type=="waiver"
    assert x.source_provides_contemporaneous_state is False


def test_incomplete_faab_claim_retains_explicit_uncertainty():
    d=fixture()
    del d["transactions"][1]["settings"]["waiver_bid"]
    x=audit(d)
    assert [i.code for i in x.issues]==["missing_waiver_bid_or_owner"]


def test_missing_end_pick_ledger_blocks_not_infers_pick():
    d=fixture()
    d["traded_picks"] = []
    x=audit(d)
    assert "missing_end_pick_anchor" in [i.code for i in x.issues]


def test_future_trade_creation_cannot_replace_completion_time():
    d=fixture()
    d["transactions"][0]["status_updated"] = None
    x=audit(d)
    assert x.completed_events_examined == 1
    assert "missing_completed_transaction_time" in [i.code for i in x.issues]
    assert x.completed_trades_examined == 0


def test_identical_timestamp_touching_disjoint_assets_not_ambiguous():
    d=fixture()
    other={"type":"free_agent","status":"complete", "transaction_id":"second",
           "created":TRADE_MS+1000, "status_updated": TRADE_MS+2000,
           "roster_ids":[2],"adds":{"unique-player":2}}
    d["transactions"].append(other)
    d["rosters"][1]["players"].append("unique-player")
    x=audit(d)
    assert x.completed_timestamp_tie_groups == 1
    assert not x.issues


def test_identical_timestamp_touching_same_asset_is_blocked():
    d=fixture()
    other={"type":"free_agent","status":"complete", "transaction_id":"second",
           "created":TRADE_MS+1000, "status_updated": TRADE_MS+2000,
           "roster_ids":[2],"adds":{"waiver-p":2}}
    d["transactions"].append(other)
    x=audit(d)
    assert "tied_completion_asset_overlap" in [i.code for i in x.issues]


def test_taxi_reserve_mismatch_not_treated_as_new_player_value():
    d=fixture()
    d["rosters"][0]["taxi"] = ["nonrostered"]
    x=audit(d)
    assert "end_anchor_taxi_not_in_players" in [i.code for i in x.issues]


def test_failed_provider_waiver_is_not_counted_as_completed():
    d=fixture()
    d["transactions"].append({"type":"waiver","status":"failed", "transaction_id":"bad", "adds":{"x":1}})
    assert audit(d).completed_events_examined==2


def test_duplicate_completed_event_never_silently_ignored():
    d=fixture()
    d["transactions"].append(deepcopy(d["transactions"][0]))
    codes=[i.code for i in audit(d).issues]
    assert "duplicate_completed_transaction_id" in codes
    assert "tied_completion_asset_overlap" in codes


def test_other_lease_or_rules_cannot_be_inferred_without_original_settings():
    d=fixture()
    del d["league"]["scoring_settings"]
    with pytest.raises(ValueError,match="season-specific rules"):
        audit(d)
