from __future__ import annotations

import pytest

from fsffl.team_utility.simulation import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    compare_counterfactual_simulation_results,
    simulate_regular_season,
    _settings_derived_playoff_rules,
)


def _request(
    *,
    mean_a: float = 110.0,
    mean_b: float = 100.0,
    std_a: float = 12.0,
    std_b: float = 10.0,
    seed: int = 77,
    playoff: bool = False,
    playoff_std_a: float = 11.0,
    playoff_std_b: float = 9.0,
) -> RegularSeasonSimulationInput:
    rules = _settings_derived_playoff_rules(2, 15) if playoff else None
    playoff_rows = (
        (
            WeeklyTeamScoringDistribution(
                week=15,
                team_id="a",
                mean_points=mean_a,
                stddev_points=playoff_std_a,
                model_version="test-playoff",
            ),
            WeeklyTeamScoringDistribution(
                week=15,
                team_id="b",
                mean_points=mean_b,
                stddev_points=playoff_std_b,
                model_version="test-playoff",
            ),
        )
        if playoff
        else ()
    )
    return RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(
                team_id="a",
                mean_points=mean_a,
                stddev_points=std_a,
                model_version="test",
            ),
            TeamScoringDistribution(
                team_id="b",
                mean_points=mean_b,
                stddev_points=std_b,
                model_version="test",
            ),
        ),
        schedule=(
            ScheduledMatchup(
                week=1,
                home_team_id="a",
                away_team_id="b",
            ),
        ),
        playoff_team_count=2,
        playoff_rules=rules,
        playoff_weekly_scoring=playoff_rows,
        simulation_count=2_000,
        seed=seed,
        model_version="counterfactual-test-v1",
    )


def test_changed_strength_same_draw_topology_is_governed_common_world_comparison() -> None:
    baseline = simulate_regular_season(_request(mean_a=110.0))
    scenario = simulate_regular_season(_request(mean_a=125.0))

    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )

    assert baseline.common_world_regular_season_coordinate == (
        scenario.common_world_regular_season_coordinate
    )
    assert delta.regular_season_common_worlds is True
    assert delta.comparison_method == "common_random_numbers"
    assert "expected_wins" in delta.common_world_metrics
    assert "playoff_probability" in delta.common_world_metrics
    assert delta.postseason_common_worlds is False
    assert delta.postseason_unavailability_reason == "playoff_start_week_unavailable"


def test_same_seed_does_not_claim_common_worlds_when_draw_topology_changes() -> None:
    baseline = simulate_regular_season(_request(std_a=12.0))
    scenario = simulate_regular_season(_request(std_a=0.0))

    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )

    assert baseline.seed == scenario.seed
    assert baseline.common_world_regular_season_coordinate != (
        scenario.common_world_regular_season_coordinate
    )
    assert delta.regular_season_common_worlds is False
    assert delta.comparison_method == "aggregate_difference"
    assert delta.regular_season_unavailability_reason == (
        "regular_season_draw_topology_mismatch"
    )
    assert delta.common_world_metrics == ()


def test_replay_identity_mismatch_fails_common_world_claim_closed() -> None:
    baseline = simulate_regular_season(_request(seed=77))
    scenario = simulate_regular_season(_request(seed=78))

    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )

    assert delta.regular_season_common_worlds is False
    assert delta.regular_season_unavailability_reason == "seed_mismatch"


def test_uniform_postseason_draw_topology_supports_common_world_title_delta() -> None:
    baseline = simulate_regular_season(_request(playoff=True, mean_a=110.0))
    scenario = simulate_regular_season(_request(playoff=True, mean_a=125.0))

    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )

    assert baseline.common_world_postseason_coordinate is not None
    assert baseline.common_world_postseason_coordinate == (
        scenario.common_world_postseason_coordinate
    )
    assert delta.regular_season_common_worlds is True
    assert delta.postseason_common_worlds is True
    assert delta.championship_comparison_method == "common_random_numbers"
    assert "championship_probability" in delta.common_world_metrics


def test_mixed_postseason_stochasticity_withholds_common_world_title_claim() -> None:
    baseline = simulate_regular_season(
        _request(playoff=True, playoff_std_a=0.0, playoff_std_b=9.0)
    )
    scenario = simulate_regular_season(
        _request(
            playoff=True,
            mean_a=125.0,
            playoff_std_a=0.0,
            playoff_std_b=9.0,
        )
    )

    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )

    assert baseline.common_world_postseason_coordinate is None
    assert baseline.common_world_postseason_unavailability_reason == (
        "mixed_deterministic_stochastic_playoff_draws"
    )
    assert delta.regular_season_common_worlds is True
    assert delta.postseason_common_worlds is False
    assert delta.championship_comparison_method == "aggregate_difference"
    assert delta.postseason_unavailability_reason == (
        "mixed_deterministic_stochastic_playoff_draws"
    )


def test_counterfactual_delta_is_exact_aggregate_difference_regardless_of_pairing_label() -> None:
    baseline = simulate_regular_season(_request(mean_a=110.0))
    scenario = simulate_regular_season(_request(mean_a=120.0))
    delta = compare_counterfactual_simulation_results(
        baseline,
        scenario,
        team_id="a",
    )
    before = next(row for row in baseline.outcomes if row.team_id == "a")
    after = next(row for row in scenario.outcomes if row.team_id == "a")

    assert delta.expected_wins == pytest.approx(after.expected_wins - before.expected_wins)
    assert delta.playoff_probability == pytest.approx(
        (after.playoff_probability or 0.0) - (before.playoff_probability or 0.0)
    )
