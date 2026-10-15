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
