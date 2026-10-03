from datetime import UTC, datetime

from fsffl.analytics.dynasty_position_room import build_dynasty_position_rooms
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.value.career_forward_intrinsic import (
    CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
    CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
    CareerForwardIntrinsicPlayerEstimate,
    CareerForwardIntrinsicShadowContract,
)


NOW = datetime(2026, 10, 3, tzinfo=UTC)


def _state() -> LeagueState:
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )


def _career_forward(state: LeagueState, values: dict[str, tuple[Position, float]]):
    estimates = tuple(
        CareerForwardIntrinsicPlayerEstimate.model_construct(
            player_id=player_id,
            position=position,
            raw_career_forward_reference=value,
        )
        for player_id, (position, value) in values.items()
    )
    return CareerForwardIntrinsicShadowContract.model_construct(
        evaluation_season=state.league.season,
        input_fingerprint="fixture-fingerprint",
        current_intrinsic_contract_version="fixture-current",
        long_horizon_contract_version="fixture-y4-y7",
        long_horizon_value_model_version="fixture-model",
        career_tail_model_version="fixture-tail",
        lineup_capacity_signature="fixture-lineup",
        estimates=estimates,
        player_count=len(estimates),
        model_version=CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
        contract_version=CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
    )
    teams = (
        Team(team_id="alpha", league_id="league", display_name="Alpha"),
        Team(team_id="beta", league_id="league", display_name="Beta"),
    )
    team_states = (
        TeamState(
            team_id="alpha",
            roster=(
                RosterEntry(player_id="a1", slot=RosterSlot.RB),
                RosterEntry(player_id="a2", slot=RosterSlot.BENCH),
                RosterEntry(player_id="a3", slot=RosterSlot.IR),
                RosterEntry(player_id="a4", slot=RosterSlot.TAXI),
            ),
        ),
        TeamState(
            team_id="beta",
            roster=(RosterEntry(player_id="b1", slot=RosterSlot.BENCH),),
        ),
    )
    return LeagueState(
        league=League(
            league_id="league",
            name="Room breadth fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=10,
                ir_size=2,
                taxi_size=2,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=NOW,
        teams=teams,
        team_states=team_states,
        players=tuple(
            Player(player_id=player_id, full_name=player_id, position=Position.RB)
            for player_id in ("a1", "a2", "a3", "a4", "b1")
        ),
        player_states=tuple(
            PlayerState(player_id=player_id, as_of=NOW, provenance=provenance)
            for player_id in ("a1", "a2", "a3", "a4", "b1")
        ),
    )


def test_dynasty_room_sums_raw_career_forward_once_and_ranks_equal_totals_together() -> None:
    state = _state()
    contract = _career_forward(
        state,
        {
            "a1": (Position.RB, 10.0),
            "a2": (Position.RB, 10.0),
            "a3": (Position.RB, 30.0),
            "a4": (Position.RB, -10.0),
            "b1": (Position.RB, 40.0),
        },
    )
    rows = build_dynasty_position_rooms(
        state,
        career_forward=contract,
        evidence_state_id=state.state_id,
        positions=(Position.RB,),
    )
    by_team = {row.team_id: row for row in rows}

    assert by_team["alpha"].rostered_player_count == 4
    assert by_team["beta"].rostered_player_count == 1
    assert by_team["alpha"].room_raw == 40.0
    assert by_team["beta"].room_raw == 40.0
    assert by_team["alpha"].league_rank == by_team["beta"].league_rank == 1
    assert by_team["alpha"].strength_index == by_team["beta"].strength_index == 100.0
    assert by_team["alpha"].model_version == "analytics-dynasty-position-room-career-forward-v1"


def test_dynasty_room_fails_closed_when_any_rostered_player_evidence_is_missing() -> None:
    state = _state()
    contract = _career_forward(
        state,
        {"a1": (Position.RB, 10.0), "b1": (Position.RB, 20.0)},
    )
    rows = build_dynasty_position_rooms(
        state,
        career_forward=contract,
        evidence_state_id=state.state_id,
        positions=(Position.RB,),
    )
    by_team = {row.team_id: row for row in rows}
    assert by_team["alpha"].rostered_player_count == 4
    assert by_team["alpha"].room_raw is None
    assert by_team["alpha"].league_rank is None
    assert by_team["beta"].room_raw == 20.0
    assert by_team["beta"].league_rank is None
    assert by_team["beta"].strength_index is None
    assert by_team["beta"].coverage_count == 1


def test_dynasty_room_requires_exact_state_evidence() -> None:
    state = _state()
    contract = _career_forward(
        state,
        {
            "a1": (Position.RB, 10.0),
            "a2": (Position.RB, 20.0),
            "a3": (Position.RB, 30.0),
            "a4": (Position.RB, 40.0),
            "b1": (Position.RB, 50.0),
        },
    )
    mismatch = build_dynasty_position_rooms(
        state,
        career_forward=contract,
        evidence_state_id="another-state",
        positions=(Position.RB,),
    )
    assert all(row.room_raw is None and row.league_rank is None for row in mismatch)
    assert all(row.room_raw is None for row in mismatch)


def test_dynasty_room_requires_actual_position_match() -> None:
    state = _state()
    contract = _career_forward(
        state,
        {
            "a1": (Position.WR, 10.0),
            "a2": (Position.RB, 20.0),
            "a3": (Position.RB, 30.0),
            "a4": (Position.RB, 40.0),
            "b1": (Position.RB, 50.0),
        },
    )
    wrong_position = build_dynasty_position_rooms(
        state,
        career_forward=contract,
        evidence_state_id=state.state_id,
        positions=(Position.RB,),
    )
    alpha = next(row for row in wrong_position if row.team_id == "alpha")
    assert alpha.room_raw is None
    assert alpha.rostered_player_count == 4
