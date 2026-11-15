"""Actual Trade Center wrappers must keep details open and explain missing inputs."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import pytest

STATIC = Path('src/fsffl/product/static')


def test_trade_evidence_status_preserves_decision_and_names_only_returned_gaps():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = """
const fs=require('fs'),vm=require('vm'),assert=require('assert');const c={window:{}};
vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const status=c.window.fsfflTradeEvidenceStatus;
const r={disposition:{disposition:'insufficient_evidence',evidence:{unavailable_metrics:['intrinsic_value']}},availability:{final_trade_disposition:false},decision_dimensions:{confidence:{missing_dimensions:['long_term_franchise_value']}}};
const before=JSON.stringify(r),s=status(r);assert.equal(s.title,'Decision incomplete');assert.equal(s.missing.length,1);assert.match(s.detail,/long-term Intrinsic trade economics/);assert.equal(JSON.stringify(r),before);
assert.equal(status({scenario_simulation_count:50000}).incomplete,true);
assert.equal(status({disposition:{disposition:'support'},availability:{final_trade_disposition:true}}).incomplete,false);
assert.match(status({disposition:{disposition:'insufficient_evidence'}}).detail,/does not include/);
assert.match(status({package_economics:{status:'incomplete'}}).detail,/package structure/);
"""
    result = subprocess.run([node, '-e', script, str(STATIC/'trade_evidence_status.js')], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_actual_trade_center_panels_stay_open_across_mutations_and_update_for_new_result(tmp_path):
    executable = shutil.which('chromium')
    if executable is None:
        pytest.skip('Local Chromium unavailable')
    playwright = pytest.importorskip('playwright.sync_api')
    html = (STATIC/'index.html').read_text()
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
    def style(match):
        name = match.group(1).split('?',1)[0].rsplit('/',1)[-1]
        return '<style>'+(STATIC/name).read_text()+'</style>'
    html = re.sub(r'<link\b[^>]*href="(/static/[^\"]+\.css[^\"]*)"[^>]*>', style, html)
    fixture = {'focal_team_id':'a','counterparty_team_id':'b','state_id_before':'s',
        'position_strength':{'positions':[{'position':'RB','before_expected_points':100,'after_expected_points':223.5,'expected_points_delta':123.5}]},
        'roster_adjusted_market_net':{'side_a':{'team_id':'a','roster_adjusted_market_delta':-81,'raw_trade_market_delta':-81,'mandatory_cut_market_cost':0,'cut_player_ids':[]},'side_b':{'team_id':'b','roster_adjusted_market_delta':81}},
        'objective_assessment':{'side_a':{'context':{'team_id':'a','explicitly_directed':True},'transaction_strategy':{'status':'priority_gain','priority_horizons':['career_contribution'],'future_gains':['career_contribution'],'future_losses':['three_year_contribution'],'positions_with_less_forecasted_depth':['WR'],'outgoing_projected_bench_ids':['depth'],'depth_conversion_candidate':True}},'side_b':{'context':{'team_id':'b'},'transaction_strategy':{'status':'priority_tradeoff','priority_horizons':['current_competitiveness'],'current_losses':['expected_wins']}}},
        'scenario_simulation_count':50000,'team_deltas':[{'team_id':'a','competitive':{'expected_wins':.1,'playoff_probability':.03,'first_place_probability':.01}},{'team_id':'b','competitive':{'expected_wins':-.1,'playoff_probability':-.03}}],
        'availability':{'competitive_outcomes':True,'final_trade_disposition':False},
        'disposition':{'disposition':'insufficient_evidence','evidence':{'unavailable_metrics':['intrinsic_value'],'material_gains':['playoff_probability'],'material_losses':['largest_single_player_lineup_drop']}}}
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        for width in (390,1200):
            page = browser.new_page(viewport={'width':width,'height':1000})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content(html)
            page.evaluate("document.querySelectorAll('.route-screen').forEach(n=>n.hidden=n.id!=='trade-center-screen')")
            page.add_script_tag(content="const state={route:'trade_center',context:{team_id:'a',state_id:'s'}};const qs=s=>document.querySelector(s);const qsa=s=>[...document.querySelectorAll(s)];const escapeHtml=s=>String(s??'');const fmtNumber=n=>String(n??'—');")
            for name in ('trade_center.js','trade_evidence_status.js','trade_decision_experience.js','trade_primary_narrative.js','beta_product_corrections.js','north_star_trade_center.js','market_trade_recomposition.js','market_trade_drilldown.js'):
                page.add_script_tag(content=(STATIC/name).read_text())
            page.evaluate("tradeUiState.counterpartyTeamId='b';tradeUiState.browser={focal_team:{team_id:'a',assets:[]},counterparties:[{team_id:'b',assets:[]}]}")
            page.wait_for_timeout(100)
            page.evaluate('(r)=>{window.renderTradeAnalysis(r);window.renderTradeSimulationResult(r)}',fixture)
            page.wait_for_selector('.ns3-drill-card')
            page.wait_for_timeout(150)
            assert page.locator('#ns2-trade-room .ns2-status').text_content()=='Simulation complete · decision incomplete'
            assert 'long-term Intrinsic trade economics' in page.locator('.beta-trade-summary.final').text_content()
            page.evaluate("window.testMutations=0;window.testObserver=new MutationObserver(rows=>testMutations+=rows.length);testObserver.observe(document.querySelector('#trade-center-screen'),{childList:true,subtree:true})")
            page.wait_for_timeout(150)
            assert page.evaluate('testMutations')==0
            page.evaluate('testObserver.disconnect()')
            for index in range(5):
                card=page.locator('.ns3-drill-card').nth(index)
                card.locator('summary').click()
                page.evaluate("document.querySelector('#trade-frontier-result').appendChild(document.createElement('span'))")
                page.wait_for_timeout(120)
                assert card.get_attribute('open') is not None
                assert card.locator('.ns3-drill-body').is_visible()
                card.locator('summary').click()
                page.wait_for_timeout(50)
                assert card.get_attribute('open') is None
            page.locator('.ns3-drill-card').nth(3).locator('summary').click()
            assert 'Missing: long-term Intrinsic trade economics' in page.locator('.ns3-missing-evidence').text_content()
            assert 'Potential depth-to-future conversion' in page.locator('.ns3-drill-card').nth(3).text_content()
            assert 'Less projected depth: WR' in page.locator('.ns3-drill-card').nth(3).text_content()
            assert 'Chosen priorities: Career' in page.locator('.ns3-drill-card').nth(3).text_content()
            assert 'Review the timeline tradeoff' in page.locator('.ns3-drill-card').nth(4).text_content()
            page.screenshot(path=str(tmp_path/f'trade-{width}.png'),full_page=True)
            updated=json.loads(json.dumps(fixture));updated['disposition']={'disposition':'support','evidence':{}};updated['availability']['final_trade_disposition']=True
            page.evaluate('(r)=>window.renderTradeSimulationResult(r)',updated)
            page.wait_for_timeout(150)
            assert page.locator('#ns2-trade-room .ns2-status').text_content()=='Decision ready'
            assert page.locator('.ns3-missing-evidence').count()==0
            assert not errors,errors
            page.close()
        browser.close()
