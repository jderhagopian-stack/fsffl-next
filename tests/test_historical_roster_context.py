from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
from fsffl.state.historical_coverage import HistoricalSeasonIdentity
from fsffl.state.historical_supplemental_evidence import (
    HistoricalSupplementalEvidenceReceipt,
    HistoricalSupplementalPlayerMovement,
    SupplementalDatePrecision,
    SupplementalEvidenceSource,
    SupplementalFindingStatus,
    SupplementalPlayerMovementKind,
)


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


def _supplement(*, effective_date=date(2023, 8, 23), player="supplement-player"):
    return HistoricalSupplementalPlayerMovement(
        season=HistoricalSeasonIdentity(
            league_family_id="family-1", league_id="league-2023-4", season=2023,
        ),
        provider="sleeper", source_player_id=player, player_id="canonical-player",
        provider_roster_id="1", kind=SupplementalPlayerMovementKind.DROPPED_TO_WAIVERS,
        effective_date=effective_date, date_precision=SupplementalDatePrecision.DATE_ONLY,
        receipt=HistoricalSupplementalEvidenceReceipt(
            evidence_id="supplement-1", source=SupplementalEvidenceSource.USER_SUPPLIED_SCREENSHOT,
            source_fingerprint_sha256="c" * 64, received_at=datetime(2026, 11, 1, tzinfo=UTC),
            source_reference="private evidence reference",
        ),
    )


def _season_with_missing_add():
    data = _season()
    july_add = int(datetime(2023, 7, 27, 7, 5, 25, 93000, tzinfo=UTC).timestamp() * 1000)
    data["transactions"].append({
        "type": "waiver", "status": "complete", "transaction_id": "missing-add",
        "created": july_add - 1000, "status_updated": july_add, "roster_ids": [1],
        "adds": {"supplement-player": 1}, "drops": {},
        "settings": {"waiver_bid": 3}, "draft_picks": [], "waiver_budget": [],
    })
    return data


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
    baseline_data = _season(season=2023, scoring=0)
    changed_data = _season(season=2024, scoring=2)
    changed_data["league"]["roster_positions"] = [
        "QB", "RB", "WR", "TE", "FLEX", "FLEX", "K", "DST", "BN",
    ]
    changed_data["league"]["settings"]["reserve_slots"] = 1
    baseline = reconstruct_sleeper_roster_context(baseline_data, source_revision="archive-sha")
    changed = reconstruct_sleeper_roster_context(changed_data, source_revision="archive-sha")

    assert baseline.league_rules_sha256 != changed.league_rules_sha256
    assert baseline.observed_team_count == changed.observed_team_count
    assert changed.raw_roster_slots == tuple(changed_data["league"]["roster_positions"])
    baseline_context = tuple((row.player_ids, row.waiver_budget_used) for row in baseline.snapshots[-1].teams)
    changed_context = tuple((row.player_ids, row.waiver_budget_used) for row in changed.snapshots[-1].teams)
    assert baseline_context == changed_context


def test_snapshot_identity_is_stable_and_scoped_to_season_rules_and_source() -> None:
    data = _season(team_count=4, season=2023, scoring=0)
    first = reconstruct_sleeper_roster_context(data, source_revision="archive-sha-a")
    repeated = reconstruct_sleeper_roster_context(data, source_revision="archive-sha-a")
    different_source = reconstruct_sleeper_roster_context(data, source_revision="archive-sha-b")

    changed_rules_data = _season(team_count=8, season=2024, scoring=2)
    changed_rules = reconstruct_sleeper_roster_context(
        changed_rules_data, source_revision="archive-sha-a"
    )
    changed_league_data = _season(team_count=4, season=2023, scoring=0)
    changed_league_data["league"]["league_id"] = "different-provider-league"
    changed_league = reconstruct_sleeper_roster_context(
        changed_league_data, source_revision="archive-sha-a"
    )

    assert first.model_version == "historical-roster-context-v3"
    assert first.history_id.startswith("hctx_")
    assert first.history_id == repeated.history_id
    assert tuple(row.snapshot_id for row in first.snapshots) == tuple(
        row.snapshot_id for row in repeated.snapshots
    )
    assert len({row.snapshot_id for row in first.snapshots}) == len(first.snapshots)
    assert all(row.history_id == first.history_id for row in first.snapshots)
    assert first.history_id != different_source.history_id
    assert first.history_id != changed_rules.history_id
    assert first.history_id != changed_league.history_id
    assert all(row.snapshot_id != other.snapshot_id
               for row in first.snapshots for other in changed_rules.snapshots)


def test_league_family_identity_requires_explicit_matching_season_identity() -> None:
    first_data = _season(team_count=4, season=2023)
    second_data = _season(team_count=4, season=2024)
    first_identity = HistoricalSeasonIdentity(
        league_family_id="family-1", league_id="league-2023-4", season=2023,
    )
    second_identity = HistoricalSeasonIdentity(
        league_family_id="family-1", league_id="league-2024-4", season=2024,
    )

    first = reconstruct_sleeper_roster_context(
        first_data, source_revision="archive-sha", season_identity=first_identity,
    )
    second = reconstruct_sleeper_roster_context(
        second_data, source_revision="archive-sha", season_identity=second_identity,
    )
    unlinked = reconstruct_sleeper_roster_context(first_data, source_revision="archive-sha")

    assert first.league_family_id == second.league_family_id == "family-1"
    assert first.family_identity_status == second.family_identity_status == "verified_family"
    assert unlinked.league_family_id is None
    assert unlinked.family_identity_status == "unlinked_season"
    assert first.history_id != unlinked.history_id
    assert second.history_id != first.history_id

    with pytest.raises(ValueError, match="must match provider league and year"):
        reconstruct_sleeper_roster_context(
            first_data, source_revision="archive-sha", season_identity=second_identity,
        )


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


def test_supported_date_only_drop_repairs_retrospective_roster_replay_without_promoting_source_audit():
    data = _season_with_missing_add()
    original = repr(data)
    baseline = reconstruct_sleeper_roster_context(data, source_revision="archive-sha")
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(_supplement(),)
    )
    changed_receipt = _supplement().receipt.model_copy(update={
        "source_fingerprint_sha256": "d" * 64,
    })
    changed_evidence = _supplement().model_copy(update={"receipt": changed_receipt})
    changed_evidence_result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(changed_evidence,)
    )

    assert repr(data) == original
    assert result.provider_audit is not None
    assert result.provider_audit.status == "incomplete_source_history"
    assert result.provider_audit_status == "incomplete_source_history"
    assert [issue.code for issue in result.provider_audit.issues] == ["post_event_player_missing"]
    assert result.supplemental_reconciliation is not None
    assert result.supplemental_reconciliation.findings[0].status == SupplementalFindingStatus.SUPPORTED_RETROSPECTIVELY
    assert result.supplemental_replay_status == "applied_retrospectively"
    assert result.history_id == baseline.history_id
    assert result.supplemental_evidence_sha256 != baseline.supplemental_evidence_sha256
    assert changed_evidence_result.history_id == result.history_id
    assert changed_evidence_result.supplemental_evidence_sha256 != result.supplemental_evidence_sha256
    assert result.supplemental_applied_evidence_ids == ("supplement-1",)
    assert result.eligible_for_pit_decision_grade is False
    assert result.membership_status == "provisionally_consistent"

    add_time = datetime(2023, 7, 27, 7, 5, 25, 93000, tzinfo=UTC)
    after_add = next(row for row in result.snapshots
                     if row.effective_at == add_time and row.boundary == "after_completed_event_batch")
    before_add = next(row for row in result.snapshots
                      if row.effective_at == add_time and row.boundary == "before_completed_event_batch")
    after_owners = {team.provider_roster_id: team.player_ids for team in after_add.teams}
    before_owners = {team.provider_roster_id: team.player_ids for team in before_add.teams}
    assert "supplement-player" in after_owners["1"]
    assert "supplement-player" not in before_owners["1"]
    assert "supplement-1" in after_add.supplemental_evidence_ids
    baseline_after_add = next(row for row in baseline.snapshots
                              if row.effective_at == add_time
                              and row.boundary == "after_completed_event_batch")
    assert baseline_after_add.snapshot_id != after_add.snapshot_id
    changed_after_add = next(row for row in changed_evidence_result.snapshots
                             if row.effective_at == add_time
                             and row.boundary == "after_completed_event_batch")
    assert changed_after_add.snapshot_id != after_add.snapshot_id


def test_same_day_player_event_makes_supported_supplement_ambiguous_and_unapplied():
    data = _season_with_missing_add()
    aug23 = int(datetime(2023, 8, 23, 12, tzinfo=UTC).timestamp() * 1000)
    data["transactions"].append({
        "type": "waiver", "status": "complete", "transaction_id": "same-day-event",
        "created": aug23 - 1000, "status_updated": aug23, "roster_ids": [1],
        "adds": {"supplement-player": 2}, "drops": {},
        "settings": {"waiver_bid": 0}, "draft_picks": [], "waiver_budget": [],
    })
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(_supplement(),)
    )

    finding = next(
        item for item in result.supplemental_reconciliation.findings
        if item.issue.provider_roster_id == "1"
    )
    assert finding.status == SupplementalFindingStatus.AMBIGUOUS
    assert result.supplemental_replay_status == "no_supported_movement"
    assert result.supplemental_applied_evidence_ids == ()
    assert result.provider_audit_status == "incomplete_source_history"


def test_exact_timestamp_supplement_is_not_collapsed_into_a_date_boundary():
    data = _season_with_missing_add()
    exact = _supplement().model_copy(update={
        "date_precision": SupplementalDatePrecision.EXACT_TIMESTAMP,
        "effective_at": datetime(2023, 8, 23, 12, tzinfo=UTC),
    })
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(exact,)
    )

    finding = next(
        item for item in result.supplemental_reconciliation.findings
        if item.issue.provider_roster_id == "1"
    )
    assert finding.status == SupplementalFindingStatus.AMBIGUOUS
    assert "exact-time supplemental replay is not supported" in finding.detail
    assert result.supplemental_replay_status == "no_supported_movement"
    assert result.supplemental_applied_evidence_ids == ()


def test_untimed_player_event_makes_supplement_ambiguous():
    data = _season_with_missing_add()
    data["transactions"].append({
        "type": "waiver", "status": "complete", "transaction_id": "untimed-event",
        "created": 1, "status_updated": None, "roster_ids": [1],
        "adds": {"supplement-player": 2}, "drops": {},
        "settings": {"waiver_bid": 0}, "draft_picks": [], "waiver_budget": [],
    })
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(_supplement(),)
    )

    finding = next(
        item for item in result.supplemental_reconciliation.findings
        if item.issue.provider_roster_id == "1"
    )
    assert finding.status == SupplementalFindingStatus.AMBIGUOUS
    assert "untimed or in-window" in finding.detail
    assert result.supplemental_replay_status == "no_supported_movement"


def test_date_only_player_is_marked_uncertain_across_timezone_window():
    data = _season_with_missing_add()
    for day in (22, 23, 24):
        event_at = int(datetime(2023, 8, day, 12, tzinfo=UTC).timestamp() * 1000)
        data["transactions"].append({
            "type": "waiver", "status": "complete", "transaction_id": f"nearby-{day}",
            "created": event_at - 1000, "status_updated": event_at, "roster_ids": [1],
            "adds": {f"other-player-{day}": 1}, "drops": {},
            "settings": {"waiver_bid": 0}, "draft_picks": [], "waiver_budget": [],
        })
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(_supplement(),)
    )
    for day in (22, 23, 24):
        same_window = next(
            row for row in result.snapshots
            if row.effective_at == datetime(2023, 8, day, 12, tzinfo=UTC)
        )
        assert "supplement-player" in same_window.uncertain_player_ids
    assert result.supplemental_replay_status == "applied_retrospectively"


def test_unmatched_supplement_is_reported_but_does_not_change_source_replay():
    data = _season_with_missing_add()
    aug23 = int(datetime(2023, 8, 23, 12, tzinfo=UTC).timestamp() * 1000)
    data["transactions"].append({
        "type": "waiver", "status": "complete", "transaction_id": "unrelated-same-window",
        "created": aug23 - 1000, "status_updated": aug23, "roster_ids": [1],
        "adds": {"player-b": 1}, "drops": {"player-b": 2},
        "settings": {"waiver_bid": 0}, "draft_picks": [], "waiver_budget": [],
    })
    baseline = reconstruct_sleeper_roster_context(data, source_revision="archive-sha")
    result = reconstruct_sleeper_roster_context(
        data, source_revision="archive-sha", supplemental_movements=(_supplement(player="unrelated-player"),)
    )

    assert result.supplemental_replay_status == "no_supported_movement"
    assert result.provider_audit_status == "incomplete_source_history"
    assert result.supplemental_applied_evidence_ids == ()
    assert result.history_id == baseline.history_id
    assert result.supplemental_evidence_sha256 != baseline.supplemental_evidence_sha256
    assert result.snapshots == baseline.snapshots
