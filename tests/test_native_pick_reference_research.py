from datetime import timedelta

import pytest

from fsffl.state.models import DraftPick
from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority
from fsffl.value.native_pick_reference_research import (
    FrozenNativePickReferenceCurve, FrozenCareerReferenceSlot, apply_frozen_native_pick_reference_curve,
)
from fsffl.persistence.native_pick_curve import save_research_curve, load_research_curve, NativePickCurveReference
from tests.test_native_pick_research import evidence, NOW
from tests.test_native_pick_curve_releases import release, Store


def curve():
    return FrozenNativePickReferenceCurve(release=release(team_count=2),source_as_of=NOW,
        source_fingerprints=('synthetic-complete-career-source',),forecast_model_version='synthetic-career-model',
        authority_basis_model_versions=('accepted-family-version-placeholder',),slots=(
            FrozenCareerReferenceSlot(slot_in_round=1,authority=CareerForwardModelAuthority(low=10,reference_center=30,high=50,width=40)),
            FrozenCareerReferenceSlot(slot_in_round=2,authority=CareerForwardModelAuthority(low=0,reference_center=10,high=20,width=20))))


def apply(c,probabilities=None,**changes):
    args=dict(owner_team_id='owner',probabilities=probabilities or evidence().slot_evidence,as_of=NOW,
        economic_scope_id='shared-eligible-universe',rules_signature='rules',scoring_signature='scoring',
        native_coordinate_id='native-coordinate',evaluation_season=2026,team_count=2)
    args.update(changes)
    return apply_frozen_native_pick_reference_curve(c,DraftPick(pick_id='pick',league_id='l',season=2027,round=1,
        original_team_id='origin'),**args)


def test_reference_mix_preserves_outer_authority_without_inventing_distribution():
    p=evidence(slot_probabilities=[{'slot_in_round':1,'probability':.25},{'slot_in_round':2,'probability':.75}]).slot_evidence
    result=apply(curve(),p)
    assert result.authority.reference_center==15
    assert result.authority.low==2.5 and result.authority.high==27.5 and result.authority.width==25
    assert result.production_eligible is False and result.point_basis=='model_reference'
    assert 'stddev' not in result.model_dump_json() and 'p10' not in result.model_dump_json()


def test_missing_positive_slot_authority_withholds_instead_of_renormalizing():
    c=curve();c=c.model_copy(update={'slots':(c.slots[0],c.slots[1].model_copy(update={'authority':None}))})
    p=evidence(slot_probabilities=[{'slot_in_round':1,'probability':.5},{'slot_in_round':2,'probability':.5}]).slot_evidence
    result=apply(c,p)
    assert result.authority is None and result.missing_slots==(2,)
    assert apply(c).authority.reference_center==30


def test_reference_codec_reuses_store_owner_and_keeps_distribution_keys_distinct():
    c=curve();store=Store();reference=save_research_curve(store,c);save_research_curve(store,c)
    assert store.writes==1
    restored=load_research_curve(store,reference,expected_economic_scope_key=reference.economic_scope_key,as_of=NOW)
    assert isinstance(restored,FrozenNativePickReferenceCurve) and restored.curve_id==c.curve_id
    old_style=NativePickCurveReference(reference.economic_scope_key,reference.curve_id)
    assert old_style.key!=reference.key
    assert load_research_curve(store,old_style,expected_economic_scope_key=reference.economic_scope_key,as_of=NOW) is None


@pytest.mark.parametrize('changes',[{'rules_signature':'other'},{'evaluation_season':2027},
    {'as_of':NOW-timedelta(days=1)},{'owner_team_id':''}])
def test_scope_and_cutoff_are_shared_with_the_existing_curve_contract(changes):
    with pytest.raises(ValueError):apply(curve(),**changes)


def test_no_historical_outcomes_can_be_relabelled_prospective_reference_evidence():
    with pytest.raises(ValueError):
        FrozenNativePickReferenceCurve(**{**curve().model_dump(),'evidence_kind':'historical_realized_outcomes'})
