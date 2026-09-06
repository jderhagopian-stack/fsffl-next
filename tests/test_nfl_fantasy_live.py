from datetime import UTC, datetime

from fsffl.providers.nfl_fantasy_live import NFLFantasyLiveProjectionSource


HTML_BY_POSITION = {
    "position=1": """<html><body>1 - 1 of 1<table><tr><th>Player</th><th>Opp</th><th>GP</th><th>Yds</th><th>TD</th><th>Int</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>TD</th><th>FumTD</th><th>2PT</th><th>Lost</th><th>Points</th></tr><tr><td>Lamar Jackson QB - BAL View News</td><td>NE</td><td>17</td><td>3704</td><td>26</td><td>8</td><td>646</td><td>3</td><td>-</td><td>-</td><td>-</td><td>-</td><td>1</td><td>-</td><td>2</td><td>334.8</td></tr></table></body></html>""",
    "position=2": """<html><body>1 - 1 of 1<table><tr><th>Player</th><th>Opp</th><th>GP</th><th>Yds</th><th>TD</th><th>Int</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>TD</th><th>FumTD</th><th>2PT</th><th>Lost</th><th>Points</th></tr><tr><td>Bijan Robinson RB - ATL</td><td>TB</td><td>17</td><td>-</td><td>-</td><td>-</td><td>1400</td><td>9</td><td>71</td><td>701</td><td>4</td><td>-</td><td>-</td><td>-</td><td>2</td><td>310</td></tr></table></body></html>""",
    "position=3": """<html><body>1 - 1 of 1<table><tr><th>Player</th><th>Opp</th><th>GP</th><th>Yds</th><th>TD</th><th>Int</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>TD</th><th>FumTD</th><th>2PT</th><th>Lost</th><th>Points</th></tr><tr><td>Drake London WR - ATL</td><td>TB</td><td>17</td><td>-</td><td>-</td><td>-</td><td>0</td><td>0</td><td>98</td><td>1273</td><td>9</td><td>-</td><td>-</td><td>-</td><td>1</td><td>230</td></tr></table></body></html>""",
    "position=4": """<html><body>1 - 1 of 1<table><tr><th>Player</th><th>Opp</th><th>GP</th><th>Yds</th><th>TD</th><th>Int</th><th>Yds</th><th>TD</th><th>Rec</th><th>Yds</th><th>TD</th><th>TD</th><th>FumTD</th><th>2PT</th><th>Lost</th><th>Points</th></tr><tr><td>Kyle Pitts TE - ATL</td><td>TB</td><td>17</td><td>-</td><td>-</td><td>-</td><td>0</td><td>0</td><td>80</td><td>900</td><td>6</td><td>-</td><td>-</td><td>-</td><td>1</td><td>180</td></tr></table></body></html>""",
}


def test_nfl_fantasy_live_parses_raw_projection_stats() -> None:
    requested_urls: list[str] = []

    def getter(url: str) -> str:
        requested_urls.append(url)
        return next(html for marker, html in HTML_BY_POSITION.items() if marker in url)

    source = NFLFantasyLiveProjectionSource(
        http_get_text=getter,
        clock=lambda: datetime(2026, 9, 5, tzinfo=UTC),
    )
    snapshot = source.fetch_latest(season=2026)
    assert snapshot.provider == "nfl_fantasy"
    assert len(snapshot.rows) == 4
    assert all("sort=29" in url for url in requested_urls)
    assert all("statSeason=2026" in url for url in requested_urls)
    assert all("statType=seasonProjectedStats" in url for url in requested_urls)
    lamar = next(row for row in snapshot.rows if row.player_name == "Lamar Jackson")
    assert lamar.stats["pass_yd"] == 3704
    assert lamar.stats["rush_yd"] == 646
    assert lamar.stats["fum_lost"] == 2
    london = next(row for row in snapshot.rows if row.player_name == "Drake London")
    assert london.stats["rec"] == 98
    assert london.stats["rec_yd"] == 1273
