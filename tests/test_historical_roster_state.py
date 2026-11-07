from datetime import UTC, datetime

from fsffl.state.historical_coverage import (
    HistoricalEvidenceKind as Kind,
    HistoricalEvidenceReceipt as Receipt,
    HistoricalSeasonIdentity as Season,
)
from fsffl.state.historical_materializer import HistoricalRosterPlacement
from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context
from fsffl.state.historical_roster_replay import CompletedRosterEvent, replay_roster_membership
from fsffl.state.historical_roster_state import (
    HistoricalDraftPickOwner,
    HistoricalRosterPlayerEvidence,
    HistoricalRosterTeamEvidence,
    HistoricalStateMaterializationStatus as Status,
    materialize_historical_roster_state,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    ProviderRef,
    Provenance,
    RosterSlot,
    ScoringRule,
    Team,
)


CUTOFF = datetime(2023, 10, 1, 17, tzinfo=UTC)
SEASON = Season(league_family_id="family-1", league_id="league-1", season=2023)


def _receipt(kind: Kind, evidence_id: str) -> Receipt:
    return Receipt(
        season=SEASON,
        kind=kind,
        evidence_id=evidence_id,
        effective_at=CUTOFF,
        available_at=CUTOFF,
        availability_basis="provider_timestamp",
        source="fixture-provider",
        source_version="fixture-v1",
    )


def _history():
    at_ms = int(CUTOFF.timestamp() * 1000)
    data = {
        "league": {
            "league_id": SEASON.league_id,
            "season": str(SEASON.season),
            "total_rosters": 2,
            "roster_positions": ["QB", "RB", "WR", "BN"],
            "settings": {"waiver_budget": 100},
            "scoring_settings": {"rec": 0.5},
        },
        "rosters": [
            {"roster_id": 1, "players": ["101"], "settings": {"waiver_budget_used": 0}},
            {"roster_id": 2, "players": ["202"], "settings": {"waiver_budget_used": 0}},
        ],
        "traded_picks": [],
        "transactions": [{
            "type": "waiver", "status": "complete", "transaction_id": "waiver-1",
            "created": at_ms - 1000, "status_updated": at_ms, "roster_ids": [1],
            "adds": {"101": 1}, "drops": {}, "settings": {"waiver_bid": 0},
            "draft_picks": [], "waiver_budget": [],
        }],
    }
    history = reconstruct_sleeper_roster_context(data, source_revision="fixture-archive")
    snapshot = next(
        item for item in history.snapshots
        if item.effective_at == CUTOFF and item.boundary == "after_completed_event_batch"
    )
    return history, snapshot


def _inputs(*, placements=True):
    history, snapshot = _history()
    league = League(
        league_id=SEASON.league_id,
        name="Synthetic league",
        season=SEASON.season,
        rules=LeagueRules(
            team_count=2,
            roster_size=18,
            taxi_size=2,
            ir_size=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(ScoringRule(stat="rec", points=0.5),),
        ),
    )
    teams = tuple(
        HistoricalRosterTeamEvidence(
            provider_roster_id=rid,
            team=Team(
                team_id=f"team-{rid}", league_id=SEASON.league_id,
                display_name=f"Team {rid}",
                provider_refs=(ProviderRef(provider="sleeper", external_id=rid),),
            ),
            faab_balance=100,
            identity_receipt=_receipt(Kind.OWNER_IDENTITY, f"team-{rid}"),
            faab_receipt=_receipt(Kind.FAAB, f"faab-{rid}"),
        )
        for rid in ("1", "2")
    )
    players = tuple(
        HistoricalRosterPlayerEvidence(
            provider_player_id=pid,
            player=Player(
                player_id=f"player-{pid}", full_name=f"Player {pid}",
                position=Position.RB if pid == "101" else Position.WR,
                provider_refs=(ProviderRef(provider="sleeper", external_id=pid),),
            ),
            player_state=PlayerState(
                player_id=f"player-{pid}", as_of=CUTOFF, status=PlayerStatus.UNKNOWN,
                provenance=Provenance(
                    source="fixture-player-catalog", retrieved_at=CUTOFF, effective_at=CUTOFF,
                ),
            ),
            identity_receipt=_receipt(Kind.PLAYER_STATUS, f"player-{pid}"),
        )
        for pid in ("101", "202")
    )
    roster_placements = (
        HistoricalRosterPlacement(
            player_id="player-101", team_id="team-1", slot=RosterSlot.BENCH,
            receipt=_receipt(Kind.ROSTERS, "slot-101"),
        ),
        HistoricalRosterPlacement(
            player_id="player-202", team_id="team-2", slot=RosterSlot.TAXI,
            receipt=_receipt(Kind.ROSTERS, "slot-202"),
        ),
    ) if placements else ()
    return {
        "season": SEASON,
        "history": history,
        "snapshot": snapshot,
        "league": league,
        "teams": teams,
        "players": players,
        "roster_placements": roster_placements,
        "draft_picks": (),
        "settings_receipt": _receipt(Kind.SETTINGS, "settings"),
        "roster_receipt": _receipt(Kind.ROSTERS, "roster"),
        "player_universe_receipt": _receipt(Kind.PLAYER_STATUS, "players"),
        "pick_universe_receipt": _receipt(Kind.DRAFT, "draft-universe"),
        "pick_universe_complete": True,
    }


def test_materializes_canonical_roster_state_from_explicit_evidence():
    result = materialize_historical_roster_state(**_inputs())

    assert result.status == Status.MATERIALIZED
    assert result.state is not None
    assert result.state.as_of == CUTOFF
    assert result.state.league.rules.taxi_size == 2
    assert {row.team_id: tuple((entry.player_id, entry.slot) for entry in row.roster)
            for row in result.state.team_states} == {
        "team-1": (("player-101", RosterSlot.BENCH),),
        "team-2": (("player-202", RosterSlot.TAXI),),
    }
    assert {row.team_id: row.faab_balance for row in result.state.team_states} == {
        "team-1": 100, "team-2": 100,
    }
    assert result.source_available_at_cutoff is True
    assert result.eligible_for_pit_decision_grade is False


def test_missing_roster_slot_evidence_blocks_state_instead_of_guessing():
    result = materialize_historical_roster_state(**_inputs(placements=False))

    assert result.status == Status.BLOCKED
    assert result.state is None
    assert "roster_slot_coverage_incomplete_or_extra" in result.blockers


def test_uncertain_membership_is_not_promoted():
    inputs = _inputs()
    history = inputs["history"]
    snapshot = inputs["snapshot"].model_copy(update={"uncertain_player_ids": ("101",)})
    inputs["snapshot"] = snapshot
    # A copied snapshot is deliberately not part of this history; both blockers remain visible.
    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "snapshot_contains_uncertain_player_membership" in result.blockers
    assert "snapshot_does_not_belong_to_history" in result.blockers


def test_archive_end_anchor_is_not_a_materialization_cutoff():
    inputs = _inputs()
    inputs["snapshot"] = next(
        item for item in inputs["history"].snapshots
        if item.boundary == "archive_end_anchor"
    )

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "archive_end_anchor_is_not_an_event_cutoff" in result.blockers


def test_wrong_league_evidence_is_rejected_as_blocked():
    inputs = _inputs()
    inputs["settings_receipt"] = inputs["settings_receipt"].model_copy(update={
        "season": Season(league_family_id="other", league_id="elsewhere", season=2023),
    })

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "settings_receipt_season_mismatch" in result.blockers


def test_pick_receipt_without_complete_universe_attestation_blocks():
    inputs = _inputs()
    inputs["pick_universe_complete"] = False

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "complete_pick_universe_not_asserted" in result.blockers


def test_supplemented_membership_requires_receipt_payload_to_be_carried_forward():
    inputs = _inputs()
    inputs["snapshot"] = inputs["snapshot"].model_copy(update={
        "supplemental_evidence_ids": ("supplement-1",),
    })

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "supplemental_evidence_receipt_coverage_mismatch" in result.blockers


def test_duplicate_provider_team_reference_blocks_identity_ambiguity():
    inputs = _inputs()
    second = inputs["teams"][1]
    wrong_team = second.team.model_copy(update={
        "provider_refs": (ProviderRef(provider="sleeper", external_id="1"),),
    })
    inputs["teams"] = (inputs["teams"][0], second.model_copy(update={"team": wrong_team}))

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert "team_provider_identity_mapping_is_not_one_to_one" in result.blockers


def _normalized_replay(*, pick_universe_complete=True):
    history = replay_roster_membership(
        provider="sleeper", league_id=SEASON.league_id, season=SEASON.season,
        source_revision="normalized-fixture", source_sha256="f" * 64,
        rules_sha256="rules-fingerprint",
        end_rosters={"1": ("101",), "2": ("202",)},
        events=(CompletedRosterEvent("cutoff", CUTOFF, "snapshot_boundary", ()),),
        end_pick_owners={}, pick_universe_complete=pick_universe_complete,
        end_budget_usage={"1": 0, "2": 0}, budget_usage_complete=True,
    )
    snapshot = next(
        item for item in history.snapshots
        if item.effective_at == CUTOFF and item.boundary == "after_completed_event_batch"
    )
    return history, snapshot


def test_materializes_canonical_state_directly_from_provider_neutral_replay():
    inputs = _inputs()
    inputs["history"], inputs["snapshot"] = _normalized_replay()

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.MATERIALIZED
    assert result.state is not None and result.state.as_of == CUTOFF
    assert {entry.player_id for team in result.state.team_states for entry in team.roster} == {
        "player-101", "player-202",
    }
    assert result.eligible_for_pit_decision_grade is False


def test_normalized_replay_cannot_claim_complete_pick_universe_without_archive_coverage():
    inputs = _inputs()
    inputs["history"], inputs["snapshot"] = _normalized_replay(pick_universe_complete=False)

    result = materialize_historical_roster_state(**inputs)

    assert result.status == Status.BLOCKED
    assert result.state is None
    assert "replay_pick_universe_incomplete" in result.blockers
