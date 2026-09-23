from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from fsffl.product.home_command_center import (
    HOME_COMMAND_CENTER_CONTRACT_VERSION,
    build_home_command_center_payload,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.state.models import (
    League,
    LeagueMatchup,
    LeagueRules,
    LeagueState,
    Provenance,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 23, 18, tzinfo=UTC)


def _provenance() -> Provenance:
    return Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )


def _state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id="home-league",
            name="Home Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=3,
                roster_size=1,
                playoff_team_count=2,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id="home-league", display_name="Alpha"),
            Team(team_id="b", league_id="home-league", display_name="Bravo"),
            Team(team_id="c", league_id="home-league", display_name="Charlie"),
        ),
        team_states=(
            TeamState(team_id="a", roster=(), max_points_for=300.0, max_points_for_provenance=_provenance()),
            TeamState(team_id="b", roster=(), max_points_for=280.0, max_points_for_provenance=_provenance()),
            TeamState(team_id="c", roster=(), max_points_for=260.0, max_points_for_provenance=_provenance()),
        ),
        players=(),
        player_states=(),
        draft_picks=(),
        pick_ownership=(),
        matchups=(
            LeagueMatchup(
                week=1,
                team_a_id="a",
                team_b_id="b",
                team_a_points=130.0,
                team_b_points=100.0,
                provenance=_provenance(),
            ),
            LeagueMatchup(
                week=1,
                team_a_id="c",
                team_b_id="a",
                team_a_points=120.0,
                team_b_points=110.0,
                provenance=_provenance(),
            ),
        ),
        completed_through_week=1,
    )


def _simulation() -> Any:
    outcomes = (
        SimpleNamespace(
            team_id="a",
            expected_wins=8.9,
            wins_stddev=1.2,
            playoff_probability=0.84,
            first_place_probability=0.33,
            championship_probability=0.14,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
        SimpleNamespace(
            team_id="b",
            expected_wins=6.4,
            wins_stddev=1.4,
            playoff_probability=0.44,
            first_place_probability=0.18,
            championship_probability=0.08,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
        SimpleNamespace(
            team_id="c",
            expected_wins=7.2,
            wins_stddev=1.3,
            playoff_probability=0.55,
            first_place_probability=0.22,
            championship_probability=0.10,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
    )
    finish = (
        SimpleNamespace(team_id="a", expected_finish=1.8),
        SimpleNamespace(team_id="b", expected_finish=2.4),
        SimpleNamespace(team_id="c", expected_finish=2.1),
    )
    views = tuple(
        SimpleNamespace(
            team_id=team_id,
            utility=SimpleNamespace(
                calculated_competitive_state=SimpleNamespace(value=state)
            ),
        )
        for team_id, state in (
            ("a", "contender"),
            ("b", "developing"),
            ("c", "competitive"),
        )
    )
    return SimpleNamespace(
        simulation_result=SimpleNamespace(
            outcomes=outcomes,
            finish_distributions=finish,
            simulation_count=50_000,
            model_version="sim-v1",
        ),
        team_views=views,
    )


def test_home_composition_reuses_matching_state_and_simulation_without_new_authority() -> None:
    state = _state()
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        simulation_analytics=cast(Any, _simulation()),
    )

    payload = build_home_command_center_payload(runtime)

    assert payload["contract_version"] == HOME_COMMAND_CENTER_CONTRACT_VERSION
    assert payload["league_state_id"] == state.state_id
    assert payload["managed_team_id"] == "a"
    assert payload["managed_standing"]["team_id"] == "a"
    assert payload["managed_standing"]["rank"] == 2
    assert payload["simulation"]["status"] == "ready"
    assert payload["simulation"]["simulation_count"] == 50_000
    assert payload["simulation"]["team"]["expected_wins"] == 8.9
    assert payload["simulation"]["team"]["playoff_probability"] == 0.84
    assert payload["simulation"]["team"]["championship_probability"] == 0.14
    assert payload["simulation"]["team"]["expected_finish"] == 1.8
    assert {row["rank"] for row in payload["around_the_league"]} == {1, 2, 3}

    authority = payload["authority"]
    assert authority["presentation_only"] is True
    assert authority["launches_opportunity_search"] is False
    assert authority["launches_decision_evaluation"] is False
    assert authority["launches_simulation"] is False
    assert authority["creates_master_score"] is False
    assert authority["creates_recommendation_authority"] is False
    assert authority["creates_value_blend"] is False


def test_home_fails_closed_when_matching_simulation_is_absent() -> None:
    state = _state()
    payload = build_home_command_center_payload(
        UserRuntimeContext(
            user_id="u",
            league_state=state,
            selected_team_id="a",
        )
    )

    assert payload["simulation"]["status"] == "unavailable"
    assert payload["simulation"]["team"] is None
    assert payload["simulation"]["simulation_count"] is None


def test_home_around_the_league_is_bounded_to_adjacent_standings() -> None:
    state = _state()
    payload = build_home_command_center_payload(
        UserRuntimeContext(
            user_id="u",
            league_state=state,
            selected_team_id="c",
            simulation_analytics=cast(Any, _simulation()),
        )
    )

    managed_rank = payload["managed_standing"]["rank"]
    assert all(
        abs(int(row["rank"]) - int(managed_rank)) <= 1
        for row in payload["around_the_league"]
    )
    assert len(payload["around_the_league"]) <= 3
