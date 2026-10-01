from collections import defaultdict
from math import sqrt
from random import Random

import pytest

from fsffl.team_utility import (
    CompletedMatchup,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    simulate_regular_season,
)
from fsffl.team_utility.simulation import (
    NUMPY_PCG64_BATCHED_GAUSS_V1,
    PYTHON_RANDOM_GAUSS_V1,
    _numpy_regular_season_matchup_batches,
)


def _reference(request: RegularSeasonSimulationInput):
    by_team = {item.team_id: item for item in request.scoring}
    by_week_team = {(item.week, item.team_id): item for item in request.weekly_scoring}
    team_ids = tuple(sorted(set(by_team) | {item.team_id for item in request.weekly_scoring}))
    rng = Random(request.seed)
    wins_sum = defaultdict(float)
    wins_sq_sum = defaultdict(float)
    playoff_count = defaultdict(int)
    first_count = defaultdict(int)

    for _ in range(request.simulation_count):
        wins = {team_id: 0.0 for team_id in team_ids}
        points_for = {team_id: 0.0 for team_id in team_ids}
        for matchup in request.schedule:
            if by_week_team:
                home_dist = by_week_team[(matchup.week, matchup.home_team_id)]
                away_dist = by_week_team[(matchup.week, matchup.away_team_id)]
            else:
                home_dist = by_team[matchup.home_team_id]
                away_dist = by_team[matchup.away_team_id]
            home = max(0.0, home_dist.mean_points if home_dist.stddev_points == 0 else rng.gauss(home_dist.mean_points, home_dist.stddev_points))
            away = max(0.0, away_dist.mean_points if away_dist.stddev_points == 0 else rng.gauss(away_dist.mean_points, away_dist.stddev_points))
            points_for[matchup.home_team_id] += home
            points_for[matchup.away_team_id] += away
            if home > away:
                wins[matchup.home_team_id] += 1.0
            elif away > home:
                wins[matchup.away_team_id] += 1.0
            else:
                wins[matchup.home_team_id] += 0.5
                wins[matchup.away_team_id] += 0.5
        standings = sorted(team_ids, key=lambda team_id: (-wins[team_id], -points_for[team_id], team_id))
        playoff_teams = set(standings[: request.playoff_team_count])
        first_count[standings[0]] += 1
        for team_id in team_ids:
            value = wins[team_id]
            wins_sum[team_id] += value
            wins_sq_sum[team_id] += value * value
            if team_id in playoff_teams:
                playoff_count[team_id] += 1

    n = request.simulation_count
    return {
        team_id: (
            wins_sum[team_id] / n,
            sqrt(max(0.0, wins_sq_sum[team_id] / n - (wins_sum[team_id] / n) ** 2)),
            playoff_count[team_id] / n,
            first_count[team_id] / n,
        )
        for team_id in team_ids
    }


def test_optimized_hot_loop_is_exactly_equivalent_to_reference_rng_and_standings() -> None:
    team_ids = ("a", "b", "c", "d")
    schedule = (
        ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),
        ScheduledMatchup(week=1, home_team_id="c", away_team_id="d"),
        ScheduledMatchup(week=2, home_team_id="a", away_team_id="c"),
        ScheduledMatchup(week=2, home_team_id="b", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="a", away_team_id="d"),
        ScheduledMatchup(week=3, home_team_id="b", away_team_id="c"),
    )
    weekly = tuple(
        WeeklyTeamScoringDistribution(
            week=week,
            team_id=team_id,
            mean_points=110.0 + index * 7.0 + week,
            stddev_points=12.0 + index,
            model_version="weekly-v1",
        )
        for week in (1, 2, 3)
        for index, team_id in enumerate(team_ids)
    )
    request = RegularSeasonSimulationInput(
        weekly_scoring=weekly,
        schedule=schedule,
        playoff_team_count=2,
        simulation_count=2_000,
        seed=987654,
        model_version="equivalence-v1",
    )

    expected = _reference(request)
    actual = {row.team_id: row for row in simulate_regular_season(request).outcomes}
    for team_id, reference in expected.items():
        row = actual[team_id]
        assert (
            row.expected_wins,
            row.wins_stddev,
            row.first_place_probability,
        ) == (reference[0], reference[1], reference[3])
        assert row.playoff_probability == reference[2]


def test_optimized_hot_loop_preserves_zero_variance_rng_behavior() -> None:
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(team_id="a", mean_points=120, stddev_points=0, model_version="v1"),
            TeamScoringDistribution(team_id="b", mean_points=120, stddev_points=0, model_version="v1"),
        ),
        schedule=(ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),),
        playoff_team_count=1,
        simulation_count=50,
        seed=22,
        model_version="zero-variance-v1",
    )
    expected = _reference(request)
    actual = {
        row.team_id: (
            row.expected_wins,
            row.wins_stddev,
            row.first_place_probability,
        )
        for row in simulate_regular_season(request).outcomes
    }
    assert {
        team_id: (row[0], row[1], row[3]) for team_id, row in expected.items()
    } == actual
    assert all(
        row.playoff_probability is None
        for row in simulate_regular_season(request).outcomes
    )


def test_performance_benchmark_reference_matches_finish_rank_playoff_estimates() -> None:
    from scripts.benchmark_simulation_performance import (
        _regular_outcome_signature,
        _reference as benchmark_reference,
        _request,
    )

    request = _request(simulation_count=100)
    reference = benchmark_reference(request)
    actual = simulate_regular_season(request).outcomes
    assert all(row.playoff_probability is not None for row in reference)
    assert _regular_outcome_signature(reference) == _regular_outcome_signature(actual)


def test_rng_equivalence_report_omits_unavailable_metrics_and_checks_availability_parity() -> None:
    from scripts.run_simulation_rng_equivalence_study import _equivalence_report

    histogram = [0] * 256
    histogram[0] = 100
    summary = {
        "simulation_count": 100,
        "outcomes": [
            {"team_id": team, "expected_wins": wins, "wins_stddev": 1.0,
             "playoff_probability": None, "first_place_probability": 0.5,
             "championship_probability": None}
            for team, wins in (("a", 4.0), ("b", 3.0))
        ],
        "finish_distributions": [
            {"team_id": team, "expected_finish": rank,
             "rank_probabilities": probs}
            for team, rank, probs in (("a", 1.5, (0.5, 0.5)), ("b", 1.5, (0.5, 0.5)))
        ],
        "team_score_histogram_range": {"a": [0.0, 100.0, 256], "b": [0.0, 100.0, 256]},
        "team_score_histograms": {"a": histogram, "b": histogram},
    }
    report = _equivalence_report([summary, summary], [summary, summary])
    assert "a.playoff_probability" not in report["team_metrics"]
    assert "a.championship_probability" not in report["team_metrics"]

    available = {**summary, "outcomes": [dict(row) for row in summary["outcomes"]]}
    available["outcomes"][0]["championship_probability"] = 0.25
    with pytest.raises(ValueError, match="same available Simulation metrics"):
        _equivalence_report([summary, summary], [available, available])


def test_completed_results_are_part_of_replay_identity_and_remaining_wins_contract() -> None:
    base = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(
                team_id="a", mean_points=110, stddev_points=0, model_version="v1"
            ),
            TeamScoringDistribution(
                team_id="b", mean_points=100, stddev_points=0, model_version="v1"
            ),
        ),
        completed_matchups=(
            CompletedMatchup(
                week=1,
                home_team_id="a",
                away_team_id="b",
                home_points=95.0,
                away_points=105.0,
            ),
        ),
        schedule=(ScheduledMatchup(week=2, home_team_id="a", away_team_id="b"),),
        playoff_team_count=1,
        simulation_count=100,
        seed=123,
        model_version="current-season-replay-v1",
    )

    first = simulate_regular_season(base)
    changed_fact = simulate_regular_season(
        base.model_copy(
            update={
                "completed_matchups": (
                    CompletedMatchup(
                        week=1,
                        home_team_id="a",
                        away_team_id="b",
                        home_points=106.0,
                        away_points=105.0,
                    ),
                )
            }
        )
    )

    by_team = {row.team_id: row for row in first.outcomes}
    assert by_team["a"].expected_wins == 1.0
    assert by_team["a"].expected_remaining_wins == 1.0
    assert by_team["b"].expected_wins == 1.0
    assert by_team["b"].expected_remaining_wins == 0.0
    assert first.simulation_input_fingerprint != changed_fact.simulation_input_fingerprint


def test_cooperative_checkpoint_preserves_exact_simulation_output() -> None:
    request = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(team_id="a", mean_points=125, stddev_points=15, model_version="v1"),
            TeamScoringDistribution(team_id="b", mean_points=115, stddev_points=12, model_version="v1"),
        ),
        schedule=tuple(
            ScheduledMatchup(week=week, home_team_id="a", away_team_id="b")
            for week in range(1, 5)
        ),
        playoff_team_count=1,
        simulation_count=250,
        seed=12345,
        model_version="paced-equivalence-v1",
    )
    baseline = simulate_regular_season(request)
    calls = 0

    def checkpoint() -> None:
        nonlocal calls
        calls += 1

    paced = simulate_regular_season(request, cooperative_yield=checkpoint)
    assert paced == baseline
    assert calls == request.simulation_count


def test_batched_rng_replay_identity_is_deterministic_and_batch_scoped() -> None:
    base = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(team_id="a", mean_points=125, stddev_points=15, model_version="v1"),
            TeamScoringDistribution(team_id="b", mean_points=115, stddev_points=12, model_version="v1"),
        ),
        schedule=tuple(
            ScheduledMatchup(week=week, home_team_id="a", away_team_id="b")
            for week in range(1, 5)
        ),
        playoff_team_count=1,
        simulation_count=2_000,
        seed=12345,
        model_version="replay-v1",
    )
    request = base.model_copy(
        update={"rng_protocol": NUMPY_PCG64_BATCHED_GAUSS_V1, "rng_batch_size": 333}
    )
    first = simulate_regular_season(request)
    replay = simulate_regular_season(request)
    other_batch = simulate_regular_season(request.model_copy(update={"rng_batch_size": 500}))
    implicit_default_batch = simulate_regular_season(
        base.model_copy(update={"rng_protocol": NUMPY_PCG64_BATCHED_GAUSS_V1})
    )
    legacy = simulate_regular_season(base)

    assert first == replay
    assert first.rng_protocol == NUMPY_PCG64_BATCHED_GAUSS_V1
    assert first.rng_runtime_version.startswith("numpy-")
    assert first.rng_bit_generator == "PCG64"
    assert first.rng_batch_size == 333
    assert first.rng_draw_dtype == "float64"
    assert first.rng_draw_layout == "batch-major;trial-major;compiled-schedule-major;home-away-v1"
    assert first.rng_seed_derivation.startswith("pcg64-regular-root-seed-v1;")
    assert first.simulation_input_fingerprint != other_batch.simulation_input_fingerprint
    assert first.outcomes == other_batch.outcomes
    assert first.finish_distributions == other_batch.finish_distributions
    assert implicit_default_batch.rng_batch_size == 500
    assert implicit_default_batch.simulation_input_fingerprint == other_batch.simulation_input_fingerprint
    assert legacy.rng_protocol == PYTHON_RANDOM_GAUSS_V1
    assert first.outcomes != legacy.outcomes


def test_numpy_rng_preserves_zero_variance_and_floor_semantics() -> None:
    base = RegularSeasonSimulationInput(
        scoring=(
            TeamScoringDistribution(team_id="a", mean_points=0, stddev_points=0, model_version="v1"),
            TeamScoringDistribution(team_id="b", mean_points=-1, stddev_points=0, model_version="v1"),
        ),
        schedule=(ScheduledMatchup(week=1, home_team_id="a", away_team_id="b"),),
        playoff_team_count=1,
        simulation_count=100,
        seed=9,
        model_version="zero-v1",
    )
    legacy = simulate_regular_season(base)
    numpy_result = simulate_regular_season(
        base.model_copy(update={"rng_protocol": NUMPY_PCG64_BATCHED_GAUSS_V1})
    )
    assert [row.expected_wins for row in legacy.outcomes] == [row.expected_wins for row in numpy_result.outcomes]
    assert [row.playoff_probability for row in legacy.outcomes] == [row.playoff_probability for row in numpy_result.outcomes]


def test_numpy_matchup_batch_preserves_scalar_addition_order_and_ties() -> None:
    import numpy as np

    compiled_schedule = (
        (0, 1, 0.0, 0.0, 0.0, 0.0),
        (0, 2, 0.0, 0.0, 0.0, 0.0),
        (1, 2, 0.0, 0.0, 0.0, 0.0),
    )
    scores = np.asarray(
        (
            (1.0, 1.0, 3.0, 2.0, 2.0, 2.0),
            (0.0, 4.0, 1.5, 1.0, 7.0, 6.0),
        ),
        dtype=np.float64,
    )

    actual_wins, actual_points = _numpy_regular_season_matchup_batches(
        scores, compiled_schedule, team_count=3
    )
    expected_wins = []
    expected_points = []
    for row in scores:
        wins = [0.0, 0.0, 0.0]
        points = [0.0, 0.0, 0.0]
        for index, (home, away, *_draw_parameters) in enumerate(compiled_schedule):
            home_score = float(row[2 * index])
            away_score = float(row[2 * index + 1])
            points[home] += home_score
            points[away] += away_score
            if home_score > away_score:
                wins[home] += 1.0
            elif away_score > home_score:
                wins[away] += 1.0
            else:
                wins[home] += 0.5
                wins[away] += 0.5
        expected_wins.append(wins)
        expected_points.append(points)

    assert actual_wins.tolist() == expected_wins
    assert actual_points.tolist() == expected_points


def test_50000_run_output_matches_governed_settings_derived_postseason_baseline() -> None:
    """Guard complete canonical output, including finish-rank postseason estimates."""
    import hashlib
    import json
    import sys

    from scripts.benchmark_simulation_performance import _request

    result = simulate_regular_season(_request())
    # The durable replay identity intentionally includes the Python patch
    # version. Normalize only that identity field here; the result rows and
    # every RNG/output field remain part of the digest.
    dumped = result.model_dump(mode="json")
    dumped["rng_runtime_version"] = f"python-{sys.version_info.major}.{sys.version_info.minor}"
    payload = json.dumps(dumped, sort_keys=True, separators=(",", ":"))
    expected_by_python_minor = {
        (3, 11): "50b0646e69143f369278373dba853668a3965476fd9a931cd08dcdbd02d9cf15",
        (3, 12): "687387fb49581d7bc4300fe537b4a95c23a1e53dc276da0e08aa0e829f85618a",
    }
    expected = expected_by_python_minor.get(sys.version_info[:2])
    assert expected is not None, (
        "add a reviewed fixed 50k replay digest for Python "
        f"{sys.version_info.major}.{sys.version_info.minor} before validating this runtime"
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    assert digest == expected
