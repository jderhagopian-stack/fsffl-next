"""NFL IR is distinct from both generic injury and the fantasy IR slot."""
from dataclasses import replace
from datetime import timedelta
import json

import pytest

from fsffl.forecast.participation import (
    NFL_IR_NO_PROJECTION_POLICY_APPROVED_AT,
    recorded_ir_no_projection_year_one_evidence,
)
from fsffl.forecast.season_comparison import apply_participation_exceptions
from fsffl.forecast.season_rollforward import compose_completed_actuals_with_ros_per_player
from fsffl.product.runtime import league_material_fingerprint, raw_forecast_input_fingerprint
from fsffl.product.season_comparison_runtime import SeasonComparisonService
from fsffl.providers.sleeper import SleeperNormalizer, _normalize_sleeper_nfl_ir
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.state.models import PlayerState, PlayerStatus, RosterSlot, RosterEntry
from tests.test_season_comparison import _state, PID, participation_result, Store, context
from tests.test_sleeper_normalizer import bundle
from tests.test_product_forecast_refresh import _evidence

NOW = NFL_IR_NO_PROJECTION_POLICY_APPROVED_AT + timedelta(seconds=1)


def state_with_fact(value=True, *, status=PlayerStatus.INJURED, observed=None):
    state = _state().model_copy(update={'completed_through_week': 2})
    observed = observed or NOW - timedelta(seconds=1)
    provenance = state.player_states[0].provenance.model_copy(update={
        'retrieved_at': observed, 'effective_at': observed})
    row = PlayerState(player_id=PID, as_of=observed, status=status,
                      nfl_injured_reserve=value, provenance=provenance)
    team = state.team_states[0]
    roster = (RosterEntry(player_id=PID, slot=RosterSlot.BENCH),)
    return state.model_copy(update={
        'player_states': (row,),
        'team_states': (team.model_copy(update={'roster': roster}),) + state.team_states[1:],
    })


@pytest.mark.parametrize('key,value', [
    ('injury_status', 'IR'), ('injury_status', 'Injured Reserve'),
    ('status', 'Reserve/Injured'), ('status', 'reserve_injured'),
    ('status', 'injured-reserve'),
])
def test_explicit_nfl_ir_survives_both_normalization_paths(key, value):
    source = bundle()
    players = {k: dict(v) for k, v in source.players.items()}
    players['p2'][key] = value
    source = replace(source, players=players)
    direct = SleeperNormalizer().normalize(source, as_of=source.retrieved_at)
    snapshot = ProviderSnapshot(provider_name='sleeper', league_external_id='123', captured_at=source.retrieved_at,
        payload={k: getattr(source, k) for k in ('league','users','rosters','players','traded_picks','matchups','nfl_state')})
    attached = SleeperSnapshotNormalizer().normalize_snapshot(snapshot, as_of=source.retrieved_at)
    for state in (direct, attached):
        row = next(p for p in state.player_states if p.player_id == 'sleeper:player:p2')
        assert row.nfl_injured_reserve is True
        assert row.status == PlayerStatus.INJURED


@pytest.mark.parametrize('label', ['Out', 'Questionable', 'Doubtful', 'PUP', 'Injured', 'Active', ''])
def test_coarse_injury_does_not_invent_nfl_ir(label):
    assert _normalize_sleeper_nfl_ir({'injury_status': label, 'status': 'Active'}) is None


def test_old_states_keep_their_canonical_and_material_identity():
    # Frozen identities calculated from main adb3b57 before the additive field.
    state = _state()
    assert state.state_id == 'a01cf7504c4350e888b4045c6fd16c4c9424e61e3822b7140363ff4bbdfc3aac'
    assert league_material_fingerprint(state) == '1ca6d2251ae0cb4064383ac57f3f5837a91a4cf557e7de808721630a3306c972'
    assert all('nfl_injured_reserve' not in row for row in json.loads(state.canonical_json())['player_states'])


def test_ir_fact_and_return_change_identity_even_with_same_coarse_injury():
    unknown = state_with_fact(None)
    ir = state_with_fact(True)
    returned = state_with_fact(False)
    assert len({s.state_id for s in (unknown, ir, returned)}) == 3
    assert len({league_material_fingerprint(s) for s in (unknown, ir, returned)}) == 3
    # Availability affects derived participation, not raw provider identity.
    assert len({raw_forecast_input_fingerprint(s) for s in (unknown, ir, returned)}) == 1


@pytest.mark.parametrize('projected,complete,allowed', [
    (False, False, True), (True, False, False), (True, True, False),
])
def test_nfl_ir_no_projection_shared_with_cards_and_current(projected, complete, allowed):
    state = state_with_fact()
    result = participation_result(state, projected=projected, complete=complete)
    reason = apply_participation_exceptions(state, result, as_of=NOW)
    assert (PID in reason) is allowed
    receipt = recorded_ir_no_projection_year_one_evidence(
        state, player_id=PID, as_of=NOW,
        available_projection_rows=result.current_runtime.source_observations)
    assert (receipt is not None) is allowed
    if allowed:
        assert receipt.source == 'fsffl:exact-state-nfl-ir-no-projection'
        assert reason[PID]['participation_basis'] == 'ir_no_projection'
        assert reason[PID]['participation_assumption'] is True
        assert result.forward_forecasts[0].distribution.mean == 0
    elif complete:
        assert result.forward_forecasts[0].distribution.mean > 0


@pytest.mark.parametrize('value,observed,cutoff', [
    (None, None, NOW), (False, None, NOW),
    (True, NOW + timedelta(seconds=1), NOW),
    (True, NOW - timedelta(seconds=3), NFL_IR_NO_PROJECTION_POLICY_APPROVED_AT - timedelta(seconds=1)),
])
def test_missing_false_future_or_pre_policy_fact_cannot_zero_ros(value, observed, cutoff):
    state = state_with_fact(value, observed=observed)
    assert recorded_ir_no_projection_year_one_evidence(
        state, player_id=PID, as_of=cutoff, available_projection_rows=()) is None


def test_nfl_ir_on_bench_completes_current_simulation_coverage_without_acquisition():
    state = state_with_fact()
    result = participation_result(state)
    apply_participation_exceptions(state, result, as_of=NOW)
    payload = dict(league_state_id=state.state_id, season=2026, as_of=NOW.isoformat(),
        completed_through_week=2, evidence_basis='current_rest_of_season',
        forward_forecasts=[r.model_dump(mode='json') for r in result.forward_forecasts])
    service = SeasonComparisonService(persistence_store=Store(),
                                     builder=lambda *a, **k: payload)
    ctx = context(state)
    service.prepare(ctx)
    bound = service.simulation_evidence(ctx, replace(_evidence(), uncertainty_ready=True))
    assert bound.uncertainty_ready
    assert bound.simulation_missing_player_ids == ()
    assert bound.simulation_forward_forecasts[0].distribution.mean == 0


def test_no_ros_assumption_preserves_earned_actuals():
    from fsffl.forecast.backtest import RealizedOutcome
    from fsffl.forecast.in_season_orchestration import canonical_week_window
    state = state_with_fact()
    result = participation_result(state)
    apply_participation_exceptions(state, result, as_of=NOW)
    start, end = canonical_week_window(2026, 1)
    actual = RealizedOutcome(player_id=PID, position=state.players[0].position,
        metric=result.forward_forecasts[0].metric, period_start=start, period_end=end,
        actual=27.5, finalized_at=end, provenance=state.player_states[0].provenance)
    outlook, failures = compose_completed_actuals_with_ros_per_player(
        completed_actuals=(actual,), ros_forecasts=result.forward_forecasts,
        season_start=start, expected_roster_positions={PID: state.players[0].position})
    assert not failures
    assert outlook[0].distribution.mean == 27.5
