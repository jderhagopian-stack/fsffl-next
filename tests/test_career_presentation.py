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
