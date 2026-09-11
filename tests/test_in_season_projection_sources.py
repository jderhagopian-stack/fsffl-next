from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from fsffl.providers.in_season_projection_sources import (
    CBSInSeasonProjectionSource,
    FFTodayWeeklyProjectionSource,
    RazzballRestOfSeasonProjectionSource,
)
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource


NOW = datetime(2026, 9, 11, 20, 0, tzinfo=UTC)


def _span_tokens(tokens: list[str]) -> str:
    return "".join(f"<span>{token}</span>" for token in tokens)


def _cbs_html(position: str, heading: str) -> str:
    tail_count = {"QB": 15, "RB": 14, "WR": 14, "TE": 10}[position]
    return (
        f"<div>{heading} Fantasy Football</div>"
        + _span_tokens([f"Test {position}", position, "NYG", *(["1"] * tail_count)])
    )


def test_cbs_explicit_ros_and_week_urls_are_horizon_guarded():
    ros_urls = []

    def ros_get(url: str) -> str:
        ros_urls.append(url)
        position = re.search(r"/stats/(QB|RB|WR|TE)/", url).group(1)
        return _cbs_html(position, "Rest of Season Proj")

    ros = CBSInSeasonProjectionSource(http_get_text=ros_get, clock=lambda: NOW).fetch_rest_of_season(
        season=2026
    )
    assert len(ros.rows) == 4
    assert all("/2026/restofseason/projections/" in url for url in ros_urls)

    week_urls = []

    def week_get(url: str) -> str:
        week_urls.append(url)
        position = re.search(r"/stats/(QB|RB|WR|TE)/", url).group(1)
        return _cbs_html(position, "Week 2 Proj")

    weekly = CBSInSeasonProjectionSource(http_get_text=week_get, clock=lambda: NOW).fetch_week(
        season=2026,
        week=2,
    )
    assert len(weekly.rows) == 4
    assert all("/2026/2/projections/" in url for url in week_urls)


def _fftoday_week_html(position: str) -> str:
    tail_count = {"QB": 10, "RB": 8, "WR": 8, "TE": 5}[position]
    return (
        "<div>2026 Week 2 Projections</div>"
        + _span_tokens([f"Test {position}", "NYG", *(["1"] * tail_count)])
    )


def test_fftoday_week_source_requires_target_week_semantics():
    position_by_id = {"10": "QB", "20": "RB", "30": "WR", "40": "TE"}
    urls = []

    def get(url: str) -> str:
        urls.append(url)
        pos_id = re.search(r"PosID=(10|20|30|40)", url).group(1)
        return _fftoday_week_html(position_by_id[pos_id])

    snapshot = FFTodayWeeklyProjectionSource(http_get_text=get, clock=lambda: NOW).fetch_week(
        season=2026,
        week=2,
    )
    assert len(snapshot.rows) == 4
    assert all("GameWeek=2" in url for url in urls)
    assert all("playerwkproj.php" in url for url in urls)


def _table(headers: list[str], values: list[str], heading: str) -> str:
    return (
        f"<div>{heading}</div><div>Updated: 2026-09-11 10:00:00 AM EDT</div>"
        "<table><tr>"
        + "".join(f"<th>{header}</th>" for header in headers)
        + "</tr><tr>"
        + "".join(f"<td>{value}</td>" for value in values)
        + "</tr></table>"
    )


def _razzball_ros_html(position: str, *, season: int = 2026) -> str:
    if position == "QB":
        headers = ["Name", "Team", "Pass Yds", "Pass TD", "Int", "Rush Yds", "Run TD"]
        values = ["Test QB", "NYG", "3000", "20", "8", "300", "3"]
    elif position == "RB":
        headers = ["Name", "Team", "Rush Yds", "Run TD", "Rec", "Rec Yds", "Rec TD"]
        values = ["Test RB", "NYG", "800", "7", "40", "350", "3"]
    else:
        headers = ["Name", "Team", "Rec", "Rec Yds", "Rec TD"]
        values = [f"Test {position}", "NYG", "60", "850", "6"]
    return _table(headers, values, f"{season} Rest of Season Projections")


def test_razzball_ros_uses_position_specific_rest_of_season_tables():
    urls = []

    def get(url: str) -> str:
        urls.append(url)
        position = re.search(r"projections-(qb|rb|wr|te)-restofseason", url).group(1).upper()
        return _razzball_ros_html(position)

    snapshot = RazzballRestOfSeasonProjectionSource(http_get_text=get, clock=lambda: NOW).fetch_latest(
        season=2026
    )
    assert {row["Pos"] for row in snapshot.rows} == {"QB", "RB", "WR", "TE"}
    assert len(urls) == 4
    assert all("restofseason" in url for url in urls)


def test_razzball_ros_rejects_current_page_for_wrong_requested_season():
    def get(url: str) -> str:
        position = re.search(r"projections-(qb|rb|wr|te)-restofseason", url).group(1).upper()
        return _razzball_ros_html(position, season=2026)

    with pytest.raises(ValueError, match="requested 2025 season"):
        RazzballRestOfSeasonProjectionSource(http_get_text=get, clock=lambda: NOW).fetch_latest(
            season=2025
        )


def test_full_season_razzball_source_never_reads_ros_pages_and_verifies_season():
    calls = []
    headers = [
        "Name",
        "Pos",
        "Team",
        "Pass Yds",
        "Pass TD",
        "Int",
        "Rush Yds",
        "Run TD",
        "Rec",
        "Rec Yds",
        "Rec TD",
    ]
    values = ["Test RB", "RB", "NYG", "0", "0", "0", "1000", "8", "40", "350", "3"]
    html = _table(headers, values, "2026 Fantasy Football Projections")

    def get(url: str) -> str:
        calls.append(url)
        return html

    snapshot = RazzballSeasonProjectionSource(http_get_text=get, clock=lambda: NOW).fetch_latest(
        season=2026
    )
    assert len(snapshot.rows) == 1
    assert calls == ["https://football.razzball.com/projections/"]
