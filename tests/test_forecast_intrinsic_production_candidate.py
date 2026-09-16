import math

import pytest

from fsffl.forecast.canonical_state import CanonicalFootballState, canonical_coverage_report
from fsffl.forecast.integrated_i1 import FROZEN_I1_REGULARIZATION, I1RegularizationPolicy, feature_dict
from fsffl.intrinsic.shapley import FROZEN_DISCOUNT, LeagueDeploymentRules, PlayerDeployment, career_intrinsic_value, deployment_shapley


def row(**overrides):
    base = dict(
        player_id="p1", position="WR", age_band="young", current_state="usable",
        horizon=1, current_fantasy_points=100.0, prior_fantasy_points=80.0,
        experience_years=2.0, role_band="established", opportunity_per_game=7.0,
        games=17.0, usage_evidence_coverage=True,
    )
    base.update(overrides)
    return CanonicalFootballState(**base)


def test_current_i1_policy_is_frozen_point_25_but_supports_governed_component_overrides():
    assert FROZEN_I1_REGULARIZATION.default_c == 0.25
    assert FROZEN_I1_REGULARIZATION.c_for("persistence.full") == 0.25
    future = I1RegularizationPolicy(default_c=0.25, component_c={"persistence.full": 0.4, "conditional.full": 0.2})
    assert future.c_for("persistence.full") == 0.4
    assert future.c_for("conditional.full") == 0.2
    assert future.c_for("persistence.reduced") == 0.25
    with pytest.raises(ValueError):
        I1RegularizationPolicy(default_c=0.0)


def test_missing_roster_evidence_fails_closed_into_reduced_feature_path():
    x = feature_dict(row(roster_evidence_coverage=False, active_share=None, released_share=None))
    assert x["r_cov"] == 0.0
    assert "active_share" not in x
    assert "released_share" not in x


def test_roster_coverage_flag_without_observed_roster_weeks_still_fails_closed():
    candidate = row(roster_evidence_coverage=True, roster_weeks=None, active_share=1.0)
    assert not candidate.has_full_i1_evidence
    assert "active_share" not in feature_dict(candidate)


def test_canonical_coverage_is_explicit_not_inferred():
    report = canonical_coverage_report((row(), row(player_id="p2", roster_evidence_coverage=True, roster_weeks=17.0)))
    assert report["players"] == 2
    assert report["full_i1_evidence"] == 1
    assert report["full_i1_evidence_share"] == 0.5


def test_unknown_experience_is_not_invented():
    x = feature_dict(row(experience_years=None))
    assert x["e=unknown"] == 1.0
    assert x["exp"] == 0.0


def test_shapley_is_roster_neutral_positive_and_deterministic():
    players = (
        PlayerDeployment("elite", "WR", 300.0),
        PlayerDeployment("ordinary", "WR", 150.0),
        PlayerDeployment("depth", "WR", 60.0),
        PlayerDeployment("qb", "QB", 250.0),
    )
    rules = LeagueDeploymentRules(team_count=1, direct_qb=1, direct_rb=0, direct_wr=1, direct_te=0, flex=0, superflex=0)
    a = deployment_shapley(players, rules, permutations=256, seed=20260914)
    b = deployment_shapley(players, rules, permutations=256, seed=20260914)
    assert a == b
    assert a["elite"] > a["ordinary"] > a["depth"] >= 0.0
    assert all(math.isfinite(v) for v in a.values())


def test_frozen_career_discount_cannot_be_silently_changed():
    assert career_intrinsic_value(10.0, (10.0, 10.0)) == pytest.approx(10 + FROZEN_DISCOUNT*10 + FROZEN_DISCOUNT**2*10)
    with pytest.raises(ValueError):
        career_intrinsic_value(10.0, (10.0,), discount=0.9)
