from copy import deepcopy

import pytest

from scripts.audit_native_pick_career_stability import audit


def cases():
    a=dict(source_case_id='a',draft_class=2018,economic_comparison_coordinate={'rules':'same'},source_fingerprints=['pin-a'],
        slots=[dict(rank=1,authority=dict(low=10,reference_center=20,high=30,width=20)),
               dict(rank=2,authority=dict(low=20,reference_center=30,high=40,width=20))])
    b=deepcopy(a);b.update(source_case_id='b',draft_class=2019,source_fingerprints=['pin-b'])
    b['slots'][0]['authority']=dict(low=30,reference_center=40,high=50,width=20)
    return [a,b]


def test_reports_sensitivity_without_creating_new_values_or_uncertainty():
    cs=cases();before=deepcopy(cs);r=audit(cs,max_slots=2)
    assert r['common_slots']==2 and r['independent_draft_class_count']==2
    assert r['slots'][0]['center_spread']==20 and r['slots'][0]['symmetric_relative_center_spread']==pytest.approx(2/3)
    assert r['source_cases'][0]['adjacent_increase_at_ranks']==[1]
    assert r['new_curve_or_promotion_created'] is False and r['production_eligible'] is False and cs==before


def test_same_class_different_sources_does_not_inflate_independent_class_count():
    cs=cases();cs[1]['draft_class']=2018;r=audit(cs,max_slots=2)
    assert r['independent_draft_class_count']==1 and r['source_case_count']==2


def test_missing_ranks_are_retained_and_not_used_as_zero_or_rank_compressed():
    cs=cases();cs[1]['slots'].pop(0);r=audit(cs,max_slots=2)
    assert r['common_slots']==1 and r['slots'][0]['missing_source_cases']==['b']
    assert r['slots'][0]['center_spread'] is None and r['slots'][1]['rank']==2


@pytest.mark.parametrize('change',['duplicate_source','coordinate','duplicate_rank','nan','lineage','class','rank'])
def test_incompatible_or_untrustworthy_inputs_fail(change):
    cs=cases()
    if change=='duplicate_source':cs[1]['source_case_id']='a'
    if change=='coordinate':cs[1]['economic_comparison_coordinate']={'rules':'other'}
    if change=='duplicate_rank':cs[1]['slots'].append(deepcopy(cs[1]['slots'][0]))
    if change=='nan':cs[1]['slots'][0]['authority']['reference_center']=float('nan')
    if change=='lineage':cs[1]['source_fingerprints']=[]
    if change=='class':cs[1]['draft_class']=True
    if change=='rank':cs[1]['slots'][0]['rank']=True
    with pytest.raises(ValueError):audit(cs,max_slots=2)
