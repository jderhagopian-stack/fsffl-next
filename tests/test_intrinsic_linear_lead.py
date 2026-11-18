import pytest

from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler


@pytest.mark.parametrize("horizon,anchor", [("three_year", 750.0), ("career", 2000.0)])
def test_linear_preserves_raw_ratios_below_anchor(horizon, anchor):
    ruler = MagnitudeRuler(horizon, anchor, "linear", "historical-anchor-pending")
    for a, b in [(anchor / 10, anchor / 5), (anchor / 4, anchor / 2)]:
        assert ruler.score(b) / ruler.score(a) == pytest.approx(b / a)
        assert ruler.score(b) - ruler.score(a) == pytest.approx(10000 * (b-a) / anchor)


def test_clipping_is_explicit_and_missing_remains_missing():
    ruler = MagnitudeRuler("career", 2000.0, "linear", "historical-anchor-pending")
    assert ruler.score(2062.3) == 10000.0
    assert ruler.score(2000) == 10000.0
    assert ruler.score(None) is None
    assert ruler.score(-50) == 0


def test_different_horizon_anchors_do_not_imply_equal_raw_units():
    near = MagnitudeRuler("three_year", 750.0, "linear", "historical-anchor-pending")
    career = MagnitudeRuler("career", 2000.0, "linear", "historical-anchor-pending")
    assert near.score(375) == career.score(1000) == 5000
    assert 375 != 1000
