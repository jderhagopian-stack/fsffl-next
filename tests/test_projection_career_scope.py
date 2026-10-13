from datetime import UTC, datetime

from fsffl.forecast.current_normalization import map_projection_rows
from fsffl.product.career_coverage import (
    build_career_position_depth_refresh,
    resolve_career_coverage,
)
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import Player, Position, ProviderRef


def test_shared_projection_mapping_feeds_new_roster_and_explore_career_subjects():
    players = (
        Player(
            player_id="sleeper:player:new-roster",
            full_name="New Roster Player",
            position=Position.WR,
            nfl_team="SEA",
            provider_refs=(ProviderRef(provider="cbs", external_id="cbs:roster"),),
        ),
        Player(
            player_id="sleeper:player:explore",
            full_name="Explore Candidate",
            position=Position.RB,
            nfl_team="BUF",
        ),
    )
    snapshot = CurrentProjectionSnapshot(
        provider="CBS",
        captured_at=datetime(2026, 10, 12, 2, tzinfo=UTC),
        effective_at=datetime(2026, 10, 12, 2, tzinfo=UTC),
        rows=(
            CurrentProjectionRow(
                provider="CBS", external_id="cbs:roster", player_name="Provider Alias",
                position=Position.WR, nfl_team="NYJ", stats={"rec_yd": 820.0},
            ),
            CurrentProjectionRow(
                provider="CBS", external_id="cbs:explore", player_name="Explore Candidate",
                position=Position.RB, nfl_team="BUF", stats={"rush_yd": 640.0},
            ),
        ),
        source_version="cbs-ros-test",
        usage_class="test",
    )
    mapped = map_projection_rows(snapshot, players=players)
    evidence = {
        player.player_id: {"provider": snapshot.provider, "external_id": row.external_id,
                           "stats": dict(row.stats)}
        for row, player in mapped
    }
    state_players = [
        {"player_id": player.player_id, "position": player.position.value,
         "nfl_team": player.nfl_team}
        for player in players
    ]
    roster_rows = [{
        "player_id": "sleeper:player:new-roster", "position": "WR", "team_id": "team-a",
        "roster_slot": "BENCH", "state_hash": "state-1",
    }]
    result = resolve_career_coverage(
        state_players=state_players,
        roster_rows=roster_rows,
        state_hash="state-1",
        precomputed_player_ids={"sleeper:player:explore"},
        evidence_by_player=evidence,
        materialize_batch=lambda subjects, packets: {
            subject.player_id: {"career_value": float(packets[subject.player_id]["stats"].get("rec_yd", 0)
                                                          + packets[subject.player_id]["stats"].get("rush_yd", 0))}
            for subject in subjects
        },
    )
    assert set(result.authority) == {player.player_id for player in players}
    assert result.authority["sleeper:player:new-roster"]["career_value"] == 820.0
    assert result.authority["sleeper:player:explore"]["career_value"] == 640.0

    depth = build_career_position_depth_refresh(
        state_hash="state-1", roster_rows=roster_rows, subjects=result.subjects,
        authority=result.authority, failures=result.missing,
    )
    assert len(depth) == 1
    assert depth[0]["player_id"] == "sleeper:player:new-roster"
    assert depth[0]["career_coverage_status"] == "career_authority_available"
