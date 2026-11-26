from copy import deepcopy

import pytest

from scripts.evaluate_pick_missingness_sensitivity import compare
from tests.test_native_pick_baseline import document, row


def run(doc, keys=(), **changes):
    args=dict(panel_keys=set(keys),panel_sha256='panel',assumption_ref='explicit-research-hypothesis',
        horizon=3,discount=.85,heldout_classes=[2018],max_slots=1,complete_through=2025)
    args.update(changes)
    return compare(doc,**args)


def test_only_training_source_absence_can_be_assumed_zero_and_inputs_unchanged():
    doc=document([row(2014,values=(100,None,60)),row(2018)])
    original=deepcopy(doc)
    result=run(doc)
    fold=result['cases'][0]['folds'][0]
    assert fold['strict_covered']==0 and fold['scenario_covered']==1
    assert fold['scenario']['predictions'][0]['estimate']==pytest.approx(143.35)
    assert fold['scenario']['predictions'][0]['observed']==pytest.approx(211.35)
    assert fold['assumed_training_seasons']==1
    assert doc==original and result['production_eligible'] is False
    assert result['validation_targets']=='observed_only'


def test_missing_native_replay_when_source_row_exists_is_not_filled():
    doc=document([row(2014,values=(100,None,60)),row(2018)])
    fold=run(doc,keys=[('player',2015)])['cases'][0]['folds'][0]
    assert fold['assumed_training_seasons']==0 and fold['scenario_covered']==0


def test_missing_validation_target_remains_unknown_even_when_source_row_absent():
    doc=document([row(2014),row(2018,values=(100,None,60))])
    fold=run(doc)['cases'][0]['folds'][0]
    assert fold['scenario_covered']==0 and fold['assumed_training_seasons']==0


def test_missing_identity_and_immature_censored_classes_are_not_imputed():
    doc=document([row(2014,player=None,values=(None,None,None)),row(2024)])
    fold=run(doc,heldout_classes=[2024])['cases'][0]['folds'][0]
    assert fold['scenario_covered']==fold['assumed_training_seasons']==0


@pytest.mark.parametrize('changes',[{'assumption_ref':''},{'panel_sha256':'different-panel'}])
def test_explicit_assumption_and_exact_panel_identity_required(changes):
    with pytest.raises(ValueError):run(document([row(2014),row(2018)]),**changes)


def test_strict_and_scenario_errors_are_also_reported_on_common_observed_targets():
    doc=document([row(2014),row(2018)])
    fold=run(doc)['cases'][0]['folds'][0]
    assert fold['common_covered']==1
    assert fold['common_strict_mae']==fold['common_scenario_mae']==0
