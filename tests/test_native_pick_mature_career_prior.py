from copy import deepcopy

import pytest

from scripts.fit_native_pick_mature_career_prior import fit
from fsffl.value.career_tail import CareerTailFeatures,build_career_tail_authority
from fsffl.state.models import LeagueRules,LineupRequirement


def document():
    rules=LeagueRules(team_count=12,roster_size=24,scoring=(),lineup=tuple(LineupRequirement(slot=s,count=n) for s,n in [('QB',1),('RB',2),('WR',3),('TE',1),('FLEX',1),('SUPERFLEX',1)]))
    row={'draft_season':2018,'rank':1,'player_id':'sample','position':'WR','native_y1_y7':[10.]*7,
         'origin_age_years':22.,'origin_experience_years':0.,'origin_connected_points':100.}
    return {'cases':[{'economic_coordinate':{'rules':rules.model_dump(mode='json'),'scoring_coordinate':'connected_league_fantasy_points','source_fingerprints':['pinned']},'selections':[row]}]}


def run(doc,**kwargs):return fit(doc,release_season=2026,max_slots=1,**kwargs)


def test_accepted_terminal_is_added_after_literal_undiscounted_first7_without_overlap():
    d=document();before=deepcopy(d);r=run(d);s=r['cases'][0]['slots'][0];sample=s['samples'][0]
    rules=LeagueRules.model_validate(d['cases'][0]['economic_coordinate']['rules'])
    tail=build_career_tail_authority(CareerTailFeatures(player_id='sample',position='WR',age_years=22,experience_years=0,current_points=100,
        current_points_coordinate='connected_league_fantasy_points',prior_points_coordinate='connected_league_fantasy_points'),rules=rules)
    assert s['authority']['reference_center']==pytest.approx(70+tail.reference_center)
    assert sample['prefix_end_season']==2024 and sample['terminal_start_season']==2025
    assert r['production_eligible'] is False and 'stddev' not in s['authority'] and d==before


def test_missing_or_censored_class_never_becomes_survivor_filtered_training():
    d=document();second=deepcopy(d['cases'][0]['selections'][0]);second['draft_season']=2019;second['player_id']='other';second['native_y1_y7'][2]=None;d['cases'][0]['selections'].append(second)
    s=run(d)['cases'][0]['slots'][0];assert s['authority'] is None and s['sample_count']==1 and s['requested_classes']==2
    d['cases'][0]['selections'][-1]['draft_season']=2020
    s=run(d)['cases'][0]['slots'][0];assert s['requested_classes']==1  # 2020 Y7 is not completed before2026.


def test_corroborated_zero_remains_an_assumption_and_unknown_features_withhold():
    d=document();d['cases'][0]['selections'][0]['native_y1_y7'][1]=None
    evidence=[{'player_id':'sample','season':2019,'source_sha256':'pinned','status':'corroborated_source_absence_not_verified_zero'}]
    with pytest.raises(ValueError):run(d,corroborated_absences=evidence)
    result=run(d,assumption_ref='explicit-research-only',corroborated_absences=evidence)
    assert result['cases'][0]['slots'][0]['samples'][0]['assumed_seasons']==[2019]
    del d['cases'][0]['selections'][0]['origin_age_years']
    assert run(d,assumption_ref='research',corroborated_absences=evidence)['cases'][0]['slots'][0]['authority'] is None


@pytest.mark.parametrize('change',['scoring','capacity','duplicate','nan'])
def test_wrong_coordinate_duplicates_and_nonfinite_labels_do_not_produce_authority(change):
    d=document();case=d['cases'][0]
    if change=='scoring':case['economic_coordinate']['scoring_coordinate']='fixed-panel'
    if change=='capacity':case['economic_coordinate']['rules']['lineup']=[r for r in case['economic_coordinate']['rules']['lineup'] if r['slot']!='SUPERFLEX']
    if change=='duplicate':case['selections'].append(deepcopy(case['selections'][0]))
    if change=='nan':case['selections'][0]['native_y1_y7'][0]=float('nan')
    with pytest.raises(ValueError):run(d)


@pytest.mark.parametrize('field,value',[('rank',True),('rank',0),('draft_season',2018.5),('draft_season',0)])
def test_class_and_slot_identifiers_must_be_positive_integers(field,value):
    d=document();d['cases'][0]['selections'][0][field]=value
    with pytest.raises(ValueError):run(d)


@pytest.mark.parametrize('kwargs',[{'release_season':2026.5,'max_slots':1},{'release_season':2026,'max_slots':True},{'release_season':2026,'max_slots':0}])
def test_release_and_slot_count_are_explicit_integers(kwargs):
    with pytest.raises(ValueError):fit(document(),**kwargs)
