from datetime import UTC, datetime

from fsffl.forecast.adapters.razzball import normalize_razzball_snapshot
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.razzball_live import RazzballLiveProjectionSource
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    Team,
    TeamState,
)


CAPTURED = datetime(2026, 9, 5, 17, 0, tzinfo=UTC)
HTML = """
<html><body>
<div>Updated: 2026-09-05 11:59:35 AM EST (2026-09-05 11:59:35 AM)</div>
<table><tr><th>Name</th><th>Something</th></tr><tr><td>Ignore</td><td>1</td></tr></table>
<table>
<tr><th>#</th><th>Name</th><th>Pos</th><th>Team</th><th>STD PTS</th><th>1/2PPR PTS</th><th>PPR PTS</th><th>Pass Yds</th><th>Pass TD</th><th>Int</th><th>Rush Yds</th><th>Run TD</th><th>Rec</th><th>Rec Yds</th><th>Rec TD</th></tr>
<tr><td></td><td>Lamar Jackson</td><td>QB</td><td>BAL</td><td>300</td><td>300</td><td>300</td><td>3821</td><td>26.4</td><td>11.1</td><td>632</td><td>3.0</td><td>0</td><td>0</td><td>0</td></tr>
<tr><td></td><td>Brian Thomas Jr.</td><td>WR</td><td>JAC</td><td>200</td><td>240</td><td>280</td><td>0</td><td>0</td><td>0</td><td>20</td><td>0</td><td>80</td><td>1200</td><td>8</td></tr>
<tr><td></td><td>Unknown Player</td><td>WR</td><td>NYJ</td><td>1</td><td>1</td><td>1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>10</td><td>0</td></tr>
</table>
</body></html>
"""


def _league_state() -> LeagueState:
    as_of = CAPTURED
    league = League(
        league_id="sleeper:1",
        name="Test",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=2, lineup=(), scoring=()),
    )
    team_a = Team(team_id="a", league_id=league.league_id, display_name="A")
    team_b = Team(team_id="b", league_id=league.league_id, display_name="B")
    provenance = Provenance(source="sleeper", retrieved_at=as_of, effective_at=as_of)
    players = (
        Player(player_id="lamar", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL"),
        Player(player_id="btj", full_name="Brian Thomas Jr.", position=Position.WR, nfl_team="JAX"),
    )
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=(team_a, team_b),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=players,
        player_states=tuple(
            PlayerState(player_id=player.player_id, as_of=as_of, nfl_team=player.nfl_team, provenance=provenance)
            for player in players
        ),
    )


def test_live_source_selects_projection_table_and_preserves_provider_update_time() -> None:
    source = RazzballLiveProjectionSource(
        http_get_text=lambda _: HTML,
        clock=lambda: CAPTURED,
    )
    snapshot = source.fetch_latest()
    assert len(snapshot.rows) == 3
    assert snapshot.rows[0]["Name"] == "Lamar Jackson"
    assert snapshot.effective_at < snapshot.captured_at
    assert snapshot.usage_class == "beta-personal-research-requires-commercial-review"


def test_adapter_maps_team_alias_and_ignores_provider_fantasy_points() -> None:
    snapshot = RazzballLiveProjectionSource(
        http_get_text=lambda _: HTML,
        clock=lambda: CAPTURED,
    ).fetch_latest()
    observations, report = normalize_razzball_snapshot(
        snapshot,
        league_state=_league_state(),
        period_end=datetime(2027, 2, 15, tzinfo=UTC),
    )
    assert report.matched_rows == 2
    assert report.exact_matches == 2
    assert any(item.player_id == "btj" and item.provider_team == "JAX" for item in report.matches)
    assert any("Unknown Player" in item for item in report.unmatched_rows)
    assert all(item.metric != ForecastMetric.FANTASY_POINTS for item in observations)
    lamar_pass = next(
        item for item in observations
        if item.player_id == "lamar" and item.metric == ForecastMetric.PASS_YARDS
    )
    assert lamar_pass.distribution.mean == 3821.0
    assert lamar_pass.provenance.source == "razzball"
