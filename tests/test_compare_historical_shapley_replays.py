from scripts.compare_historical_shapley_replays import compare


def _inputs():
    old = {"observed_years": [{"season": 2003}, {"season": 2004}], "cohorts": [{"start_season": 2003, "players": [
        {"id": "p", "annual_shapley_hindsight": [12.5, None]}]}]}
    new = {"years": [2003, 2004], "evidence_kind": "hindsight_production_shapley_not_career_intrinsic",
           "cohorts": [{"start_season": 2003, "players": [
               {"player_id": "p", "annual_observed_shapley": [12.5, None]}]}]}
    return old, new


def test_identical_player_level_and_null_parity():
    old, new = _inputs()
    assert compare(old, new)["status"] == "pass"


def test_detects_drift_and_missingness_instead_of_rubber_stamping():
    old, new = _inputs()
    new["cohorts"][0]["players"][0]["annual_observed_shapley"][0] = 12.6
    assert compare(old, new)["status"] == "fail"
    new["cohorts"][0]["players"][0]["annual_observed_shapley"][0] = 12.5
    new["cohorts"][0]["players"][0]["annual_observed_shapley"][1] = 0.0
    assert compare(old, new)["status"] == "fail"


def test_rejects_incomplete_player_universe():
    old, new = _inputs()
    new["cohorts"][0]["players"] = []
    assert compare(old, new)["status"] == "fail"
