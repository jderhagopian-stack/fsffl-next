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
