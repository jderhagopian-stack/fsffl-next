from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from fsffl.product.league_atlas import (
    LEAGUE_ATLAS_CONTRACT_VERSION,
    _frozen_preseason_rows,
    build_league_atlas_payload,
)
from fsffl.product.league_atlas_preseason import (
    LEAGUE_ATLAS_PRESEASON_MODEL_VERSION,
    LeagueAtlasPreseasonBaseline,
    LeagueAtlasPreseasonTeam,
    load_preseason_baseline,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    PickOwnership,
    Provenance,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 22, 20, tzinfo=UTC)


def _provenance() -> Provenance:
    return Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )


def _state() -> LeagueState:
    league_id = "league"
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Atlas Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                playoff_team_count=2,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id=league_id, display_name="Alpha"),
            Team(team_id="b", league_id=league_id, display_name="Beta"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(),
                max_points_for=250.25,
                max_points_for_provenance=_provenance(),
            ),
            TeamState(
                team_id="b",
                roster=(),
                max_points_for=230.50,
                max_points_for_provenance=_provenance(),
            ),
        ),
        players=(),
        player_states=(),
        draft_picks=(
            DraftPick(
                pick_id="2027-a-1",
                league_id=league_id,
                season=2027,
                round=1,
                original_team_id="a",
            ),
            DraftPick(
                pick_id="2027-b-1",
                league_id=league_id,
                season=2027,
                round=1,
                original_team_id="b",
            ),
            DraftPick(
                pick_id="2028-a-2",
                league_id=league_id,
                season=2028,
                round=2,
                original_team_id="a",
            ),
            DraftPick(
                pick_id="2028-b-3",
                league_id=league_id,
                season=2028,
                round=3,
                original_team_id="b",
            ),
        ),
        pick_ownership=(
            PickOwnership(pick_id="2027-a-1", owner_team_id="b"),
            PickOwnership(pick_id="2027-b-1", owner_team_id="b"),
            PickOwnership(pick_id="2028-a-2", owner_team_id="a"),
            PickOwnership(pick_id="2028-b-3", owner_team_id="a"),
        ),
        matchups=(
            LeagueMatchup(
                week=1,
                team_a_id="a",
                team_b_id="b",
                team_a_points=121.5,
                team_b_points=99.0,
                provenance=_provenance(),
            ),
            LeagueMatchup(
                week=2,
                team_a_id="a",
                team_b_id="b",
                team_a_points=110.0,
                team_b_points=110.0,
                provenance=_provenance(),
            ),
        ),
    )


def test_atlas_contract_aggregates_current_state_and_preserves_unavailable_layers() -> None:
    state = _state()
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
    )

    payload = build_league_atlas_payload(runtime)

    assert payload["contract_version"] == LEAGUE_ATLAS_CONTRACT_VERSION
    assert payload["league_state_id"] == state.state_id
    assert payload["last_completed_week"] == 2
    assert payload["managed_team_id"] == "a"

    standings = payload["standings"]
    assert [row["team_id"] for row in standings] == ["a", "b"]
    assert standings[0]["rank"] == 1
    assert standings[0]["wins"] == 1
    assert standings[0]["losses"] == 0
    assert standings[0]["ties"] == 1
    assert standings[0]["points_for"] == 231.5
    assert standings[0]["points_against"] == 209.0
    assert standings[0]["max_points_for"] == 250.25
    assert standings[0]["max_points_for_provenance"]["source"] == "fixture"

    assert payload["simulation"]["status"] == "unavailable"
    assert payload["simulation"]["teams"] == []
    assert "Simulation evidence" in payload["simulation"]["reason"]
    assert payload["preseason_expectation"]["status"] == "unavailable"
    assert payload["preseason_expectation"]["teams"] == []


def test_pick_map_preserves_true_owner_original_team_and_round_identity() -> None:
    state = _state()
    payload = build_league_atlas_payload(
        UserRuntimeContext(user_id="u", league_state=state, selected_team_id="a")
    )
    pick_map = payload["pick_map"]
    teams = {row["team_id"]: row for row in pick_map["teams"]}

    assert pick_map["seasons"] == [2027, 2028]
    assert pick_map["rounds"] == [1, 2, 3]

    alpha_owned = {row["pick_id"]: row for row in teams["a"]["owned"]}
    alpha_traded = {
        row["pick_id"]: row for row in teams["a"]["traded_away_original_picks"]
    }
    beta_owned = {row["pick_id"]: row for row in teams["b"]["owned"]}

    assert alpha_owned["2028-a-2"]["status"] == "own"
    assert alpha_owned["2028-b-3"]["status"] == "acquired"
    assert alpha_traded["2027-a-1"]["status"] == "traded_away"
    assert alpha_traded["2027-a-1"]["owner_team_id"] == "b"
    assert beta_owned["2027-a-1"]["original_team_id"] == "a"
    assert beta_owned["2027-a-1"]["status"] == "acquired"

    alpha_2028 = next(row for row in teams["a"]["by_year"] if row["season"] == 2028)
    assert alpha_2028["round_counts"] == {"1": 0, "2": 1, "3": 1}
    assert alpha_2028["total_picks"] == 2


def test_simulation_is_presented_without_recomputing_or_inventing_a_power_score() -> None:
    state = _state()
    outcomes = (
        SimpleNamespace(
            team_id="a",
            expected_wins=10.2,
            wins_stddev=1.4,
            playoff_probability=0.82,
            playoff_seed_probabilities=(0.55, 0.27),
            bye_probability=0.55,
            bye_unavailability_reason=None,
            first_place_probability=0.55,
            championship_probability=0.31,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
        SimpleNamespace(
            team_id="b",
            expected_wins=6.1,
            wins_stddev=1.5,
            playoff_probability=0.18,
            first_place_probability=0.08,
            championship_probability=0.04,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
    )
    finish = (
        SimpleNamespace(
            team_id="a",
            expected_finish=1.2,
            median_finish=1,
            rank_probabilities=(0.80, 0.20),
        ),
        SimpleNamespace(
            team_id="b",
            expected_finish=1.8,
            median_finish=2,
            rank_probabilities=(0.20, 0.80),
        ),
    )
    team_views = (
        SimpleNamespace(
            team_id="a",
            utility=SimpleNamespace(
                calculated_competitive_state=SimpleNamespace(value="contender")
            ),
        ),
        SimpleNamespace(
            team_id="b",
            utility=SimpleNamespace(
                calculated_competitive_state=SimpleNamespace(value="rebuilding")
            ),
        ),
    )
    simulation = SimpleNamespace(
        simulation_result=SimpleNamespace(
            outcomes=outcomes,
            finish_distributions=finish,
            simulation_count=50_000,
            model_version="sim-v1",
        ),
        team_views=team_views,
    )
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        simulation_analytics=cast(Any, simulation),
    )

    payload = build_league_atlas_payload(runtime)
    rows = {row["team_id"]: row for row in payload["simulation"]["teams"]}

    assert payload["simulation"]["status"] == "ready"
    assert payload["simulation"]["simulation_count"] == 50_000
    assert rows["a"]["playoff_probability"] == 0.82
    assert rows["a"]["playoff_seed_probabilities"] == [0.55, 0.27]
    assert rows["a"]["bye_probability"] == 0.55
    assert rows["a"]["expected_finish"] == pytest.approx(1.2)
    assert rows["a"]["median_finish"] == 1
    assert rows["a"]["finish_rank_probabilities"] == [0.80, 0.20]
    assert rows["a"]["competitive_state"] == "contender"
    assert rows["a"]["current_rank"] == 1
    assert rows["a"]["movement_vs_current_rank"] == pytest.approx(-0.2)

    authority = payload["authority"]
    assert authority["presentation_creates_model_truth"] is False
    assert authority["team_intrinsic_total_created"] is False
    assert authority["summed_market_percentiles_created"] is False
    assert authority["league_market_value_available"] is False
    assert authority["power_score_created"] is False
    assert authority["recommendation_strength_created"] is False
    assert authority["acceptance_probability_created"] is False


def test_atlas_route_uses_preserved_preseason_forecast_only_with_historical_state() -> None:
    from pathlib import Path

    webapp = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    persistent = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )

    assert '@application.get("/api/league/atlas")' in webapp
    assert "preseason_forecast_loader" in webapp
    assert "state_snapshot_store.latest_at_or_before" in webapp
    assert "preseason_state.league.season != league_state.league.season" in webapp
    assert "No exact pre-kickoff 2026 State can be proven" in webapp
    assert "historical TAXI/IR/active-slot moves" in webapp
    assert "completed_matchups(preseason_state)" in webapp
    assert "capture_preseason_baseline_if_eligible" in webapp
    assert "load_preseason_baseline" in webapp
    assert "_preseason_forecast_loader = make_preseason_baseline_authority_loader" in persistent
    assert "preseason_forecast_loader=_preseason_forecast_loader" in persistent
    assert "state_snapshot_store=_state_snapshot_store" in persistent
    assert "persistence_store=_persistence_store" in persistent

def test_future_zero_schedule_rows_do_not_create_ties_or_advance_current_rank() -> None:
    state = _state()
    future = LeagueMatchup(
        week=14,
        team_a_id="a",
        team_b_id="b",
        team_a_points=0.0,
        team_b_points=0.0,
        provenance=_provenance(),
    )
    state = state.model_copy(
        update={
            "matchups": state.matchups + (future,),
            "completed_through_week": 2,
        }
    )
    outcomes = (
        SimpleNamespace(
            team_id="a",
            expected_wins=10.2,
            wins_stddev=1.4,
            playoff_probability=0.82,
            first_place_probability=0.55,
            championship_probability=0.31,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
        SimpleNamespace(
            team_id="b",
            expected_wins=6.1,
            wins_stddev=1.5,
            playoff_probability=0.18,
            first_place_probability=0.08,
            championship_probability=0.04,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
    )
    finish = (
        SimpleNamespace(team_id="a", expected_finish=1.2),
        SimpleNamespace(team_id="b", expected_finish=1.8),
    )
    team_views = (
        SimpleNamespace(
            team_id="a",
            utility=SimpleNamespace(
                calculated_competitive_state=SimpleNamespace(value="contender")
            ),
        ),
        SimpleNamespace(
            team_id="b",
            utility=SimpleNamespace(
                calculated_competitive_state=SimpleNamespace(value="rebuilding")
            ),
        ),
    )
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        simulation_analytics=cast(
            Any,
            SimpleNamespace(
                simulation_result=SimpleNamespace(
                    outcomes=outcomes,
                    finish_distributions=finish,
                    simulation_count=50_000,
                    model_version="sim-v1",
                ),
                team_views=team_views,
            ),
        ),
    )

    payload = build_league_atlas_payload(runtime)

    assert payload["last_completed_week"] == 2
    standings = {row["team_id"]: row for row in payload["standings"]}
    assert standings["a"]["wins"] == 1
    assert standings["a"]["losses"] == 0
    assert standings["a"]["ties"] == 1
    assert standings["a"]["games"] == 2
    assert standings["a"]["points_for"] == 231.5
    assert standings["a"]["points_against"] == 209.0
    assert standings["a"]["rank"] == 1
    simulation = {row["team_id"]: row for row in payload["simulation"]["teams"]}
    assert simulation["a"]["current_rank"] == 1
    assert simulation["a"]["movement_vs_current_rank"] == pytest.approx(-0.2)


def test_legacy_state_with_trailing_zero_schedule_rows_fails_closed() -> None:
    state = _state()
    future = LeagueMatchup(
        week=14,
        team_a_id="a",
        team_b_id="b",
        team_a_points=0.0,
        team_b_points=0.0,
        provenance=_provenance(),
    )
    legacy = state.model_copy(update={"matchups": state.matchups + (future,)})

    payload = build_league_atlas_payload(
        UserRuntimeContext(user_id="u", league_state=legacy, selected_team_id="a")
    )

    assert legacy.completed_through_week is None
    assert payload["last_completed_week"] == 2
    standings = {row["team_id"]: row for row in payload["standings"]}
    assert standings["a"]["games"] == 2
    assert standings["a"]["ties"] == 1



def test_real_league_sanity_consumes_canonical_completed_week_without_hardcoding() -> None:
    source = Path("scripts/run_league_atlas_north_star_sanity.py").read_text(
        encoding="utf-8"
    )

    assert 'payload["last_completed_week"] != state.completed_through_week' in source
    assert 'state.completed_through_week != 2' not in source
    assert "live provider evidence proves Week 2 complete" not in source
    assert "governed completed-week boundary is Week {state.completed_through_week}" in source


def test_frozen_preseason_rows_preserve_postseason_unavailability_reasons() -> None:
    state = _state()
    baseline = LeagueAtlasPreseasonBaseline(
        league_id="league",
        season=2026,
        state_id=state.state_id,
        state_as_of=NOW,
        forecast_evaluation_as_of=NOW,
        forecast_model_version="forecast-v1",
        simulation_model_version="simulation-v1",
        simulation_count=50_000,
        opener_date="2026-09-10",
        opener_coordinate_source="fixture",
        teams=(
            LeagueAtlasPreseasonTeam(
                team_id="a",
                projected_starter_points=100.0,
                rank=1,
                playoff_probability=None,
                playoff_unavailability_reason="playoff_rules_unavailable",
                championship_probability=None,
                championship_unavailability_reason="playoff_rules_unavailable",
                first_place_probability=0.5,
                expected_wins=7.0,
                expected_finish=1.5,
            ),
        ),
    )

    row = _frozen_preseason_rows(state, baseline)[0]

    assert row["playoff_probability"] is None
    assert row["playoff_unavailability_reason"] == "playoff_rules_unavailable"
    assert row["championship_probability"] is None
    assert row["championship_unavailability_reason"] == "playoff_rules_unavailable"


def test_preseason_baseline_loader_requests_new_governed_postseason_version() -> None:
    class Store:
        request: dict[str, object] | None = None

        def get_latest_reusable_artifact(self, **kwargs):
            self.request = kwargs
            return None

    store = Store()
    assert load_preseason_baseline(store, state=_state()) is None
    assert store.request is not None
    assert store.request["model_version"] == LEAGUE_ATLAS_PRESEASON_MODEL_VERSION
    assert LEAGUE_ATLAS_PRESEASON_MODEL_VERSION != "phase3-league-atlas-preseason-v1"
