from datetime import UTC, datetime, timedelta

from fsffl.state.historical_coverage import (
    HistoricalEvidenceKind as Kind,
    HistoricalEvidenceReceipt as Receipt,
    HistoricalSeasonIdentity as Season,
)
from fsffl.state.historical_materializer import (
    HistoricalRosterPlacement,
    HistoricalTransactionWindow,
    MaterializationStatus,
    materialize_post_trade_state,
)
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import (
    DraftPick,
    FaabAsset,
    League,
    LeagueRules,
    LeagueState,
    PickAsset,
    PickOwnership,
    Player,
    PlayerAsset,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)


T0 = datetime(2023, 10, 1, 17, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)
SEASON = Season(league_family_id="family", league_id="league-2023", season=2023)


def provenance(at: datetime) -> Provenance:
    return Provenance(source="fixture", retrieved_at=T1 + timedelta(days=365), effective_at=at)


def receipt(kind: Kind, at: datetime, evidence_id: str, *, available_at=None) -> Receipt:
    return Receipt(
        season=SEASON,
        kind=kind,
        evidence_id=evidence_id,
        effective_at=at,
        available_at=available_at,
        availability_basis="provider_timestamp" if available_at is not None else None,
        source="fixture-provider",
    )


def before_state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id=SEASON.league_id,
            name="League",
            season=SEASON.season,
            rules=LeagueRules(team_count=2, roster_size=10, lineup=(), scoring=()),
        ),
        as_of=T0,
        teams=(
            Team(team_id="a", league_id=SEASON.league_id, display_name="A"),
            Team(team_id="b", league_id=SEASON.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(RosterEntry(player_id="p-a", slot=RosterSlot.BENCH),),
                faab_balance=20,
            ),
            TeamState(
                team_id="b",
                roster=(RosterEntry(player_id="p-b", slot=RosterSlot.BENCH),),
                faab_balance=15,
            ),
        ),
        players=(
            Player(player_id="p-a", full_name="Player A", position=Position.RB),
            Player(player_id="p-b", full_name="Player B", position=Position.WR),
        ),
        player_states=(
            PlayerState(player_id="p-a", as_of=T0, provenance=provenance(T0)),
            PlayerState(player_id="p-b", as_of=T0, provenance=provenance(T0)),
        ),
        draft_picks=(
            DraftPick(
                pick_id="pick-a",
                league_id=SEASON.league_id,
                season=2025,
                round=3,
                original_team_id="a",
            ),
        ),
        pick_ownership=(PickOwnership(pick_id="pick-a", owner_team_id="a"),),
    )


def trade() -> HistoricalTradeRecord:
    return HistoricalTradeRecord(
        transaction_id="trade-1",
        league_id=SEASON.league_id,
        completed_at=T1,
        provenance=provenance(T1),
        legs=(
            HistoricalTradeLeg(
                team_id="a",
                sends=(PlayerAsset(player_id="p-a"), PickAsset(pick_id="pick-a"), FaabAsset(amount=3)),
            ),
            HistoricalTradeLeg(
                team_id="b",
                sends=(PlayerAsset(player_id="p-b"), FaabAsset(amount=2)),
            ),
        ),
    )


def materialize(*, available_at=None, slots=True):
    placements = (
        HistoricalRosterPlacement(
            player_id="p-a",
            team_id="b",
            slot=RosterSlot.BENCH,
            receipt=receipt(Kind.ROSTERS, T1, "placement-p-a", available_at=available_at),
        ),
        HistoricalRosterPlacement(
            player_id="p-b",
            team_id="a",
            slot=RosterSlot.BENCH,
            receipt=receipt(Kind.ROSTERS, T1, "placement-p-b", available_at=available_at),
        ),
    ) if slots else ()
    return materialize_post_trade_state(
        season=SEASON,
        before=before_state(),
        before_roster_receipt=receipt(Kind.ROSTERS, T0, "before", available_at=available_at),
        trade=trade(),
        transaction_window=HistoricalTransactionWindow(
            season=SEASON,
            start_exclusive=T0,
            end_inclusive=T1,
            transaction_ids=("trade-1",),
            receipt=receipt(Kind.TRANSACTIONS, T1, "transaction-window", available_at=available_at),
        ),
        roster_placements=placements,
        faab_receipt=receipt(Kind.FAAB, T0, "faab", available_at=available_at),
        draft_receipt=receipt(Kind.DRAFT, T0, "draft", available_at=available_at),
    )


def test_materializes_post_trade_canonical_state_without_grading():
    result = materialize(available_at=T1)
    assert result.status == MaterializationStatus.MATERIALIZED
    assert result.state is not None
    assert result.state.as_of == T1
    assert {row.team_id: {entry.player_id for entry in row.roster} for row in result.state.team_states} == {
        "a": {"p-b"},
        "b": {"p-a"},
    }
    assert {row.team_id: row.faab_balance for row in result.state.team_states} == {"a": 19, "b": 16}
    assert result.state.pick_ownership == (PickOwnership(pick_id="pick-a", owner_team_id="b"),)
    assert result.source_available_at_cutoff is True
    assert result.eligible_for_pit_decision_grade is False


def test_retroactive_receipts_allow_factual_state_but_mark_source_unavailable_then():
    result = materialize(available_at=T1 + timedelta(days=365))
    assert result.status == MaterializationStatus.MATERIALIZED
    assert result.source_available_at_cutoff is False
    assert result.eligible_for_pit_decision_grade is False


def test_missing_roster_slot_blocks_instead_of_inventing_bench_assignment():
    result = materialize(slots=False)
    assert result.status == MaterializationStatus.BLOCKED
    assert result.state is None
    assert "missing_receiving_roster_slot:p-a" in result.blockers
    assert "missing_receiving_roster_slot:p-b" in result.blockers


def test_unapplied_event_in_window_blocks_trade_only_materialization():
    window = HistoricalTransactionWindow(
        season=SEASON,
        start_exclusive=T0,
        end_inclusive=T1,
        transaction_ids=("trade-1", "waiver-2"),
        receipt=receipt(Kind.TRANSACTIONS, T1, "complete-window"),
    )
    result = materialize_post_trade_state(
        season=SEASON,
        before=before_state(),
        before_roster_receipt=receipt(Kind.ROSTERS, T0, "before"),
        trade=trade(),
        transaction_window=window,
        roster_placements=(),
    )
    assert result.status == MaterializationStatus.BLOCKED
    assert result.blockers == ("transaction_window_contains_unapplied_events",)
