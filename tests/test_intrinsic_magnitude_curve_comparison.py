import pytest
from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler

CURVES = ("linear", "sqrt", "power_075", "piecewise")

@pytest.mark.parametrize("curve", CURVES)
@pytest.mark.parametrize("horizon,anchor", (("three_year", 750.0), ("career", 2000.0)))
def test_monotone_continuous_and_bounded(curve, horizon, anchor):
    ruler = MagnitudeRuler(horizon, anchor, curve, "diagnostic-v1")
    samples = [anchor * n / 1000 for n in range(1001)]
    values = [ruler.score(x) for x in samples]
    assert values == sorted(values)
    assert values[0] == 0
    assert values[-1] == 10000
    assert ruler.score(anchor * 2) == 10000
    assert max(b-a for a,b in zip(values, values[1:])) < 325

@pytest.mark.parametrize("curve", CURVES)
def test_fixed_reference_population_invariance(curve):
    ruler = MagnitudeRuler("career", 2000, curve, "fixed-v1")
    observed = ruler.score(450)
    for new_population_size in (10, 335, 3000):
        _ = [ruler.score(i) for i in range(new_population_size)]
        assert ruler.score(450) == observed

def test_distinct_candidate_shapes():
    score = {curve: MagnitudeRuler("career", 2000, curve, "fixed-v1").score(500) for curve in CURVES}
    assert score["sqrt"] > score["power_075"] > score["linear"]
    assert score["piecewise"] > 0
