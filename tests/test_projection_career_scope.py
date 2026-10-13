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
    snapshots = tuple(
        CurrentProjectionSnapshot(
            provider=provider,
            captured_at=datetime(2026, 10, 12, 2, tzinfo=UTC),
            effective_at=datetime(2026, 10, 12, 2, tzinfo=UTC),
            rows=(
                CurrentProjectionRow(
                    provider=provider,
                    external_id=f"{provider.lower()}:roster",
                    player_name="Provider Alias" if provider == "CBS" else "New Roster Player",
                    position=Position.WR, nfl_team="NYJ" if provider == "CBS" else "SEA",
                    stats={"rec_yd": 820.0 if provider == "CBS" else 800.0},
                ),
                CurrentProjectionRow(
                    provider=provider, external_id=f"{provider.lower()}:explore",
                    player_name="Explore Candidate", position=Position.RB, nfl_team="BUF",
                    stats={"rush_yd": 640.0 if provider == "CBS" else 620.0},
                ),
            ),
            source_version=f"{provider.lower()}-ros-test",
            usage_class="test",
        )
        for provider in ("CBS", "Razzball")
    )
    mapped = tuple(
        pair for snapshot in snapshots for pair in map_projection_rows(snapshot, players=players)
    )
    evidence = {}
    for row, player in mapped:
        evidence.setdefault(player.player_id, []).append(
            {"provider": row.provider, "external_id": row.external_id, "stats": dict(row.stats)}
        )
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
            subject.player_id: {
                "career_value": float(sum(
                    row["stats"].get("rec_yd", 0) + row["stats"].get("rush_yd", 0)
                    for row in packets[subject.player_id]
                ) / 2),
                "providers": sorted(row["provider"] for row in packets[subject.player_id]),
            }
            for subject in subjects
        },
    )
    assert set(result.authority) == {player.player_id for player in players}
    assert result.authority["sleeper:player:new-roster"]["career_value"] == 810.0
    assert result.authority["sleeper:player:explore"]["career_value"] == 630.0
    assert result.authority["sleeper:player:new-roster"]["providers"] == ["CBS", "Razzball"]
    assert result.authority["sleeper:player:explore"]["providers"] == ["CBS", "Razzball"]

    depth = build_career_position_depth_refresh(
        state_hash="state-1", roster_rows=roster_rows, subjects=result.subjects,
        authority=result.authority, failures=result.missing,
    )
    assert len(depth) == 1
    assert depth[0]["player_id"] == "sleeper:player:new-roster"
    assert depth[0]["career_coverage_status"] == "career_authority_available"
