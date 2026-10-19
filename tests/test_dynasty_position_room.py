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


def _three_year(state, values):
    from fsffl.value.shapley_intrinsic_contract import (
        ShapleyIntrinsicContract, ShapleyIntrinsicPlayerEstimate,
        ShapleyIntrinsicAvailability,
    )
    return ShapleyIntrinsicContract.model_construct(
        status=ShapleyIntrinsicAvailability.READY, evaluation_season=state.league.season,
        estimates=tuple(ShapleyIntrinsicPlayerEstimate.model_construct(
            player_id=pid, raw_intrinsic_value=value) for pid, value in values.items()),
    )


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


def test_three_year_room_uses_existing_shapley_not_career_or_display_values():
    from fsffl.analytics.dynasty_position_room import build_three_year_position_rooms
    state = _state()
    values = {'a1': 2., 'a2': 3., 'a3': 4., 'a4': -1., 'b1': 16.}
    contract = _three_year(state, values)
    rows = build_three_year_position_rooms(state, intrinsic=contract,
        evidence_state_id=state.state_id, positions=(Position.RB,))
    alpha, beta = rows
    assert alpha.room_raw == 8 and beta.room_raw == 16
    assert (alpha.league_rank, beta.league_rank) == (2, 1)
    assert alpha.strength_index == 100 * 8 / 12
    assert alpha.model_version == 'analytics-position-room-three-year-intrinsic-v2:career-current-annual-extension'
    assert contract.estimates[0].raw_intrinsic_value == 2


def test_three_year_room_preserves_ties_missing_coverage_and_state_fences():
    from fsffl.analytics.dynasty_position_room import build_three_year_position_rooms
    state = _state()
    contract = _three_year(state, {'a1': 2., 'a2': 3., 'a3': 4., 'a4': -1., 'b1': 8.})
    def rooms(c=contract, state_id=state.state_id):
        return build_three_year_position_rooms(state, intrinsic=c,
            evidence_state_id=state_id, positions=(Position.RB,))
    assert [row.league_rank for row in rooms()] == [1, 1]
    missing = contract.model_copy(update={'estimates': contract.estimates[1:]})
    incomplete = rooms(missing)
    assert incomplete[0].room_raw is None and incomplete[1].room_raw == 8
    assert all(row.league_rank is None for row in incomplete)
    for bad in (None, contract.model_copy(update={'display_scaling_applied': True}),
                contract.model_copy(update={'quantity_semantics': 'market'}),
                contract.model_copy(update={'evaluation_season': 2025})):
        assert all(row.room_raw is None for row in rooms(bad))
    assert all(row.room_raw is None for row in rooms(state_id='older-state'))


def test_three_year_extension_uses_only_missing_rostered_career_annual_components():
    from fsffl.analytics.dynasty_position_room import (
        build_three_year_intrinsic_player_values,
        build_three_year_position_rooms,
    )
    state = _state()
    standalone = _three_year(state, {'a1': 2., 'a2': 3., 'a3': 4., 'b1': 16.})
    # a1 and b1 deliberately disagree with their retained Career components.
    # Their stand-alone 3-Year values must remain authoritative and unchanged.
    career = _career_current_components(state, {
        'a1': (100., 100., 100.),
        'a4': (10., 20., 40.),
        'b1': (200., 200., 200.),
        'unrostered': (1., 2., 3.),
    })
    values = build_three_year_intrinsic_player_values(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=career, career_evidence_state_id=state.state_id,
    )
    by_id = {row.player_id: row for row in values}
    assert by_id['a1'].raw_intrinsic_value == 2.
    assert by_id['a1'].source == 'standalone_three_year_shapley'
    assert by_id['b1'].raw_intrinsic_value == 16.
    assert by_id['a4'].raw_intrinsic_value == pytest.approx(10 + .85 * 20 + .85**2 * 40)
    assert by_id['a4'].raw_intrinsic_value != career.estimates[1].raw_career_forward_reference
    assert by_id['a4'].source == 'career_current_y1_y3_discounted_extension'
    assert 'unrostered' not in by_id

    rooms = build_three_year_position_rooms(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=career, career_evidence_state_id=state.state_id,
        positions=(Position.RB,),
    )
    alpha, beta = rooms
    assert alpha.room_raw == pytest.approx(2 + 3 + 4 + 10 + .85 * 20 + .85**2 * 40)
    assert beta.room_raw == 16.
    assert alpha.league_rank is not None and beta.league_rank is not None
    assert all(row.coverage_count == row.team_count == 2 for row in rooms)


def test_three_year_extension_fails_closed_on_state_position_horizon_or_numeric_mismatch():
    from fsffl.analytics.dynasty_position_room import build_three_year_intrinsic_player_values
    state = _state()
    standalone = _three_year(state, {'a1': 2., 'a2': 3., 'a3': 4., 'b1': 8.})
    career = _career_current_components(
        state, {'a4': (10., 20., 30.)}, positions={'a4': Position.WR},
    )
    wrong_state = build_three_year_intrinsic_player_values(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=career, career_evidence_state_id='older-state',
    )
    assert {row.player_id for row in wrong_state} == {'a1', 'a2', 'a3', 'b1'}

    degraded = standalone.model_copy(update={'status': 'degraded'})
    complete_career = _career_current_components(state, {
        'a1': (1., 2., 3.), 'a2': (1., 2., 3.), 'a3': (1., 2., 3.),
        'a4': (1., 2., 3.), 'b1': (1., 2., 3.),
    })
    degraded_values = build_three_year_intrinsic_player_values(
        state, intrinsic=degraded, evidence_state_id=state.state_id,
        career_forward=complete_career, career_evidence_state_id=state.state_id,
    )
    assert degraded_values == ()

    wrong_position = build_three_year_intrinsic_player_values(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=career, career_evidence_state_id=state.state_id,
    )
    assert {row.player_id for row in wrong_position} == {'a1', 'a2', 'a3', 'b1'}

    wrong_season_row = career.estimates[0].model_copy(update={
        'uncertainty': career.estimates[0].uncertainty.model_copy(update={
            'current_y1_y3': tuple(
                item.model_copy(update={'target_season': 2027}) if item.year_index == 2 else item
                for item in career.estimates[0].uncertainty.current_y1_y3
            ),
        }),
    })
    wrong_season = career.model_copy(update={'estimates': (wrong_season_row,)})
    missing_horizon = build_three_year_intrinsic_player_values(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=wrong_season, career_evidence_state_id=state.state_id,
    )
    assert {row.player_id for row in missing_horizon} == {'a1', 'a2', 'a3', 'b1'}

    nonfinite_row = career.estimates[0].model_copy(update={
        'uncertainty': career.estimates[0].uncertainty.model_copy(update={
            'current_y1_y3': tuple(
                item.model_copy(update={'raw_shapley_contribution': float('nan')})
                if item.year_index == 2 else item
                for item in career.estimates[0].uncertainty.current_y1_y3
            ),
        }),
    })
    nonfinite = career.model_copy(update={'estimates': (nonfinite_row,)})
    missing_numeric = build_three_year_intrinsic_player_values(
        state, intrinsic=standalone, evidence_state_id=state.state_id,
        career_forward=nonfinite, career_evidence_state_id=state.state_id,
    )
    assert {row.player_id for row in missing_numeric} == {'a1', 'a2', 'a3', 'b1'}

    duplicate = standalone.model_copy(update={
        'estimates': (*standalone.estimates, standalone.estimates[0]),
    })
    ambiguous = build_three_year_intrinsic_player_values(
        state, intrinsic=duplicate, evidence_state_id=state.state_id,
        career_forward=career, career_evidence_state_id=state.state_id,
    )
    assert ambiguous == ()

    malformed_estimate = standalone.estimates[0].model_copy(update={
        'raw_intrinsic_value': float('nan'),
    })
    malformed_contract = standalone.model_copy(update={
        'estimates': (malformed_estimate, *standalone.estimates[1:]),
    })
    career_with_same_player = _career_current_components(
        state, {'a1': (100., 100., 100.), 'a4': (1., 2., 3.)},
    )
    malformed_values = build_three_year_intrinsic_player_values(
        state, intrinsic=malformed_contract, evidence_state_id=state.state_id,
        career_forward=career_with_same_player, career_evidence_state_id=state.state_id,
    )
    malformed_by_id = {row.player_id: row for row in malformed_values}
    assert 'a1' not in malformed_by_id
    assert 'a4' in malformed_by_id


def test_three_year_route_reads_completed_owner_only_and_fences_publication():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    state = _state()
    contract = _three_year(state, {'a1': 2., 'a2': 3., 'a3': 4., 'a4': -1., 'b1': 8.})
    record = SimpleNamespace(status=IntrinsicBuildStatus.COMPLETED, contract=contract,
        league_state_id=state.state_id, intrinsic_input_fingerprint='owned-current')
    class ReadOnlyOwner:
        def completed_for_state(self, context): return record
        def current(self, context): raise AssertionError("GET must not resolve fingerprints")
        def request(self, *a): raise AssertionError('GET must not start work')
    context = SimpleNamespace(league_state=state, publication_generation_id='published')
    app = FastAPI()
    install_career_intrinsic_routes(app, runtime_store=SimpleNamespace(get=lambda _: context),
        loader=None, coordinator=None, current_intrinsic_coordinator=ReadOnlyOwner())
    endpoint = next(route.endpoint for route in app.routes
        if route.path == '/api/league/three-year-position-rooms')
    result = endpoint(state.state_id, 'published', 'user')
    assert result['status'] == 'ready'
    assert result['publication_generation_id'] == 'published'
    assert result['dynasty_rank_readiness']['status'] == 'ready'
    assert result['input_fingerprint'] == 'owned-current'
    assert endpoint(state.state_id, 'older-generation', 'user')['status'] == 'superseded'
    record = None
    assert endpoint(state.state_id, 'published', 'user')['status'] == 'unavailable'


def test_three_year_route_extends_only_from_matching_completed_career_record():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    state = _state()
    standalone = _three_year(state, {'a1': 2., 'a2': 3., 'a3': 4., 'b1': 8.})
    career = _career_current_components(state, {'a4': (10., 20., 30.)})
    current_record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED, contract=standalone,
        league_state_id=state.state_id, intrinsic_input_fingerprint='three-year-fp',
    )
    career_record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED, contract=career,
        league_state_id=state.state_id, intrinsic_input_fingerprint='career-fp',
    )

    class ReadOnlyOwner:
        def __init__(self, record):
            self.record = record
            self.calls = 0
        def completed_for_state(self, context):
            self.calls += 1
            return self.record
        def current(self, *args):
            raise AssertionError('GET must not resolve fingerprints')
        def request(self, *args):
            raise AssertionError('GET must not start work')

    current_owner = ReadOnlyOwner(current_record)
    career_owner = ReadOnlyOwner(career_record)
    context = SimpleNamespace(
        league_state=state, publication_generation_id='published', user_id='user',
    )
    app = FastAPI()
    install_career_intrinsic_routes(
        app, runtime_store=SimpleNamespace(get=lambda _: context),
        loader=None, coordinator=career_owner,
        current_intrinsic_coordinator=current_owner,
    )
    endpoint = next(route.endpoint for route in app.routes
        if route.path == '/api/league/three-year-position-rooms')
    result = endpoint(state.state_id, 'published', 'user')
    assert result['status'] == 'ready'
    assert result['input_fingerprint'] == 'three-year-fp'
    assert result['source_input_fingerprints'] == {
        'standalone_three_year': 'three-year-fp',
        'career_current_components': 'career-fp',
    }
    assert result['coverage']['RB'] == {
        'rostered': 5, 'covered': 5, 'extended_from_career_current_components': 1,
    }
    assert result['dynasty_rank_readiness']['status'] == 'ready'
    player = next(row for row in result['players'] if row['player_id'] == 'a4')
    assert player['source'] == 'career_current_y1_y3_discounted_extension'
    assert player['raw_intrinsic_value'] == pytest.approx(10 + .85 * 20 + .85**2 * 30)
    assert current_owner.calls == career_owner.calls == 1


def test_three_year_route_requires_completed_standalone_owner_before_extension():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.foundation4_shadow_routes import install_career_intrinsic_routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    state = _state()
    career = _career_current_components(state, {
        'a1': (1., 2., 3.), 'a2': (2., 3., 4.), 'a3': (3., 4., 5.),
        'a4': (4., 5., 6.), 'b1': (5., 6., 7.),
    })
    career_record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED, contract=career,
        league_state_id=state.state_id, intrinsic_input_fingerprint='career-fp',
    )
    class ReadOnlyOwner:
        def completed_for_state(self, context): return career_record
        def current(self, *args): raise AssertionError('GET must not resolve fingerprints')
        def request(self, *args): raise AssertionError('GET must not start work')

    context = SimpleNamespace(
        league_state=state, publication_generation_id='published', user_id='user',
    )
    app = FastAPI()
    install_career_intrinsic_routes(
        app, runtime_store=SimpleNamespace(get=lambda _: context),
        loader=None, coordinator=ReadOnlyOwner(),
    )
    endpoint = next(route.endpoint for route in app.routes
        if route.path == '/api/league/three-year-position-rooms')
    result = endpoint(state.state_id, 'published', 'user')
    assert result['status'] == 'unavailable'
    assert 'No completed 3-Year' in result['reason']


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
        assert coordinator.completed_for_state(context) is None
        context.publication_generation_id = 'published'
        coordinator._records[('owner', state.league.league_id, 'other-source')] = record
        assert coordinator.completed_for_state(context) is None  # never guess source identity
        coordinator._records.pop(('owner', state.league.league_id, 'other-source'))
        coordinator._records[key] = SimpleNamespace(league_state_id='older-state',
            status=IntrinsicBuildStatus.COMPLETED, contract=object())
        assert coordinator.completed_for_state(context) is None
    finally:
        coordinator._executor.shutdown(wait=False)
