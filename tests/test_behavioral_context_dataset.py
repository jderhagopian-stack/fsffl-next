from datetime import timedelta

from fsffl.behavioral.context_dataset import build_behavioral_context_calibration_dataset
from fsffl.behavioral.models import BehavioralAsset, BehavioralAssetKind
from fsffl.state.history import InMemorySnapshotStore
from tests.test_behavioral_action_context import EVENT_AT, PRE_AT, _event, _state


def test_builds_calibration_row_with_observed_outcomes_and_pre_action_context() -> None:
    event = _event().model_copy(
        update={
            "acquired": (
                BehavioralAsset(kind=BehavioralAssetKind.PLAYER, asset_ref="rb-x", position="RB"),
                BehavioralAsset(kind=BehavioralAssetKind.PICK, asset_ref="pick-x", pick_season=2027, pick_round=1),
            ),
            "disposed": (
                BehavioralAsset(kind=BehavioralAssetKind.PLAYER, asset_ref="wr-x", position="WR"),
            ),
        }
    )
    dataset = build_behavioral_context_calibration_dataset(
        [event],
        snapshots=InMemorySnapshotStore((_state(PRE_AT),)),
        league_id_by_event={event.event_id: "league-1"},
        team_id_by_event={event.event_id: "a"},
    )
    assert dataset.total_event_count == 1
    assert dataset.usable_event_count == 1
    assert dataset.coverage_rate == 1.0
    assert dataset.unavailable == ()
    row = dataset.rows[0]
    assert row.acquired_position_counts == {"RB": 1}
    assert row.disposed_position_counts == {"WR": 1}
    assert row.acquired_pick_count == 1
    assert row.context.snapshot_as_of == PRE_AT


def test_missing_mapping_and_missing_snapshot_are_reported_in_coverage() -> None:
    event_a = _event()
    event_b = _event().model_copy(
        update={"event_id": "evt-2", "occurred_at": EVENT_AT + timedelta(days=1)}
    )
    dataset = build_behavioral_context_calibration_dataset(
        [event_a, event_b],
        snapshots=InMemorySnapshotStore(),
        league_id_by_event={event_a.event_id: "league-1"},
        team_id_by_event={event_a.event_id: "a"},
    )
    assert dataset.total_event_count == 2
    assert dataset.usable_event_count == 0
    assert dataset.coverage_rate == 0.0
    assert len(dataset.unavailable) == 2
    reasons = {issue.event_id: issue.reason for issue in dataset.unavailable}
    assert "no league-state snapshot" in reasons["evt-1"]
    assert reasons["evt-2"] == "missing canonical league/team identity mapping"


def test_duplicate_event_ids_fail_closed() -> None:
    event = _event()
    try:
        build_behavioral_context_calibration_dataset(
            [event, event],
            snapshots=InMemorySnapshotStore((_state(PRE_AT),)),
            league_id_by_event={event.event_id: "league-1"},
            team_id_by_event={event.event_id: "a"},
        )
    except ValueError as exc:
        assert "unique event ids" in str(exc)
    else:
        raise AssertionError("duplicate behavioral event ids should fail closed")
