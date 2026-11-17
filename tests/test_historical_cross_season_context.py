from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.historical_coverage import HistoricalEvidenceKind as Kind
from fsffl.state.historical_pick_inventory import (
    HistoricalPickRight, HistoricalPickTransferEvent, HistoricalPickUse, build_historical_pick_inventory,
)
from fsffl.state.historical_pick_lineage import HistoricalSeasonPickInventory, reconcile_historical_pick_lineage
from fsffl.state.historical_roster_replay import DraftPickTransfer
from fsffl.state.historical_season_lineage import (
    HistoricalRosterBinding as Binding, HistoricalSeasonLink as Link, SeasonLinkProof,
    build_historical_season_lineage,
)
from fsffl.state.historical_trade_context_coverage import (
    HistoricalTradeContextRequest, build_historical_trade_context_coverage,
)
from tests.test_historical_season_lineage import source, receipt

AT = datetime(2024, 8, 1, tzinfo=UTC)
OBS = datetime(2026, 11, 17, tzinfo=UTC)


def setup(*, renumber=False, same_franchises=True, linked=True):
    old = source(2023, teams=2, provider_id="old")
    new = source(2024, teams=2, provider_id="new")
    old = old.model_copy(update={"roster_bindings": (
        Binding(provider_roster_id="0", canonical_team_id="A", provider_manager_id="owner-a"),
        Binding(provider_roster_id="1", canonical_team_id="B", provider_manager_id="owner-b"))})
    ids = ("7", "8") if renumber else ("0", "1")
    new = new.model_copy(update={"roster_bindings": (
        Binding(provider_roster_id=ids[0], canonical_team_id="A" if same_franchises else "other-A", provider_manager_id="new-owner"),
        Binding(provider_roster_id=ids[1], canonical_team_id="B" if same_franchises else "other-B", provider_manager_id="owner-b"))})
    links = (Link(previous=old.season, current=new.season, previous_provider_ref=old.provider_ref,
        observed_parent_provider_league_id="old", evidence=receipt(new.season, Kind.OWNER_IDENTITY, "link"),
        proof=SeasonLinkProof.PROVIDER_PREVIOUS_LEAGUE),) if linked else ()
    return old, new, build_historical_season_lineage(sources=(old, new), links=links)


def inventory(src, *, event=None, use=None, complete=False, through=OBS, scope="source"):
    ids = tuple(b.provider_roster_id for b in src.roster_bindings)
    return build_historical_pick_inventory(team_ids=ids,
        rights=(HistoricalPickRight("local-pick", 2025, 1, ids[0], scope, AT-timedelta(days=500), AT-timedelta(days=500)),),
        events=(event,) if event else (), uses=(use,) if use else (), declared_draft_seasons=(2025,),
        scope_source_ref=scope, coverage_through=through, transfer_ledger_complete=complete,
        use_ledger_complete=complete, allotment_complete=True)


def entry(src, model, namespace="provider-global"):
    return HistoricalSeasonPickInventory(src.season, model, namespace)


def test_joins_explicit_franchise_crosswalk_when_provider_roster_numbers_change():
    old, new, lineage = setup(renumber=True)
    move = HistoricalPickTransferEvent("tx", AT, (DraftPickTransfer("local-pick", "0", "1"),), "older-ledger")
    first = inventory(old, event=move, complete=True)
    # Same exact transfer receipt in the second source, expressed in its own IDs.
    later_move = replace(move, transfers=(DraftPickTransfer("local-pick", "7", "8"),), source_ref="later-copy")
    second = inventory(new, event=later_move, complete=True)
    joined = reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, first), entry(new, second)))
    assert len(joined.inventory.rights) == len(joined.inventory.events) == 1
    assert joined.inventory.at(AT).known_outstanding_owners[0][1] == "B"
    assert joined.inventory.at(AT, boundary="before").known_outstanding_owners[0][1] == "A"
    assert joined.inventory.at(AT).complete_for_declared_seasons


def test_equal_raw_rosters_or_manager_ids_do_not_supply_franchise_continuity():
    old, new, lineage = setup(same_franchises=False)
    with pytest.raises(ValueError, match="complete draft allotments"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, inventory(old)), entry(new, inventory(new))))


def test_unlinked_seasons_and_duplicate_inputs_are_rejected():
    old, new, lineage = setup(linked=False)
    with pytest.raises(ValueError, match="unlinked"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, inventory(old)), entry(new, inventory(new))))
    with pytest.raises(ValueError, match="distinct"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, inventory(old)),)*2)


def test_cross_family_and_missing_roster_crosswalk_are_rejected():
    old, new, lineage = setup()
    wrong = new.season.model_copy(update={"league_family_id": "unregistered"})
    with pytest.raises(ValueError, match="unregistered"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(replace(entry(new, inventory(new)), season=wrong),))
    partial = replace(inventory(old), team_ids=("0",))
    with pytest.raises(ValueError, match="crosswalk"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, partial),))


def test_duplicate_event_receipts_merge_but_conflicting_movements_do_not():
    old, new, lineage = setup()
    a = HistoricalPickTransferEvent("tx", AT, (DraftPickTransfer("local-pick", "0", "1"),), "source-a")
    b = replace(a, effective_at=AT+timedelta(seconds=1))
    with pytest.raises(ValueError, match="conflicting event identity"):
        reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, inventory(old, event=a)), entry(new, inventory(new, event=b))))
    different_scope = reconcile_historical_pick_lineage(lineage=lineage,
        seasons=(entry(old, inventory(old, event=a), "old-season"), entry(new, inventory(new, event=b), "new-season")))
    assert len(different_scope.inventory.events) == 2


def test_partial_scans_remain_partial_but_terminal_use_receipts_can_be_joined():
    old, new, lineage = setup()
    use = HistoricalPickUse("local-pick", "0", "draft", AT+timedelta(days=1), AT+timedelta(days=2))
    joined = reconcile_historical_pick_lineage(lineage=lineage,
        seasons=(entry(old, inventory(old)), entry(new, inventory(new, use=use))))
    assert joined.inventory.use_ledger_complete is True
    assert joined.inventory.transfer_ledger_complete is False
    assert joined.inventory.at(OBS).picks[0].status == "used"
    assert not joined.inventory.at(OBS).complete_for_declared_seasons


def test_conflicting_use_owner_or_nonoverlapping_time_evidence_is_not_overwritten():
    old, new, lineage = setup()
    use = HistoricalPickUse("local-pick", "0", "a", AT, AT)
    for other in (replace(use, owner_team_id="1"), replace(use, not_before=AT+timedelta(days=1), by=AT+timedelta(days=1))):
        with pytest.raises(ValueError, match="conflicting"):
            reconcile_historical_pick_lineage(lineage=lineage,
                seasons=(entry(old, inventory(old, use=use)), entry(new, inventory(new, use=other))))


def test_mixed_observation_cutoffs_do_not_extrapolate_earlier_ownership():
    old, new, lineage = setup()
    joined = reconcile_historical_pick_lineage(lineage=lineage, seasons=(
        entry(old, inventory(old, complete=True, through=AT)), entry(new, inventory(new, complete=True))))
    assert joined.inventory.transfer_ledger_complete is False


def request(src, tid="tx", when=AT):
    return HistoricalTradeContextRequest(src.season, tid, when-timedelta(days=1), when, ("0", "1"), "trade-source")


def test_coverage_deduplicates_trade_requests_without_calling_them_model_ready():
    old, _, lineage = setup()
    req = request(old)
    report = build_historical_trade_context_coverage(requests=(req, req), lineage=lineage, roster_histories={})
    assert report.summary()["trade_rows"] == report.duplicate_request_count == 1
    assert report.summary()["different_creation_completion_clock_rows"] == 1
    assert report.summary()["archived_full_model_input_rows"] == 0
    assert not report.rows[0].player_membership_context_available
    with pytest.raises(ValueError, match="conflicting repeated"):
        build_historical_trade_context_coverage(requests=(req, replace(req, created_at=AT)), lineage=lineage, roster_histories={})


def test_cutoff_queries_reuse_one_snapshot_per_timestamp_and_reject_wrong_crosswalk(monkeypatch):
    old, new, lineage = setup()
    joined = reconcile_historical_pick_lineage(lineage=lineage, seasons=(entry(old, inventory(old)),))
    calls = []
    original = type(joined.inventory).at
    def counted(self, *args, **kwargs):
        calls.append(args[0])
        return original(self, *args, **kwargs)
    monkeypatch.setattr(type(joined.inventory), "at", counted)
    report = build_historical_trade_context_coverage(requests=(request(old, "one"), request(old, "two")),
        lineage=lineage, roster_histories={}, picks=joined)
    assert len(report.rows) == 2 and calls == [AT]
    changed = old.model_copy(update={"roster_bindings": tuple(replace_binding(b) for b in old.roster_bindings)})
    other = build_historical_season_lineage(sources=(changed,), links=())
    with pytest.raises(ValueError, match="different registered"):
        build_historical_trade_context_coverage(requests=(request(changed),), lineage=other, roster_histories={}, picks=joined)


def replace_binding(binding):
    return binding.model_copy(update={"canonical_team_id": "changed-"+binding.canonical_team_id})


def provider_case(data=None):
    from tests.test_historical_roster_context import _season
    from tests.test_historical_pick_inventory import season as draft_fixture
    from fsffl.state.historical_roster_context import _digest
    from fsffl.state.models import ProviderRef
    from fsffl.providers.sleeper_historical_context import HistoricalRookieDraftEvidence
    data = _season(season=2024) if data is None else data
    data["drafts"] = draft_fixture(4, 1)["drafts"]
    for row in data["rosters"]:
        row["owner_id"] = f"u{row['roster_id']}"
    src = source(2024, teams=4, provider_id=data["league"]["league_id"])
    src = src.model_copy(update={"provider_ref": ProviderRef(provider="sleeper", external_id=data["league"]["league_id"]),
        "source_content_sha256": _digest(data), "roster_bindings": tuple(Binding(provider_roster_id=str(i),
            canonical_team_id=f"franchise-{i}", provider_manager_id=f"u{i}") for i in range(1, 5))})
    lineage = build_historical_season_lineage(sources=(src,), links=())
    spec = HistoricalRookieDraftEvidence(src.season, "d", "rookie-purpose", "historical-rosters")
    return data, src, lineage, spec


def test_provider_integration_builds_each_native_history_once_and_preserves_clocks(monkeypatch):
    import fsffl.providers.sleeper_historical_context as module
    data, src, lineage, spec = provider_case()
    calls = []
    native = module.reconstruct_sleeper_roster_context
    def counted(*args, **kwargs):
        calls.append(1)
        return native(*args, **kwargs)
    monkeypatch.setattr(module, "reconstruct_sleeper_roster_context", counted)
    result = module.build_sleeper_historical_context(seasons={src.season: data}, lineage=lineage,
        rookie_drafts=(spec,), source_revision="test-source", source_observed_at=OBS)
    assert calls == [1]
    summary = result.trades.summary()
    assert summary["trade_rows"] == summary["membership_context_rows"] == 1
    assert summary["different_creation_completion_clock_rows"] == 1
    assert summary["complete_pick_count_rows"] == summary["archived_full_model_input_rows"] == 0
    assert result.picks.inventory.use_ledger_complete
    assert not result.picks.inventory.transfer_ledger_complete


def test_provider_rejects_unregistered_source_or_missing_purpose_instead_of_guessing():
    from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
    data, src, lineage, spec = provider_case()
    data["league"]["league_id"] = "wrong-provider-season"
    with pytest.raises(ValueError, match="provider identity"):
        build_sleeper_historical_context(seasons={src.season: data}, lineage=lineage,
            rookie_drafts=(spec,), source_revision="test", source_observed_at=OBS)
    data, src, lineage, _ = provider_case()
    with pytest.raises(ValueError, match="allotment evidence"):
        build_sleeper_historical_context(seasons={src.season: data}, lineage=lineage,
            rookie_drafts=(), source_revision="test", source_observed_at=OBS)


def test_provider_never_substitutes_creation_clock_for_missing_completion():
    from tests.test_historical_roster_context import _season
    from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
    data = _season(season=2024)
    data["transactions"][0]["status_updated"] = None
    data, src, lineage, spec = provider_case(data)
    with pytest.raises(ValueError, match="completion clock"):
        build_sleeper_historical_context(seasons={src.season: data}, lineage=lineage,
            rookie_drafts=(spec,), source_revision="test", source_observed_at=OBS)


def test_report_checks_source_fingerprints_and_exact_precompletion_snapshot():
    from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
    data, src, lineage, _ = provider_case()
    provider_identity = src.season.model_copy(update={"league_id": src.provider_ref.external_id})
    history = reconstruct_sleeper_roster_context(data, source_revision="test", season_identity=provider_identity)
    at = datetime.fromtimestamp(data["transactions"][0]["status_updated"]/1000, tz=UTC)
    req = HistoricalTradeContextRequest(src.season, "trade-1", at-timedelta(seconds=60), at, ("1", "2"), "trade")
    report = build_historical_trade_context_coverage(requests=(req,), lineage=lineage, roster_histories={src.season: history})
    assert report.rows[0].player_membership_context_available
    mismatch = replace(req, completed_at=at+timedelta(seconds=1))
    report = build_historical_trade_context_coverage(requests=(mismatch,), lineage=lineage, roster_histories={src.season: history})
    assert not report.rows[0].pre_completion_snapshot_available
    wrong = src.model_copy(update={"source_content_sha256": "f"*64})
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        build_historical_trade_context_coverage(requests=(req,), lineage=build_historical_season_lineage(sources=(wrong,), links=()),
            roster_histories={src.season: history})
