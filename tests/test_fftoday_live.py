from datetime import UTC, datetime

from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource


def test_fftoday_live_parses_qb_and_position_pages() -> None:
    pages = {
        "PosID=10": """<html><body>Quarterback Projections Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Cmp</th><th>Att</th><th>Yds</th><th>TD</th><th>INT</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Lamar Jackson</td><td>BAL</td><td>13</td><td>304</td><td>475</td><td>3704</td><td>26</td><td>8</td><td>127</td><td>646</td><td>3</td><td>334.8</td></tr></table></body></html>""",
        "PosID=20": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Att</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Bijan Robinson</td><td>ATL</td><td>11</td><td>292</td><td>1536</td><td>11</td><td>71</td><td>594</td><td>3</td><td>328</td></tr></table></body></html>""",
        "PosID=30": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Rec</th><th>Yds</th><th>TD</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Drake London</td><td>ATL</td><td>11</td><td>99</td><td>1312</td><td>7</td><td>0</td><td>0</td><td>0</td><td>173.2</td></tr></table></body></html>""",
        "PosID=40": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Rec</th><th>Yds</th><th>TD</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Kyle Pitts</td><td>ATL</td><td>11</td><td>80</td><td>900</td><td>6</td><td>0</td><td>0</td><td>0</td><td>166</td></tr></table></body></html>""",
    }

    def getter(url: str) -> str:
        return next(html for marker, html in pages.items() if marker in url)

    source = FFTodayLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    )
    snapshot = source.fetch_latest(season=2026)
    assert snapshot.provider == "fftoday"
    assert len(snapshot.rows) == 4
    lamar = next(row for row in snapshot.rows if row.player_name == "Lamar Jackson")
    assert lamar.stats["pass_yd"] == 3704
    assert lamar.stats["rush_yd"] == 646
