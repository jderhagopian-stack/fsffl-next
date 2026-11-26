from copy import deepcopy
from types import SimpleNamespace as NS

from fsffl.opportunity.confirmation_quality import current_required_teams
from fsffl.opportunity.shortlist_quality import curate_shortlist,shortlist_receipt
from tests.test_shortlist_quality import inferred_tradeoff,evaluated
from fsffl.product.progressive_discovery import ProgressiveDiscovery
from fsffl.product.strategic_discovery import StrategicDiscoveryRequest
from tests.test_progressive_discovery import read_fixture


def test_current_purchase_needs_existing_materiality_but_rebuilding_does_not():
    purchase=inferred_tradeoff(current=(4,-2),three=(-30,30),career=(-100,100))
    # Context contains the same fixture team IDs; only Current-funded owner needs confirmation.
    assert current_required_teams(purchase)==(purchase['objective_assessment']['side_a']['context']['team_id'],)
    curve=deepcopy(purchase)
    curate_shortlist([curve],require_current_confirmation=True)
    assert curve['shortlist_quality']['status']=='review'
    curve['screen_confirmation']={'status':'verified','reason':'material_current_case'}
    curate_shortlist([curve],require_current_confirmation=True)
    assert curve['shortlist_quality']['status']=='strategic_tradeoff'
    assert curve['display_context']==purchase['display_context']
    receipt=shortlist_receipt(curve)
    assert current_required_teams(receipt)==current_required_teams(curve)
    curate_shortlist([receipt],require_current_confirmation=True)
    assert receipt['shortlist_quality']['status']=='strategic_tradeoff'


def test_failed_current_case_cannot_hide_a_verified_alternative():
    bad=inferred_tradeoff('bad',current=(10,-1),three=(-10,10),career=(-20,20))
    good=inferred_tradeoff('good',current=(4,-2),three=(-30,30),career=(-100,100))
    bad['screen_confirmation']={'status':'not_worthwhile','reason':'current_gain_not_demonstrated'}
    good['screen_confirmation']={'status':'verified'}
    curate_shortlist([bad,good],require_current_confirmation=True)
    assert bad['shortlist_quality']['status']=='review'
    assert good['shortlist_quality']['status']=='strategic_tradeoff'


def test_one_finalist_per_batch_receipts_preserve_rejections_without_resimulation(monkeypatch):
    import fsffl.product.progressive_discovery as module
    calls=[]
    def build(runtime,request,**kwargs):
        r=evaluated('second' if kwargs['previously_screened'] else 'first')
        for side in ('side_a','side_b'):
            r['objective_assessment'][side]['context']['team_id']=side
        r['evaluation_kind']='root'
        return {'candidate_packages':[r],'diagnostics':{'unexamined_pool_count':20,'repair_sequence_attempted':False}}
    monkeypatch.setattr(module,'build_strategic_discovery',build)
    def confirm(runtime,row,read,instructions):
        calls.append(row['point_id']);return {'status':'not_worthwhile','reason':'current_gain_not_demonstrated'}
    runtime,_,_,_=read_fixture();service=ProgressiveDiscovery(finalist_evaluator=confirm)
    first=service.build(runtime,StrategicDiscoveryRequest())
    assert calls==['first'] and first['search_progress']['shortlisted_choice_count']==0
    again=service.build(runtime,StrategicDiscoveryRequest())
    assert again['search_progress']['cache_hit'] and calls==['first']
    assert again['diagnostics']['changed_state_simulation_calls']==0
    assert again['diagnostics']['finalist_confirmation_attempts']==0
    second=service.build(runtime,StrategicDiscoveryRequest(continuation_token=first['search_progress']['next_token']))
    assert calls==['first','second']
    assert second['search_progress']['finalist_confirmations']==2
    assert second['shortlist_updates']['first']['status']=='review'


def test_market_indifference_is_existing_upstream_policy_not_a_new_cross_unit_price():
    a=evaluated('less-useful',current=(1,2),three=(-80,80),career=(-100,100),market=-50)
    b=evaluated('more-useful',current=(2,1),three=(10,-10),career=(-5,5),market=-100)
    curate_shortlist([a,b],market_tolerance=60.)
    assert a['shortlist_quality']['status']=='alternative'
    # A materially worse Market price must not be silently waived.
    curate_shortlist([a,b],market_tolerance=40.)
    assert a['shortlist_quality']['status']=='shortlist'


def test_resource_reserve_defers_before_any_scenario_or_proposal_work(monkeypatch):
    from fsffl.product.discovery_confirmation import evaluate_finalist
    from fsffl.product import resource_coordinator
    monkeypatch.setattr(resource_coordinator,'current_rss_bytes',lambda:400*1024*1024)
    called=[]
    runtime=NS(simulation_analytics=NS(simulation_result=NS(simulation_count=50_000)))
    proof=evaluate_finalist(runtime,{},NS(),None,simulation_loader=lambda *a:called.append(a),
        memory_budget_bytes=429496729,reclaim=lambda label:None)
    assert proof=={'status':'deferred','reason':'resource_headroom'}
    assert called==[]


def test_missing_current_owner_identity_is_not_treated_as_no_confirmation_needed():
    row=evaluated()
    assert current_required_teams(row)==('unresolved:side_a','unresolved:side_b')
    curate_shortlist([row],require_current_confirmation=True)
    assert row['shortlist_quality']['status']=='review'


def test_current_confirmation_preserves_existing_contender_depth_conversion():
    from fsffl.product.discovery_confirmation import _current_case_gates,COMPETITIVE_METRICS
    from tests.test_trade_transaction_strategy import assess,roles
    from tests.test_trade_objectives import metric
    from fsffl.trade_decision.objectives import TradeObjective as G
    values=[metric(G.CURRENT,0),metric(G.THREE_YEAR,20),metric(G.CAREER,50),
        metric(G.RESILIENCE,0,higher_is_better=False)]
    strategy=assess((G.CURRENT,),values,roles())
    assert strategy['depth_conversion_candidate'] and not strategy['surplus_confirmed']
    material={'side_a':{'team_id':'contender',**{k:'immaterial' for k in COMPETITIVE_METRICS}},
              'side_b':{'team_id':'partner'}}
    owner={'context':{'source':'calculated_state_posture_hypothesis_v1','explicitly_directed':False},
           'transaction_strategy':strategy}
    assert _current_case_gates(material,{'side_a':owner},{'contender'})==([],[],[],['contender'])
    lost_title=deepcopy(material);lost_title['side_a']['championship_probability']='material_loss'
    assert _current_case_gates(lost_title,{'side_a':owner},{'contender'})[3]==[]
    explicit=deepcopy(owner);explicit['context']['explicitly_directed']=True
    assert _current_case_gates(material,{'side_a':explicit},{'contender'})[0]==['contender']
    # Existing Decision-owned roster/resilience evidence prevents a false surplus.
    for bad_strategy in [assess((G.CURRENT,),values,roles(after_unfilled_slots=1)),
            assess((G.CURRENT,),values[:-1]+[metric(G.RESILIENCE,2,higher_is_better=False)],roles())]:
        owner['transaction_strategy']=bad_strategy
        assert not bad_strategy['depth_conversion_candidate']
        assert _current_case_gates(material,{'side_a':owner},{'contender'})[0]==['contender']


def test_either_inferred_balanced_owner_can_fund_current_help_with_future_cost():
    # The selected franchise gets more future assets AND Current production.
    # The balanced partner gives up future production for a Current upgrade.
    # Swapping which owner is selected must not create a one-sided veto.
    from fsffl.product.strategic_discovery_presentation import discovery_display_context
    for three,career in [((30,-30),(80,-80)),((-30,30),(-80,80))]:
        row=inferred_tradeoff(current=(4,3),three=three,career=career)
        row['objective_assessment']['side_b']['context']['objectives']=['current_competitiveness','three_year_contribution','career_contribution']
        row['display_context']=discovery_display_context(row)
        assert row['display_context']['group']=='priority_tradeoff'
        curate_shortlist([row])
        assert row['shortlist_quality']['status']=='strategic_tradeoff'
        cost_side='side_b' if career[0]>0 else 'side_a'
        assert current_required_teams(row)==(cost_side,)
        curate_shortlist([row],require_current_confirmation=True)
        assert row['shortlist_quality']['status']=='review'
        row['screen_confirmation']={'status':'verified'}
        curate_shortlist([row],require_current_confirmation=True)
        assert row['shortlist_quality']['status']=='strategic_tradeoff'
        row['objective_assessment'][cost_side]['context']['explicitly_directed']=True
        curate_shortlist([row])
        assert row['shortlist_quality']['status']=='needs_terms'
