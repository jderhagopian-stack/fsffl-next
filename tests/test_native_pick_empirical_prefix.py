from copy import deepcopy
import pytest
from scripts.fit_native_pick_empirical_prefix import fit


def doc():
    a={'draft_class':2019,'source_case_id':'a','selections':[{'rank':1,'annual':[10.,20.,30.]}]}
    b={'draft_class':2020,'source_case_id':'b','selections':[{'rank':1,'annual':[30.,40.,50.]}]}
    return {'economic_coordinate':{'rules':{'team_count':1},'scoring_coordinate':'connected_league_fantasy_points','source_fingerprints':['pin']},'source_cases':[a,b],
        'fallback_cases':[deepcopy(a)]}


def run(d,**kw):return fit(d,release_season=2026,draft_season=2027,max_slots=1,**kw)


def test_classes_not_draft_counts_determine_weight_and_inputs_unchanged():
    d=doc()
    for i in (1,2):
        b=deepcopy(d['source_cases'][1]);b['source_case_id']=str(i);d['source_cases'].append(b)
    before=deepcopy(d);r=run(d)
    assert r['slots'][0]['annual_mean']==pytest.approx([20,30,40]) and r['production_eligible'] is False and d==before


def test_prefix_maturity_uses_only_required_historical_window():
    d=doc();r=fit(d,release_season=2022,draft_season=2023,max_slots=1,prefix_years=2)
    assert r['source_classes']==[2019,2020]
    r=fit(d,release_season=2022,draft_season=2023,max_slots=1,prefix_years=3)
    assert r['source_classes']==[2019]


def test_missing_source_mass_is_backed_off_or_withheld_not_dropped():
    d=doc();d['source_cases'][1]['selections'][0]['annual'][0]=None;r=run(d)
    assert r['slots'][0]['backoff_mass']==.5 and r['slots'][0]['annual_mean']==[10.,20.,30.]
    d['fallback_cases']=[];assert run(d)['slots'][0]['forecast'] is None


def test_duplicate_and_rank_gaps_fail():
    d=doc();d['source_cases']*=2
    with pytest.raises(ValueError):run(d)
    d=doc();d['source_cases'][1]['selections'][0]['rank']=2
    with pytest.raises(ValueError):run(d)


def test_excluded_target_class_cannot_reenter_through_forecast_backoff():
    d=doc();d['source_cases'][1]['selections'][0]['annual'][0]=None
    assert run(d,excluded_classes=(2019,))['slots'][0]['forecast'] is None


@pytest.mark.parametrize('change',['nonfinite','unattributed_absence','short_path','boolean_rank','missing_identity'])
def test_backoff_evidence_has_the_same_source_guards_as_training(change):
    d=doc();case=d['fallback_cases'][0];row=case['selections'][0]
    if change=='nonfinite':row['annual'][0]=float('nan')
    if change=='unattributed_absence':row['assumed_seasons']=[2019]
    if change=='short_path':row['annual']=[10.]
    if change=='boolean_rank':row['rank']=True
    if change=='missing_identity':case['source_case_id']=' '
    with pytest.raises(ValueError):run(d)
