from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import pytest
from fsffl.providers.sleeper_historical_draft_players import normalize_sleeper_draft_player_allocation
from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
from tests.test_historical_roster_context import _season

OBS = datetime(2024,12,1,tzinfo=UTC)
def ms(month,day,hour=0):return int(datetime(2024,month,day,hour,tzinfo=UTC).timestamp()*1000)

def source():
    data=_season(season=2024)
    rosters={str(r['roster_id']):r for r in data['rosters']}
    rosters['1']['players'].append('rookie')
    rosters['4']['players'].append('veteran')
    data['drafts']=[{'draft':{'draft_id':'draft','status':'complete','start_time':ms(6,1),'last_picked':ms(6,2)},
        'picks':[{'player_id':'rookie','roster_id':3,'round':1,'draft_slot':3},{'player_id':'veteran','roster_id':4,'round':1,'draft_slot':4}]}]
    def tx(tid,when,adds,drops):return {'transaction_id':tid,'status':'complete','type':'free_agent',
        'created':when-100,'status_updated':when,'adds':adds,'drops':drops,'roster_ids':[1]}
    data['transactions'].extend([
        tx('early',ms(3,1),{'player-a':1,'player-b':2},{'player-a':2,'player-b':1}),
        tx('veteran-drop',ms(4,1),{}, {'veteran':2}),
        tx('inside',ms(6,1,12),{},{}),
        tx('rookie-trade',ms(7,1),{'rookie':1},{'rookie':3})])
    return data

def allocation(data):return normalize_sleeper_draft_player_allocation(data,draft_id='draft',
    purpose_source_ref='declared-fantasy-draft',roster_identity_source_ref='source-roster-map',
    source_revision='fixture',source_observed_at=OBS, expected_selection_keys=frozenset({(1,3),(1,4)}))

def replay(data,alloc=None):return reconstruct_sleeper_roster_context(data,source_revision='fixture',
    draft_allocations=(allocation(data) if alloc is None else alloc,))

def before(history,event):return next(s for s in history.snapshots
    if event in s.transaction_ids and s.boundary=='before_completed_event_batch')

def owners(s):return {p:t.provider_roster_id for t in s.teams for p in t.player_ids}

def test_allocation_removes_later_ownership_but_preserves_veteran_earlier_holding():
    data=source(); original=deepcopy(data); h=replay(data)
    assert not h.membership_issues
    early=before(h,'early')
    assert 'rookie' not in owners(early)
    assert owners(early)['veteran']=='2'
    assert 'veteran' not in next(t.player_ids for t in early.teams if t.provider_roster_id=='4')
    assert not early.membership_uncertainty_reasons and not early.uncertain_player_ids
    # Post-draft transactions remain in chronological ownership order.
    assert owners(before(h,'rookie-trade'))['rookie']=='3'
    assert owners(before(h,'trade-1'))['rookie']=='1'
    assert h.completed_event_count==len(data['transactions'])
    assert len(h.snapshots)==len(data['transactions'])*2+1  # No fabricated draft timestamp snapshots.
    assert h.model_version=='historical-roster-context-v4:draft-allocations'
    assert data==original


def test_cutoff_inside_draft_keeps_selection_time_unknown():
    h=replay(source()); s=before(h,'inside')
    assert set(s.uncertain_player_ids)=={'rookie','veteran'}
    assert s.membership_uncertainty_reasons==('draft_allocation_interval',)


def test_selected_player_movement_inside_window_remains_uncertain_before_draft():
    data=source();data['transactions']=[t for t in data['transactions'] if t['transaction_id']!='rookie-trade']
    data['rosters'][0]['players'].remove('rookie')
    data['transactions'].append({'transaction_id':'ambiguous','status':'complete','type':'free_agent',
        'created':ms(6,1,8)-100,'status_updated':ms(6,1,8),'adds':{},'drops':{'rookie':3},'roster_ids':[3]})
    h=replay(data)
    assert 'rookie' in before(h,'early').uncertain_player_ids
    assert 'draft_player_movement_order_unknown' in before(h,'early').membership_uncertainty_reasons
    assert not before(h,'trade-1').uncertain_player_ids
    assert not before(h,'trade-1').membership_uncertainty_reasons


def test_missing_player_details_do_not_invent_allocations_or_erase_later_facts():
    data=source();data['drafts'][0]['picks'][0].pop('player_id')
    a=allocation(data);assert not a.player_details_complete
    h=replay(data,a)
    assert 'draft_player_details_incomplete' in before(h,'early').membership_uncertainty_reasons
    assert not before(h,'trade-1').membership_uncertainty_reasons


def test_identity_and_source_cohort_are_required():
    data=source();a=allocation(data)
    with pytest.raises(ValueError,match='source cohort'):
        replay(data,replace(a,source_sha256='0'*64))
    with pytest.raises(ValueError,match='bounds'):
        replace(a,source_observed_at=datetime(2024,1,1,tzinfo=UTC))
    with pytest.raises(ValueError,match='duplicate admitted'):
        reconstruct_sleeper_roster_context(data,source_revision='fixture',draft_allocations=(a,a))
    with pytest.raises(ValueError,match='purpose'):
        normalize_sleeper_draft_player_allocation(data,draft_id='draft',purpose_source_ref='',
            roster_identity_source_ref='x',source_revision='x',source_observed_at=OBS)


def test_duplicate_draft_players_are_not_silently_deduplicated():
    data=source();data['drafts'][0]['picks'].append(data['drafts'][0]['picks'][0])
    with pytest.raises(ValueError,match='unique'):
        allocation(data)


def test_bare_archive_is_not_certified_before_an_unadmitted_completed_draft():
    h=reconstruct_sleeper_roster_context(source(),source_revision='fixture')
    assert 'draft_player_allocation_not_admitted' in before(h,'early').membership_uncertainty_reasons
    assert not before(h,'trade-1').membership_uncertainty_reasons


def test_missing_selection_cannot_be_declared_a_complete_allocation():
    data=source();data['drafts'][0]['picks'].pop()
    assert not allocation(data).player_details_complete


def test_no_allotment_manifest_cannot_certify_full_player_selection_coverage():
    a=normalize_sleeper_draft_player_allocation(source(),draft_id='draft',purpose_source_ref='declared',
        roster_identity_source_ref='admitted',source_revision='fixture',source_observed_at=OBS)
    assert not a.player_details_complete


def test_explicit_keeper_retention_does_not_erase_earlier_ownership():
    data=source()
    data['transactions']=[t for t in data['transactions'] if t['transaction_id']!='veteran-drop']
    for p in data['drafts'][0]['picks']:
        p['is_keeper']=True
    a=allocation(data)
    assert a.player_details_complete and not a.player_transfers
    h=replay(data,a)
    assert owners(before(h,'early'))['veteran']=='4'
    assert owners(before(h,'early'))['rookie']=='3'
    assert not before(h,'inside').membership_uncertainty_reasons


def test_overlapping_drafts_cannot_invent_selected_player_order():
    data=source();a=allocation(data)
    other=replace(a,draft_id='second-admitted-draft')
    h=reconstruct_sleeper_roster_context(data,source_revision='fixture',draft_allocations=(a,other))
    assert set(before(h,'early').uncertain_player_ids)=={'rookie','veteran'}
    assert 'draft_player_movement_order_unknown' in before(h,'early').membership_uncertainty_reasons


def test_legacy_identity_without_draft_evidence_is_unchanged():
    h=reconstruct_sleeper_roster_context(_season(season=2024),source_revision='fixture')
    assert h.model_version=='historical-roster-context-v3'
    assert h.history_id=='hctx_156f6566410cdd8bdc7ff27efd6c12e63203ba5cfbd0c47c691cf9ee72c60677'
    assert h.snapshots[0].snapshot_id=='hsnap_14bfbf858cb75cf67f128f136774d0819ccb923ce223d1c26baabe78ec6d50f3'


def test_absent_lower_bound_is_not_invented_and_blocks_earlier_membership():
    data=source();data['drafts'][0]['draft'].pop('start_time')
    a=allocation(data);assert a.not_before is None
    h=replay(data,a)
    assert 'draft_allocation_interval' in before(h,'early').membership_uncertainty_reasons
    assert not before(h,'trade-1').membership_uncertainty_reasons


def test_missing_last_pick_uses_recorded_observation_upper_bound_not_guessed_time():
    data=source();data['drafts'][0]['draft'].pop('last_picked')
    a=allocation(data);assert a.by==OBS
    assert before(replay(data,a),'trade-1').membership_uncertainty_reasons


def test_empty_draft_selection_payload_does_not_certify_no_allocations():
    data=source();data['drafts'][0]['picks']=[]
    a=allocation(data);assert not a.player_details_complete
    assert before(replay(data,a),'early').membership_uncertainty_reasons


def test_unstarted_draft_rights_do_not_require_invented_player_allocations():
    data=source();data['drafts'][0]['draft']['status']='pre_draft';data['drafts'][0]['picks']=[]
    assert allocation(data) is None


def test_in_progress_selections_are_partial_not_a_complete_draft_cohort():
    data=source();data['drafts'][0]['draft']['status']='drafting'
    a=allocation(data);assert a is not None and not a.player_details_complete
    assert before(replay(data,a),'early').membership_uncertainty_reasons
