"""Research bridge only: calendar alignment, uncertainty and evidence barriers."""
from datetime import datetime, timezone, timedelta
from math import sqrt

import pytest
from pydantic import ValidationError

from fsffl.value.native_pick_research import NativePickResearchEvidence, estimate_native_pick_research

NOW=datetime(2026,11,14,tzinfo=timezone.utc)


def evidence(*, draft=2027, scenarios=None, **changes):
    if scenarios is None:
        scenarios=[{'probability':1,'annual':[{'season':draft+i,'raw_shapley':v} for i,v in enumerate((100,80,60))],
            'terminal_start_season':draft+3,'terminal_raw_shapley':20}]
    probabilities=changes.pop('slot_probabilities',[{'slot_in_round':1,'probability':1}])
    slot_evidence=changes.pop('slot_evidence',dict(draft_season=draft,original_team_id='origin',
        slot_probabilities=probabilities,expected_slot=sum(p['slot_in_round']*p['probability'] for p in probabilities),
        median_slot=1,early_probability=1,mid_probability=0,late_probability=0,simulation_count=100,
        simulation_model_version='synthetic-simulation',simulation_input_fingerprint='synthetic-slot-source',
        draft_order_policy_id='synthetic-policy',draft_order_policy_version='1',draft_order_policy_authority='synthetic',
        draft_order_projection_model_version='synthetic-origin',provenance='synthetic-test'))
    fields=dict(pick_id='pick',original_team_id='origin',owner_team_id='different-owner',evaluation_season=2026,
        draft_season=draft,round=1,team_count=12,evidence_as_of=NOW,rules_signature='rules',scoring_signature='scoring',
        native_coordinate_id='native-coordinate',forecast_model_version='synthetic-joint',
        source_fingerprints=['synthetic-source'],slot_evidence=slot_evidence,
        slot_forecasts=[{'slot_in_round':1,'scenarios':scenarios}])
    fields.update(changes)
    return NativePickResearchEvidence(**fields)


def estimate(e,**changes):
    return estimate_native_pick_research(e,**dict(as_of=NOW,expected_rules_signature='rules',
        expected_scoring_signature='scoring',expected_native_coordinate_id='native-coordinate',**changes))


@pytest.mark.parametrize(('draft','expected'),[(2026,211.35),(2027,142.8),(2028,72.25),(2029,0)])
def test_calendar_window_and_career_preserve_frozen_discount_and_undiscounted_career(draft,expected):
    result=estimate(evidence(draft=draft))
    assert result.three_year.estimate.distribution.mean==pytest.approx(expected)
    assert result.career.estimate.distribution.mean==260
    assert result.original_team_id=='origin' and result.owner_team_id=='different-owner'
    assert result.production_eligible is False
    assert result.three_year.status==result.career.status=='research_only'
    assert result.three_year.estimate.scale.scale_id.startswith('research-native-shapley:')


def test_calendar_proof_allows_zero_beyond_three_year_window_without_fabricating_career():
    result=estimate(evidence(draft=2030,slot_forecasts=[]))
    assert result.three_year.estimate.distribution.mean==result.three_year.estimate.distribution.stddev==0
    assert result.career.estimate is None and result.career.missing_slots==(1,)


def test_joint_path_variance_does_not_add_correlated_annual_standard_deviations():
    scenarios=[{'probability':.5,'annual':[{'season':2027,'raw_shapley':a},{'season':2028,'raw_shapley':b}],
        'terminal_start_season':2029,'terminal_raw_shapley':0} for a,b in ((100,0),(0,100))]
    result=estimate(evidence(scenarios=scenarios))
    assert result.career.estimate.distribution.mean==100
    assert result.career.estimate.distribution.stddev==0
    assert result.three_year.estimate.distribution.mean==pytest.approx(78.625)
    assert result.three_year.estimate.distribution.stddev==pytest.approx(6.375)


def test_existing_slot_mixture_preserves_between_slot_and_within_slot_variance():
    e=evidence();a=e.slot_forecasts[0].model_dump(mode='json')
    b={**a,'slot_in_round':2,'scenarios':[{'probability':1,'annual':[{'season':2027,'raw_shapley':520}],
        'terminal_start_season':2028,'terminal_raw_shapley':0}]}
    result=estimate(evidence(slot_probabilities=[{'slot_in_round':1,'probability':.25},{'slot_in_round':2,'probability':.75}],slot_forecasts=[a,b]))
    assert result.career.estimate.distribution.mean==455
    assert result.career.estimate.distribution.stddev==pytest.approx(sqrt(.25*(260-455)**2+.75*(520-455)**2))
    assert result.career.estimate.distribution.p10 is None


def test_missing_slot_mass_is_not_renormalized_or_filled_with_market_or_zero():
    e=evidence(slot_probabilities=[{'slot_in_round':1,'probability':.5},{'slot_in_round':2,'probability':.5}])
    result=estimate(e)
    for h in (result.three_year,result.career):
        assert h.status=='unavailable' and h.estimate is None and h.missing_slots==(2,)


def test_missing_terminal_withholds_career_but_keeps_complete_three_year():
    e=evidence(scenarios=[{'probability':1,'annual':[{'season':2027,'raw_shapley':100},{'season':2028,'raw_shapley':80}]}])
    result=estimate(e)
    assert result.three_year.estimate.distribution.mean==pytest.approx(142.8)
    assert result.career.estimate is None


@pytest.mark.parametrize('missing',[None,'absent'])
def test_missing_annual_is_not_treated_as_retirement_or_a_verified_zero(missing):
    annual=[{'season':2027,'raw_shapley':100}]+([] if missing=='absent' else [{'season':2028,'raw_shapley':None}])
    result=estimate(evidence(scenarios=[{'probability':1,'annual':annual,'terminal_start_season':2029,'terminal_raw_shapley':0}]))
    assert result.three_year.estimate is result.career.estimate is None


def test_signed_native_values_are_not_clipped():
    result=estimate(evidence(scenarios=[{'probability':1,'annual':[{'season':2027,'raw_shapley':-10},{'season':2028,'raw_shapley':0}],
        'terminal_start_season':2029,'terminal_raw_shapley':0}]))
    assert result.three_year.estimate.distribution.mean==-8.5
    assert result.career.estimate.distribution.mean==-10


@pytest.mark.parametrize('change',[{'market_inputs_used':True},{'evidence_kind':'historical_realized_outcomes'},
    {'shapley_model_version':'a-different-engine'}, {'source_fingerprints':['']}, {'rules_signature':''},
    {'slot_probabilities':[{'slot_in_round':1,'probability':.9}]},
    {'slot_probabilities':[{'slot_in_round':13,'probability':1}]}])
def test_incompatible_or_unproven_evidence_rejected(change):
    with pytest.raises(ValidationError):evidence(**change)


@pytest.mark.parametrize('field',['rules_signature','scoring_signature','native_coordinate_id'])
def test_exact_requested_economic_coordinate_is_required(field):
    with pytest.raises(ValueError,match='economic coordinate'):estimate(evidence(**{field:'other'}))


def test_future_evidence_and_timezone_free_cutoff_rejected():
    with pytest.raises(ValueError,match='cutoff'):estimate(evidence(evidence_as_of=NOW+timedelta(seconds=1)))
    with pytest.raises(ValueError,match='cutoff'):estimate_native_pick_research(evidence(),as_of=NOW.replace(tzinfo=None),
        expected_rules_signature='rules',expected_scoring_signature='scoring',expected_native_coordinate_id='native-coordinate')


@pytest.mark.parametrize('scenario',[
    {'probability':1,'annual':[{'season':2026,'raw_shapley':0}]},
    {'probability':1,'annual':[{'season':2027,'raw_shapley':1},{'season':2027,'raw_shapley':2}]},
    {'probability':1,'annual':[{'season':2027,'raw_shapley':1}],'terminal_start_season':2027,'terminal_raw_shapley':2},
    {'probability':1,'annual':[{'season':2027,'raw_shapley':float('nan')}]},
    {'probability':.5,'annual':[]},
])
def test_pre_draft_production_duplicates_terminal_overlap_and_invalid_numbers_fail(scenario):
    with pytest.raises(ValidationError):evidence(scenarios=[scenario])


def test_finite_inputs_that_overflow_a_horizon_are_rejected():
    e=evidence(scenarios=[{'probability':1,'annual':[{'season':2027,'raw_shapley':1e308},{'season':2028,'raw_shapley':1e308}],
        'terminal_start_season':2029,'terminal_raw_shapley':1e308}])
    with pytest.raises(ValueError,match='remain finite'):estimate(e)


def test_origin_probability_cannot_be_replaced_with_current_owners_or_another_draft_year():
    base=evidence();slot=base.slot_evidence.model_dump(mode='json')
    for changed in ({'original_team_id':'different-owner'},{'draft_season':2028}):
        with pytest.raises(ValidationError,match='origin and draft season'):
            evidence(slot_evidence={**slot,**changed})


def test_evidence_fingerprint_changes_when_native_path_or_origin_probabilities_change():
    base=evidence();first=estimate(base)
    assert estimate(base).input_fingerprint==first.input_fingerprint
    changed=evidence(scenarios=[{'probability':1,'annual':[{'season':2027,'raw_shapley':1},{'season':2028,'raw_shapley':0}],
        'terminal_start_season':2029,'terminal_raw_shapley':0}])
    assert estimate(changed).input_fingerprint!=first.input_fingerprint
    assert first.source_fingerprints==('synthetic-source','synthetic-slot-source')
