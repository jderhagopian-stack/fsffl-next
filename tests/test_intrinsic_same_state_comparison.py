import pytest
from fsffl.product.intrinsic_same_state_comparison import compare_same_state


def fixture():
    state, cutoff = "state-a", "cutoff-a"
    return {
        "league_state_id": state, "forecast_cutoff": cutoff,
        "curve": "sqrt", "anchors": {"three_year": 750, "career": 2000},
        "reference_version": "diagnostic-only-v0",
        "three_year": {"league_state_id": state, "forecast_cutoff": cutoff, "players": {"a": {"raw": 100}, "b": {"raw": None}}},
        "career": {"league_state_id": state, "forecast_cutoff": cutoff, "players": {"a": {"raw": 300}, "b": {"raw": 20}}},
        "published": {"league_state_id": state, "forecast_cutoff": cutoff, "players": {"a": {"name": "Example", "position": "RB", "three_year": 1000, "career": 2000}, "b": {"name": "Unsupported", "position": "WR"}}},
    }


def test_valid_same_state_generates_complete_and_unsupported_ledger():
    result = compare_same_state(fixture())
    assert result["player_count"] == 2
    assert result["complete_count"] == 1
    assert result["rows"][0]["status"] == "complete"
    assert result["rows"][1]["status"] == "unsupported_raw"
    assert result["rows"][1]["shadow_three_year"] is None


@pytest.mark.parametrize("source", ["three_year", "career", "published"])
def test_mismatched_state_refused(source):
    case = fixture()
    case[source]["league_state_id"] = "other"
    with pytest.raises(ValueError, match="mismatch"):
        compare_same_state(case)


@pytest.mark.parametrize("source", ["three_year", "career", "published"])
def test_mismatched_cutoff_refused(source):
    case = fixture()
    case[source]["forecast_cutoff"] = "other"
    with pytest.raises(ValueError, match="mismatch"):
        compare_same_state(case)


def test_new_player_remains_explicit_missing_source():
    case = fixture()
    case["career"]["players"]["only-career"] = {"raw": 40}
    result = compare_same_state(case)
    row = next(x for x in result["rows"] if x["player_id"] == "only-career")
    assert row["status"] == "missing_source"
    assert set(row["missing"]) == {"three_year", "published"}
