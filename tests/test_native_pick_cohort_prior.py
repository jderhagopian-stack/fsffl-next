from copy import deepcopy

import pytest

from scripts.fit_native_pick_cohort_prior import fit
from tests.test_native_pick_baseline import document,row


def run(rows,**kwargs):
    return fit(document(rows),release_season=2020,draft_season=2021,round_number=1,
               team_count=1,complete_through=2019,selection_policy_ref='synthetic-qualification',**kwargs)


def test_empirical_fit_preserves_joint_trajectories_and_uses_only_mature_classes():
    result=run([row(2014,values=(10,100,0)),row(2015,values=(100,0,10)),row(2018,values=(999,999,999))])
    case=result['cases'][0];scenarios=case['forecasts'][0]['scenarios']
    assert case['training_classes']==[2014,2015]
    assert [s['probability'] for s in scenarios]==[.5,.5]
    assert [[a['raw_shapley'] for a in s['annual']] for s in scenarios]==[[10,100,0],[100,0,10]]
    assert [a['season'] for a in scenarios[0]['annual']]==[2021,2022,2023]
    assert result['production_eligible'] is False and case['career_available'] is False


def test_missing_training_class_is_not_dropped():
    result=run([row(2014),row(2015,values=(100,None,60))])
    assert result['cases'][0]['forecasts']==[]
    assert result['cases'][0]['unsupported_slots']==[1]


def test_corroboration_is_an_explicit_training_assumption_and_does_not_mutate_input():
    rows=[row(2014,values=(100,None,60))];before=deepcopy(rows)
    gap={'player_id':'player','season':2015,'status':'corroborated_source_absence_not_verified_zero','source_sha256':'pinned'}
    with pytest.raises(ValueError,match='assumption'):run(rows,corroborated_gaps=[gap])
    result=run(rows,corroborated_gaps=[gap],absence_assumption_ref='research-only-source-policy')
    assert result['cases'][0]['forecasts'][0]['scenarios'][0]['annual'][1]['raw_shapley']==0
    assert len(result['cases'][0]['assumed_training_seasons'])==1
    assert rows==before


def test_stats_presence_cannot_be_zero_filled():
    gap={'player_id':'player','season':2015,'status':'stats_row_present_native_label_unresolved','source_sha256':'pinned'}
    with pytest.raises(ValueError):run([row(2014)],corroborated_gaps=[gap],absence_assumption_ref='research')


def test_source_cases_are_not_pooled_and_invalid_label_fails():
    doc=document([row(2014)]);other=deepcopy(doc['cases'][0]);other['selections'][0]['raw_observed']['3']=[200,160,120];doc['cases'].append(other)
    result=fit(doc,release_season=2020,draft_season=2020,round_number=1,team_count=1,complete_through=2019,selection_policy_ref='synthetic')
    assert len(result['cases'])==2
    assert result['cases'][0]['forecasts']!=result['cases'][1]['forecasts']
    with pytest.raises(ValueError):run([row(2014,values=(float('nan'),0,0))])


def test_fitted_prior_uses_existing_frozen_curve_without_inventing_Career():
    from fsffl.value.native_pick_curve_releases import freeze_native_pick_research_curve
    from tests.test_native_pick_curve_releases import release
    from tests.test_native_pick_research import evidence
    doc=document([row(2014,values=(100,80,60)),row(2015,values=(200,160,120))])
    fitted=fit(doc,release_season=2026,draft_season=2027,round_number=1,team_count=12,
               complete_through=2025,selection_policy_ref='synthetic-test')
    source=evidence(slot_forecasts=fitted['cases'][0]['forecasts'],forecast_model_version=fitted['forecast_model_version'])
    curve=freeze_native_pick_research_curve(source,release())
    assert curve.slots[0].three_year.mean==pytest.approx(214.2)
    assert curve.slots[0].career is None
    assert all(s.three_year is None for s in curve.slots[1:])
    assert curve.production_eligible is False
