from types import SimpleNamespace

import pytest

from fsffl.opportunity.frontier import make_frontier_point, substitute_packages
from fsffl.opportunity.trade_universe import TeamTradeInventory, TradeSearchBounds
from fsffl.product.counter_search import order_counter_hypotheses
from fsffl.state.models import PickAsset, PlayerAsset
from tests.test_opportunity_frontier_search import _seed, _candidate
from fsffl.opportunity.frontier_search import explore_negotiation_frontier, FrontierSearchPolicy
from fsffl.opportunity.models import ActionAuthority


def test_singleton_substitutions_reach_owned_picks_without_growing_package():
    starter = PlayerAsset(player_id='starter')
    bench = PlayerAsset(player_id='bench')
    pick = PickAsset(pick_id='future')
    inventory = TeamTradeInventory(team_id='a', assets=(starter, bench, pick))
    options = substitute_packages(_seed('a', starter), inventory=inventory,
                                  bounds=TradeSearchBounds(max_assets_per_side=1))
    assert {p.assets for p in options} == {(bench,), (pick,)}
    assert all(len(p.assets) == 1 for p in options)
    filtered = substitute_packages(_seed('a', starter), inventory=inventory,
        bounds=TradeSearchBounds(max_assets_per_side=1, include_picks=False))
    assert [p.assets for p in filtered] == [(bench,)]
    with pytest.raises(ValueError, match='outside'):
        substitute_packages(_seed('a', PlayerAsset(player_id='unowned')), inventory=inventory,
                            bounds=TradeSearchBounds())


def test_repair_lanes_retain_starter_and_keep_native_horizons_separate():
    starter, bench, other = (PlayerAsset(player_id=p) for p in ('starter','bench','other'))
    pick = PickAsset(pick_id='future')
    seed = make_frontier_point(_seed('a', starter), _seed('b', other))
    bench_option = make_frontier_point(_seed('a', bench), seed.counterparty_package)
    pick_option = make_frontier_point(_seed('a', pick), seed.counterparty_package)
    larger = make_frontier_point(_seed('a', starter, bench), seed.counterparty_package)
    published = SimpleNamespace(values={'three_year':{'starter':100,'bench':60,'other':80},
        'career':{'starter':1000,'bench':900,'other':950}},
        pick_values={'three_year':{'future':70},'career':{'future':800}})
    effects = {'teams':{'a':{'current':-10,'three_year':-20,'career':-50},
                        'b':{'current':10,'three_year':20,'career':50}}}
    neighbors = (larger, pick_option, bench_option)
    result = order_counter_hypotheses(seed, neighbors, seed_effects=effects,
                                     published=published, starters={'a':{'starter'}})
    assert result[0] == pick_option   # Retain starter; owned compensation, canonical tie.
    assert result[1] == bench_option  # Next independent repair, without repeats.
    assert {p.point_id for p in result} == {p.point_id for p in neighbors}
    assert neighbors == (larger, pick_option, bench_option)
    # Missing native evidence never becomes zero; structural options remain.
    published.values = {}; published.pick_values = {}
    assert len(order_counter_hypotheses(seed, neighbors, seed_effects=effects,
        published=published, starters={})) == 3


def test_budgeted_search_reaches_substitution_that_old_geometry_cannot_reach():
    a, spare, b = (PlayerAsset(player_id=p) for p in ('a','spare','b'))
    seed = make_frontier_point(_seed('a', a), _seed('b', b))
    kwargs = dict(focal_inventory=TeamTradeInventory(team_id='a',assets=(a,spare)),
        counterparty_inventory=TeamTradeInventory(team_id='b',assets=(b,)),
        bounds=TradeSearchBounds(max_assets_per_side=1),
        evaluator=lambda p:_candidate(p.point_id,'a',ActionAuthority.DIAGNOSTIC_ONLY))
    original = explore_negotiation_frontier(seed,**kwargs,
        policy=FrontierSearchPolicy(max_depth=1,max_evaluations=2))
    improved = explore_negotiation_frontier(seed,**kwargs,
        policy=FrontierSearchPolicy(max_depth=1,max_evaluations=2,include_substitutions=True))
    assert len(original.evaluated)==1 and len(improved.evaluated)==2
    assert improved.evaluated[1].point.focal_package.assets==(spare,)
    assert all(p.candidate.action_authority==ActionAuthority.DIAGNOSTIC_ONLY for p in improved.evaluated)
    with pytest.raises(ValueError,match='preserve'):
        explore_negotiation_frontier(seed,**kwargs,
            policy=FrontierSearchPolicy(max_depth=1,max_evaluations=2,include_substitutions=True),
            order_neighbors=lambda p,ns:())


def test_native_order_closes_each_shortfall_in_its_own_units():
    a, b, c, d = (PlayerAsset(player_id=p) for p in ('a','b','c','d'))
    seed = make_frontier_point(_seed('a', a), _seed('b', b))
    c_offer = make_frontier_point(_seed('a', c), seed.counterparty_package)
    d_offer = make_frontier_point(_seed('a', d), seed.counterparty_package)
    evidence = SimpleNamespace(values={'three_year':{'a':100,'b':80,'c':79,'d':90},
        'career':{'a':10000,'b':5000,'c':9900,'d':4999}},pick_values={})
    losses = {'teams':{'a':{'three_year':-20,'career':-5000},'b':{}}}
    ordered = order_counter_hypotheses(seed,(d_offer,c_offer),seed_effects=losses,
                                      published=evidence,starters={})
    # C closes 3Y with least extra compensation; D independently closes Career.
    assert ordered == (c_offer,d_offer)
