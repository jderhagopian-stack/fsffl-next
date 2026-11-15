"""Any timeline may motivate a trade; position context never invents surplus."""
from fsffl.trade_decision.objectives import assess_owner_objectives, TradeObjective as G
from fsffl.trade_decision.transaction_strategy import assess_transaction_strategy
from tests.test_trade_objectives import context,metric


def assess(goals,values,positions=None,explicit=False):
    ctx=context(*goals,explicitly_directed=explicit)
    metrics=tuple(values)
    return assess_transaction_strategy(assess_owner_objectives(ctx,metrics),metrics,positions)


def roles(**updates):
    return {'status':'complete','before_unfilled_slots':0,'after_unfilled_slots':0,
        'positions':[{'position':'WR','outgoing_bench_ids':['depth'],
            'outgoing_starter_ids':[],'before_forecasted_bench_ids':['depth','reserve'],
            'after_forecasted_bench_ids':['reserve']}],**updates}


def test_future_priority_is_valid_without_current_gain():
    r=assess((G.THREE_YEAR,G.CAREER),[metric(G.THREE_YEAR,20),metric(G.CAREER,50),metric(G.CURRENT,0)])
    assert r['status']=='priority_gain'
    assert r['future_gains']==('three_year_contribution','career_contribution')
    assert r['action_authority']=='directional_review_only'
    assert not r['materiality_assessed']


def test_contender_can_convert_projected_depth_for_future_contribution():
    r=assess((G.CURRENT,),[metric(G.CURRENT,0),metric(G.THREE_YEAR,20),metric(G.CAREER,50),
        metric(G.RESILIENCE,0,higher_is_better=False)],roles())
    assert r['status']=='future_gain_current_preserved'
    assert r['opportunistic_future_case'] and r['depth_conversion_candidate']
    assert r['positions_with_less_forecasted_depth']==('WR',)
    assert not r['surplus_confirmed']


def test_explicit_current_only_does_not_silently_change_goals():
    r=assess((G.CURRENT,),[metric(G.CURRENT,0),metric(G.CAREER,50)],roles(),explicit=True)
    assert r['status']=='no_priority_gain'
    assert not r['depth_conversion_candidate']


def test_starter_or_resilience_or_coverage_cost_prevents_depth_conversion_label():
    values=[metric(G.CURRENT,0),metric(G.CAREER,50),metric(G.RESILIENCE,0,higher_is_better=False)]
    for p in (roles(after_unfilled_slots=1),roles(positions=[{'position':'WR','outgoing_starter_ids':['starter'],'outgoing_bench_ids':['depth']}])):
        assert not assess((G.CAREER,),values,p)['depth_conversion_candidate']
    assert not assess((G.CAREER,),values[:-1]+[metric(G.RESILIENCE,2,higher_is_better=False)],roles())['depth_conversion_candidate']


def test_future_gain_with_current_cost_is_an_explicit_tradeoff():
    r=assess((G.CURRENT,G.CAREER),[metric(G.CURRENT,-.2),metric(G.CAREER,50)],roles())
    assert r['status']=='priority_tradeoff'
    assert not r['current_direction_preserved']
    assert r['current_losses']==('native_delta',)
    assert not r['depth_conversion_candidate']


def test_current_gain_never_hides_native_loss_or_combines_horizons():
    r=assess((G.CURRENT,),[metric(G.CURRENT,.2),metric(G.THREE_YEAR,20),metric(G.CAREER,-50)],roles())
    assert r['status']=='priority_gain'
    assert r['future_losses']==('career_contribution',)
    assert r['future_gains']==('three_year_contribution',)
    assert not r['surplus_confirmed']


def test_missing_or_preview_current_evidence_cannot_confirm_current_preservation():
    for values in ([metric(G.CAREER,50)],[metric(G.CAREER,50),metric(G.CURRENT,None)]):
        r=assess((G.CAREER,),values,roles())
        assert not r['current_direction_preserved']
        assert not r['depth_conversion_candidate']
    r=assess((G.CURRENT,),[metric(G.CURRENT,None),metric(G.CAREER,50)],roles())
    assert r['status']=='incomplete'


def test_protected_assets_block_any_timeline_motive():
    ctx=context(G.CAREER,protected_player_ids=('keep',))
    metrics=(metric(G.CAREER,100),metric(G.CURRENT,0))
    a=assess_owner_objectives(ctx,metrics,cut_player_ids=('keep',))
    assert assess_transaction_strategy(a,metrics,roles())['status']=='constraints_violated'
