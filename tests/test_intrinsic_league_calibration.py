from fsffl.product.intrinsic_league_calibration import (
    CalibrationReference, configuration_fingerprint, resolve_league_calibration,
)


def rules(superflex=False):
    return {
        "team_count": 12,
        "scoring": {"reception": 1},
        "starting_slots": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "SUPERFLEX": int(superflex)},
        "roster_slots": 24,
    }


def test_league_specific_reference_is_selected_only_for_matching_rules():
    one = configuration_fingerprint(rules())
    registry = {one: CalibrationReference(one, 750, 2200, "reference-v1", "approved")}
    result = resolve_league_calibration(rules(), registry)
    assert result is not None
    three, career = result
    assert three.score(375) == 5000
    assert career.score(1100) == 5000
    assert resolve_league_calibration(rules(superflex=True), registry) is None


def test_unknown_league_fails_closed():
    assert resolve_league_calibration(rules(), {}) is None
