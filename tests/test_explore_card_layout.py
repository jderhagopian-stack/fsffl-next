"""Render the actual Explore shell and all production styles, with mock data."""
from pathlib import Path
import json
import re
import shutil
import pytest

STATIC=Path('src/fsffl/product/static')


def test_explore_impact_cells_fit_inside_real_generic_screen(tmp_path):
    playwright=pytest.importorskip('playwright.sync_api')
    executable=shutil.which('chromium')
    if executable is None:
        pytest.skip('Local Chromium is unavailable')
    # Preserve the index DOM and production stylesheet order. In particular,
    # #generic-screen is essential: its legacy table rule caused the clipping.
    html=(STATIC/'index.html').read_text()
    html=re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
    def style(match):
        path=match.group(1).split('?',1)[0].rsplit('/',1)[-1]
        return '<style data-production-stylesheet="'+path+'">'+(STATIC/path).read_text()+'</style>'
    html=re.sub(r'<link\b[^>]*href="(/static/[^\"]+\.css[^\"]*)"[^>]*>',style,html)
    def asset(ref,label):return {'asset_ref':ref,'label':label,'asset_kind':'player','detail':'WR','player_id':ref.split(':')[-1]}
    sent=[asset('player:send','Outgoing Player')]
    received=[asset('player:get','Incoming Player')]
    large_sent=[asset(f'player:s{i}',f'Long Developmental Player {i}') for i in range(8)]
    large_received=[asset(f'player:g{i}',f'Incoming Player {i}') for i in range(2)]
    def row(key,send,receive):
        native=lambda a,b:{'roster_adjusted':{'side_a':{'status':'complete','roster_adjusted_intrinsic_delta':a},'side_b':{'status':'complete','roster_adjusted_intrinsic_delta':b}}}
        return {'point_id':key,'counterparty_team_id':'b','send':send,'receive':receive,
            'display_context':{'group':'priority_tradeoff'},'evidence_status':'pre_simulation_screened',
            'preliminary_decision_screen':{'current_points_basis':'remaining_regular_season_weekly_mean',
                'focal':{'starter_points_delta':8.5},'counterparty':{'starter_points_delta':3.6}},
            'horizon_asset_economics':{'three_year':native(1234.5,-1234.5),'career':native(-80.7,80.7)}}
    result={'league_state_id':'s','focal_team_id':'a','publication_generation_id':'g',
        'candidate_packages':[row('small',sent,received),row('large',large_sent,large_received)]}
    browser={'state_id':'s','focal_team':{'team_id':'a','assets':sent+large_sent},
        'counterparties':[{'team_id':'b','display_name':'Other Franchise With A Long Name','assets':received+large_received}]}
    setup='const state={route:"opportunities",context:{league_id:"l",team_id:"a",state_id:"s",publication_generation_id:"g"}};const fixture='+json.dumps(result)+';const browser='+json.dumps(browser)+';async function api(path){return path.endsWith("/browser")?browser:fixture;}'
    with playwright.sync_playwright() as p:
        engine=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
        for width in (320,390,430,768,1200):
            page=engine.new_page(viewport={'width':width,'height':1000})
            page.set_content(html)
            page.evaluate("document.querySelectorAll('.route-screen').forEach(n=>n.hidden=n.id!=='generic-screen')")
            page.add_script_tag(content=setup)
            for name in ('strategic_explore.js','north_star_market.js'):
                page.add_script_tag(content=(STATIC/name).read_text())
            page.evaluate('window.fsfflMarketNorthStar.render({status:"ready"})')
            page.wait_for_selector('.se-card')
            assert page.locator('.se-card').count()==2
            assert page.locator('.se-card .se-asset').count()==12
            for card in page.locator('.se-card').all():
                measurements=card.evaluate('''card=>{const bounds=card.getBoundingClientRect(),table=card.querySelector('.se-impact table');return {cardWidth:card.clientWidth,tableWidth:table.scrollWidth,minWidth:getComputedStyle(table).minWidth,cells:[...table.querySelectorAll('th,td')].map(cell=>{const b=cell.getBoundingClientRect();return {text:cell.textContent,left:b.left,right:b.right,inside:b.left>=bounds.left&&b.right<=bounds.right}})}}''')
                assert measurements['tableWidth']<=measurements['cardWidth'],(width,measurements)
                assert all(c['inside'] for c in measurements['cells']),(width,measurements)
                assert card.locator('.se-impact td').count()==6
                assert [c.text_content() for c in card.locator('.se-impact td').all()]==['+8.5','+1,234.5','-80.7','+3.6','-1,234.5','+80.7']
            # Scrollable Player Board / generic data tables keep their existing widths.
            other=page.evaluate('''()=>{const host=document.querySelector('#generic-screen .panel');const div=document.createElement('div');div.className='market-ns-player-table';div.innerHTML='<table><tr><td>Player Board</td></tr></table>';host.appendChild(div);const width=parseFloat(getComputedStyle(div.querySelector('table')).minWidth);div.remove();return width}''')
            assert other>=720
            page.locator('.se-card').first.screenshot(path=str(tmp_path/f'card-{width}.png'))
            page.close()
        engine.close()
