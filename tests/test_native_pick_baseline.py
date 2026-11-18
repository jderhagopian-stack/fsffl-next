"""Chronological benchmark: missingness and coordinate isolation matter more than fit."""
from copy import deepcopy

import pytest

from scripts.evaluate_native_pick_baseline import evaluate


def row(year, slot=1, values=(100, 80, 60), player='player'):
    return dict(draft_season=year, rank=slot, player_id=player, raw_observed={'3':list(values)})


def document(rows):
    return dict(cases=[dict(economic_coordinate=dict(rules={'lineup':'synthetic'},scoring_signature='fixed',
        native_model_version='synthetic',panel_sha256='panel'),selections=rows,
        selection_evidence_limitations=['synthetic rank proxy'])])


def run(doc, **changes):
    args=dict(horizon=3,discount=.85,heldout_classes=[2017],max_slots=1,complete_through=2025)
    args.update(changes)
    return evaluate(doc,**args)


def test_past_outcome_must_mature_before_heldout_and_future_classes_cannot_train():
    result=run(document([row(2014),row(2015,values=(999,999,999)),row(2017),row(2018)]))
    fold=result['cases'][0]['folds'][0]
    assert fold['training_classes']==[2014]
    assert fold['covered']==1 and fold['mae']==0
    assert fold['predictions'][0]['estimate']==pytest.approx(211.35)
    assert result['production_eligible'] is False
    assert fold['predictive_intervals_available'] is False


@pytest.mark.parametrize('gap',[None,'absent_row','absent_identity'])
def test_missing_training_mass_cannot_be_discarded_or_zero_filled(gap):
    rows=[row(2014),row(2015,values=(100,None,60)),row(2018)]
    if gap=='absent_row':rows[1]=row(2015,slot=2)
    if gap=='absent_identity':rows[1]=row(2015,player=None)
    fold=run(document(rows),heldout_classes=[2018])['cases'][0]['folds'][0]
    assert fold['covered']==0 and fold['mae'] is None
    assert fold['abstentions']=={'incomplete_training_slot':1}


def test_observed_zero_is_a_real_label_and_signed_contributions_are_retained():
    fold=run(document([row(2014,values=(0,-10,0)),row(2017,values=(0,-10,0))]))['cases'][0]['folds'][0]
    assert fold['covered']==1 and fold['predictions'][0]['estimate']==-8.5


def test_target_censoring_not_retirement_and_no_immature_training():
    fold=run(document([row(2014),row(2024)]),heldout_classes=[2024])['cases'][0]['folds'][0]
    assert fold['abstentions']=={'target_right_censored':1}
    fold=run(document([row(2015),row(2017)]))['cases'][0]['folds'][0]
    assert fold['training_classes']==[] and fold['abstentions']=={'no_mature_training_classes':1}


def test_rules_cases_are_never_pooled_and_identity_fingerprints_change():
    doc=document([row(2014),row(2017)])
    other=deepcopy(doc['cases'][0]);other['economic_coordinate']['rules']={'lineup':'different'}
    other['selections'][0]['raw_observed']['3']=[200,160,120]
    first=run(doc);doc['cases'].append(other);both=run(doc)
    assert both['cases'][0]['folds'][0]['mae']==0
    assert both['cases'][1]['folds'][0]['mae']==pytest.approx(211.35)
    assert first['input_sha256']!=both['input_sha256']


@pytest.mark.parametrize('change',['duplicate','nan','unknown_coordinate'])
def test_invalid_evidence_fails_explicitly(change):
    doc=document([row(2014),row(2017)])
    if change=='duplicate':doc['cases'][0]['selections'].append(row(2014))
    if change=='nan':doc['cases'][0]['selections'][0]['raw_observed']['3'][0]=float('nan')
    if change=='unknown_coordinate':doc['cases'][0]['economic_coordinate']['scoring_signature']=''
    with pytest.raises(ValueError):run(doc)


def test_career_is_not_supported_by_a_finite_observed_window():
    with pytest.raises(ValueError):run(document([]),horizon=20)


def test_isotonic_prior_pools_training_rank_reversals_without_filling_gaps():
    from scripts.evaluate_native_pick_baseline import monotone_slot_means
    assert monotone_slot_means({1:100,2:200,4:20})=={1:150,2:150,4:20}
    doc=document([row(2014,1,(100,0,0)),row(2014,2,(200,0,0)),row(2017,1,(10,0,0)),row(2017,2,(999,0,0))])
    first=run(doc,max_slots=3,estimator='isotonic_slot_mean')['cases'][0]['folds'][0]
    assert [r['estimate'] for r in first['predictions']]==[150,150]
    assert first['abstentions']=={'incomplete_training_slot':1}
    doc['cases'][0]['selections'][-1]['raw_observed']['3']=[0,0,0]
    changed=run(doc,max_slots=3,estimator='isotonic_slot_mean')['cases'][0]['folds'][0]
    assert [r['estimate'] for r in changed['predictions']]==[150,150]


def test_isotonic_pooling_uses_block_counts_and_avoids_large_sum_overflow():
    from scripts.evaluate_native_pick_baseline import monotone_slot_means
    assert monotone_slot_means({1:0,2:30,3:60})=={1:30,2:30,3:30}
    values=monotone_slot_means({1:8e307,2:1e308})
    assert values[1]==values[2]==9e307
