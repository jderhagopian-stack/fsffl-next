import pytest
from pydantic import ValidationError

from fsffl.trade_decision.objectives import (
    ObjectiveMetric, OwnerObjectiveContext, TradeObjective as G, assess_owner_objectives,
)
from fsffl.product.trade_objectives import TradeSearchInstructions, build_trade_objective_assessment
from tests.test_trade_intrinsic_evidence import fixture


def metric(goal, value, **kwargs):
    return ObjectiveMetric(objective=goal, metric=kwargs.pop('metric', 'native_delta'),
        unit='native', source_identity='state:source', delta=value, authoritative=True, **kwargs)


def context(*goals, **kwargs):
    return OwnerObjectiveContext(team_id='alpha', objectives=goals, source='test', **kwargs)


def test_opposing_priorities_preserve_all_sacrifices_without_blending():
    metrics = (metric(G.THREE_YEAR, -10), metric(G.CAREER, 20), metric(G.MARKET, -5))
    long = assess_owner_objectives(context(G.CAREER), metrics)
    short = assess_owner_objectives(context(G.THREE_YEAR), metrics)
    assert long.status == 'aligns_with_priorities'
    assert short.status == 'conflicts_with_priorities'
    assert {m.objective for m in long.sacrifices} == {G.THREE_YEAR, G.MARKET}
    assert long.decision_effect == 'no_disposition_change'
    assert assess_owner_objectives(context(G.THREE_YEAR, G.CAREER), metrics).status == 'mixed'


def test_competitive_vector_conflicts_and_missing_do_not_promote_alignment():
    metrics = (metric(G.CURRENT, 0.1, metric='wins'), metric(G.CURRENT, -0.01, metric='playoffs'))
    assert assess_owner_objectives(context(G.CURRENT), metrics).status == 'mixed'
    assert assess_owner_objectives(context(G.CURRENT), (metrics[0], metric(G.CURRENT, None, metric='playoffs'))).status == 'incomplete'
    preview = metrics[0].model_copy(update={'authoritative': False})
    assert assess_owner_objectives(context(G.CURRENT), (preview,)).status == 'incomplete'
    assert assess_owner_objectives(context(G.CAREER), metrics).unresolved == (G.CAREER,)


def test_zero_signs_constraints_and_resilience_orientation():
    assert assess_owner_objectives(context(G.CAREER), (metric(G.CAREER, 0),)).status == 'unchanged'
    assert assess_owner_objectives(context(G.RESILIENCE), (metric(G.RESILIENCE, -1, higher_is_better=False),)).status == 'aligns_with_priorities'
    for field in ('sent_player_ids', 'cut_player_ids'):
        result = assess_owner_objectives(context(G.CAREER, protected_player_ids=('a1',)),
            (metric(G.CAREER, 20),), **{field: ('a1',)})
        assert result.status == 'constraints_violated'
        assert result.protected_players_lost == ('a1',)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_not_economic_evidence(value):
    with pytest.raises(ValidationError): metric(G.CAREER, value)


def test_duplicate_goals_and_channels_rejected():
    with pytest.raises(ValidationError): context(G.CAREER, G.CAREER)
    with pytest.raises(ValidationError): context()
    with pytest.raises(ValueError):
        assess_owner_objectives(context(G.CAREER), (metric(G.CAREER, 1), metric(G.CAREER, 2)))


def test_product_both_teams_inferred_user_override_and_preview_authority():
    runtime, _, proposal = fixture()
    result = {'scenario_computation': {'authoritative': False},
        'team_deltas': [{'team_id': 'alpha', 'competitive': {'expected_wins': 10,
            'playoff_probability': 0.2, 'first_place_probability': 0.3}}]}
    before = repr(result)
    instructions = TradeSearchInstructions(objectives=(G.CURRENT,))
    assessment = build_trade_objective_assessment(runtime, proposal, result, instructions)
    assert assessment['side_a']['context']['explicitly_directed'] is True
    assert assessment['side_b']['context']['explicitly_directed'] is False
    assert assessment['side_a']['status'] == 'incomplete'
    assert assessment['side_b']['context']['objectives'] == [G.CURRENT, G.THREE_YEAR, G.CAREER]
    assert repr(result) == before
    result['scenario_computation']['authoritative'] = True
    assert build_trade_objective_assessment(runtime, proposal, result, instructions)['side_a']['status'] == 'aligns_with_priorities'


def test_real_api_user_instruction_ownership_rejection_and_legacy_routes(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    runtime, record, _ = fixture()
    store = PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id, runtime.league_state)
    store.select_team(runtime.user_id, 'alpha')
    calls = []
    def provider(context, proposal, result):
        from fsffl.product.trade_intrinsic_evidence import build_trade_intrinsic_evidence
        from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
        calls.append(result)
        context = replace(context, publication_generation_id='g1')
        return build_trade_intrinsic_evidence(context, proposal, record=record,
            publication_validator=lambda c,r: True,
            roster_resolutions=tuple(TeamRosterLegalityResolution.model_validate(row) for row in result['roster_legality']))
    from dataclasses import replace
    client = TestClient(create_app(runtime_store=store, trade_horizon_evidence_provider=provider))
    body = {'counterparty_team_id': 'beta', 'focal_asset_refs': ['player:a1'], 'counterparty_asset_refs': ['player:b1'],
        'search_instructions': {'objectives': ['career_contribution'], 'protected_player_ids': ['a2']}}
    response = client.post('/api/trade-center/analyze', json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['objective_assessment']['side_a']['context']['explicitly_directed'] is True
    assert payload['objective_assessment']['side_b']['context']['explicitly_directed'] is False
    assert payload['objective_assessment']['side_a']['status'] == 'aligns_with_priorities'
    assert payload['decision'] is None
    assert len(calls) == 1
    for instructions in ({'objectives': []}, {'objectives': ['career_contribution']*2},
                         {'objectives': ['career_contribution'], 'protected_player_ids': ['b1']},
                         {'objectives': ['career_contribution'], 'protected_player_ids': ['a1']}):
        for route in ('analyze', 'simulate'):
            assert client.post('/api/trade-center/'+route, json={**body, 'search_instructions': instructions}).status_code == 422
    assert len(calls) == 1
    # Guided frontiers preserve goals and exclude protected sends before exploration.
    response = client.post('/api/trade-center/frontier', json=body)
    assert response.status_code == 200
    points = response.json()['points']
    assert points
    assert all(a['asset'].get('player_id') != 'a2' for p in points for a in p['focal_assets'])
    assert all(p['objective_assessment']['side_a']['context']['objectives'] == ['career_contribution'] for p in points)
    # The legacy opportunity route still rejects unsupported instructions.
    assert client.post('/api/opportunities/trade', json=body).status_code == 422
    assert store.get(runtime.user_id).league_state == runtime.league_state


@pytest.mark.parametrize('state,expected', [
    ('contender', (G.CURRENT,)), ('competitive', (G.CURRENT,G.THREE_YEAR,G.CAREER)),
    ('developing', (G.THREE_YEAR,)), ('rebuilding', (G.CAREER,)),
    ('unknown', (G.CURRENT,G.THREE_YEAR,G.CAREER)),
])
def test_default_inference_is_a_hypothesis_and_explicit_direction_wins(monkeypatch, state, expected):
    import fsffl.product.trade_objectives as module
    from fsffl.team_utility.utility import CalculatedCompetitiveState
    runtime, _, _ = fixture()
    seen = []
    def calculated(context):
        seen.append(context.selected_team_id)
        return CalculatedCompetitiveState(state)
    monkeypatch.setattr(module, 'calculated_competitive_state', calculated)
    context = module.objective_context(runtime, 'beta')
    assert context.objectives == expected
    assert context.calculated_competitive_state == state
    assert context.explicitly_directed is False
    assert 'hypothesis' in context.source
    explicit = module.objective_context(runtime, 'alpha', TradeSearchInstructions(objectives=(G.MARKET,)))
    assert explicit.objectives == (G.MARKET,)
    assert explicit.explicitly_directed
    assert seen == ['beta']
    assert runtime.selected_team_id == 'alpha'


def test_optional_assessment_failure_preserves_legacy_result(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    import fsffl.product.webapp as webapp
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    runtime, _, _ = fixture()
    store = PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id, runtime.league_state)
    store.select_team(runtime.user_id, 'alpha')
    def unavailable(*args): raise ValueError('optional source problem')
    monkeypatch.setattr(webapp, 'build_trade_objective_assessment', unavailable)
    client = TestClient(webapp.create_app(runtime_store=store))
    response = client.post('/api/trade-center/analyze', json={'counterparty_team_id': 'beta',
        'focal_asset_refs': ['player:a1'], 'counterparty_asset_refs': ['player:b1']})
    assert response.status_code == 200
    assert response.json()['objective_assessment']['status'] == 'unavailable'
    assert response.json()['roster_legality']
    assert response.json()['decision'] is None


def test_protections_without_goals_preserve_server_inference_and_handoff(monkeypatch):
    from fsffl.product.trade_objectives import objective_context
    import fsffl.product.trade_objectives as module
    from fsffl.team_utility.utility import CalculatedCompetitiveState
    runtime, _, _ = fixture()
    monkeypatch.setattr(module, 'calculated_competitive_state', lambda _: CalculatedCompetitiveState.CONTENDER)
    automatic = objective_context(runtime, 'alpha')
    protected = TradeSearchInstructions(protected_player_ids=('a2',))
    current = objective_context(runtime, 'alpha', protected)
    assert current.objectives == automatic.objectives == (G.CURRENT,)
    assert current.explicitly_directed is False
    assert current.source == automatic.source
    assert current.protected_player_ids == ('a2',)
    custom = objective_context(runtime, 'alpha', TradeSearchInstructions(objectives=(G.CAREER,), protected_player_ids=('a2',)))
    assert custom.objectives == (G.CAREER,)
    assert custom.explicitly_directed
    assert objective_context(runtime, 'alpha', protected) == current
