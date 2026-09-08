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


def test_fftoday_live_parses_hosted_text_grid_when_no_html_table_is_present() -> None:
    pages = {
        "PosID=10": """<html><body><h1>Quarterback Projections: 2026</h1><div>Regular Season, Updated: 9/3/2026</div><div>Player</div><div>Tm</div><div>Bye</div><a>Lamar Jackson</a><span>BAL</span><span>13</span><span>304</span><span>475</span><span>3,704</span><span>26</span><span>8</span><span>127</span><span>646</span><span>3</span><span>334.8</span></body></html>""",
        "PosID=20": """<html><body><div>Running Back Projections: 2026</div><div>Updated: 9/3/2026</div><a>Bijan Robinson</a><span>ATL</span><span>11</span><span>280</span><span>1,402</span><span>9</span><span>84</span><span>707</span><span>3</span><span>324.9</span></body></html>""",
        "PosID=30": """<html><body><div>Wide Receiver Projections: 2026</div><div>Updated: 9/3/2026</div><a>Drake London</a><span>ATL</span><span>11</span><span>99</span><span>1,312</span><span>7</span><span>0</span><span>0</span><span>0</span><span>222.7</span></body></html>""",
        "PosID=40": """<html><body><div>Tight End Projections: 2026</div><div>Updated: 9/3/2026</div><a>Kyle Pitts</a><span>ATL</span><span>11</span><span>80</span><span>900</span><span>6</span><span>166</span></body></html>""",
    }

    def getter(url: str) -> str:
        return next(html for marker, html in pages.items() if marker in url)

    snapshot = FFTodayLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    ).fetch_latest(season=2026)

    assert len(snapshot.rows) == 4
    lamar = next(row for row in snapshot.rows if row.player_name == "Lamar Jackson")
    assert lamar.stats["pass_yd"] == 3704
    bijan = next(row for row in snapshot.rows if row.player_name == "Bijan Robinson")
    assert bijan.stats["rec"] == 84
    london = next(row for row in snapshot.rows if row.player_name == "Drake London")
    assert london.stats["rush_yd"] == 0
    pitts = next(row for row in snapshot.rows if row.player_name == "Kyle Pitts")
    assert pitts.stats["rec_yd"] == 900
    assert pitts.stats["rush_yd"] == 0


def test_fftoday_live_follows_hosted_next_page_and_deduplicates_rows() -> None:
    single_pages = {
        "PosID=20": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Att</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Bijan Robinson</td><td>ATL</td><td>11</td><td>292</td><td>1536</td><td>11</td><td>71</td><td>594</td><td>3</td><td>328</td></tr></table></body></html>""",
        "PosID=30": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Rec</th><th>Yds</th><th>TD</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Drake London</td><td>ATL</td><td>11</td><td>99</td><td>1312</td><td>7</td><td>0</td><td>0</td><td>0</td><td>173.2</td></tr></table></body></html>""",
        "PosID=40": """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Rec</th><th>Yds</th><th>TD</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Kyle Pitts</td><td>ATL</td><td>11</td><td>80</td><td>900</td><td>6</td><td>0</td><td>0</td><td>0</td><td>166</td></tr></table></body></html>""",
    }
    qb_first = """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Cmp</th><th>Att</th><th>Yds</th><th>TD</th><th>INT</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Lamar Jackson</td><td>BAL</td><td>13</td><td>304</td><td>475</td><td>3704</td><td>26</td><td>8</td><td>127</td><td>646</td><td>3</td><td>334.8</td></tr></table><a>Next Page</a><a>Last Page</a></body></html>"""
    qb_second = """<html><body>Updated: 9/3/2026<table><tr><th>Player</th><th>Tm</th><th>Bye</th><th>Cmp</th><th>Att</th><th>Yds</th><th>TD</th><th>INT</th><th>Att</th><th>Yds</th><th>TD</th><th>FPts</th></tr><tr><td>Lamar Jackson</td><td>BAL</td><td>13</td><td>304</td><td>475</td><td>3704</td><td>26</td><td>8</td><td>127</td><td>646</td><td>3</td><td>334.8</td></tr><tr><td>Josh Allen</td><td>BUF</td><td>7</td><td>326</td><td>479</td><td>3787</td><td>26</td><td>9</td><td>113</td><td>567</td><td>12</td><td>384.2</td></tr></table><a>First Page</a><a>Previous Page</a></body></html>"""
    requested: list[str] = []

    def getter(url: str) -> str:
        requested.append(url)
        if "PosID=10" in url:
            return qb_second if "cur_page=1" in url else qb_first
        return next(html for marker, html in single_pages.items() if marker in url)

    snapshot = FFTodayLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    ).fetch_latest(season=2026)

    qb_names = {row.player_name for row in snapshot.rows if row.position.value == "QB"}
    assert qb_names == {"Lamar Jackson", "Josh Allen"}
    qb_urls = [url for url in requested if "PosID=10" in url]
    assert len(qb_urls) == 2
    assert "cur_page=1" not in qb_urls[0]
    assert "cur_page=1" in qb_urls[1]
