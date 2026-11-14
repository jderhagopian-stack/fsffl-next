from copy import deepcopy

import pytest

from scripts.audit_native_pick_annual_prior import audit
from tests.test_native_pick_baseline import document, row


def run(rows,**kwargs):
    return audit(document(rows),release_season=2020,complete_through=2019,max_slots=1,**kwargs)


def test_all_mature_classes_required_no_survivor_filter_and_no_future_training():
    result=run([row(2014),row(2015,values=(100,None,60)),row(2018,values=(999,999,999))])
    case=result['cases'][0]
    assert case['training_classes']==[2014,2015]
    assert case['supported_slots']==0
    assert case['slots'][0]['estimate_first_three_post_draft'] is None
    assert case['gaps'][0]['missing_seasons']==[2016]
    assert result['production_eligible'] is False


def test_real_zero_and_calendar_offsets_preserved_without_Career_inference():
    case=run([row(2014,values=(100,0,60))])['cases'][0]
    slot=case['slots'][0]
    assert slot['estimate_first_three_post_draft']==pytest.approx(143.35)
    assert slot['calendar_three_year_by_draft_offset']==pytest.approx({'0':143.35,'1':85.,'2':72.25})
    assert case['career_available'] is False
    assert slot['leave_one_class_mean_min'] is None


def test_short_calendar_prefix_supported_without_imputing_missing_later_year():
    case=run([row(2014,values=(100,80,None))])['cases'][0]
    slot=case['slots'][0]
    assert slot['estimate_first_three_post_draft'] is None
    assert slot['calendar_three_year_by_draft_offset']['1']==pytest.approx(142.8)
    assert slot['calendar_three_year_by_draft_offset']['2']==pytest.approx(72.25)


def test_leave_one_class_is_sensitivity_not_confidence_interval():
    slot=run([row(2014,values=(0,0,0)),row(2015,values=(200,0,0))])['cases'][0]['slots'][0]
    assert slot['estimate_first_three_post_draft']==100
    assert slot['leave_one_class_mean_min']==0 and slot['leave_one_class_mean_max']==200
    assert slot['sensitivity_kind']=='leave_one_class_not_confidence_or_prediction_interval'


def test_missing_selection_and_identity_remain_explicit():
    doc=document([row(2014,slot=2),row(2015,player=None)])
    case=audit(doc,release_season=2020,complete_through=2019,max_slots=1)['cases'][0]
    assert case['gap_counts']=={'selection_rank_absent':1,'identity_unresolved':1}


def test_source_case_separation_and_input_immutability():
    doc=document([row(2014)]);other=deepcopy(doc['cases'][0]);other['selections'][0]['raw_observed']['3']=[200,160,120]
    doc['cases'].append(other);before=deepcopy(doc)
    cases=audit(doc,release_season=2020,complete_through=2019,max_slots=1)['cases']
    assert cases[1]['slots'][0]['estimate_first_three_post_draft']==2*cases[0]['slots'][0]['estimate_first_three_post_draft']
    assert doc==before


@pytest.mark.parametrize('values',[(float('nan'),0,0),(True,0,0)])
def test_invalid_labels_rejected(values):
    with pytest.raises(ValueError):run([row(2014,values=values)])


def test_same_year_completed_boundary_cannot_be_used_at_annual_release():
    with pytest.raises(ValueError,match='before release'):
        audit(document([]),release_season=2020,complete_through=2020,max_slots=1)
