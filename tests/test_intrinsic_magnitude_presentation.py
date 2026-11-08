from copy import deepcopy

import pytest

from fsffl.product.career_presentation import CareerPresentationCoordinate
from fsffl.product.foundation4_shadow_inputs import FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
from fsffl.product.intrinsic_presentation import (
    INTRINSIC_MAGNITUDE_VERSION, intrinsic_magnitude_coordinate, reproject_published_intrinsic,
)
from fsffl.state.models import LeagueRules, LineupRequirement, RosterSlot, ScoringRule


def supported_rules():
    return LeagueRules(
        team_count=12, roster_size=24,
        lineup=tuple(LineupRequirement(slot=RosterSlot(slot), count=count) for slot, count in (
            ("QB", 1), ("RB", 2), ("WR", 3), ("TE", 1), ("FLEX", 1), ("SUPERFLEX", 1),
        )), scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    )


@pytest.mark.parametrize("horizon,anchor", [("three_year", 750), ("career", 2200)])
def test_fixed_magnitudes_preserve_ratios_and_do_not_move_with_reference_population(horizon, anchor):
    ruler = intrinsic_magnitude_coordinate(supported_rules(), horizon)
    assert ruler is not None
    assert ruler.index(anchor / 4) == 2500
    assert ruler.index(anchor / 2) == 5000
    assert ruler.index(-5) == 0
    assert ruler.index(None) is None
    assert ruler.index(float("nan")) is None
    assert ruler.index(float("inf")) is None
    assert ruler.index(anchor) == 10000 and not ruler.overflow(anchor)
    assert ruler.index(anchor + 1) == 10000 and ruler.overflow(anchor + 1)
    first = CareerPresentationCoordinate.from_reference(
        {"a": 10, "b": 100}, reference_ids=frozenset({"a", "b"}), magnitude=ruler,
    )
    expanded = CareerPresentationCoordinate.from_reference(
        {"a": 10, "b": 100, "new": 4000}, reference_ids=frozenset({"a", "b", "new"}), magnitude=ruler,
    )
    assert first.index(100) == expanded.index(100) == ruler.index(100)
    assert first.fingerprint == expanded.fingerprint
    assert first.summary()["version"] == INTRINSIC_MAGNITUDE_VERSION


def test_references_do_not_leak_into_other_scoring_or_lineup_economies():
    rules = supported_rules()
    assert intrinsic_magnitude_coordinate(rules, "career")
    assert intrinsic_magnitude_coordinate(rules.model_copy(update={"team_count": 10}), "career") is None
    changed_scoring = tuple(ScoringRule(stat=r.stat, points=1) if r.stat == "rec" else r for r in rules.scoring)
    assert intrinsic_magnitude_coordinate(rules.model_copy(update={"scoring": changed_scoring}), "three_year") is None


def test_saved_raw_projection_is_pure_versioned_and_does_not_impute_missing_rows():
    old = {
        "publication_generation_id": "saved-generation", "league_state_id": "saved-state",
        "career_intrinsic": {"status": "ready"}, "fsffl_intrinsic": {"status": "ready"},
        "players": [
            {"player_id": "p", "three_year_raw_intrinsic_value": 375,
             "raw_career_forward_reference": 2300, "intrinsic_value_index": 99,
             "career_intrinsic_index": 88, "broad_market_value_index": 123,
             "value_index_gap": 76},
            {"player_id": "missing", "three_year_raw_intrinsic_value": None,
             "raw_career_forward_reference": None, "intrinsic_value_index": None},
        ],
    }
    original = deepcopy(old)
    new = reproject_published_intrinsic(old, supported_rules())
    assert old == original
    assert new["publication_generation_id"] == old["publication_generation_id"]
    assert new["players"][0]["intrinsic_value_index"] == 5000
    assert new["players"][0]["career_intrinsic_index"] == 10000
    assert new["players"][0]["career_index_overflow"] is True
    assert new["players"][0]["raw_career_forward_reference"] == 2300
    assert new["players"][0]["broad_market_value_index"] == 123
    assert new["players"][0]["value_index_gap"] is None
    assert new["players"][1]["intrinsic_value_index"] is None
    assert new["players"][1]["career_intrinsic_index"] is None
    assert new["intrinsic_display"]["career"]["reference_raw"] == 2200
    assert reproject_published_intrinsic(new, supported_rules()) == new


def test_value_lens_route_uses_same_fixed_rulers_without_market_shape(monkeypatch):
    from types import SimpleNamespace as N
    from fastapi import FastAPI
    from fsffl.product import league_value_lens_routes as routes
    monkeypatch.setattr(routes, "career_reference_player_ids", lambda: frozenset({"a", "b"}))
    monkeypatch.setattr(routes, "build_three_year_intrinsic_player_values", lambda *args, **kwargs: (
        N(player_id="a", raw_intrinsic_value=75.), N(player_id="b", raw_intrinsic_value=150.),
    ))
    record = N(status=N(value="completed"), league_state_id="S", contract=N(
        player_input_assumptions={}, estimates=(
            N(player_id="a", raw_career_forward_reference=220.),
            N(player_id="b", raw_career_forward_reference=440.),
        )))
    runtime = N(league_state=N(state_id="S", league=N(rules=supported_rules())),
                publication_generation_id="G", forecast_evidence=object(), value_evidence=None)
    saved = {"league_state_id": "S", "publication_generation_id": "G",
             "fsffl_intrinsic": {}, "players": [{"player_id": "a"}, {"player_id": "b"}]}
    app = FastAPI()
    routes.install_league_value_lens_routes(
        app, runtime_store=N(get=lambda user: runtime), contract_loader=lambda runtime: None,
        require_user=lambda: "u", career_record_loader=lambda runtime: record,
        background_coordinator=N(completed_player_ids_for_state=lambda runtime: frozenset({"a", "b"})),
        presentation_payload_loader=lambda *args: saved,
    )
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/league/value-lenses")
    result = endpoint(user_id="u")
    assert [r["intrinsic_value_index"] for r in result["players"]] == [1000., 2000.]
    assert [r["career_intrinsic_index"] for r in result["players"]] == [1000., 2000.]
    assert result["career_intrinsic"]["presentation"]["version"] == INTRINSIC_MAGNITUDE_VERSION
    assert result["fsffl_intrinsic"]["presentation"]["version"] == INTRINSIC_MAGNITUDE_VERSION
    assert all(r["value_index_gap"] is None for r in result["players"])


def test_player_card_uses_career_owned_three_year_raw_and_same_career_reference(monkeypatch):
    from types import SimpleNamespace as N
    from fastapi import FastAPI
    from fsffl.product import player_intelligence_routes as routes
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability
    monkeypatch.setattr(routes, "career_reference_ids_from_current", lambda record: frozenset({"a", "b"}))
    monkeypatch.setattr(routes, "build_player_intelligence_overview", lambda *args, **kwargs: {
        "value": {"raw_shapley_marginal_points": 999, "intrinsic_value_index": 888},
    })
    monkeypatch.setattr(routes, "build_three_year_intrinsic_player_values", lambda *args, **kwargs: (
        N(player_id="a", raw_intrinsic_value=75.), N(player_id="b", raw_intrinsic_value=150.),
    ))
    current = N(status=IntrinsicBuildStatus.COMPLETED, contract=N(
        status=ShapleyIntrinsicAvailability.READY, estimates=(N(player_id="a"), N(player_id="b")),
        status_reason=None,
    ))
    career = N(status=IntrinsicBuildStatus.COMPLETED, league_state_id="S", contract=N(
        player_input_assumptions={}, estimates=(N(player_id="a", raw_career_forward_reference=220.),
                                               N(player_id="b", raw_career_forward_reference=440.)),
    ))
    runtime = N(league_state=N(state_id="S", league=N(rules=supported_rules())),
                publication_generation_id="G")
    app = FastAPI()
    routes.install_player_intelligence_routes(
        app, runtime_store=N(get=lambda user: runtime), require_user=lambda: "u",
        intrinsic_coordinator=N(current=lambda runtime: current),
        career_record_loader=lambda runtime: career, future_cache=N(), history_coordinator=N(),
    )
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/player-intelligence/{player_id}")
    result = endpoint(player_id="a", user_id="u")
    assert result["value"]["intrinsic_value_index"] == 1000
    assert result["value"]["career_intrinsic_index"] == 1000
    assert result["value"]["three_year_raw_intrinsic_value"] == 75
    assert result["value"]["raw_career_forward_reference"] == 220
    assert result["value"]["intrinsic_presentation"]["version"] == INTRINSIC_MAGNITUDE_VERSION
