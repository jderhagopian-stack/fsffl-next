from pathlib import Path
import shutil
import subprocess

import pytest


def test_market_overflow_is_independent_and_analytics_survives_null_index_gaps():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for production browser-consumer regression")
    static = Path(__file__).parents[1] / "src/fsffl/product/static"
    script = "global.window=globalThis;global.document={querySelector:()=>null,createElement:()=>({style:{}}),head:{appendChild:()=>{}}};\n"
    script += (static / "my_team_dashboard.js").read_text() + "\n"
    script += (static / "analytics_terminal.js").read_text() + "\n"
    script += r"""
const assert=require('node:assert/strict');
fsfflMyTeamState.view={context:{league_state_id:'S'},publication_generation_id:'G'};
fsfflMyTeamState.valueLenses={league_state_id:'S',publication_generation_id:'G',players:[{
  player_id:'p',broad_market_value_index:6000,intrinsic_value_index:10000,
  intrinsic_index_overflow:true,broad_market_percentile:.6,intrinsic_percentile:.9
}]};
const market=franchiseNSMarketDisplay({player_id:'p'});
assert.match(market,/<strong>6,000<\/strong>/);
assert.doesNotMatch(market,/6,000\+/);
assert.match(franchiseNSIntrinsicDisplay({player_id:'p'}),/10,000\+/);

fsfflAnalyticsTerminal.teamViews={team_views:[{team_id:'T',display_name:'Team',players:[
  {player_id:'a',full_name:'Alpha',position:'QB'},
  {player_id:'b',full_name:'Beta',position:'RB'},
  {player_id:'missing',full_name:'Missing',position:'WR'}
]}]};
fsfflAnalyticsTerminal.valueLenses={players:[
  {player_id:'a',broad_market_value_index:6000,intrinsic_value_index:10000,
   broad_market_percentile:.1,intrinsic_percentile:.9,value_index_gap:null,intrinsic_index_overflow:true},
  {player_id:'b',broad_market_value_index:9000,intrinsic_value_index:1000,
   broad_market_percentile:.95,intrinsic_percentile:.75,value_index_gap:null}
]};
const markup=atDivergenceMarkup();
assert.match(markup,/Alpha/);assert.match(markup,/Beta/);assert.doesNotMatch(markup,/Missing/);
assert.ok(markup.indexOf('Alpha')<markup.indexOf('Beta'));
assert.match(markup,/\+80\.0 pct pts/);assert.match(markup,/-20\.0 pct pts/);
assert.match(markup,/10,000\+/);assert.match(markup,/<th>Percentile gap<\/th>/);
"""
    result = subprocess.run([node], input=script, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
