from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.historical_pick_inventory import (
    HistoricalPickRight, HistoricalPickTransferEvent, HistoricalPickUse,
    build_historical_pick_inventory,
    enumerate_round_pick_allotment,
)
from fsffl.state.historical_roster_replay import DraftPickTransfer
from fsffl.providers.sleeper_historical_pick_inventory import (
    inspect_sleeper_draft_pick_coverage, normalize_sleeper_historical_pick_inventory,
    sleeper_linear_draft_allotment,
)

T = datetime(2024, 5, 1, tzinfo=UTC)


def right(pid="p", owner="a", issued=T-timedelta(days=30)):
    return HistoricalPickRight(pid, 2024, 1, owner, "rules-receipt", issued, issued)


def inventory(*, rights=None, events=(), uses=(), complete=True, uncertain=()):
    return build_historical_pick_inventory(team_ids=("a", "b", "c"),
        rights=rights if rights is not None else (right(),), events=events, uses=uses,
        declared_draft_seasons=(2024,), scope_source_ref="complete-allotment-receipt",
        coverage_through=T+timedelta(days=30),
        transfer_ledger_complete=complete, uncertain_pick_ids=uncertain, use_ledger_complete=True)


def test_untraded_rights_and_issuance_are_present_without_any_transactions():
    model = inventory(rights=(right(), right("untraded", "b")))
    assert model.at(T).known_outstanding_owners == (("p", "a"), ("untraded", "b"))
    assert model.at(T-timedelta(days=31)).picks[0].status == "not_issued"
    assert model.at(T).complete_for_declared_seasons is True


def test_transfer_then_selection_and_exact_cutoff_boundaries():
    event = HistoricalPickTransferEvent("trade", T, (DraftPickTransfer("p", "a", "b"),), "tx")
    use = HistoricalPickUse("p", "b", "selection", T+timedelta(days=2), T+timedelta(days=2))
    model = inventory(events=(event,), uses=(use,))
    assert model.at(T, boundary="before").known_outstanding_owners == (("p", "a"),)
    assert model.at(T).known_outstanding_owners == (("p", "b"),)
    assert model.at(use.by, boundary="before").picks[0].status == "outstanding"
    assert model.at(use.by).picks[0].status == "used"
    assert model.at(use.by).known_outstanding_owners == ()


def test_bounded_draft_use_does_not_invent_per_selection_timestamps():
    use = HistoricalPickUse("p", "a", "draft", T, T+timedelta(days=4))
    model = inventory(uses=(use,))
    assert model.at(T-timedelta(seconds=1)).picks[0].status == "outstanding"
    assert model.at(T+timedelta(days=1)).picks[0].status == "unknown"
    assert model.at(T+timedelta(days=4)).picks[0].status == "used"
    assert model.at(T+timedelta(days=1)).complete_for_declared_seasons is False


def test_missing_issuance_is_unknown_until_observed_transfer_proves_existence():
    event = HistoricalPickTransferEvent("trade", T, (DraftPickTransfer("p", "a", "b"),), "tx")
    model = inventory(rights=(right(issued=None),), events=(event,))
    assert model.at(T-timedelta(days=1)).picks[0].status == "unknown"
    assert model.at(T).known_outstanding_owners == (("p", "b"),)


def test_conflicting_same_time_batch_is_atomic_and_other_rights_remain_usable():
    events = tuple(HistoricalPickTransferEvent(str(i), T, (DraftPickTransfer("p", owner, "b"),), "tx")
                   for i, owner in enumerate(("a", "c")))
    model = inventory(rights=(right(), right("other", "c")), events=events)
    snapshot = model.at(T)
    assert "ambiguous_same_timestamp_pick_order" in snapshot.issues
    assert snapshot.known_outstanding_owners == (("other", "c"),)
    assert snapshot.complete_for_declared_seasons is False


def test_transfer_after_known_use_and_wrong_use_owner_are_conflicts():
    use = HistoricalPickUse("p", "a", "draft", T, T)
    event = HistoricalPickTransferEvent("late", T+timedelta(days=1), (DraftPickTransfer("p", "a", "b"),), "tx")
    assert inventory(uses=(use,), events=(event,)).at(T+timedelta(days=2)).picks[0].status == "conflict"
    wrong = HistoricalPickUse("p", "b", "draft", T, T)
    assert "pick_use_owner_mismatch" in inventory(uses=(wrong,)).at(T).issues


def test_incomplete_ledger_never_certifies_conditional_ownership():
    snapshot = inventory(complete=False).at(T)
    assert snapshot.picks[0].owner_team_id == "a"
    assert snapshot.transfer_ledger_complete is False
    assert snapshot.known_outstanding_owners == ()
    assert snapshot.complete_for_declared_seasons is False


def test_unknown_use_is_scoped_and_identity_binds_bounds_and_source():
    base = inventory(rights=(right(), right("other", "b")), uncertain=("p",))
    assert base.at(T).picks[1].status == "unknown"  # sorted IDs: other, p
    assert base.at(T).known_outstanding_owners == (("other", "b"),)
    assert inventory().inventory_id == inventory().inventory_id
    assert inventory(rights=(right(issued=T),)).inventory_id != inventory().inventory_id
    with pytest.raises(ValueError, match="duplicate"):
        inventory(rights=(right(), right()))
    with pytest.raises(ValueError, match="timezone"):
        inventory().at(datetime(2024, 1, 1))


def season(teams=4, rounds=6):
    ms = lambda t: int(t.timestamp()*1000)
    return {"league": {"season": "2024"},
        "rosters": [{"roster_id": str(i), "owner_id": f"u{i}"} for i in range(1, teams+1)],
        "transactions": [], "drafts": [{"draft": {"draft_id": "d", "season": "2024",
            "type": "linear", "status": "complete", "start_time": ms(T),
            "last_picked": ms(T+timedelta(days=2)), "settings": {"teams": teams, "rounds": rounds},
            "draft_order": {f"u{i}": i for i in range(1, teams+1)}},
            "picks": [{"round": rnd, "draft_slot": i, "roster_id": str(i)}
                      for rnd in range(1, rounds+1) for i in range(1, teams+1)]}]}


def normalize(data, *, rights=None, bindings=None):
    if rights is None:
        rights, bindings = sleeper_linear_draft_allotment(data, draft_id="d", purpose="rookie",
            purpose_source_ref="rules", roster_identity_source_ref="rosters",
            issued_not_before=T-timedelta(days=100), issued_by=T-timedelta(days=100))
    return normalize_sleeper_historical_pick_inventory(data, rights=rights, draft_pick_bindings=bindings,
        declared_draft_seasons=(2024,), scope_source_ref="inventory", source_revision="pinned-archive",
        source_observed_at=T+timedelta(days=10), transfer_ledger_complete=True, use_ledger_complete=True)


@pytest.mark.parametrize("teams,rounds", [(2, 1), (4, 6), (16, 4)])
def test_source_adapter_covers_untraded_allotments_and_used_drafts_without_round_heuristic(teams, rounds):
    model = normalize(season(teams, rounds))
    assert len(model.at(T-timedelta(days=1)).known_outstanding_owners) == teams*rounds
    assert model.at(T+timedelta(days=1)).complete_for_declared_seasons is False
    assert all(p.status == "used" for p in model.at(T+timedelta(days=2)).picks)
    assert model.at(T+timedelta(days=2)).known_outstanding_owners == ()
    assert model.eligible_for_pit_decision_grade is False


def test_source_adapter_uses_completion_clock_and_reconciles_traded_pick_selection():
    data = season(2, 1)
    at = T-timedelta(days=2)
    data["transactions"] = [{"status": "complete", "transaction_id": "tx", "created": int((at-timedelta(days=2)).timestamp()*1000),
        "status_updated": int(at.timestamp()*1000), "draft_picks": [{"season": "2024", "round": 1,
            "roster_id": "1", "previous_owner_id": "1", "owner_id": "2"}]}]
    data["drafts"][0]["picks"][0]["roster_id"] = "2"
    model = normalize(data)
    assert dict(model.at(at-timedelta(days=1)).known_outstanding_owners)["2024:1:1"] == "1"
    assert dict(model.at(at).known_outstanding_owners)["2024:1:1"] == "2"
    assert model.at(T+timedelta(days=3)).issues == ()


def test_missing_selections_or_bindings_never_leave_completed_draft_rights_tradable():
    data = season(2, 1)
    data["drafts"][0]["picks"].pop()
    model = normalize(data)
    assert "completed_draft_selection_coverage_incomplete" in model.issues
    assert model.at(T+timedelta(days=3)).picks[1].status == "unknown"
    assert model.at(T+timedelta(days=3)).known_outstanding_owners == ()


def test_draft_purpose_and_roster_mapping_are_not_guessed():
    data = season()
    with pytest.raises(ValueError, match="purpose"):
        sleeper_linear_draft_allotment(data, draft_id="d", purpose="startup", purpose_source_ref="rules", roster_identity_source_ref="r")
    data["rosters"][0]["owner_id"] = "unknown"
    with pytest.raises((ValueError, KeyError)):
        normalize(data)


def test_sanitized_source_probe_contains_counts_only():
    result = inspect_sleeper_draft_pick_coverage(season())
    assert result["selection_records"] == result["selections_with_round_slot_roster"] == 24
    assert all(type(v) is int for v in result.values())


def test_future_allotments_do_not_require_known_draft_order_or_three_year_window():
    rights = enumerate_round_pick_allotment(draft_season=2030, rounds=2, original_team_ids=("a", "b"),
        source_ref="explicit-future-rights-rule", issued_not_before=T, issued_by=T)
    model = build_historical_pick_inventory(team_ids=("a", "b"), rights=rights, events=(), uses=(),
        declared_draft_seasons=(2030,), scope_source_ref="rule", transfer_ledger_complete=True,
        coverage_through=T,
        use_ledger_complete=True)
    assert len(model.at(T).known_outstanding_owners) == 4
    assert model.at(T).complete_for_declared_seasons is True


def test_missing_use_ledger_does_not_assume_rights_are_still_outstanding():
    model = build_historical_pick_inventory(team_ids=("a", "b"), rights=(right(),), events=(), uses=(),
        declared_draft_seasons=(2024,), scope_source_ref="rule", transfer_ledger_complete=True, coverage_through=T)
    assert model.at(T).picks[0].status == "unknown"
    assert model.at(T).known_outstanding_owners == ()


def test_ledger_cannot_certify_current_ownership_beyond_its_observation_cutoff():
    snapshot = inventory().at(T+timedelta(days=31))
    assert snapshot.known_outstanding_owners == ()
    assert snapshot.picks[0].status == "unknown"
    assert "cutoff_after_ledger_coverage" in snapshot.issues
    future = HistoricalPickTransferEvent("future", T+timedelta(days=31), (DraftPickTransfer("p", "a", "b"),), "tx")
    with pytest.raises(ValueError, match="after source coverage"):
        inventory(events=(future,))


def test_multi_year_transfers_reuse_original_pick_identity():
    issued = T-timedelta(days=1000)
    rights = enumerate_round_pick_allotment(draft_season=2030, rounds=1, original_team_ids=("a", "b", "c"),
        source_ref="allotment", issued_not_before=issued, issued_by=issued)
    events = (HistoricalPickTransferEvent("older", T-timedelta(days=730),
        (DraftPickTransfer("2030:1:a", "a", "b"),), "older-season-ledger"),
        HistoricalPickTransferEvent("later", T, (DraftPickTransfer("2030:1:a", "b", "c"),), "later-ledger"))
    model = build_historical_pick_inventory(team_ids=("a", "b", "c"), rights=rights, events=events, uses=(),
        declared_draft_seasons=(2030,), scope_source_ref="verified-cross-season-roster-identity",
        coverage_through=T, transfer_ledger_complete=True, use_ledger_complete=True)
    assert dict(model.at(T-timedelta(days=365)).known_outstanding_owners)["2030:1:a"] == "b"
    assert dict(model.at(T).known_outstanding_owners)["2030:1:a"] == "c"
