from datetime import UTC, datetime

from fsffl.providers.razzball_live import RazzballLiveProjectionSource

CAPTURED = datetime(2026, 9, 5, 20, 0, tzinfo=UTC)
BASE = """
<div>Updated: 2026-09-04 03:27:24 PM EST</div>
<table>
<tr><th>Name</th><th>Pos</th><th>Team</th><th>Pass Yds</th><th>Pass TD</th><th>Int</th><th>Rush Yds</th><th>Run TD</th><th>Rec</th><th>Rec Yds</th><th>Rec TD</th></tr>
<tr><td>Lamar Jackson</td><td>QB</td><td>BAL</td><td>3822</td><td>26.4</td><td>11.1</td><td>632</td><td>3</td><td>0</td><td>0</td><td>0</td></tr>
</table>
"""
FUMBLES = """
<div>Updated: 2026-09-04 03:27:24 PM EST</div>
<table>
<tr><th>Name</th><th>Team</th><th>Fum Lst</th></tr>
<tr><td>Lamar Jackson</td><td>BAL</td><td>3.1</td></tr>
</table>
"""


def test_position_pages_add_fumbles_without_replacing_base_projection_rows() -> None:
    def getter(url: str) -> str:
        return BASE if url == RazzballLiveProjectionSource.source_url else FUMBLES

    snapshot = RazzballLiveProjectionSource(http_get_text=getter, clock=lambda: CAPTURED).fetch_latest()
    lamar = snapshot.rows[0]
    assert lamar["Pass Yds"] == "3822"
    assert lamar["Fum Lst"] == "3.1"
