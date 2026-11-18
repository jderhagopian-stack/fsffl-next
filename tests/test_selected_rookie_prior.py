from copy import deepcopy

import pytest

from scripts.evaluate_selected_rookie_prior import evaluate


def case():
    entrants=[dict(player_id=str(y),entry_season=y,position='WR',nfl_pick=10,raw_three_year=100.,label_basis='observed') for y in (2014,2017,2023)]
    return dict(economic_coordinate=dict(rules={'synthetic':True},scoring_signature='s',native_model_version='v',panel_sha256='h'),
        entrants=entrants,draft_selections=[dict(player_id=str(y),draft_season=y,rank=1) for y in (2017,2023)])


def test_only_mature_training_and_observed_conditional_targets_are_used():
    result=evaluate(case(),target_season=2023,validation_seasons=[2017])
    assert result['training_classes']==[2014,2017]
    assert result['selection_folds'][0]['training_classes']==[2014]
    assert result['target_count']==1 and result['production_eligible'] is False
    assert result['capital_mae']==pytest.approx(0,abs=.001)
    assert result['career_available'] is result['predictive_intervals_available'] is False


def test_validation_target_never_trains_or_selects_hyperparameters():
    doc=case();first=evaluate(doc,target_season=2023,validation_seasons=[2017])
    doc['entrants'][-1]['raw_three_year']=10000
    second=evaluate(doc,target_season=2023,validation_seasons=[2017])
    assert first['model']==second['model'] and first['selected_alpha']==second['selected_alpha']
    assert first['predictions'][0]['capital_mean']==second['predictions'][0]['capital_mean']


def test_assumptions_may_train_with_reference_but_never_become_validation_truth():
    doc=case();doc['entrants'][-1].update(label_basis='research_assumed_source_absence',assumption_ref='research')
    result=evaluate(doc,target_season=2023,validation_seasons=[2017])
    assert result['target_count']==0 and result['unscored_ranks']==[1]


@pytest.mark.parametrize('change',['duplicate','missing_assumption','future_validation','invalid_pick'])
def test_invalid_identity_or_evidence_fails(change):
    doc=case();years=[2017]
    if change=='duplicate':doc['entrants'].append(deepcopy(doc['entrants'][0]))
    if change=='missing_assumption':doc['entrants'][0]['label_basis']='research_assumed_source_absence'
    if change=='future_validation':years=[2022]
    if change=='invalid_pick':doc['entrants'][0]['nfl_pick']=0
    with pytest.raises(ValueError):evaluate(doc,target_season=2023,validation_seasons=years)
