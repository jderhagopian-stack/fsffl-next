from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_pick import exact_slot_from_historical_snapshot
from fsffl.state.draft_order_snapshot import HistoricalDraftOrderSnapshot, HistoricalDraftSlotAssignment
from fsffl.state.models import DraftPick, LeagueRules, Provenance


RULES = LeagueRules(
    team_count=4,
    roster_size=20,
    rookie_draft_rounds=3,
    lineup=(),
    scoring=(),
)
PICK = DraftPick(
    pick_id="pick-2027-r1-a",
    league_id="league",
    season=2027,
    round=1,
    original_team_id="a",
)


def _snapshot(available_at: datetime) -> HistoricalDraftOrderSnapshot:
    return HistoricalDraftOrderSnapshot(
        league_id="league",
        draft_season=2027,
        available_at=available_at,
        assignments=(
            HistoricalDraftSlotAssignment(team_id="a", slot_in_round=3),
            HistoricalDraftSlotAssignment(team_id="b", slot_in_round=1),
            HistoricalDraftSlotAssignment(team_id="c", slot_in_round=4),
            HistoricalDraftSlotAssignment(team_id="d", slot_in_round=2),
        ),
        version="1",
        provenance=Provenance(
            source="historical-test",
            retrieved_at=available_at,
            effective_at=available_at,
        ),
    )


def test_exact_slot_bridge_preserves_known_at_timestamp():
    known_at = datetime(2026, 12, 20, tzinfo=UTC)
    slot, returned_known_at = exact_slot_from_historical_snapshot(
        pick=PICK,
        snapshot=_snapshot(known_at),
        league_rules=RULES,
        as_of=datetime(2027, 1, 10, tzinfo=UTC),
    )

    assert slot == 3
    assert returned_known_at == known_at


def test_exact_slot_bridge_rejects_snapshot_learned_after_trade():
    with pytest.raises(ValueError, match="not knowable"):
        exact_slot_from_historical_snapshot(
            pick=PICK,
            snapshot=_snapshot(datetime(2027, 1, 11, tzinfo=UTC)),
            league_rules=RULES,
            as_of=datetime(2027, 1, 10, tzinfo=UTC),
        )
