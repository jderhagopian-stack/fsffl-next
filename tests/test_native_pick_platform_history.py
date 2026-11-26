from copy import deepcopy

import pytest

from scripts.audit_native_pick_platform_history import audit


def history():
    picks=[{'draft_id':'d','pick_no':i,'round':(i-1)//2+1,'metadata':{'position':'WR'}} for i in range(1,7)]
    return [{'league':{'league_id':'l','season':'2023','roster_positions':['QB','WR','SUPER_FLEX'],'scoring_settings':{'rec':.5,'fum_lost':-2}},
             'drafts':[{'draft':{'draft_id':'d','league_id':'l','season':'2023','status':'complete',
              'settings':{'teams':2,'rounds':3,'player_type':0,'slots_wr':1,'slots_super_flex':1}},'picks':picks}]}]


def run(h):return audit(h,source_ref='synthetic-export',expected_sha256='pinned',payload_sha256='pinned')


def test_exact_context_is_retained_and_not_promoted_or_mutated():
    h=history();before=deepcopy(h);r=run(h);d=r['drafts'][0]
    assert d['missing_ranks']==[] and d['selection_count']==6
    assert d['scoring_settings']['fum_lost']==-2
    assert d['eligibility_code']==0 and d['supplemental_three_round_candidate']
    assert r['production_eligible'] is False and h==before


def test_missing_selection_is_not_filled_or_rank_compressed():
    h=history();h[0]['drafts'][0]['picks'].pop(2);d=run(h)['drafts'][0]
    assert d['missing_ranks']==[3] and d['selection_count']==5


@pytest.mark.parametrize('change',['scope','duplicate_rank','round','duplicate_draft'])
def test_conflicting_identity_or_coordinates_rejected(change):
    h=history();item=h[0]['drafts'][0]
    if change=='scope':item['draft']['season']='2024'
    if change=='duplicate_rank':item['picks'].append(deepcopy(item['picks'][0]))
    if change=='round':item['picks'][0]['round']=2
    if change=='duplicate_draft':h.append(deepcopy(h[0]))
    with pytest.raises(ValueError):run(h)


def test_startup_and_incomplete_draft_are_not_supplemental_training_classes():
    for status,rounds in [('complete',20),('drafting',3)]:
        h=history();h[0]['drafts'][0]['draft']['status']=status;h[0]['drafts'][0]['draft']['settings']['rounds']=rounds
        assert run(h)['drafts'][0]['supplemental_three_round_candidate'] is False


def test_source_identity_and_scoring_changes_are_visible():
    h=history();first=run(h)['drafts'][0]['context_fingerprint'];h[0]['league']['scoring_settings']['fum_lost']=-1
    assert run(h)['drafts'][0]['context_fingerprint']!=first
    with pytest.raises(ValueError):audit(h,source_ref='export',expected_sha256='old',payload_sha256='new')
