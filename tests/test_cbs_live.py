from datetime import UTC, datetime

from fsffl.providers.cbs_live import CBSLiveProjectionSource


def test_cbs_live_parses_current_position_pages() -> None:
    pages = {
        "/QB/": """<table><tr><th>Player</th><th>GP</th><th>CMP</th><th>ATT</th><th>YDS</th><th>TD</th><th>INT</th><th>RATT</th><th>RAVG</th><th>RYDS</th><th>RYDSG</th><th>RTD</th><th>FL</th><th>FPTS</th></tr><tr><td>L. Jackson QB BAL Lamar Jackson QB BAL</td><td>17</td><td>304</td><td>475</td><td>3704</td><td>26</td><td>8</td><td>127</td><td>5.1</td><td>646</td><td>38.0</td><td>3</td><td>2</td><td>334.8</td></tr></table>""",
        "/RB/": """<table><tr><th>Player</th><th>GP</th><th>ATT</th><th>YDS</th><th>AVG</th><th>TD</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDSG</th><th>AVG</th><th>TD</th><th>FL</th></tr><tr><td>B. Robinson RB ATL Bijan Robinson RB ATL</td><td>17</td><td>291</td><td>1400</td><td>4.8</td><td>9</td><td>91</td><td>71</td><td>701</td><td>41.2</td><td>9.9</td><td>4</td><td>2</td></tr></table>""",
        "/WR/": """<table><tr><th>Player</th><th>GP</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDSG</th><th>AVG</th><th>TD</th><th>ATT</th><th>YDS</th><th>AVG</th><th>TD</th><th>FL</th></tr><tr><td>D. London WR ATL Drake London WR ATL</td><td>17</td><td>140</td><td>98</td><td>1273</td><td>74.9</td><td>13.0</td><td>9</td><td>0</td><td>0</td><td>0</td><td>0</td><td>1</td></tr></table>""",
        "/TE/": """<table><tr><th>Player</th><th>GP</th><th>TGT</th><th>REC</th><th>YDS</th><th>YDSG</th><th>AVG</th><th>TD</th></tr><tr><td>K. Pitts TE ATL Kyle Pitts TE ATL</td><td>17</td><td>110</td><td>80</td><td>900</td><td>52.9</td><td>11.3</td><td>6</td></tr></table>""",
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
    assert lamar.stats["pass_yd"] == 3704
    bijan = next(row for row in snapshot.rows if row.player_name == "Bijan Robinson")
    assert bijan.stats["rec"] == 71
