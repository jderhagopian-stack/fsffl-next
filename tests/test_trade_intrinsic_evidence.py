from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import ast

import pytest
from fastapi.testclient import TestClient

from fsffl.product.intrinsic_background import IntrinsicBuildStatus
from fsffl.product.runtime import PrivateBetaRuntimeStore, UserRuntimeContext
from fsffl.product.trade_intrinsic_evidence import build_trade_intrinsic_evidence
from fsffl.product.webapp import create_app
from fsffl.state.models import PlayerAsset, PickAsset
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.value.shapley_intrinsic_contract import discounted_three_year_shapley_value

# Reuse the existing accepted annual-component fixture and canonical State.
from tests.test_dynasty_position_room import _state, _career_current_components


def fixture():
    state = _state()
    contract = _career_current_components(state, {'a1': (10., 20., 30.), 'b1': (20., 30., 40.)})
    rows = tuple(row.model_copy(update={
        'long_horizon_raw_y4_y7_reference': 800., 'terminal_raw_y8_plus_reference': 200.,
    }) for row in contract.estimates)
    contract = contract.model_copy(update={'estimates': rows})
    runtime = UserRuntimeContext(user_id='local-beta-user', league_state=state, selected_team_id='alpha', publication_generation_id='g1')
    record = SimpleNamespace(user_id=runtime.user_id, league_state_id=state.state_id,
        status=IntrinsicBuildStatus.COMPLETED, contract=contract, intrinsic_input_fingerprint='dependency')
    proposal = BilateralTradeProposal(proposal_id='test', as_of=state.as_of,
        side_a=TradeLeg(team_id='alpha', sends=(PlayerAsset(player_id='a1'),)),
        side_b=TradeLeg(team_id='beta', sends=(PlayerAsset(player_id='b1'),)))
    return runtime, record, proposal


def build(runtime, record, proposal, validator=lambda c, r: True):
    return build_trade_intrinsic_evidence(runtime, proposal, record=record, publication_validator=validator)


def test_horizons_reuse_raw_authority_and_do_not_mutate_source():
    runtime, record, proposal = fixture()
    before = record.contract.model_dump(mode='json')
    result = build(runtime, record, proposal)
    assert result['status'] == 'complete'
    a = result['three_year']['side_a']
    b = result['three_year']['side_b']
    assert a['sent_mean'] == discounted_three_year_shapley_value((10., 20., 30.))
    assert a['received_mean'] == discounted_three_year_shapley_value((20., 30., 40.))
    assert a['mean_delta'] == -b['mean_delta']
    assert result['career']['side_a']['mean_delta'] == 30.
    assert a['scale'] != result['career']['side_a']['scale']
    assert result['three_year']['package_uncertainty'] is None
    assert result['career']['package_uncertainty'] is None
    assert result['decision_effect'] == 'evidence_only_no_disposition_change'
    assert record.contract.model_dump(mode='json') == before


@pytest.mark.parametrize('mutation', ['state', 'user', 'status', 'publication', 'contract'])
def test_wrong_or_unpublished_source_cannot_produce_evidence(mutation):
    runtime, record, proposal = fixture()
    if mutation == 'state': record.league_state_id = 'other'
    if mutation == 'user': record.user_id = 'other'
    if mutation == 'status': record.status = IntrinsicBuildStatus.RUNNING
    if mutation == 'publication': runtime = replace(runtime, publication_generation_id=None)
    if mutation == 'contract': record.contract = None
    assert build(runtime, record, proposal)['status'] == 'unavailable'


def test_same_state_wrong_generation_is_rejected():
    runtime, record, proposal = fixture()
    assert build(runtime, record, proposal, validator=lambda c, r: False)['status'] == 'unavailable'


def test_wrong_proposal_team_and_time_are_rejected():
    runtime, record, proposal = fixture()
    assert build(replace(runtime, selected_team_id='unrelated'), record, proposal)['status'] == 'unavailable'
    newer = proposal.model_copy(update={'as_of': proposal.as_of + timedelta(days=1)})
    assert build(runtime, record, newer)['status'] == 'unavailable'


def test_missing_pick_is_explicit_and_does_not_become_zero():
    runtime, record, proposal = fixture()
    proposal = proposal.model_copy(update={'side_b': TradeLeg(team_id='beta', sends=(PickAsset(pick_id='pick'),))})
    result = build(runtime, record, proposal)
    assert result['status'] == 'partial'
    for name in ('three_year', 'career'):
        assert result[name]['side_a']['mean_delta'] is None
        assert any(item['asset_id'] == 'pick' and item['flow'] == 'received' for item in result[name]['missing_evidence']['side_a'])


def test_zero_negative_values_and_missing_player_are_preserved():
    runtime, record, proposal = fixture()
    source = _career_current_components(runtime.league_state, {'a1': (0., 0., 0.), 'b1': (-10., -20., -30.)})
    source = source.model_copy(update={'estimates': tuple(r.model_copy(update={
        'long_horizon_raw_y4_y7_reference': 800., 'terminal_raw_y8_plus_reference': 200.,
    }) for r in source.estimates)})
    record.contract = source
    result = build(runtime, record, proposal)
    assert result['three_year']['side_a']['sent_mean'] == 0.
    assert result['three_year']['side_a']['received_mean'] < 0.
    record.contract = source.model_copy(update={'estimates': source.estimates[:1], 'player_count': 1})
    missing = build(runtime, record, proposal)
    assert missing['status'] == 'partial'
    assert missing['career']['side_a']['mean_delta'] is None


def test_nonfinite_or_inconsistent_components_are_missing():
    runtime, record, proposal = fixture()
    broken = record.contract.estimates[1].model_copy(update={'raw_career_forward_reference': float('nan')})
    record.contract = record.contract.model_copy(update={'estimates': (record.contract.estimates[0], broken)})
    result = build(runtime, record, proposal)
    assert result['career']['side_a']['mean_delta'] is None
    assert result['three_year']['side_a']['mean_delta'] is not None  # Independent valid horizon survives.


def test_hosted_provider_reads_only_existing_memory_owner():
    runtime, record, proposal = fixture()
    path = Path(__file__).resolve().parents[1] / 'src/fsffl/product/persistent_webapp.py'
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_published_trade_intrinsic_provider')
    calls = []
    scope = {'__package__': 'fsffl.product',
        '_career_intrinsic_coordinator': SimpleNamespace(readiness_record_for_state=lambda c: calls.append(c) or record),
        '_presentation_continuity': SimpleNamespace(career_generation_hint_matches=lambda c, r: c is runtime and r is record)}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), scope)
    result = scope[fn.name](runtime, proposal)
    assert result['status'] == 'complete'
    assert calls == [runtime]  # No loader, DB/payload read, restore, fit or alternate cache exists in this fixture.


@pytest.mark.parametrize('failure', [False, True])
def test_real_analysis_api_adds_evidence_without_changing_existing_result(monkeypatch, failure):
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    runtime, record, _ = fixture()
    store = PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id, runtime.league_state)
    store.select_team(runtime.user_id, 'alpha')
    store.bind_publication_generation_id(runtime.user_id, publication_generation_id='g1')
    calls = []
    def provider(context, proposal):
        calls.append(proposal)
        if failure: raise RuntimeError('source unavailable')
        return build(context, record, proposal)
    client = TestClient(create_app(runtime_store=store, trade_intrinsic_provider=provider))
    body = {'counterparty_team_id': 'beta', 'focal_asset_refs': ['player:a1'], 'counterparty_asset_refs': ['player:b1']}
    response = client.post('/api/trade-center/analyze', json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['state_id_before'] == runtime.league_state.state_id
    assert result['horizon_asset_economics']['status'] == ('unavailable' if failure else 'complete')
    assert result['availability']['competitive_outcomes'] is False
    assert result['decision'] is None  # No manufactured final recommendation.
    assert len(calls) == 1
    invalid = client.post('/api/trade-center/analyze', json={**body, 'focal_asset_refs': ['player:b1']})
    assert invalid.status_code == 422
    assert len(calls) == 1  # Ownership is validated before evidence is requested.


def test_real_simulation_route_attaches_evidence_only_after_success(monkeypatch):
    import fsffl.product.webapp as webapp
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    runtime, record, _ = fixture()
    store = PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id, runtime.league_state)
    store.select_team(runtime.user_id, 'alpha')
    store.bind_publication_generation_id(runtime.user_id, 'g1')
    calls = []
    def simulate(context, proposal, **kwargs):
        calls.append('simulation')
        return {'state_id_before': context.league_state.state_id, 'scenario_simulation_count': 50000, 'existing_field': 'preserved'}
    monkeypatch.setattr(webapp, 'build_post_trade_simulation_comparison', simulate)
    def provider(context, proposal):
        calls.append('evidence')
        return build(context, record, proposal)
    client = TestClient(create_app(runtime_store=store, trade_intrinsic_provider=provider))
    body = {'counterparty_team_id': 'beta', 'focal_asset_refs': ['player:a1'], 'counterparty_asset_refs': ['player:b1']}
    result = client.post('/api/trade-center/simulate', json=body)
    assert result.status_code == 200
    assert result.json()['horizon_asset_economics']['status'] == 'complete'
    assert result.json()['existing_field'] == 'preserved'
    assert calls == ['simulation', 'evidence']
    calls.clear()
    def blocked(*args, **kwargs):
        raise ValueError('No authoritative Forecast')
    monkeypatch.setattr(webapp, 'build_post_trade_simulation_comparison', blocked)
    assert client.post('/api/trade-center/simulate', json=body).status_code == 409
    assert calls == []


def test_large_source_only_projects_selected_rows_and_preserves_cohort(monkeypatch):
    import fsffl.product.trade_intrinsic_evidence as module
    runtime, record, proposal = fixture()
    original_rows = record.contract.estimates
    extra = tuple(original_rows[0].model_copy(update={'player_id': f'outside-{i}'}) for i in range(333))
    record.contract = record.contract.model_copy(update={'estimates': (*original_rows, *extra), 'player_count': 335})
    original = module.build_three_year_intrinsic_player_values
    seen = []
    def bounded(state, *, career_forward, career_evidence_state_id):
        seen.append(career_forward)
        return original(state, career_forward=career_forward, career_evidence_state_id=career_evidence_state_id)
    monkeypatch.setattr(module, 'build_three_year_intrinsic_player_values', bounded)
    result = build(runtime, record, proposal)
    assert result['status'] == 'complete'
    assert len(seen) == 1 and len(seen[0].estimates) == 2
    assert seen[0].estimates[0] is original_rows[0]
    assert result['source']['source_player_count'] == 335
    assert result['source']['selected_player_count'] == 2
    assert result['source']['input_fingerprint'] == record.contract.input_fingerprint
    assert len(record.contract.estimates) == 335


def test_source_scoring_qualifications_and_input_assumptions_survive():
    runtime, record, proposal = fixture()
    record.contract = record.contract.model_copy(update={
        'scoring_coordinate_limitation': 'Source qualification retained',
        'ignored_long_term_residual_rule_stats': ('qualified-stat',),
        'player_input_assumptions': {'a1': 'Accepted sparse Current evidence', 'outside': 'Not in this trade'},
    })
    result = build(runtime, record, proposal)
    assert result['source']['scoring_coordinate_limitation'] == 'Source qualification retained'
    assert result['source']['ignored_long_term_residual_rule_stats'] == ['qualified-stat']
    assert result['input_assumptions'] == {'a1': 'Accepted sparse Current evidence'}
