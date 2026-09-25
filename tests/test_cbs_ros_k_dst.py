from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.forecast.models import ForecastMetric
from fsffl.providers.cbs_ros_k_dst import CBSRosKDstProjectionSource
from fsffl.providers.ros_projection_rows import ProjectionRightsStatus
from fsffl.state.models import Position


NOW = datetime(2026, 9, 25, 12, 28, tzinfo=UTC)


def _k_page() -> str:
    return """
    <html><body>
      <h1>2026 Rest of Season Proj Fantasy Football Kicker Stats</h1>
      <table>
        <tr><th>Player</th><th>GP</th><th>FGM</th><th>FGA</th><th>1-19</th><th>20-29</th><th>30-39</th><th>40-49</th><th>50+</th><th>XPM</th><th>XPA</th></tr>
        <tr><td>Brandon Aubrey K DAL</td><td>15</td><td>30</td><td>34</td><td>1</td><td>8</td><td>8</td><td>8</td><td>5</td><td>40</td><td>41</td></tr>
      </table>
    </body></html>
    """


def _dst_page() -> str:
    return """
    <html><body>
      <h1>2026 Rest of Season Proj Fantasy Football DST Stats</h1>
      <table>
        <tr><th>Team</th><th>GP</th><th>INT</th><th>SAF</th><th>SACK</th><th>FR</th><th>FF</th><th>TD</th><th>PA</th><th>YDS</th></tr>
        <tr><td>Denver Broncos DST DEN</td><td>15</td><td>14</td><td>1</td><td>42</td><td>9</td><td>11</td><td>4</td><td>310</td><td>5100</td></tr>
      </table>
    </body></html>
    """


def test_cbs_ros_adapter_is_horizon_explicit_rights_classified_and_raw_only() -> None:
    def getter(url: str) -> str:
        return _k_page() if "/K/" in url else _dst_page()

    snapshot = CBSRosKDstProjectionSource(
        http_get_text=getter,
        clock=lambda: NOW,
    ).fetch_latest(season=2026)

    assert snapshot.horizon == "rest_of_season"
    assert snapshot.rights_status == ProjectionRightsStatus.RESEARCH_ONLY
    assert snapshot.captured_at == NOW
    assert len(snapshot.content_sha256) == 64

    kicker = next(row for row in snapshot.rows if row.position == Position.K)
    assert kicker.projected_games == 15
    assert kicker.stat_map[ForecastMetric.FG_MADE.value] == 30
    assert kicker.stat_map[ForecastMetric.FG_MADE_50_PLUS.value] == 5
    assert ForecastMetric.FG_MADE_60_PLUS.value not in kicker.stat_map

    dst = next(row for row in snapshot.rows if row.position == Position.DST)
    assert dst.stat_map[ForecastMetric.DST_SACK.value] == 42
    assert dst.stat_map[ForecastMetric.DST_INTERCEPTION.value] == 14
    assert dst.stat_map["diagnostic_points_allowed"] == 310
    assert all(
        not key.startswith("pts_allow_")
        for key in dst.stat_map
    )


def test_cbs_ros_adapter_rejects_wrong_year_content() -> None:
    wrong = _k_page().replace("2026", "2025")
    source = CBSRosKDstProjectionSource(
        http_get_text=lambda _url: wrong,
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="does not prove season 2026"):
        source.fetch_latest(season=2026)


def test_cbs_ros_adapter_rejects_full_season_content_as_ros() -> None:
    wrong = _k_page().replace("Rest of Season", "Full Season")
    source = CBSRosKDstProjectionSource(
        http_get_text=lambda _url: wrong,
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="does not prove ROS horizon"):
        source.fetch_latest(season=2026)


def test_cbs_ros_adapter_is_hard_disabled_outside_2026() -> None:
    source = CBSRosKDstProjectionSource(
        http_get_text=lambda _url: _k_page(),
        clock=lambda: NOW,
    )
    with pytest.raises(ValueError, match="only for 2026"):
        source.fetch_latest(season=2027)
