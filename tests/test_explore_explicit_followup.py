from fsffl.product.strategic_discovery_presentation import discovery_display_context
from fsffl.opportunity.shortlist_quality import curate_shortlist
from tests.test_shortlist_quality import evaluated


def test_counterparty_depth_cannot_mask_explicit_current_career_loss():
    r=evaluated(current=(2,0),three=(-10,10),career=(-40,40))
    r['objective_assessment']['side_a']['context'].update(objectives=['current_competitiveness','career_contribution'],explicitly_directed=True)
    other=r['objective_assessment']['side_b']
    other['context'].update(source='calculated_state_posture_hypothesis_v1',explicitly_directed=False)
    other['transaction_strategy']={'depth_conversion_candidate':True,'future_losses':[]}
    r['display_context']=discovery_display_context(r)
    assert r['display_context']['group']=='priority_tradeoff'
    curate_shortlist([r])
    assert r['shortlist_quality']['status']=='needs_terms'


def test_card_keeps_confirmed_title_with_missing_future_and_correct_points_units():
    import subprocess
    script=r"""
const vm=require('vm'),fs=require('fs'),assert=require('assert');
const c={window:{addEventListener:()=>{}},console};vm.createContext(c);
vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8').replace('{render,run,priorities,applyIntent}','{render,run,priorities,applyIntent,choiceSummary}'),c);
const r={evidence_status:'pre_simulation_screened',preliminary_decision_screen:{current_points_basis:'optimized_horizon_lineup',focal:{starter_points_delta:20}},horizon_asset_economics:{three_year:{roster_adjusted:{side_a:{roster_adjusted_intrinsic_delta:10}}}},screen_confirmation:{material:{side_a:{team_id:'a',championship_probability:'material_gain'}},competitive:{a:{championship_probability:.04}}}};
let text=c.window.fsfflStrategicExplore.choiceSummary(r,'Other');
assert(text.includes('Title chances rise by 4.0 percentage points'));assert(text.includes('Career estimate unavailable'));assert(text.includes('Three-year contribution rises'));
r.screen_confirmation={};text=c.window.fsfflStrategicExplore.choiceSummary(r,'Other');
assert(text.includes('20.0 total points over the projection period'));assert(!text.includes('20.0 points a week'));
r.preliminary_decision_screen.current_points_basis='remaining_regular_season_weekly_mean';
assert(c.window.fsfflStrategicExplore.choiceSummary(r,'Other').includes('20.0 points a week'));
"""
    subprocess.run(['node','-e',script],check=True,capture_output=True,text=True)
