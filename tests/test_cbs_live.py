from datetime import UTC, datetime

from fsffl.providers.cbs_live import CBSLiveProjectionSource


def test_cbs_live_parses_current_position_pages() -> None:
    pages = {
        "/QB/": """<table><tr><th>Player</th><th>GP</th><th>ATT</th><th>CMP</th><th>YDS</th><th>YDS/G</th><th>TD</th><th>INT</th><th>RATE</th><th>ATT</th><th>YDS</th><th>AVG</th><th>TD</th><th>FL</th><th>FPTS</th><th>FPPG</th></tr><tr><td>L. Jackson QB BAL Lamar Jackson QB BAL</td><td>17</td><td>405</td><td>268</td><td>3364</td><td>197.9</td><td>33</td><td>11</td><td>107.7</td><td>107</td><td>604</td><td>5.6</td><td>3</td><td>4</td><td>362</td><td>21.3</td></tr></table>""",
        "/RB/": """<table><tr><th>Player</th><th>GP</th><th>ATT</th><th>YDS</th><th>AVG</th><th>TD</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDS/G</th><th>AVG</th><th>TD</th><th>FL</th><th>FPTS</th></tr><tr><td>B. Robinson RB ATL Bijan Robinson RB ATL</td><td>17</td><td>291</td><td>1400</td><td>4.8</td><td>9</td><td>91</td><td>71</td><td>701</td><td>41.2</td><td>9.9</td><td>4</td><td>2</td><td>269</td></tr></table>""",
        "/WR/": """<table><tr><th>Player</th><th>GP</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDS/G</th><th>AVG</th><th>TD</th><th>ATT</th><th>YDS</th><th>AVG</th><th>TD</th><th>FL</th><th>FPTS</th></tr><tr><td>D. London WR ATL Drake London WR ATL</td><td>17</td><td>140</td><td>98</td><td>1273</td><td>74.9</td><td>13.0</td><td>9</td><td>0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>181</td></tr></table>""",
        "/TE/": """<table><tr><th>Player</th><th>GP</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDS/G</th><th>AVG</th><th>TD</th><th>FL</th><th>FPTS</th></tr><tr><td>K. Pitts TE ATL Kyle Pitts TE ATL</td><td>17</td><td>110</td><td>80</td><td>900</td><td>52.9</td><td>11.3</td><td>6</td><td>1</td><td>126</td></tr></table>""",
    }

    def getter(url: str) -> str:
        return next(html for marker, html in pages.items() if marker in url)

    source = CBSLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    )
    snapshot = source.fetch_latest(season=2026)
    assert snapshot.provider == "cbs"
    assert len(snapshot.rows) == 4
    lamar = next(row for row in snapshot.rows if row.player_name == "Lamar Jackson")
    assert lamar.nfl_team == "BAL"
    assert lamar.stats["pass_yd"] == 3364
    assert lamar.stats["pass_td"] == 33
    assert lamar.stats["rush_yd"] == 604
    assert lamar.stats["fum_lost"] == 4
    bijan = next(row for row in snapshot.rows if row.player_name == "Bijan Robinson")
    assert bijan.stats["rec"] == 71
    assert bijan.stats["fum_lost"] == 2


def test_cbs_live_parses_hosted_text_grid_when_no_html_table_is_present() -> None:
    pages = {
        "/QB/": """<html><body><h1>2026 Projections Fantasy Football Quarterback Stats</h1><a>J. Jackson</a><span>QB</span><span>BAL</span><a>Lamar Jackson</a><span>QB</span><span>BAL</span><span>17</span><span>405</span><span>268</span><span>3,364</span><span>197.9</span><span>33</span><span>11</span><span>107.7</span><span>107</span><span>604</span><span>5.6</span><span>3</span><span>4</span><span>362</span><span>21.3</span></body></html>""",
        "/RB/": """<html><body><h1>2026 Projections Fantasy Football Running Back Stats</h1><a>B. Robinson</a><span>RB</span><span>ATL</span><a>Bijan Robinson</a><span>RB</span><span>ATL</span><span>17</span><span>291</span><span>1,400</span><span>4.8</span><span>9</span><span>91</span><span>71</span><span>701</span><span>41.2</span><span>9.9</span><span>4</span><span>2</span><span>269</span><span>15.8</span></body></html>""",
        "/WR/": """<html><body><h1>2026 Projections Fantasy Football Wide Receiver Stats</h1><a>D. London</a><span>WR</span><span>ATL</span><a>Drake London</a><span>WR</span><span>ATL</span><span>17</span><span>153</span><span>94</span><span>1,257</span><span>73.9</span><span>13.4</span><span>12</span><span>0</span><span>0</span><span>0.0</span><span>0</span><span>1</span><span>187</span><span>11.0</span></body></html>""",
        "/TE/": """<html><body><h1>2026 Projections Fantasy Football Tight End Stats</h1><a>K. Pitts</a><span>TE</span><span>ATL</span><a>Kyle Pitts</a><span>TE</span><span>ATL</span><span>17</span><span>103</span><span>74</span><span>822</span><span>48.4</span><span>11.1</span><span>6</span><span>0</span><span>109</span><span>6.4</span></body></html>""",
    }

    def getter(url: str) -> str:
        return next(html for marker, html in pages.items() if marker in url)

    snapshot = CBSLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    ).fetch_latest(season=2026)

    assert len(snapshot.rows) == 4
    lamar = next(row for row in snapshot.rows if row.player_name == "Lamar Jackson")
    assert lamar.stats["pass_yd"] == 3364
    assert lamar.stats["fum_lost"] == 4
    bijan = next(row for row in snapshot.rows if row.player_name == "Bijan Robinson")
    assert bijan.stats["rec_yd"] == 701
    london = next(row for row in snapshot.rows if row.player_name == "Drake London")
    assert london.stats["rec_td"] == 12
    pitts = next(row for row in snapshot.rows if row.player_name == "Kyle Pitts")
    assert pitts.stats["rec_yd"] == 822
    assert pitts.stats["rush_yd"] == 0
