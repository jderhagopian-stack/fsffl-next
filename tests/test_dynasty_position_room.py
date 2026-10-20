from datetime import UTC, datetime

import pytest

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


def _career_current_components(state, components, positions=None):
    from fsffl.value.career_forward_intrinsic import (
        CAREER_FORWARD_AGGREGATION,
        CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
        CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
        CAREER_FORWARD_RAW_QUANTITY,
        CareerForwardCurrentAnnualContribution,
        CareerForwardIntrinsicPlayerEstimate,
        CareerForwardIntrinsicShadowContract,
        CareerForwardUncertaintyContract,
    )
    from fsffl.value.shapley_intrinsic_contract import ShapleyHorizonUncertainty

    positions = positions or {}
    estimates = []
    for player_id, annual_values in components.items():
        annual = tuple(
            CareerForwardCurrentAnnualContribution.model_construct(
                year_index=index,
                target_season=state.league.season + index - 1,
                raw_shapley_contribution=value,
                uncertainty=ShapleyHorizonUncertainty(evidence_path="fixture"),
            )
            for index, value in enumerate(annual_values, start=1)
        )
        estimates.append(CareerForwardIntrinsicPlayerEstimate.model_construct(
            player_id=player_id,
            position=positions.get(player_id, Position.RB),
            current_intrinsic_raw_y1_y3=sum(annual_values),
            raw_career_forward_reference=1000.0 + sum(annual_values),
            uncertainty=CareerForwardUncertaintyContract.model_construct(
                current_y1_y3=annual,
            ),
            raw_quantity=CAREER_FORWARD_RAW_QUANTITY,
            aggregation=CAREER_FORWARD_AGGREGATION,
        ))
    return CareerForwardIntrinsicShadowContract.model_construct(
        evaluation_season=state.league.season,
        input_fingerprint="fixture-career-fingerprint",
        current_intrinsic_contract_version="intrinsic-shapley-contract-v2:effective-horizon-seeds",
        long_horizon_contract_version="fixture-long-contract",
        long_horizon_value_model_version="fixture-long-model",
        career_tail_model_version="fixture-tail-model",
        lineup_capacity_signature="fixture-lineup-signature",
        estimates=tuple(estimates),
        player_count=len(estimates),
        model_version=CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
        contract_version=CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
    )



def test_three_year_values_all_come_from_career_current_annual_components():
    from fsffl.analytics.dynasty_position_room import (
        build_three_year_intrinsic_player_values,
        build_three_year_position_rooms,
    )
    state = _state()
    components = {
        "a1": (1., 2., 3.),
        "a2": (2., 3., 4.),
        "a3": (3., 4., 5.),
        "a4": (4., 5., 6.),
        "b1": (5., 6., 7.),
        "unrostered": (8., 9., 10.),
    }
    career = _career_current_components(state, components)
    career = career.model_copy(update={
        "player_input_assumptions": {"a4": "Approved YTD-only Current input"},
    })

    values = build_three_year_intrinsic_player_values(
        state, career_forward=career, career_evidence_state_id=state.state_id,
    )
    by_id = {row.player_id: row for row in values}
    assert set(by_id) == {"a1", "a2", "a3", "a4", "b1"}
    for player_id, annual in components.items():
        if player_id == "unrostered":
            continue
        assert by_id[player_id].raw_intrinsic_value == pytest.approx(
            annual[0] + .85 * annual[1] + .85**2 * annual[2]
        )
        assert by_id[player_id].source == "career_current_y1_y3_components"
    assert by_id["a4"].input_assumption == "Approved YTD-only Current input"
    assert by_id["a1"].raw_intrinsic_value != career.estimates[0].raw_career_forward_reference

    rooms = build_three_year_position_rooms(
        state, career_forward=career, career_evidence_state_id=state.state_id,
        positions=(Position.RB,),
    )
    alpha, beta = rooms
    assert alpha.room_raw == pytest.approx(sum(
        by_id[player_id].raw_intrinsic_value for player_id in ("a1", "a2", "a3", "a4")
    ))
    assert beta.room_raw == by_id["b1"].raw_intrinsic_value
    assert all(row.league_rank is not None for row in rooms)
    assert all(row.coverage_count == row.team_count == 2 for row in rooms)
    assert rooms[0].model_version == (
        "analytics-position-room-three-year-intrinsic-v3:career-current-y1-y3-source"
    )


def test_three_year_rankings_fail_closed_without_complete_exact_career_components():
    from fsffl.analytics.dynasty_position_room import build_three_year_position_rooms
    state = _state()
    complete = _career_current_components(state, {
        "a1": (1., 0., 0.), "a2": (1., 0., 0.), "a3": (1., 0., 0.),
        "a4": (1., 0., 0.), "b1": (4., 0., 0.),
    })

    def rooms(contract=complete, state_id=state.state_id):
        return build_three_year_position_rooms(
            state, career_forward=contract, career_evidence_state_id=state_id,
            positions=(Position.RB,),
        )

    tied = rooms()
    assert [row.league_rank for row in tied] == [1, 1]
    missing = complete.model_copy(update={
        "estimates": complete.estimates[1:], "player_count": len(complete.estimates) - 1,
    })
    incomplete = rooms(missing)
    assert incomplete[0].room_raw is None and incomplete[1].room_raw is not None
    assert all(row.league_rank is None for row in incomplete)
    for bad in (
        None,
        complete.model_copy(update={"display_scaling_applied": True}),
        complete.model_copy(update={"market_inputs_used": True}),
        complete.model_copy(update={"evaluation_season": 2025}),
        complete.model_copy(update={"status": "unavailable"}),
    ):
        assert all(row.room_raw is None for row in rooms(bad))
    assert all(row.room_raw is None for row in rooms(state_id="older-state"))


def test_three_year_rejects_malformed_career_rows_without_using_later_horizons():
    from fsffl.analytics.dynasty_position_room import build_three_year_intrinsic_player_values
    state = _state()
    complete = _career_current_components(state, {
        "a1": (1., 2., 3.), "a2": (2., 3., 4.), "a3": (3., 4., 5.),
        "a4": (4., 5., 6.), "b1": (5., 6., 7.),
    })
    assert len(build_three_year_intrinsic_player_values(
        state, career_forward=complete, career_evidence_state_id=state.state_id,
    )) == 5

    for player_id, row_update in (
        ("a1", {"position": Position.WR}),
        ("a2", {"discounting_applied": True}),
    ):
        malformed = complete.model_copy(update={
            "estimates": tuple(
                row.model_copy(update=row_update) if row.player_id == player_id else row
                for row in complete.estimates
            ),
        })
        values = build_three_year_intrinsic_player_values(
            state, career_forward=malformed, career_evidence_state_id=state.state_id,
        )
        assert player_id not in {row.player_id for row in values}

    original = complete.estimates[0]
    bad_horizon = original.model_copy(update={
        "uncertainty": original.uncertainty.model_copy(update={
            "current_y1_y3": tuple(
                    item.model_copy(update={"target_season": 2028})
                if item.year_index == 2 else item
                for item in original.uncertainty.current_y1_y3
            ),
        }),
    })
    bad_numeric = original.model_copy(update={
        "uncertainty": original.uncertainty.model_copy(update={
            "current_y1_y3": tuple(
                item.model_copy(update={"raw_shapley_contribution": float("nan")})
                if item.year_index == 2 else item
                for item in original.uncertainty.current_y1_y3
            ),
        }),
    })
    for row in (bad_horizon, bad_numeric):
        malformed = complete.model_copy(update={
            "estimates": (row, *complete.estimates[1:]),
        })
        values = build_three_year_intrinsic_player_values(
            state, career_forward=malformed, career_evidence_state_id=state.state_id,
        )
        assert "a1" not in {item.player_id for item in values}

    duplicate = complete.model_copy(update={
        "estimates": (*complete.estimates, complete.estimates[0]),
        "player_count": len(complete.estimates) + 1,
    })
    assert build_three_year_intrinsic_player_values(
        state, career_forward=duplicate, career_evidence_state_id=state.state_id,
    ) == ()


def test_three_year_route_uses_only_published_completed_career_owner():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    state = _state()
    career = _career_current_components(state, {
        "a1": (1., 2., 3.), "a2": (2., 3., 4.), "a3": (3., 4., 5.),
        "a4": (10., 20., 30.), "b1": (5., 6., 7.),
    }).model_copy(update={
        "player_input_assumptions": {"a4": "Approved YTD-only Current input"},
    })
    career_record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED, contract=career,
        league_state_id=state.state_id, intrinsic_input_fingerprint="career-fp",
    )

    class CareerOwner:
        calls = 0
        def completed_for_state(self, context):
            self.calls += 1
            return career_record
        def current(self, *args):
            raise AssertionError("GET must not resolve fingerprints")
        def request(self, *args):
            raise AssertionError("GET must not start work")

    class ForbiddenStandaloneOwner:
        def completed_for_state(self, context):
            raise AssertionError("3-Year GET must not read a second value owner")

    owner = CareerOwner()
    context = SimpleNamespace(
        league_state=state, publication_generation_id="published", user_id="user",
    )
    validator_calls = []
    app = FastAPI()
    install_career_intrinsic_routes(
        app, runtime_store=SimpleNamespace(get=lambda _: context),
        loader=None, coordinator=owner,
        current_intrinsic_coordinator=ForbiddenStandaloneOwner(),
        career_generation_validator=lambda runtime, record: (
            validator_calls.append((runtime, record)) or True
        ),
    )
    endpoint = next(route.endpoint for route in app.routes
        if route.path == "/api/league/three-year-position-rooms")
    result = endpoint(state.state_id, "published", "user")
    assert result["status"] == "ready"
    assert result["input_fingerprint"] == "career-fp"
    assert result["source_input_fingerprints"] == {
        "career_current_components": "career-fp",
    }
    assert result["coverage"]["RB"] == {
        "rostered": 5, "covered": 5, "career_current_components": 5,
    }
    assert result["dynasty_rank_readiness"]["status"] == "ready"
    player = next(row for row in result["players"] if row["player_id"] == "a4")
    assert player["source"] == "career_current_y1_y3_components"
    assert player["input_assumption"] == "Approved YTD-only Current input"
    assert player["raw_intrinsic_value"] == pytest.approx(10 + .85 * 20 + .85**2 * 30)
    assert owner.calls == 1 and validator_calls == [(context, career_record)]
    context.publication_generation_id = None
    assert endpoint(state.state_id, "published", "user")["status"] == "superseded"


def test_three_year_route_fails_closed_without_published_career_source():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    state = _state()
    career = _career_current_components(state, {"a1": (1., 2., 3.)})
    record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED, contract=career,
        league_state_id=state.state_id, intrinsic_input_fingerprint="career-fp",
    )
    context = SimpleNamespace(
        league_state=state, publication_generation_id="published", user_id="user",
    )
    app = FastAPI()
    install_career_intrinsic_routes(
        app, runtime_store=SimpleNamespace(get=lambda _: context),
        loader=None, coordinator=SimpleNamespace(completed_for_state=lambda _: record),
        career_generation_validator=lambda *_: False,
    )
    endpoint = next(route.endpoint for route in app.routes
        if route.path == "/api/league/three-year-position-rooms")
    assert endpoint(state.state_id, "published", "user")["status"] == "unavailable"


def test_three_year_completed_state_lookup_cannot_touch_loader_or_fingerprints():
    from types import SimpleNamespace
    from fsffl.product.intrinsic_background import (
        ShapleyIntrinsicBackgroundCoordinator, IntrinsicBuildStatus,
    )
    state = _state()
    context = SimpleNamespace(user_id='owner', league_state=state,
        publication_generation_id='published')
    def forbidden(*args):
        raise AssertionError('read must never load, restore or fingerprint forecasts')
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        forbidden, intrinsic_input_fingerprint_resolver=forbidden,
        forecast_coordinate_resolver=forbidden,
    )
    record = SimpleNamespace(league_state_id=state.state_id,
        status=IntrinsicBuildStatus.COMPLETED, contract=object())
    key = ('owner', state.league.league_id, 'published-source')
    try:
        assert coordinator.completed_for_state(context) is None
        coordinator._records[key] = record
        assert coordinator.completed_for_state(context) is record
        assert coordinator.completed_for_state(SimpleNamespace(
            user_id='other-user', league_state=state, publication_generation_id='published')) is None
        context.publication_generation_id = None
        # Publication composition must be able to bind retained owners to its
        # replacement manifest before the runtime has a generation ID.
        assert coordinator.completed_for_state(context) is record
        context.publication_generation_id = 'published'
        coordinator._records[('owner', state.league.league_id, 'other-source')] = record
        assert coordinator.completed_for_state(context) is None  # never guess source identity
        coordinator._records.pop(('owner', state.league.league_id, 'other-source'))
        coordinator._records[key] = SimpleNamespace(league_state_id='older-state',
            status=IntrinsicBuildStatus.COMPLETED, contract=object())
        assert coordinator.completed_for_state(context) is None
    finally:
        coordinator._executor.shutdown(wait=False)
