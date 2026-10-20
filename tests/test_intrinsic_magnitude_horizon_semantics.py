"""Acceptance checks that retain the distinct meaning of each valuation horizon.

These are illustrative raw-value fixtures, not claims about any named player.
Presentation must not force cross-horizon ordering or change accepted raw models.
"""
from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler


def test_productive_veteran_can_have_higher_three_year_than_career_display():
    near = MagnitudeRuler("three_year", 750, "sqrt", "research-v0")
    career = MagnitudeRuler("career", 2000, "sqrt", "research-v0")
    # Productive veteran RB: nearly all remaining career modeled near term.
    assert near.score(335.3) > career.score(389.9)
    assert career.score(389.9) > 0


def test_young_long_horizon_prospect_can_have_higher_career_display():
    near = MagnitudeRuler("three_year", 750, "sqrt", "research-v0")
    career = MagnitudeRuler("career", 2000, "sqrt", "research-v0")
    # Young QB: weak 3-year, much of remaining contribution in later seasons.
    assert career.score(369.6) > near.score(31.3)


def test_cross_horizon_score_is_not_raw_arithmetic():
    near = MagnitudeRuler("three_year", 750, "sqrt", "research-v0")
    career = MagnitudeRuler("career", 2000, "sqrt", "research-v0")
    # The longer horizon can have higher raw cumulative contribution,
    # without requiring a numerically higher normalized display score.
    assert 493 > 220
    assert career.score(493) < near.score(220)


def test_horizon_score_is_independent_of_other_horizon():
    three = MagnitudeRuler("three_year", 750, "linear", "research-v0")
    career = MagnitudeRuler("career", 2000, "linear", "research-v0")
    original_three = three.score(220)
    original_career = career.score(493)
    assert three.score(220) == original_three
    assert career.score(493) == original_career
    # A new long-term estimate does not change the near-term coordinate.
    assert career.score(800) != original_career
    assert three.score(220) == original_three
