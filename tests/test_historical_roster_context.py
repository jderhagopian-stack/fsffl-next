from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context


def _season(*, team_count: int = 4, season: int = 2023, scoring: int = 0):
    trade_at = int(datetime(season, 10, 1, tzinfo=UTC).timestamp() * 1000)
    waiver_at = trade_at + 100_000
    rosters = []
    for roster_id in range(1, team_count + 1):
        players = ["player-b", "waiver-player"] if roster_id == 1 else ["player-a"] if roster_id == 2 else []
        used = 14 if roster_id == 1 else 15 if roster_id == 2 else 0
        rosters.append({"roster_id": roster_id, "players": players,
                        "settings": {"waiver_budget_used": used}})
    return {
        "league": {
            "league_id": f"league-{season}-{team_count}", "season": str(season),
            "total_rosters": team_count, "roster_positions": ["QB", "WR", "SUPER_FLEX", "BN"],
            "settings": {"waiver_budget": 100, "reserve_slots": 2},
            "scoring_settings": {"fum_lost": scoring},
        },
        "rosters": rosters,
        "traded_picks": [{"season": str(season + 3), "round": 3,
                           "roster_id": min(3, team_count), "owner_id": 2}],
        "transactions": [
            {"type": "trade", "status": "complete", "transaction_id": "trade-1",
             "created": trade_at - 60_000, "status_updated": trade_at,
             "roster_ids": [1, 2], "adds": {"player-a": 2, "player-b": 1},
             "drops": {"player-a": 1, "player-b": 2},
             "draft_picks": [{"season": str(season + 3), "round": 3,
                              "roster_id": min(3, team_count),
                              "previous_owner_id": 3, "owner_id": 2}],
             "waiver_budget": [{"sender": 2, "receiver": 1, "amount": 10}]},
            {"type": "waiver", "status": "complete", "transaction_id": "waiver-1",
             "created": waiver_at - 1000, "status_updated": waiver_at,
             "roster_ids": [1], "adds": {"waiver-player": 1}, "drops": {},
             "settings": {"waiver_bid": 4}, "draft_picks": [], "waiver_budget": []},
        ],
    }


@pytest.mark.parametrize("team_count", [4, 12, 18])
def test_reconstructs_all_event_boundaries_without_fixed_team_count(team_count: int) -> None:
    result = reconstruct_sleeper_roster_context(_season(team_count=team_count), source_revision="archive-sha")

    assert result.membership_status == "provisionally_consistent"
    assert result.observed_team_count == team_count
    assert result.completed_event_count == 2
    assert result.eligible_for_pit_decision_grade is False
    assert result.raw_roster_slots == ("QB", "WR", "SUPER_FLEX", "BN")
    assert all(row.roster_slot_coverage == "unknown" for row in result.snapshots)
    assert result.snapshots[-1].boundary == "archive_end_anchor"

    trade_ms = int(datetime(2023, 10, 1, tzinfo=UTC).timestamp() * 1000)
    trade_before = next(row for row in result.snapshots
                        if row.effective_at == datetime.fromtimestamp(trade_ms / 1000, tz=UTC)
                        and row.boundary == "before_completed_event_batch")
    owners = {row.provider_roster_id: row for row in trade_before.teams}
    assert owners["1"].player_ids == ("player-a",)
    assert owners["2"].player_ids == ("player-b",)
    assert owners[str(min(3, team_count))].traded_pick_ids == (f"{2026}:3:{min(3, team_count)}",)
    assert owners["2"].waiver_budget_used == 5
    assert owners["1"].waiver_budget_used == 20


def test_season_rules_are_fingerprinted_not_hardcoded() -> None:
    baseline = reconstruct_sleeper_roster_context(_season(season=2023, scoring=0), source_revision="archive-sha")
    changed = reconstruct_sleeper_roster_context(_season(season=2024, scoring=2), source_revision="archive-sha")

    assert baseline.league_rules_sha256 != changed.league_rules_sha256
    assert baseline.observed_team_count == changed.observed_team_count
    baseline_context = tuple((row.player_ids, row.waiver_budget_used) for row in baseline.snapshots[-1].teams)
    changed_context = tuple((row.player_ids, row.waiver_budget_used) for row in changed.snapshots[-1].teams)
    assert baseline_context == changed_context


def test_missing_event_timestamp_keeps_supported_membership_but_marks_history_incomplete() -> None:
    data = _season()
    data["transactions"][1]["status_updated"] = None
    result = reconstruct_sleeper_roster_context(data, source_revision="archive-sha")

    assert result.membership_status == "incomplete_source_history"
    assert "completed_event_missing_completion_timestamp" in result.issues
    assert result.snapshots


def test_faab_reconstruction_issue_does_not_block_roster_membership_context() -> None:
    data = _season()
    data["rosters"][0]["settings"]["waiver_budget_used"] = 1
    result = reconstruct_sleeper_roster_context(data, source_revision="archive-sha")

    assert result.membership_status == "provisionally_consistent"
    assert not result.membership_issues
    assert "reconstructed_waiver_usage_out_of_bounds" in result.faab_issues
    assert any(
        next(row for row in snapshot.teams if row.provider_roster_id == "1").waiver_budget_used is None
        for snapshot in result.snapshots[:-1]
    )
