from copy import deepcopy

import pytest

from scripts.summarize_native_pick_mature_prior import summarize


def fitted():
    case={'training_classes':[2019],'economic_coordinate':{'source':'pinned'},'slots':[
        {'rank':1,'authority':{'low':10.,'reference_center':20.,'high':30.,'width':20.}}]}
    return {'cases':[case,deepcopy(case)],'assumption_ref':'explicit'}


def test_selection_frequency_preserves_class_count_model_authority_and_inputs():
    d=fitted();d['cases'][1]['slots'][0]['authority']={'low':30.,'reference_center':40.,'high':50.,'width':20.};before=deepcopy(d)
    r=summarize(d);assert r['slots'][0]['authority']==dict(low=20,reference_center=30,high=40,width=20)
    assert r['source_draft_count']==2 and r['independent_draft_classes']==1 and r['production_eligible'] is False and d==before


def test_missing_source_is_not_renormalized_out_of_the_summary():
    d=fitted();d['cases'][1]['slots'][0]['authority']=None;r=summarize(d)
    assert r['slots'][0]['authority'] is None and r['slots'][0]['supported_source_drafts']==1
    assert r['slots'][0]['missing_source_drafts']==[1]


@pytest.mark.parametrize('change',['class','coordinate','rank','multi_class','empty'])
def test_mixed_or_incomplete_coordinates_fail(change):
    d=fitted()
    if change=='class':d['cases'][1]['training_classes']=[2018]
    if change=='coordinate':d['cases'][1]['economic_coordinate']={'source':'different'}
    if change=='rank':d['cases'][1]['slots'][0]['rank']=2
    if change=='multi_class':d['cases'][0]['training_classes']=[2018,2019]
    if change=='empty':d['cases']=[]
    with pytest.raises(ValueError):summarize(d)
