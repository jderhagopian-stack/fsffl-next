from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import isfinite

import pytest

from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler, shadow_compare


@pytest.mark.parametrize("horizon,anchor", [("career", 2000.0), ("three_year", 750.0)])
@pytest.mark.parametrize("curve", ["linear", "sqrt"])
def test_endpoints_monotonic_and_bounded(horizon, anchor, curve):
    ruler = MagnitudeRuler(horizon, anchor, curve, "research-only-reference-v0")
    points = [-100, 0, anchor / 100, anchor / 4, anchor / 2, anchor, anchor * 2]
    scores = [ruler.score(value) for value in points]
    assert scores == sorted(scores)
    assert scores[0] == 0
    assert scores[-1] == 10000
    assert all(isfinite(value) and 0 <= value <= 10000 for value in scores)


@pytest.mark.parametrize("curve", ["linear", "sqrt"])
def test_values_do_not_change_when_reference_population_expands(curve):
    ruler = MagnitudeRuler("career", 2000, curve, "fixed-historical-v0")
    original = shadow_compare({"a": 200, "b": 1000, "missing": None}, ruler=ruler)
    expanded = shadow_compare(
        {"a": 200, "b": 1000, "missing": None, "new": 1, "another": 2},
        ruler=ruler,
    )
    assert original == {key: expanded[key] for key in original}
    assert original["missing"] is None


def test_fixed_difference_is_not_rank_based():
    ruler = MagnitudeRuler("career", 2000, "linear", "fixed-historical-v0")
    assert ruler.score(100) == 500
    assert ruler.score(500) == 2500
    assert ruler.score(1000) == 5000


def test_raw_input_not_mutated_and_ruler_is_frozen():
    inputs = {"a": 100.0, "b": None}
    ruler = MagnitudeRuler("three_year", 750, "sqrt", "fixed-historical-v0")
    _ = shadow_compare(inputs, ruler=ruler)
    assert inputs == {"a": 100.0, "b": None}
    with pytest.raises(FrozenInstanceError):
        ruler.anchor = 850


def test_provenance_and_horizon_change_fingerprint():
    a = MagnitudeRuler("career", 2000, "sqrt", "v1")
    b = MagnitudeRuler("career", 2000, "sqrt", "v2")
    c = MagnitudeRuler("three_year", 2000, "sqrt", "v1")
    assert len(a.fingerprint) == 64
    assert len({a.fingerprint, b.fingerprint, c.fingerprint}) == 3


@pytest.mark.parametrize("invalid", [0, -1, float("inf"), float("nan")])
def test_invalid_anchors_rejected(invalid):
    with pytest.raises(ValueError):
        MagnitudeRuler("career", invalid, "linear", "v1")


@pytest.mark.parametrize("invalid", [float("inf"), float("nan")])
def test_invalid_raw_values_rejected(invalid):
    ruler = MagnitudeRuler("career", 2000, "sqrt", "v1")
    with pytest.raises(ValueError):
        ruler.score(invalid)


def test_missing_reference_version_rejected():
    with pytest.raises(ValueError):
        MagnitudeRuler("career", 2000, "linear", " ")
