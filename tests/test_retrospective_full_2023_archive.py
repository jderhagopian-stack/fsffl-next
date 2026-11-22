"""Real source longitudinal acceptance (source mounted ephemerally, no league data in git)."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
import json
import os
from pathlib import Path

import pytest
from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season
from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
from fsffl.providers.sleeper_historical_pick_inventory import (
    normalize_sleeper_historical_pick_inventory, sleeper_linear_draft_allotment,
)

PINNED_BLOB = "e18c01bf25f58c5dfe3d0802f53de484ea257ca1"


def test_cross_season_pick_join_and_trade_field_coverage_on_pinned_archive():
    from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
    from tests.historical_archive_context_fixture import declared_archive_context_inputs
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original archive not mounted; no real-source claim")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    observed = datetime(2026, 11, 17, tzinfo=UTC)
    records, lineage, drafts = declared_archive_context_inputs(json.loads(raw), observed=observed,
        source_revision="git-blob:"+PINNED_BLOB)
    result = build_sleeper_historical_context(seasons=records, lineage=lineage, rookie_drafts=drafts,
        source_revision="git-blob:"+PINNED_BLOB, source_observed_at=observed)
    summary = result.trades.summary()
    by_year = {}
    for year in (2022, 2023, 2024, 2025, 2026):
        rows = tuple(r for r in result.trades.rows if r.request.season.season == year)
        by_year[year] = {"trades": len(rows), "membership_context": sum(r.player_membership_context_available for r in rows)}
    end = result.picks.inventory.at(observed)
    # Counts/codes only. No owner, player, pick or transaction IDs in output.
    print(json.dumps({"historical_context_field_coverage": summary, "by_season": by_year,
        "coverage_issue_counts": result.trades.issue_counts(), "joined_pick_rights": len(result.picks.inventory.rights),
        "joined_pick_transfer_events": len(result.picks.inventory.events),
        "joined_pick_movements": sum(len(e.transfers) for e in result.picks.inventory.events),
        "joined_terminal_uses": len(result.picks.inventory.uses), "end_pick_issue_codes": end.issues,
        "identity_scope": "declared_retrospective_fixture_crosswalk_not_independent_at_time_certification"}, sort_keys=True))
    assert summary["trade_rows"] == summary["pre_completion_snapshot_rows"] == 144, summary
    # Seven previously counted clean-year boundaries fall inside drafts with
    # no exact selection clocks. Keep those partial instead of asserting roster
    # completion. Eight other in-draft boundaries already belong to the2023gap.
    assert summary["membership_context_rows"] == 89, summary
    assert result.trades.issue_counts()["draft_allocation_interval"] == 15
    assert summary["archived_full_model_input_rows"] == 0
    assert summary["complete_pick_count_rows"] == 0
    assert len(result.picks.inventory.rights) == len(result.picks.inventory.uses) == 144
    assert all(p.status == "used" for p in end.picks), end.issues
    assert result.picks.inventory.transfer_ledger_complete is False


def test_retained_rookie_drafts_bind_complete_allotments_and_consumed_rights():
    """Known fixture purpose, not a generic year/type-based draft classifier.

    2022 is this fixture's startup. Its separately identified 2023–2026 drafts
    are rookie drafts. Neither selection lineage nor retrospective roster maps
    certify the complete inter-season ownership ledger or original availability.
    """
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original archived source not mounted; no real-source claim")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    observed = datetime(2026, 11, 17, tzinfo=UTC)
    counts = []
    for year in json.loads(raw):
        season = int(year["league"]["season"])
        if season not in (2023, 2024, 2025, 2026):
            continue
        drafts = year.get("drafts") or ()
        assert len(drafts) == 1
        draft_id = str(drafts[0]["draft"]["draft_id"])
        rights, bindings = sleeper_linear_draft_allotment(year, draft_id=draft_id, purpose="rookie",
            purpose_source_ref="pinned-fixture:identified-rookie-draft",
            roster_identity_source_ref="pinned-fixture:retrospective-season-rosters")
        model = normalize_sleeper_historical_pick_inventory(year, rights=rights, draft_pick_bindings=bindings,
            declared_draft_seasons=(season,), scope_source_ref="pinned-fixture:single-draft-allotment",
            source_revision="git-blob:"+PINNED_BLOB, source_observed_at=observed)
        snapshot = model.at(observed)
        counts.append((season, len(rights), len(model.uses)))
        assert not model.issues
        status_counts = {status: sum(p.status == status for p in snapshot.picks)
                         for status in ("used", "unknown", "conflict", "outstanding", "not_issued")}
        assert status_counts["used"] == len(rights), (season, status_counts, snapshot.issues)
        assert snapshot.known_outstanding_owners == ()
        # Current-season transfers alone do not cover earlier-season ownership.
        assert snapshot.transfer_ledger_complete is False
        assert snapshot.complete_for_declared_seasons is False
        assert snapshot.eligible_for_pit_decision_grade is False
    assert sorted(counts) == [(2023, 36, 36), (2024, 36, 36), (2025, 36, 36), (2026, 36, 36)]


def test_yearwide_2023_catches_exact_single_waiver_evidence_gap():
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original archived source not mounted; no real-source claim")
    source = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() == PINNED_BLOB
    seasons = [s for s in json.loads(source) if str(s["league"]["season"]) == "2023"]
    assert len(seasons) == 1
    out = audit_retrospective_sleeper_season(seasons[0], source_revision="git-blob:"+PINNED_BLOB)
    assert out.season == 2023
    assert out.team_count == 12
    assert out.completed_events_examined == 350
    assert out.completed_trades_examined == 48
    assert out.player_movements_examined == 588
    assert out.pick_movements_examined == 83
    assert out.faab_transfers_examined == 24
    assert out.waiver_bids_examined == 82
    assert out.completed_timestamp_tie_groups == 21
    assert out.status == "incomplete_source_history"
    assert len(out.issues) == 1, out.issues
    assert out.issues[0].code == "post_event_player_missing"
    assert out.issues[0].event_type == "waiver"
    assert out.issues[0].completed_at == datetime(2023, 7, 27, 7, 5, 25, 93000, tzinfo=UTC)
    assert out.source_provides_contemporaneous_state is False
    assert out.eligible_for_pit_decision_grade is False
    assert out.historically_validated_faab_balances is False


def test_all_retained_seasons_preserve_original_rules_and_expose_incomplete_years():
    """Source-wide research acceptance, not a claim of full historical coverage."""
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original historical source not mounted")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    years = sorted(json.loads(raw), key=lambda x: int(x["league"]["season"]))
    assert [int(y["league"]["season"]) for y in years] == [2022, 2023, 2024, 2025, 2026]
    summaries = []
    for idx, y in enumerate(years):
        if idx:
            assert str(y["league"]["previous_league_id"]) == str(years[idx-1]["league"]["league_id"])
        audit = audit_retrospective_sleeper_season(y, source_revision="git-blob:" + PINNED_BLOB)
        assert audit.team_count == len(y["rosters"])
        assert audit.completed_events_examined == len([t for t in y["transactions"] if t["status"] == "complete"])
        assert audit.source_provides_contemporaneous_state is False
        assert audit.eligible_for_pit_decision_grade is False
        summaries.append(audit)
    expected = [(2022, 246, 14), (2023, 350, 48), (2024, 358, 26), (2025, 339, 34), (2026, 107, 22)]
    assert [(x.season, x.completed_events_examined, x.completed_trades_examined) for x in summaries] == expected
    assert summaries[1].status == "incomplete_source_history"
    assert [issue.code for issue in summaries[1].issues] == ["post_event_player_missing"]
    assert all(not x.issues for idx, x in enumerate(summaries) if idx != 1)
    assert summaries[1].original_rules_sha256 != summaries[2].original_rules_sha256
    # Even a source-consistent 2022 or archived 2026 portion is not a valid PIT
    # decision State: startup/draft events and original availability still need proof.
    assert all(x.historically_validated_faab_balances is False for x in summaries)


def test_all_retained_seasons_produce_rule_scoped_roster_context_snapshots():
    """Exercise the reusable provider across the complete retained year cohort."""
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original historical source not mounted")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    years = sorted(json.loads(raw), key=lambda x: int(x["league"]["season"]))
    histories = [
        reconstruct_sleeper_roster_context(year, source_revision="git-blob:" + PINNED_BLOB)
        for year in years
    ]

    assert [row.season for row in histories] == [2022, 2023, 2024, 2025, 2026]
    assert [row.observed_team_count for row in histories] == [12, 12, 12, 12, 12]
    assert [row.completed_event_count for row in histories] == [246, 350, 358, 339, 107]
    assert all(row.provider_league_id == str(year["league"]["league_id"])
               for row, year in zip(histories, years))
    assert all(row.raw_roster_slots == tuple(year["league"]["roster_positions"])
               for row, year in zip(histories, years))
    assert all(row.league_rules_sha256 for row in histories)
    assert len({row.league_rules_sha256 for row in histories}) > 1
    assert all(row.eligible_for_pit_decision_grade is False for row in histories)
    assert all(snapshot.roster_slot_coverage == "unknown"
               for history in histories for snapshot in history.snapshots)
    assert histories[1].membership_status == "incomplete_source_history"
    assert "post_event_player_ownership_mismatch" in histories[1].issues
    non_2023_issues = [
        (history.season, history.membership_issues)
        for index, history in enumerate(histories) if index != 1 and history.membership_issues
    ]
    assert not non_2023_issues, non_2023_issues
    assert {2022, 2024}.issubset({history.season for history in histories if history.faab_issues})
    assert all(history.membership_status == "provisionally_consistent"
               for history in histories if history.season in {2022, 2024})


def test_real_draft_allocations_correct_pre_draft_membership_without_erasing_veterans(monkeypatch):
    """Exact public fixture; print counts only, not private ownership payloads."""
    import fsffl.providers.sleeper_historical_context as module
    from tests.historical_archive_context_fixture import declared_archive_context_inputs
    path=os.getenv('FSFFL_RESEARCH_HISTORICAL_ARCHIVE')
    if not path:
        pytest.skip('original pinned archive not mounted; no real-source claim')
    raw=Path(path).read_bytes()
    assert sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==PINNED_BLOB
    observed=datetime(2026,11,17,tzinfo=UTC)
    records,lineage,drafts=declared_archive_context_inputs(json.loads(raw),observed=observed,
        source_revision='git-blob:'+PINNED_BLOB)
    captured={}; native=module.reconstruct_sleeper_roster_context
    def retain(*args,**kwargs):
        h=native(*args,**kwargs);captured[h.season]=h;return h
    monkeypatch.setattr(module,'reconstruct_sleeper_roster_context',retain)
    module.build_sleeper_historical_context(seasons=records,lineage=lineage,rookie_drafts=drafts,
        source_revision='git-blob:'+PINNED_BLOB,source_observed_at=observed)
    assert len(captured)==5
    counts=[]
    for identity,data in records.items():
        year=identity.season
        if year not in (2024,2025,2026):
            continue
        corrected=captured[year]
        assert not corrected.membership_issues, corrected.membership_issues
        original=native(data,source_revision='git-blob:'+PINNED_BLOB)
        draft=data['drafts'][0];start=int(draft['draft']['start_time'])
        trades=sorted((t for t in data['transactions'] if t.get('status')=='complete' and t.get('type')=='trade'),
            key=lambda t:int(t['status_updated']))
        candidates=[t for t in trades if int(t['status_updated'])<start]
        tx=max(candidates,key=lambda t:len(t.get('draft_picks')or[])) if year==2025 else candidates[0]
        def pre(h,event):return next(s for s in h.snapshots if str(event['transaction_id']) in s.transaction_ids
            and s.boundary=='before_completed_event_batch')
        before=pre(corrected,tx);old=pre(original,tx)
        owners={t.provider_roster_id:set(t.player_ids)for t in before.teams}
        changes=sum(len(set(t.player_ids)^owners[t.provider_roster_id])for t in old.teams)
        assert changes==36, 'expected one corrected allocation per original draft selection'
        assert not before.uncertain_player_ids and not before.membership_uncertainty_reasons
        if year in (2024,2026):
            name='Kadarius Toney' if year==2024 else 'Stefon Diggs'
            pid=next(str(p['player_id'])for p in draft['picks']if
                ((p.get('metadata')or{}).get('first_name','')+' '+(p.get('metadata')or{}).get('last_name',''))==name)
            assert sum(pid in players for players in owners.values())==1, 'earlier veteran ownership must survive'
        if year==2024:
            post=next(t for t in trades if int(t['status_updated'])>int(draft['draft']['last_picked']) and len(t.get('adds')or{})>=2)
            after={t.provider_roster_id:set(t.player_ids)for t in pre(corrected,post).teams}
            assert sum(len(set(t.player_ids)^after[t.provider_roster_id])for t in pre(original,post).teams)==0
        counts.append({'season':year,'corrected_assignments':changes})
    print(json.dumps({'draft_player_allocation_regression':counts,'raw_ownership_printed':False},sort_keys=True))
