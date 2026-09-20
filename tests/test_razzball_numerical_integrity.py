from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.forecast.current_normalization import (
    current_snapshot_from_razzball,
    normalize_current_projection_snapshot,
)
from fsffl.forecast.live_ensemble import (
    LiveForecastSourceBatch,
    build_authoritative_live_ensemble,
)
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.current_projection_rows import (
    CurrentProjectionRow,
    CurrentProjectionSnapshot,
)
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource
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


NOW = datetime(2026, 9, 20, 16, 0, tzinfo=UTC)


def _html(*, duplicate: bool = False) -> str:
    row = (
        "<tr><td></td><td>Puka Nacua</td><td>WR</td><td>LAR</td>"
        "<td>410.0</td><td>521.5</td><td>633.0</td>"
        "<td>0</td><td>0</td><td>0</td>"
        "<td>114</td><td>0.9</td><td>223</td><td>2926</td><td>17</td></tr>"
    )
    return f"""
    <html><body>
    <h1>2026 Fantasy Football Projections</h1>
    <div>Updated: 2026-09-20 09:48:44 AM EST</div>
    <table>
      <tr><th>#</th><th>Name</th><th>Pos</th><th>Team</th><th>STD PTS</th>
      <th>1/2PPR PTS</th><th>PPR PTS</th><th>Pass Yds</th><th>Pass TD</th>
      <th>Int</th><th>Rush Yds</th><th>Run TD</th><th>Rec</th><th>Rec Yds</th><th>Rec TD</th></tr>
      {row}
      {row if duplicate else ""}
    </table>
    </body></html>
    """


def _state() -> LeagueState:
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )
    league = League(
        league_id="trace",
        name="Trace",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
    )
    player = Player(
        player_id="puka",
        full_name="Puka Nacua",
        position=Position.WR,
        nfl_team="LAR",
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id="trace", display_name="A"),
            Team(team_id="b", league_id="trace", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(player,),
        player_states=(
            PlayerState(
                player_id="puka",
                as_of=NOW,
                nfl_team="LAR",
                provenance=provenance,
            ),
        ),
    )


def _normalized_razzball(*, duplicate: bool = False):
    raw = RazzballSeasonProjectionSource(
        http_get_text=lambda _url: _html(duplicate=duplicate),
        clock=lambda: NOW,
    ).fetch_latest(season=2026)
    current = current_snapshot_from_razzball(raw)
    normalized = normalize_current_projection_snapshot(
        current,
        league_state=_state(),
        season=2026,
        evaluation_as_of=NOW,
    )
    return raw, current, normalized


def test_razzball_source_to_normalization_preserves_numeric_values_exactly() -> None:
    raw, current, normalized = _normalized_razzball()
    assert len(raw.rows) == 1
    assert raw.rows[0]["Rec"] == "223"
    assert raw.rows[0]["Rec Yds"] == "2926"
    assert raw.rows[0]["Rec TD"] == "17"

    assert len(current.rows) == 1
    assert current.rows[0].stats["rec"] == 223.0
    assert current.rows[0].stats["rec_yd"] == 2926.0
    assert current.rows[0].stats["rec_td"] == 17.0

    means = {item.metric: item.distribution.mean for item in normalized}
    assert means[ForecastMetric.RECEPTIONS] == 223.0
    assert means[ForecastMetric.REC_YARDS] == 2926.0
    assert means[ForecastMetric.REC_TD] == 17.0


def test_razzball_normalization_does_not_apply_hidden_multiplier() -> None:
    _, current, normalized = _normalized_razzball()
    source_stats = current.rows[0].stats
    metric_map = {
        ForecastMetric.RECEPTIONS: "rec",
        ForecastMetric.REC_YARDS: "rec_yd",
        ForecastMetric.REC_TD: "rec_td",
        ForecastMetric.RUSH_YARDS: "rush_yd",
        ForecastMetric.RUSH_TD: "rush_td",
    }
    for observation in normalized:
        key = metric_map.get(observation.metric)
        if key is not None:
            assert observation.distribution.mean == source_stats[key]


def test_duplicate_single_provider_observation_fails_closed_in_ensemble() -> None:
    _, _, razzball = _normalized_razzball(duplicate=True)
    fftoday_snapshot = CurrentProjectionSnapshot(
        provider="fftoday",
        captured_at=NOW,
        effective_at=NOW,
        rows=(
            CurrentProjectionRow(
                provider="fftoday",
                external_id="puka-fftoday",
                player_name="Puka Nacua",
                position=Position.WR,
                nfl_team="LAR",
                stats={
                    "rush_yd": 72.0,
                    "rush_td": 1.0,
                    "rec": 113.0,
                    "rec_yd": 1521.0,
                    "rec_td": 9.0,
                },
            ),
        ),
        source_version="fixture",
        usage_class="fixture",
    )
    fftoday = normalize_current_projection_snapshot(
        fftoday_snapshot,
        league_state=_state(),
        season=2026,
        evaluation_as_of=NOW,
    )

    with pytest.raises(ValueError, match="duplicate forecast source within one ensemble group"):
        build_authoritative_live_ensemble(
            (
                LiveForecastSourceBatch(source_id="razzball", observations=razzball),
                LiveForecastSourceBatch(source_id="fftoday", observations=fftoday),
            )
        )


def test_ensemble_is_exact_equal_weight_not_hidden_provider_multiplication() -> None:
    _, _, razzball = _normalized_razzball()
    fftoday_snapshot = CurrentProjectionSnapshot(
        provider="fftoday",
        captured_at=NOW,
        effective_at=NOW,
        rows=(
            CurrentProjectionRow(
                provider="fftoday",
                external_id="puka-fftoday",
                player_name="Puka Nacua",
                position=Position.WR,
                nfl_team="LAR",
                stats={
                    "rush_yd": 72.0,
                    "rush_td": 1.0,
                    "rec": 113.0,
                    "rec_yd": 1521.0,
                    "rec_td": 9.0,
                },
            ),
        ),
        source_version="fixture",
        usage_class="fixture",
    )
    fftoday = normalize_current_projection_snapshot(
        fftoday_snapshot,
        league_state=_state(),
        season=2026,
        evaluation_as_of=NOW,
    )
    ensemble, _coverage = build_authoritative_live_ensemble(
        (
            LiveForecastSourceBatch(source_id="razzball", observations=razzball),
            LiveForecastSourceBatch(source_id="fftoday", observations=fftoday),
        )
    )
    rec_yards = next(item for item in ensemble if item.metric == ForecastMetric.REC_YARDS)
    assert rec_yards.distribution.mean == pytest.approx((2926.0 + 1521.0) / 2.0)
