from __future__ import annotations

import pytest

from fsffl.team_utility.simulation import (
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    PYTHON_RANDOM_GAUSS_V1,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    _settings_derived_playoff_rules,
    simulate_regular_season,
)


def _stochastic_request(
    *,
    rng_protocol: str,
    batch_size: int | None,
    mean_a: float = 120.0,
) -> RegularSeasonSimulationInput:
    team_ids = ("a", "b", "c", "d")
    means = {"a": mean_a, "b": 115.0, "c": 105.0, "d": 95.0}
    schedule = (
        ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),
        ScheduledMatchup(week=1, home_team_id="c", away_team_id="d"),
        ScheduledMatchup(week=2, home_team_id="a", away_team_id="c"),
        ScheduledMatchup(week=2, home_team_id="b", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="a", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="b", away_team_id="c"),
    )
    playoff_rules = _settings_derived_playoff_rules(4, 4)
    assert playoff_rules is not None
    return RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=team_id,
                mean_points=means[team_id],
                stddev_points=22.0,
                model_version="multiverse-test",
            )
            for team_id in team_ids
        ),
        playoff_weekly_scoring=tuple(
            WeeklyTeamScoringDistribution(
                week=week,
                team_id=team_id,
                mean_points=means[team_id],
                stddev_points=20.0,
                model_version="multiverse-playoff-test",
            )
            for week in playoff_rules.round_weeks
            for team_id in team_ids
        ),
        schedule=schedule,
        playoff_team_count=4,
        playoff_rules=playoff_rules,
        simulation_count=500,
        seed=20261002,
        model_version="multiverse-test-v1",
        rng_protocol=rng_protocol,
        rng_batch_size=batch_size,
    )


@pytest.mark.parametrize(
    ("rng_protocol", "batch_size"),
    (
        (PYTHON_RANDOM_GAUSS_V1, None),
        (NUMPY_PCG64_BATCHED_GAUSS_V1, 64),
    ),
)
def test_multiverse_examples_are_bounded_replayable_and_from_same_simulation(
    rng_protocol: str,
    batch_size: int | None,
) -> None:
    request = _stochastic_request(
        rng_protocol=rng_protocol,
        batch_size=batch_size,
    )

    first = simulate_regular_season(request)
    replay = simulate_regular_season(request)

    assert first.multiverse_worlds == replay.multiverse_worlds
    assert first.multiverse_model_version == "next4-multiverse-v1"
    assert 5 <= len(first.multiverse_worlds) <= 8
    categories = {world.category for world in first.multiverse_worlds}
    assert {
        "expected_like",
        "plausible_upside",
        "plausible_downside",
        "extreme_tail",
        "biggest_blowout",
        "low_seed_champion",
    }.issubset(categories)

    simulation_ids = {world.simulation_id for world in first.multiverse_worlds}
    assert len(simulation_ids) == 1
    world_id_by_index: dict[int, str] = {}
    for world in first.multiverse_worlds:
        if world.world_index in world_id_by_index:
            assert world_id_by_index[world.world_index] == world.world_id
        else:
            world_id_by_index[world.world_index] = world.world_id
        assert 0 <= world.world_index < request.simulation_count
        assert world.root_seed == request.seed
        assert world.rng_protocol == rng_protocol
        assert world.rng_runtime_version == first.rng_runtime_version
        assert world.rng_bit_generator == first.rng_bit_generator
        assert world.rng_batch_size == batch_size
        assert world.rng_draw_layout == first.rng_draw_layout
        assert world.rng_seed_derivation == first.rng_seed_derivation
        assert world.simulation_input_fingerprint == first.simulation_input_fingerprint
        assert world.rarity.sample_count == request.simulation_count
        assert len(world.standings) == 4
        assert len(world.team_outcomes) == 4
        assert {row.team_id for row in world.team_outcomes} == set(world.standings)

    expected_like = next(
        world for world in first.multiverse_worlds if world.category == "expected_like"
    )
    assert expected_like.rarity.basis == "representative_typicality"
    assert expected_like.rarity.label == "representative"
    assert expected_like.rarity.empirical_probability is None

    for category in ("plausible_upside", "plausible_downside", "extreme_tail"):
        world = next(
            item for item in first.multiverse_worlds if item.category == category
        )
        assert world.rarity.empirical_probability is not None
        assert 0.0 < world.rarity.empirical_probability <= 1.0


def test_multiverse_simulation_identity_changes_when_governed_input_changes() -> None:
    baseline = simulate_regular_season(
        _stochastic_request(rng_protocol=PYTHON_RANDOM_GAUSS_V1, batch_size=None)
    )
    changed = simulate_regular_season(
        _stochastic_request(
            rng_protocol=PYTHON_RANDOM_GAUSS_V1,
            batch_size=None,
            mean_a=130.0,
        )
    )

    assert baseline.simulation_input_fingerprint != changed.simulation_input_fingerprint
    assert baseline.multiverse_worlds[0].simulation_id != (
        changed.multiverse_worlds[0].simulation_id
    )
    assert baseline.multiverse_worlds[0].world_id != changed.multiverse_worlds[0].world_id


def test_multiverse_records_strong_expected_team_missing_playoffs_as_empirical_event() -> None:
    weekly = (
        WeeklyTeamScoringDistribution(
            week=1, team_id="a", mean_points=200.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=1, team_id="b", mean_points=0.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=1, team_id="c", mean_points=100.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=1, team_id="d", mean_points=90.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=2, team_id="a", mean_points=0.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=2, team_id="b", mean_points=100.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=2, team_id="c", mean_points=50.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=2, team_id="d", mean_points=0.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=3, team_id="a", mean_points=0.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=3, team_id="b", mean_points=100.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=3, team_id="c", mean_points=0.0, stddev_points=0.0, model_version="v1"
        ),
        WeeklyTeamScoringDistribution(
            week=3, team_id="d", mean_points=50.0, stddev_points=0.0, model_version="v1"
        ),
    )
    request = RegularSeasonSimulationInput(
        weekly_scoring=weekly,
        schedule=(
            ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),
            ScheduledMatchup(week=1, home_team_id="c", away_team_id="d"),
            ScheduledMatchup(week=2, home_team_id="a", away_team_id="c"),
            ScheduledMatchup(week=2, home_team_id="b", away_team_id="d"),
            ScheduledMatchup(week=3, home_team_id="a", away_team_id="d"),
            ScheduledMatchup(week=3, home_team_id="b", away_team_id="c"),
        ),
        playoff_team_count=2,
        simulation_count=25,
        seed=7,
        model_version="strong-team-miss-v1",
    )

    result = simulate_regular_season(request)
    world = next(
        item
        for item in result.multiverse_worlds
        if item.category == "strong_team_misses_playoffs"
    )

    assert world.focal_team_id == "a"
    a = next(item for item in world.team_outcomes if item.team_id == "a")
    assert a.regular_season_rank == 3
    assert a.made_playoffs is False
    assert world.rarity.basis == "empirical_event_frequency"
    assert world.rarity.empirical_probability == pytest.approx(1.0)
    assert world.rarity.label == "common"


def test_multiverse_biggest_blowout_carries_matchup_explanation() -> None:
    result = simulate_regular_season(
        _stochastic_request(rng_protocol=PYTHON_RANDOM_GAUSS_V1, batch_size=None)
    )
    world = next(
        item for item in result.multiverse_worlds if item.category == "biggest_blowout"
    )

    assert world.notable_matchup is not None
    assert world.notable_matchup.margin == pytest.approx(
        abs(
            world.notable_matchup.home_points
            - world.notable_matchup.away_points
        )
    )
    assert world.rarity.basis == "empirical_upper_tail"
    assert world.rarity.empirical_probability is not None
