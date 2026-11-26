from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from fsffl.opportunity.shortlist_quality import curate_shortlist, shortlist_receipt
from fsffl.product.strategic_discovery import _representative_indices
from fsffl.product.strategic_discovery_presentation import discovery_display_context
from fsffl.product.discovery_families import focal_package_family
from tests.test_strategic_discovery_presentation import row


def evaluated(point='p', *, current=(2,1), three=(20,-20), career=(40,-40), market=0):
    r=row(goals_a=('current_competitiveness',),goals_b=('current_competitiveness',),
          current=current,three=three,career=career)
    r.update(point_id=point,preliminary_economic_band='robust_or_ordinary')
    r['horizon_asset_economics']={h:{'roster_adjusted':{'side_a':{'status':'complete','roster_adjusted_intrinsic_delta':d[0]}}}
        for h,d in [('three_year',three),('career',career)]}
    r['roster_adjusted_market_net']={'side_a':{'status':'complete','roster_adjusted_market_delta':market}}
    r['display_context']=discovery_display_context(r)
    return r


@pytest.mark.parametrize('current,three,career',[
    ((.8,-1.2),(-420,420),(-493.5,493.5)),
    ((-.1,2.5),(-316.6,256),(146,-238.3)),
    ((-1,3.7),(-263.1,235.8),(412.2,-455)),
    ((-.8,1.7),(-363.1,295.4),(141.7,-225.8)),
    ((-.1,.4),(-57.1,57.1),(308.9,-308.9)),
])
def test_reported_mixed_cases_cannot_become_automatic_recommendations(current,three,career):
    r=evaluated(current=current,three=three,career=career)
    r['objective_assessment']['side_a']['context']['objectives']=['current_competitiveness','three_year_contribution','career_contribution']
    r['objective_assessment']['side_b']['context']['objectives']=['current_competitiveness','three_year_contribution','career_contribution']
    r['display_context']=discovery_display_context(r)
    effects=deepcopy(r)
    curate_shortlist([r])
    assert r['shortlist_quality']['status']!='shortlist'
    assert r['display_context']==effects['display_context']
    assert r['horizon_asset_economics']==effects['horizon_asset_economics']
    assert r['shortlist_quality']['decision_changed'] is False


def test_explicit_future_priority_survives_current_sacrifice():
    r=evaluated(current=(-2,4),three=(-20,20),career=(300,-300))
    r['objective_assessment']['side_a']['context'].update(objectives=['career_contribution'],explicitly_directed=True)
    r['display_context']=discovery_display_context(r)
    curate_shortlist([r])
    assert r['shortlist_quality']['status']=='shortlist'


def test_focal_alternatives_compare_magnitudes_without_maximizing_a_donation_to_other_owner():
    poor=evaluated('poor',current=(.8,3),three=(-420,420),career=(-493,493),market=-100)
    better=evaluated('better',current=(4,1),three=(-10,10),career=(-20,20),market=-20)
    # Both partners gain in their requested Current objective; giving the poor
    # deal's partner MORE future value must not make it a preferable offer.
    curate_shortlist([poor,better])
    assert poor['shortlist_quality']['replaced_by_point_ids']==['better']
    assert poor['shortlist_quality']['status']=='alternative'
    assert better['shortlist_quality']['status']=='shortlist'


def test_incomparable_horizons_missing_evidence_and_counterparty_costs_are_not_zero_filled():
    a=evaluated('a',three=(20,-20),career=(10,-10))
    b=evaluated('b',three=(10,-10),career=(20,-20))
    c=evaluated('c',current=(100,-10),three=(100,-100),career=(100,-100))
    d=evaluated('d');d['horizon_asset_economics']['career']['roster_adjusted']['side_a']['status']='incomplete'
    curate_shortlist([a,b,c,d])
    assert all(x['shortlist_quality']['status']=='shortlist' for x in (a,b,d))
    assert c['shortlist_quality']['status']=='review'


def test_signed_cursor_receipt_preserves_frontier_and_equivalent_family_across_batches():
    a=evaluated('old');a['focal_package_family']='family'
    saved=shortlist_receipt(a)
    b=evaluated('new',current=(3,1));b['focal_package_family']='family'
    curate_shortlist([saved,b])
    assert saved['shortlist_quality']['status']=='alternative'
    equal=evaluated('equal',current=(3,2));equal['focal_package_family']='family'
    curate_shortlist([shortlist_receipt(b),equal])
    assert equal['shortlist_quality']['status']=='alternative'


def test_family_coverage_precedes_repeating_same_pick_shape_for_another_owner():
    def r(team,family):return {'counterparty_team_id':team,'preliminary_economic_band':'robust_or_ordinary',
        'send':[{'asset_ref':'player:starter'}],'receive':[{'asset_ref':'pick:'+team}],
        'focal_package_family':family,'hypotheses':[]}
    rows=[r('a','same'),r('b','same'),r('c','different')]
    assert _representative_indices(rows,2)==[0,2]
    assert _representative_indices(rows,1,visited_families={'same'})==[2]


def test_neutral_prior_can_group_equivalent_picks_but_never_known_slots_or_different_years():
    picks={k:NS(season=y,round=1) for k,y in [('x',2028),('y',2028),('z',2029)]}
    read=NS(pick_values={h:{k:100. for k in picks} for h in ('three_year','career')},
        pick_sources={k:{'probability_basis':'exchangeable_future_slot_prior','release_id':'r','original_team_id':k} for k in picks})
    def key(k):return focal_package_family({'send':[{'asset_ref':'player:starter'}],'receive':[{'asset_ref':'pick:'+k}]},picks=picks,read=read)
    assert key('x')==key('y') and key('x')!=key('z')
    read.pick_sources['y']['probability_basis']='published_simulation'
    assert key('x')!=key('y')


def inferred_tradeoff(point='choice', *, current=(4,-2), three=(-20,20), career=(-30,30)):
    r=evaluated(point,current=current,three=three,career=career)
    for side,goals in [('side_a',['current_competitiveness','three_year_contribution','career_contribution']),
                       ('side_b',['career_contribution'])]:
        r['objective_assessment'][side]['context'].update(objectives=goals,source='calculated_state_posture_hypothesis_v1',explicitly_directed=False)
    # Use complete native effects for BOTH sides, including cuts, never sign mocks.
    r['horizon_asset_economics']={h:{'roster_adjusted':{side:{'status':'complete','roster_adjusted_intrinsic_delta':d[i]}
        for i,side in enumerate(('side_a','side_b'))}} for h,d in [('three_year',three),('career',career)]}
    r['display_context']=discovery_display_context(r)
    return r


def test_inferred_balanced_owner_can_consider_a_funded_current_future_exchange():
    choice=inferred_tradeoff()
    original=deepcopy(choice)
    curate_shortlist([choice])
    assert choice['shortlist_quality']['status']=='strategic_tradeoff'
    assert choice['display_context']==original['display_context']
    assert choice['horizon_asset_economics']==original['horizon_asset_economics']
    assert choice['shortlist_quality']['decision_changed'] is False
    saved=shortlist_receipt(choice)
    curate_shortlist([saved])
    assert saved['shortlist_quality']['status']=='strategic_tradeoff'
    explicit=deepcopy(original)
    explicit['objective_assessment']['side_a']['context']['explicitly_directed']=True
    curate_shortlist([explicit])
    assert explicit['shortlist_quality']['status']=='needs_terms'


def test_narrow_future_window_requires_review_when_only_inferred():
    r=inferred_tradeoff(current=(2,-8),three=(-30,30),career=(100,-100))
    r['objective_assessment']['side_b']['context']['objectives']=['three_year_contribution']
    r['display_context']=discovery_display_context(r)
    curate_shortlist([r])
    assert r['shortlist_quality']['reason']=='unconfirmed_future_window_preference'
    assert r['shortlist_quality']['status']=='review'
    # Long-term rebuilding can still give up Current AND 3-Year production.
    rebuild=inferred_tradeoff(current=(-4,2),three=(-50,50),career=(300,-300))
    rebuild['objective_assessment']['side_a']['context']['objectives']=['career_contribution']
    rebuild['objective_assessment']['side_b']['context']['objectives']=['current_competitiveness']
    rebuild['display_context']=discovery_display_context(rebuild)
    curate_shortlist([rebuild])
    assert rebuild['shortlist_quality']['status']=='shortlist'


def test_small_current_gain_with_far_greater_future_sacrifice_loses_to_better_choice():
    bad=inferred_tradeoff('bad',current=(.8,-1),three=(-420,420),career=(-493,493))
    useful=inferred_tradeoff('useful',current=(4,-2),three=(-20,20),career=(-30,30))
    curate_shortlist([bad,useful])
    assert bad['shortlist_quality']['status']=='alternative'
    assert useful['shortlist_quality']['status']=='strategic_tradeoff'
