from copy import deepcopy

import pytest

from scripts.fit_native_pick_selection_transport import fit


def row(value,position='WR'):
    return {'rank':1,'position':position,'annual':[value]*7,'career_authority':dict(low=value*7,reference_center=value*8,high=value*9,width=value*2)}


def document():
    return {'economic_coordinate':{'rules':{'team_count':1},'scoring_coordinate':'connected_league_fantasy_points','source_fingerprints':['pinned']},
        'selection_cases':[{'draft_class':2019,'source_case_id':'one','selections':[{'rank':1,'position':'WR'}]}],
        'outcome_cases':[{'draft_class':2014,'selections':[row(10)]},{'draft_class':2016,'selections':[row(30)]}],
        'fallback_cases':[{'draft_class':2019,'source_case_id':'fallback','selections':[row(100)]}]}


def run(d):return fit(d,release_season=2026,draft_season=2027,max_slots=1)


def test_empirical_outcome_class_weights_and_calendar_preserve_joint_paths_and_inputs():
    d=document();before=deepcopy(d);r=run(d);s=r['slots'][0]
    assert [x['probability'] for x in s['three_year_forecast']['scenarios']]==[.5,.5]
    assert s['three_year_forecast']['scenarios'][0]['annual'][0]['season']==2027
    assert s['career_authority']['reference_center']==160 and s['career_prefix_reference']==[20.]*7
    assert s['career_backoff_mass']==0 and d==before and r['production_eligible'] is False


def test_selection_classes_have_equal_weight_despite_different_draft_counts():
    d=document();d['outcome_cases'][1]['selections'][0]['position']='QB'
    for i in range(3):d['selection_cases'].append({'draft_class':2020,'source_case_id':str(i),'selections':[{'rank':1,'position':'QB'}]})
    s=run(d)['slots'][0];m={(x['position'],x['positional_rank']):x['probability'] for x in s['selection_feature_mass']}
    assert m=={('QB',1):.5,('WR',1):.5} and s['career_backoff_mass']==.5


def test_missing_mass_uses_explicit_forecast_backoff_not_silent_renormalization():
    d=document();d['outcome_cases'][1]['selections'][0]['annual'][0]=None;d['outcome_cases'][1]['selections'][0]['career_authority']=None
    s=run(d)['slots'][0]
    assert s['three_year_backoff_mass']==.5 and s['career_backoff_mass']==.5
    assert s['career_authority']['reference_center']==440
    d['fallback_cases']=[];s=run(d)['slots'][0]
    assert s['three_year_forecast'] is None and s['career_authority'] is None


def test_late_missingness_does_not_destroy_supported_first3():
    d=document();d['outcome_cases'][1]['selections'][0]['annual'][6]=None;d['outcome_cases'][1]['selections'][0]['career_authority']=None
    s=run(d)['slots'][0];assert s['three_year_backoff_mass']==0 and s['career_backoff_mass']==.5


@pytest.mark.parametrize('change',['duplicate_selection','duplicate_class','censored','gap','nan','missing_assumption','coordinate'])
def test_unsupported_input_never_becomes_a_forecast(change):
    d=document()
    if change=='duplicate_selection':d['selection_cases']*=2
    if change=='duplicate_class':d['outcome_cases'][1]['draft_class']=2014
    if change=='censored':d['outcome_cases'][1]['draft_class']=2020
    if change=='gap':d['selection_cases'][0]['selections'][0]['rank']=2
    if change=='nan':d['outcome_cases'][0]['selections'][0]['annual'][0]=float('nan')
    if change=='missing_assumption':d['outcome_cases'][0]['selections'][0]['assumed_seasons']=[2014]
    if change=='coordinate':d['economic_coordinate']['scoring_coordinate']='legacy_points'
    with pytest.raises(ValueError):run(d)


def test_composition_preserves_one_prefix_authority_without_double_counting():
    from scripts.fit_native_pick_empirical_prefix import fit as prefix_fit
    from scripts.fit_native_pick_selection_transport import compose_reference
    d=document();long=run(d)
    prefix=prefix_fit({'economic_coordinate':d['economic_coordinate'],'source_cases':[{'draft_class':2019,'source_case_id':'actual','selections':[{'rank':1,'annual':[100.,200.,300.]}]}],'fallback_cases':[]},release_season=2026,draft_season=2027,max_slots=1)
    result=compose_reference(prefix,long);s=result['slots'][0]
    assert s['career_prefix_reference'][:3]==[100.,200.,300.]
    assert s['career_authority']['reference_center']==pytest.approx(160+600-60)
    assert s['career_authority']['width']==40 and result['production_eligible'] is False
    broken=deepcopy(prefix);broken['draft_season']=2028
    with pytest.raises(ValueError):compose_reference(broken,long)
    broken=deepcopy(prefix);broken['slots'][0]['annual_mean'][0]=999
    with pytest.raises(ValueError):compose_reference(broken,long)
    for supplied in ([100.], [100.,200.,float('nan')]):
        broken=deepcopy(prefix);broken['slots'][0]['annual_mean']=supplied
        with pytest.raises(ValueError):compose_reference(broken,long)
