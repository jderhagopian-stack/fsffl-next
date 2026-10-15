import pytest
from fsffl.product.career_presentation import CareerPresentationCoordinate


def test_career_own_reference_ruler_is_independent_of_dynamic_roster_and_market():
    reference_ids = frozenset({'a', 'b', 'c', 'd'})
    raw = {'a': -5., 'b': 10., 'c': 10., 'd': 100.}
    ruler = CareerPresentationCoordinate.from_reference(raw, reference_ids=reference_ids)
    expanded = CareerPresentationCoordinate.from_reference({**raw, 'new': 5000.}, reference_ids=reference_ids)
    assert expanded == ruler
    assert ruler.index(-5.) == 0
    assert ruler.index(10.) == 5000
    assert ruler.index(100.) == 10000
    assert ruler.index(55.) == 7500
    assert ruler.index(-100.) == 0
    assert ruler.index(1000.) == 10000
    assert ruler.index(None) is None
    assert ruler.index(float('nan')) is None
    assert ruler.fingerprint == expanded.fingerprint
    assert ruler.summary()['market_inputs_used'] is False
    assert raw == {'a': -5., 'b': 10., 'c': 10., 'd': 100.}


def test_missing_reference_is_explicit_not_replaced_by_roster_distribution():
    with pytest.raises(ValueError, match='incomplete'):
        CareerPresentationCoordinate.from_reference({'a': 5.}, reference_ids=frozenset({'a', 'b'}))
    with pytest.raises(ValueError, match='finite'):
        CareerPresentationCoordinate((('a', 1.), ('b', float('inf'))))
    tied = CareerPresentationCoordinate((('a', 5.), ('b', 5.)))
    assert tied.index(5.) == 5000


def test_product_overlay_preserves_other_lenses_and_rejects_last_good_state(monkeypatch):
    from types import SimpleNamespace
    from fsffl.product.career_presentation import attach_career_player_lenses
    monkeypatch.setattr('fsffl.product.career_presentation.career_reference_player_ids',
                        lambda: frozenset({'a', 'b'}))
    record = SimpleNamespace(status=SimpleNamespace(value='completed'), league_state_id='new',
        contract=SimpleNamespace(estimates=(SimpleNamespace(player_id='a',raw_career_forward_reference=-5.),
                                          SimpleNamespace(player_id='b',raw_career_forward_reference=15.))))
    payload = {'league_state_id':'new', 'fsffl_intrinsic':{'status':'ready'},
        'players':[{'player_id':'a','intrinsic_value_index':7777.,'broad_market_value_index':3333.},
                   {'player_id':'outside','intrinsic_value_index':10.}]}
    result = attach_career_player_lenses(payload, record=record, current_state_id='new')
    first, missing = result['players']
    assert first['intrinsic_value_index'] == 7777
    assert first['broad_market_value_index'] == 3333
    assert first['career_intrinsic_index'] == 0
    assert first['raw_career_forward_reference'] == -5.
    assert missing['career_intrinsic_index'] is None
    assert result['fsffl_intrinsic']['label'] == '3-Year Intrinsic'
    assert 'career_intrinsic_index' not in payload['players'][0]
    stale = {**payload, 'presentation_continuity': {'served_league_state_id':'old'}}
    result = attach_career_player_lenses(stale, record=record, current_state_id='new')
    assert result['career_intrinsic']['status'] == 'unavailable'
    assert all(row['career_intrinsic_index'] is None for row in result['players'])


def test_same_state_old_generation_is_not_relabelled_as_current_career(monkeypatch):
    from types import SimpleNamespace
    from fsffl.product.career_presentation import attach_career_player_lenses
    monkeypatch.setattr('fsffl.product.career_presentation.career_reference_player_ids',
                        lambda: frozenset({'a', 'b'}))
    record = SimpleNamespace(status=SimpleNamespace(value='completed'), league_state_id='same-state',
        intrinsic_input_fingerprint='dependency-fp', contract=SimpleNamespace(
            input_fingerprint='economic-fp',model_version='accepted-model',contract_version='contract-v1',
            estimates=(SimpleNamespace(player_id='a',raw_career_forward_reference=1.),
                       SimpleNamespace(player_id='b',raw_career_forward_reference=2.))))
    payload = {'league_state_id':'same-state','publication_generation_id':'old',
               'players':[{'player_id':'a'}]}
    old = attach_career_player_lenses(payload,record=record,current_state_id='same-state',current_generation_id='new')
    assert old['publication_generation_id'] == 'old'
    assert old['career_intrinsic']['status'] == 'unavailable'
    assert old['players'][0]['career_intrinsic_index'] is None
    current = attach_career_player_lenses({**payload,'publication_generation_id':'new'},
        record=record,current_state_id='same-state',current_generation_id='new')
    summary = current['career_intrinsic']
    assert summary['input_fingerprint'] == 'economic-fp'
    assert summary['dependency_fingerprint'] == 'dependency-fp'
    assert summary['presentation']['input_fingerprint'] != 'economic-fp'
    assert summary['presentation']['market_inputs_used'] is False
    assert current['players'][0]['career_intrinsic_index'] == 0


def test_partial_reference_does_not_recalibrate_on_available_career_rows(monkeypatch):
    from types import SimpleNamespace
    from fsffl.product.career_presentation import career_lens_for_publication, career_reference_ids_from_current
    monkeypatch.setattr('fsffl.product.career_presentation.career_reference_player_ids',
                        lambda: frozenset({'a', 'b', 'c'}))
    current = SimpleNamespace(status=SimpleNamespace(value='completed'),contract=SimpleNamespace(
        estimates=tuple(SimpleNamespace(player_id=key) for key in ('a','b','c'))))
    expected = career_reference_ids_from_current(current)
    record = SimpleNamespace(status=SimpleNamespace(value='completed'),league_state_id='S',
        contract=SimpleNamespace(estimates=(SimpleNamespace(player_id='a',raw_career_forward_reference=1.),
                                           SimpleNamespace(player_id='b',raw_career_forward_reference=2.))))
    summary, rows = career_lens_for_publication(record,served_state_id='S',reference_ids=expected)
    assert summary['status'] == 'unavailable'
    assert 'incomplete' in summary['reason']
    assert rows == {}


def test_unversioned_saved_value_payload_is_not_promoted_to_current_career():
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fsffl.product.league_value_lens_routes import install_league_value_lens_routes
    runtime = SimpleNamespace(league_state=SimpleNamespace(state_id='S'),
                              publication_generation_id='current',forecast_evidence=object())
    saved = {'league_state_id':'S','players':[{'player_id':'a','intrinsic_value_index':100.}]}
    calls = []
    app = FastAPI()
    install_league_value_lens_routes(app,runtime_store=SimpleNamespace(get=lambda _:runtime),
        contract_loader=lambda _:calls.append('build'),require_user=lambda:'fixture',
        background_coordinator=SimpleNamespace(current=lambda _:calls.append('current')),
        career_record_loader=lambda _:calls.append('career'),
        presentation_payload_loader=lambda *_:saved)
    endpoint = next(route.endpoint for route in app.routes if route.path=='/api/league/value-lenses')
    result = endpoint(user_id='fixture')
    assert result.get('publication_generation_id') is None
    assert result['career_intrinsic']['status'] == 'unavailable'
    assert result['players'][0]['career_intrinsic_index'] is None
    assert result['players'][0]['intrinsic_value_index'] == 100.
    assert calls == []
