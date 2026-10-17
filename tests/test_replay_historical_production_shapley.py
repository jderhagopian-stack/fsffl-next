from scripts.replay_historical_production_shapley import fixture, replay


def test_full_year_pool_is_used_and_unobserved_future_is_not_zero_filled():
    panel = {
        2003: [("a", "QB", 300.), ("b", "RB", 200.)],
        2004: [("a", "QB", 240.), ("new", "RB", 230.)],
        2005: [("a", "QB", 220.), ("new", "RB", 190.)],
        2006: [("a", "QB", 200.)],
        2007: [("a", "QB", 170.)],
        2008: [("a", "QB", 150.)],
        2009: [("a", "QB", 100.)],
        2010: [("a", "QB", 80.)],
    }
    result = replay(panel, starts=(2003,), rules=fixture(), permutations=8)
    cohort = result["cohorts"][0]
    assert cohort["player_count"] == 2
    by_id = {x["player_id"]: x for x in cohort["players"]}
    assert by_id["a"]["three_year_hindsight"] is not None
    assert by_id["b"]["three_year_hindsight"] is None
    assert by_id["b"]["seven_year_hindsight"] is None
    assert result["evidence_kind"] == "hindsight_production_shapley_not_career_intrinsic"
    assert result["seed"] == 20260915
