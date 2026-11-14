"""Seasonal persistence, provenance and refresh reuse, independent of model fitting."""
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import pytest

from tests.test_native_pick_research import NOW, evidence, estimate
from fsffl.persistence.native_pick_curve import curve_reference, load_research_curve, save_research_curve
from fsffl.state.models import DraftPick
from fsffl.value.native_pick_curve_releases import (
    NativePickCurveRelease, apply_frozen_native_pick_curve, freeze_native_pick_research_curve,
)


def release(**changes):
    fields=dict(economic_scope_id='shared-eligible-universe',
        evaluation_season=2026,draft_season=2027,round=1,team_count=12,rules_signature='rules',
        scoring_signature='scoring',native_coordinate_id='native-coordinate',stage='annual_baseline',
        released_at=NOW,event_evidence_refs=('platform-picks-available',))
    fields.update(changes)
    return NativePickCurveRelease(**fields)


def apply(curve, source=None, **changes):
    source=source or evidence()
    arguments=dict(owner_team_id=source.owner_team_id,probabilities=source.slot_evidence,
        as_of=NOW,economic_scope_id='shared-eligible-universe',rules_signature='rules',
        scoring_signature='scoring',native_coordinate_id='native-coordinate',evaluation_season=2026,team_count=12)
    arguments.update(changes)
    return apply_frozen_native_pick_curve(curve,DraftPick(pick_id='pick',league_id='league',season=2027,round=1,
        original_team_id='origin'),**arguments)


class Store:
    def __init__(self):self.rows={};self.reads=0;self.writes=0
    def get_reusable_artifact(self,key):
        self.reads+=1
        return self.rows.get(key)
    def put_artifact(self,row):
        self.writes+=1
        self.rows[row.key]=row


def test_restored_release_matches_existing_math_and_many_refreshes_do_not_refit_or_access_db():
    source=evidence();curve=freeze_native_pick_research_curve(source,release());store=Store()
    reference=save_research_curve(store,curve)
    save_research_curve(store,curve)
    assert store.writes==1
    restored=load_research_curve(store,reference,expected_economic_scope_key=reference.economic_scope_key,as_of=NOW)
    counts=store.reads,store.writes
    with patch('fsffl.value.native_pick_curve_releases.native_slot_research_distribution',side_effect=AssertionError('refit')):
        for _ in range(100):
            actual=apply(restored)
            assert actual.three_year.estimate.distribution==estimate(source).three_year.estimate.distribution
            assert actual.career.estimate.distribution==estimate(source).career.estimate.distribution
    assert (store.reads,store.writes)==counts
    assert actual.production_eligible is False


def test_owner_changes_do_not_change_slot_release_and_probabilities_only_change_mixture():
    source=evidence();first=source.slot_forecasts[0].model_dump()
    second={**first,'slot_in_round':2,'scenarios':[{'probability':1,'annual':[{'season':2027,'raw_shapley':520}],
        'terminal_start_season':2028,'terminal_raw_shapley':0}]}
    source=evidence(slot_forecasts=[first,second]);curve=freeze_native_pick_research_curve(source,release())
    moved=source.model_copy(update={'owner_team_id':'new-owner'})
    assert freeze_native_pick_research_curve(moved,release()).curve_id==curve.curve_id
    probabilities=evidence(slot_probabilities=[{'slot_in_round':2,'probability':1}]).slot_evidence
    assert apply(curve).career.estimate.distribution.mean==260
    assert apply(curve,probabilities=probabilities,owner_team_id='new-owner').career.estimate.distribution.mean==520
    assert curve.slots[0].career.mean==260


def test_missing_mass_withholds_horizon_without_rebuilding():
    curve=freeze_native_pick_research_curve(evidence(),release())
    probabilities=evidence(slot_probabilities=[{'slot_in_round':1,'probability':.5},
        {'slot_in_round':2,'probability':.5}]).slot_evidence
    result=apply(curve,probabilities=probabilities)
    assert result.career.estimate is None and result.career.missing_slots==(2,)


def test_explicit_stage_preserves_old_release_and_reader_does_not_select_latest():
    store=Store();old=freeze_native_pick_research_curve(evidence(),release())
    old_ref=save_research_curve(store,old)
    later=release(stage='post_nfl_draft',supersedes_curve_id=old.curve_id,released_at=NOW+timedelta(days=1))
    new=freeze_native_pick_research_curve(evidence(),later);new_ref=save_research_curve(store,new)
    assert old_ref!=new_ref and store.writes==2
    assert load_research_curve(store,old_ref,expected_economic_scope_key=old_ref.economic_scope_key,as_of=NOW).curve_id==old.curve_id
    with pytest.raises(ValueError,match='postdates'):
        load_research_curve(store,new_ref,expected_economic_scope_key=new_ref.economic_scope_key,as_of=NOW)


def test_missing_invalidated_and_corrupt_artifacts_never_rebuild():
    store=Store();curve=freeze_native_pick_research_curve(evidence(),release());ref=curve_reference(curve)
    assert load_research_curve(store,ref,expected_economic_scope_key=ref.economic_scope_key,as_of=NOW) is None
    save_research_curve(store,curve);row=store.rows[ref.key]
    store.rows[ref.key]=replace(row,invalidated_at=NOW)
    assert load_research_curve(store,ref,expected_economic_scope_key=ref.economic_scope_key,as_of=NOW) is None
    with pytest.raises(ValueError,match='invalidated'):save_research_curve(store,curve)
    store.rows[ref.key]=replace(row,payload={**row.payload,'native_input_fingerprint':'corrupted'})
    with pytest.raises(ValueError,match='exact reference'):
        load_research_curve(store,ref,expected_economic_scope_key=ref.economic_scope_key,as_of=NOW)
    assert store.writes==1


@pytest.mark.parametrize('field',['economic_scope_id','rules_signature','scoring_signature','native_coordinate_id'])
def test_binding_rejects_wrong_scope(field):
    curve=freeze_native_pick_research_curve(evidence(),release())
    with pytest.raises(ValueError,match='economic scope'):apply(curve,**{field:'wrong'})


def test_origin_and_draft_year_not_borrowed_from_other_picks():
    curve=freeze_native_pick_research_curve(evidence(),release())
    for changes in ({'original_team_id':'other'},{'draft_season':2028}):
        with pytest.raises(ValueError,match='origin'):
            apply(curve,probabilities=evidence().slot_evidence.model_copy(update=changes))


def test_correction_requires_reason_and_exact_predecessor():
    for changes in ({'stage':'correction'},{'stage':'correction','supersedes_curve_id':'old'},
                    {'revision':2,'supersedes_curve_id':'old'}):
        with pytest.raises(ValueError):release(**changes)
    assert release(stage='correction',supersedes_curve_id='old',correction_reason='verified defect').stage=='correction'
