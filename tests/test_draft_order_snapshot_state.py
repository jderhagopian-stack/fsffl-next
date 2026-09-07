from datetime import UTC, datetime

import pytest

from fsffl.state.draft_order_snapshot import (
    HistoricalDraftOrderSnapshot,
    HistoricalDraftSlotAssignment,
    resolve_historical_draft_order_snapshot,
)
from fsffl.state.models import LeagueRules, Provenance


RULES = LeagueRules(
    team_count=4,
    roster_size=20,
    rookie_draft_rounds=3,
    lineup=(),
    scoring=(),
)


def _provenance(at: datetime) -> Provenance:
    return Provenance(source="historical-test", retrieved_at=at, effective_at=at)


def _snapshot(available_at: datetime, version: str = "1") -> HistoricalDraftOrderSnapshot:
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
        version=version,
        provenance=_provenance(available_at),
    )


def test_snapshot_resolves_only_after_it_was_knowable():
    learned = datetime(2026, 12, 20, tzinfo=UTC)
    snapshot = _snapshot(learned)

    assert resolve_historical_draft_order_snapshot(
        (snapshot,), league_id="league", draft_season=2027, as_of=datetime(2026, 12, 19, tzinfo=UTC)
    ) is None
    assert resolve_historical_draft_order_snapshot(
        (snapshot,), league_id="league", draft_season=2027, as_of=learned
    ) == snapshot


def test_snapshot_uses_configured_team_count_for_slot_validation():
    snapshot = HistoricalDraftOrderSnapshot(
        league_id="league",
        draft_season=2027,
        available_at=datetime(2026, 12, 20, tzinfo=UTC),
        assignments=(HistoricalDraftSlotAssignment(team_id="a", slot_in_round=5),),
        version="1",
        provenance=_provenance(datetime(2026, 12, 20, tzinfo=UTC)),
    )

    with pytest.raises(ValueError, match="exceeds configured league team count"):
        snapshot.exact_slot_for_team("a", league_rules=RULES)


def test_snapshot_rejects_duplicate_team_or_slot_assignments():
    at = datetime(2026, 12, 20, tzinfo=UTC)
    with pytest.raises(ValueError, match="team ids must be unique"):
        HistoricalDraftOrderSnapshot(
            league_id="league",
            draft_season=2027,
            available_at=at,
            assignments=(
                HistoricalDraftSlotAssignment(team_id="a", slot_in_round=1),
                HistoricalDraftSlotAssignment(team_id="a", slot_in_round=2),
            ),
            version="1",
            provenance=_provenance(at),
        )

    with pytest.raises(ValueError, match="slots must be unique"):
        HistoricalDraftOrderSnapshot(
            league_id="league",
            draft_season=2027,
            available_at=at,
            assignments=(
                HistoricalDraftSlotAssignment(team_id="a", slot_in_round=1),
                HistoricalDraftSlotAssignment(team_id="b", slot_in_round=1),
            ),
            version="1",
            provenance=_provenance(at),
        )
