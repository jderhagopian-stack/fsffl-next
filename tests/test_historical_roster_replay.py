from datetime import UTC, datetime

import pytest

from fsffl.state.historical_roster_replay import (
    CompletedRosterEvent,
    PlayerTransfer,
    replay_roster_membership,
)


def _run(team_count: int, *, rules: str = "rules-a"):
    teams = {f"team-{index}": (f"p-{index}",) for index in range(team_count)}
    teams["team-0"] = ("p-0",)
    event = CompletedRosterEvent(
        event_id="event-1",
        effective_at=datetime(2023, 8, 23, 18, tzinfo=UTC),
        event_type="waiver_drop",
        player_transfers=(PlayerTransfer("moved", "team-0", None),),
    )
    return replay_roster_membership(
        provider="provider-test",
        league_id=f"league-{team_count}",
        season=2023,
        source_revision="immutable-rev",
        source_sha256="a" * 64,
        rules_sha256=rules,
        end_rosters=teams,
        events=(event,),
    )


@pytest.mark.parametrize("team_count", [2, 4, 8, 12, 16, 18])
def test_replays_membership_across_variable_league_sizes(team_count):
    history = _run(team_count)
    before = history.pre_transaction_state("event-1")
    after = history.state_at(datetime(2023, 8, 23, 18, tzinfo=UTC))

    assert before is not None
    assert after is not None
    assert "moved" in before.owner_map()
    assert "moved" not in after.owner_map()
    assert "moved" in after.free_agents
    assert history.eligible_for_pit_decision_grade is False


def test_replay_identity_tracks_rules_and_source_revision():
    baseline = _run(10)
    changed_rules = _run(10, rules="rules-b")
    assert baseline.history_id != changed_rules.history_id


def test_same_timestamp_shared_player_is_not_ordered_or_partially_replayed():
    at = datetime(2023, 9, 1, tzinfo=UTC)
    anchor = {"a": (), "b": ("p",), "c": ()}
    events = (
        CompletedRosterEvent("one", at, "trade", (PlayerTransfer("p", "a", "b"),)),
        CompletedRosterEvent("two", at, "trade", (PlayerTransfer("p", "c", "b"),)),
    )
    history = replay_roster_membership(
        provider="provider", league_id="league", season=2023,
        source_revision="rev", source_sha256="b" * 64, rules_sha256="c" * 64,
        end_rosters=anchor, events=events,
    )
    before = next(row for row in history.snapshots if row.boundary == "before_completed_event_batch")
    assert "ambiguous_same_timestamp_player_order" in history.issues
    assert before.owner_map() == {"p": "b"}
    assert history.pre_transaction_state("one") is None


def test_conflicting_anchor_blocks_whole_batch_without_mutation():
    at = datetime(2023, 9, 1, tzinfo=UTC)
    history = replay_roster_membership(
        provider="provider", league_id="league", season=2023,
        source_revision="rev", source_sha256="b" * 64, rules_sha256="c" * 64,
        end_rosters={"a": (), "b": ()},
        events=(CompletedRosterEvent("one", at, "trade", (PlayerTransfer("p", "a", "b"),)),),
    )
    before = history.pre_transaction_state("one")
    assert "post_event_player_ownership_mismatch" in history.issues
    assert before is not None and before.owner_map() == {}
