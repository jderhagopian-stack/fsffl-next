"""Budget/retention contracts with a canonical controlled generation corpus."""
from dataclasses import replace
from types import SimpleNamespace as NS
from collections import Counter

import pytest

from fsffl.product import strategic_discovery as module
from fsffl.product import trade_objectives
from fsffl.product.strategic_discovery import StrategicDiscoveryRequest
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
from fsffl.product.intrinsic_background import IntrinsicBuildStatus
from fsffl.opportunity.strategic_packages import StrategicSeed
from fsffl.opportunity.trade_pairs import generate_bilateral_trade_proposals
from fsffl.opportunity.trade_universe import TradePackageSeed, canonical_package_id
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision.objectives import OwnerObjectiveContext
from tests.test_strategic_feedback import controlled_root
from tests.test_simulation_ros_inputs import market
from tests.test_dynasty_position_room import _career_current_components


def setup(monkeypatch, *, superflex=False, duplicates=False, fail_repair=False, extra_roots=False):
    runtime, _, _ = controlled_root(superflex=superflex)
    state = runtime.league_state
    runtime = replace(runtime, value_evidence=market(state), publication_generation_id='synthetic-generation')
    components = {p.player_id: ((1., 1., 1.) if p.player_id == 'opp' else (100., 100., 100.))
                  for p in state.players}
    contract = _career_current_components(state, components, positions={p.player_id: p.position for p in state.players})
    contract = contract.model_copy(update={'estimates': tuple(row.model_copy(update={
        'long_horizon_raw_y4_y7_reference': 800., 'terminal_raw_y8_plus_reference': 200.})
        for row in contract.estimates)})
    record = NS(user_id='u', league_state_id=state.state_id, status=IntrinsicBuildStatus.COMPLETED,
                contract=contract, intrinsic_input_fingerprint='synthetic-dependency')
    read = read_published_trade_horizon_values(runtime, player_ids=frozenset(components),
        record=record, publication_validator=lambda c, r: True)
    original_context = trade_objectives.objective_context
    def context(current, team_id, instructions=None):
        if instructions is not None:
            return original_context(current, team_id, instructions)
        return OwnerObjectiveContext(team_id=team_id, source='controlled-synthetic-preference',
            objectives=('current_competitiveness',) if team_id == 'a' else ('three_year_contribution',))
    monkeypatch.setattr(module, 'objective_context', context)
    monkeypatch.setattr(trade_objectives, 'objective_context', context)
    def package(team, ids):
        assets = tuple(PlayerAsset(player_id=x) for x in ids)
        return TradePackageSeed(team_id=team, assets=assets, canonical_id=canonical_package_id(team, assets))
    receiver = package('b', ('opp',))
    packages = [package('a', ('second', 'bench'))]
    if duplicates:
        packages.extend((package('a', ('bench',)), package('a', ('bench', 'reserve'))))
    seeds = tuple(StrategicSeed(generate_bilateral_trade_proposals((p,), (receiver,),
        as_of=state.as_of).proposals[0], ('controlled_root',)) for p in packages)
    if extra_roots:
        extras = [package('a', ('second',)), package('a', ('bench',))]
        seeds += tuple(StrategicSeed(generate_bilateral_trade_proposals((p,), (receiver,), as_of=state.as_of).proposals[0], ('other_root',)) for p in extras)
    captured = []
    def generate(lanes, *, as_of, bounds):
        captured.append(bounds.max_pair_visits)
        return seeds, {'pair_visits': len(seeds), 'max_candidates': bounds.max_candidates,
            'shapes': dict(Counter(f'{len(x.seed.proposal.side_a.sends)}_for_1' for x in seeds)), 'hypotheses': {'controlled_root': len(seeds)}}
    monkeypatch.setattr(module, 'generate_strategic_packages', generate)
    actual = module.evaluate_candidate_path
    calls = []
    def evaluate(current, row, **kwargs):
        calls.append(row['point_id'])
        depth = (row.get('repair_lineages') or [{}])[-1].get('depth', 0)
        if fail_repair and depth:
            raise ValueError('controlled missing current authority')
        result = actual(current, row, **kwargs)
        # Controlled upstream feedback isolates integration from model accuracy.
        # Real saved-input replay separately verifies actual numerical usefulness.
        result['preliminary_bilateral_screen']['focal']['starter_points_delta'] = 2 if depth == 2 else -5
        return result
    monkeypatch.setattr(module, 'evaluate_candidate_path', evaluate)
    return runtime, read, calls, captured


@pytest.mark.parametrize('superflex', [False, True])
def test_one_shared_budget_preserves_failed_parent_and_exact_target(monkeypatch, superflex):
    runtime, read, calls, generation = setup(monkeypatch, superflex=superflex)
    before = runtime.league_state.model_dump(mode='json')
    request = StrategicDiscoveryRequest(max_candidates=3, evaluation_budget=8, target_asset_ref='player:opp',
        search_instructions={'objectives': ['current_competitiveness']})
    result = module.build_strategic_discovery(runtime, request, read=read)
    d, rows = result['diagnostics'], result['candidate_packages']
    assert len(rows) == len(calls) == len(set(calls)) == 3
    assert generation == [18]  # 24 total visits minus six reserved before generation.
    assert d['pair_visits'] == d['generation_pair_visits'] + d['repair_pair_visits'] <= 24
    assert d['root_screen_attempts'] == 1 and d['repair_screen_attempts'] == 2
    assert d['effective_preliminary_decision_budget'] == d['evaluated_points_retained'] == 3
    assert rows[0]['preliminary_decision_screen']['focal']['starter_points_delta'] == -5
    assert rows[-1]['preliminary_decision_screen']['focal']['starter_points_delta'] == 2
    assert rows[-1]['repair_lineages'][0]['parent_point_id'] == rows[1]['point_id']
    assert all([a['asset_ref'] for a in r['receive']] == ['player:opp'] for r in rows)
    assert all(r['action_authority'] == 'diagnostic_only' for r in rows)
    assert d['changed_state_simulation_calls'] == d['forecast_or_intrinsic_recomputations'] == 0
    assert runtime.league_state.model_dump(mode='json') == before


def test_existing_pool_repairs_are_not_evaluated_or_returned_twice(monkeypatch):
    runtime, read, calls, _ = setup(monkeypatch, duplicates=True)
    result = module.build_strategic_discovery(runtime, StrategicDiscoveryRequest(), read=read)
    d = result['diagnostics']
    assert len(calls) == len(set(calls)) == 3
    assert len(result['candidate_packages']) == 3
    assert d['repair_existing_pool_points'] == 2
    assert d['candidate_pool_unique_count'] == d['generated_candidate_pool_unique_count'] == 3


@pytest.mark.parametrize('limit', [0, 1, 2])
def test_small_screen_or_return_limits_do_not_create_hidden_repairs(monkeypatch, limit):
    runtime, read, calls, generation = setup(monkeypatch)
    result = module.build_strategic_discovery(runtime,
        StrategicDiscoveryRequest(max_candidates=max(1, limit), evaluation_budget=limit), read=read)
    assert result['diagnostics']['repair_visit_budget'] == 0
    assert len(calls) <= limit
    assert len(result['candidate_packages']) <= max(1, limit)


def test_source_failure_keeps_diagnostic_parent_and_stops_second_step(monkeypatch):
    runtime, read, calls, _ = setup(monkeypatch, fail_repair=True)
    result = module.build_strategic_discovery(runtime, StrategicDiscoveryRequest(), read=read)
    rows = result['candidate_packages']
    assert result['diagnostics']['preliminary_decision_errors'] == 1
    assert len(calls) == 2 and rows[1]['evidence_status'] == 'screen_unavailable'
    assert rows[1]['repair_lineages'][0]['root_point_id'] == rows[0]['point_id']


def test_request_protection_excludes_every_alternative_without_new_visits(monkeypatch):
    runtime, read, calls, _ = setup(monkeypatch)
    request = StrategicDiscoveryRequest(search_instructions={'objectives': ['current_competitiveness'],
        'protected_player_ids': ['reserve', 'starter']})
    result = module.build_strategic_discovery(runtime, request, read=read)
    assert result['diagnostics']['repair_screen_attempts'] == 0
    assert result['diagnostics']['repair_pair_visits'] == 0
    assert len(calls) == 1


def test_unused_repair_screens_backfill_independent_roots(monkeypatch):
    runtime, read, calls, _ = setup(monkeypatch, extra_roots=True)
    request = StrategicDiscoveryRequest(evaluation_budget=3, search_instructions={
        'objectives': ['current_competitiveness'], 'protected_player_ids': ['reserve', 'starter']})
    result = module.build_strategic_discovery(runtime, request, read=read)
    assert result['diagnostics']['root_screen_attempts'] == len(calls) == 3
    assert result['diagnostics']['repair_screen_attempts'] == 0
    assert result['diagnostics']['repair_visit_budget'] > 0
    assert result['diagnostics']['repair_pair_visits'] == 0
