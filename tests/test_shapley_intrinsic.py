from __future__ import annotations

import math
import random

import pytest

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FutureStateForecast,
    PlayerIntrinsicForecast,
    ShapleyScenarioResult,
    _Basis,
    build_intrinsic_shapley_estimates,
    full_game_value,
    monte_carlo_shapley_scenarios,
    subset_caps_from_rules,
)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(),
    )


def _legacy_scenario_loop(
    players: list[tuple[str, str, float]],
    scenario_values: dict[str, tuple[float, ...]],
    caps: tuple[tuple[tuple[int, ...], int], ...],
    *,
    permutations: int,
    seed: int,
) -> ShapleyScenarioResult:
    """Frozen pre-optimization loop retained only as an exact equivalence oracle."""

    rng = random.Random(seed)
    player_ids = [row[0] for row in players]
    by_id = {player_id: (position, float(weight)) for player_id, position, weight in players}
    sums = {player_id: [0.0] * len(scenario_values[player_id]) for player_id in player_ids}
    sums_sq = {player_id: [0.0] * len(scenario_values[player_id]) for player_id in player_ids}
    for _ in range(permutations):
        order = player_ids[:]
        rng.shuffle(order)
        basis = _Basis(caps)
        for player_id in order:
            position, baseline = by_id[player_id]
            for index, scenario in enumerate(scenario_values[player_id]):
                marginal, _ = basis.marginal(position, scenario)
                sums[player_id][index] += marginal
                sums_sq[player_id][index] += marginal * marginal
            basis.add(player_id, position, baseline)
    estimates = {
        player_id: tuple(value / permutations for value in values)
        for player_id, values in sums.items()
    }
    standard_errors: dict[str, tuple[float, ...]] = {}
    for player_id in player_ids:
        row: list[float] = []
        for total, total_sq in zip(sums[player_id], sums_sq[player_id], strict=True):
            mean = total / permutations
            variance = max(
                0.0,
                (total_sq - permutations * mean * mean) / (permutations - 1),
            ) if permutations > 1 else 0.0
            row.append(math.sqrt(variance / permutations))
        standard_errors[player_id] = tuple(row)
    full = full_game_value(players, caps)
    return ShapleyScenarioResult(
        estimates=estimates,
        standard_errors=standard_errors,
        full_value=full,
        efficiency_residual=sum(estimates[player_id][0] for player_id in player_ids) - full,
        permutations=permutations,
        seed=seed,
    )


def test_frozen_constants() -> None:
    assert FROZEN_SHAPLEY_PERMUTATIONS == 2048
    assert FROZEN_INTRINSIC_DISCOUNT == 0.85


def test_shapley_efficiency_and_zero_dummy() -> None:
    # LeagueRules governs team_count >= 2; use the smallest valid structural game.
    rules = LeagueRules(
        team_count=2,
        roster_size=3,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
    )
    caps = subset_caps_from_rules(rules)
    players = [("a", "QB", 10.0), ("b", "QB", 6.0), ("c", "QB", 0.0)]
    scenarios = {player_id: (weight,) for player_id, _position, weight in players}
    result = monte_carlo_shapley_scenarios(players, scenarios, caps, permutations=2048, seed=777)
    assert abs(result.efficiency_residual) < 1e-8
    assert abs(result.estimates["c"][0]) < 1e-12
    assert result.estimates["a"][0] > result.estimates["b"][0]


def test_scenario_plan_optimization_is_bit_for_bit_equivalent_to_frozen_loop() -> None:
    rules = _rules()
    caps = subset_caps_from_rules(rules)
    players = [
        ("q1", "QB", 315.0),
        ("q2", "QB", 280.0),
        ("q3", "QB", 220.0),
        ("r1", "RB", 210.0),
        ("r2", "RB", 175.0),
        ("r3", "RB", 120.0),
        ("w1", "WR", 230.0),
        ("w2", "WR", 190.0),
        ("w3", "WR", 150.0),
        ("w4", "WR", 90.0),
        ("t1", "TE", 165.0),
        ("t2", "TE", 95.0),
    ]
    scenarios = {
        player_id: (
            weight,
            0.0,
            weight * 0.25,
            weight * 0.5,
            weight,
            weight * 1.2,
            weight * 1.5,
        )
        for player_id, _position, weight in players
    }
    legacy = _legacy_scenario_loop(players, scenarios, caps, permutations=64, seed=20260915)
    optimized = monte_carlo_shapley_scenarios(
        players,
        scenarios,
        caps,
        permutations=64,
        seed=20260915,
    )
    assert optimized.estimates == legacy.estimates
    assert optimized.standard_errors == legacy.standard_errors
    assert optimized.full_value == legacy.full_value
    assert optimized.efficiency_residual == legacy.efficiency_residual


@pytest.mark.parametrize("team_count", [2, 8, 12, 16])
@pytest.mark.parametrize("superflex", [False, True])
def test_prepared_scenarios_match_frozen_loop_across_formats_and_ties(team_count, superflex):
    rules = _rules().model_copy(update={
        "team_count": team_count,
        "lineup": tuple(r for r in _rules().lineup
                        if superflex or r.slot != RosterSlot.SUPERFLEX),
    })
    # More candidates than slots forces replacements, including equal weights,
    # dummy/negative production and either side of the accepted 1e-12 threshold.
    values = (-10.0, 0.0, 1e-13, 1.0, 1.0 + 5e-13, 1.0 + 2e-12, 10.0, 37.5)
    players = [(f"p{i:03}", ("QB", "RB", "WR", "TE")[i % 4], values[(i // 4) % len(values)])
               for i in range(team_count * 12)]
    scenarios = {
        pid: ((weight,) if i % 3 == 0 else (weight, -1.0, 0.0, 1e-13, 1.0, 1.0 + 2e-12, 40.0))
        for i, (pid, _, weight) in enumerate(players)
    }
    caps = subset_caps_from_rules(rules)
    expected = _legacy_scenario_loop(players, scenarios, caps, permutations=64, seed=73)
    assert monte_carlo_shapley_scenarios(players, scenarios, caps, permutations=64, seed=73) == expected


@pytest.mark.parametrize("permutations", [1, 64])
def test_no_feasible_slot_and_empty_cohort_preserve_frozen_statistics(permutations):
    caps = subset_caps_from_rules(_rules().model_copy(update={"lineup": ()}))
    players = [("a", "QB", 10.0), ("b", "WR", -1.0)]
    scenarios = {"a": (10.0, 0.0, 50.0), "b": (-1.0, 10.0, 0.0)}
    for cohort, weights in ((players, scenarios), ([], {})):
        expected = _legacy_scenario_loop(cohort, weights, caps, permutations=permutations, seed=73)
        assert monte_carlo_shapley_scenarios(cohort, weights, caps, permutations=permutations, seed=73) == expected


def test_future_rights_are_discounted_without_holding_cost() -> None:
    states = ("out", "depth", "usable", "starter", "premium", "elite")
    future = FutureStateForecast(
        probabilities={"out": 0.05, "depth": 0.15, "usable": 0.2, "starter": 0.35, "premium": 0.2, "elite": 0.05},
        state_means={state: value for state, value in zip(states, (0, 20, 50, 90, 130, 170), strict=True)},
        anticipated_points=85.0,
    )
    forecasts = (
        PlayerIntrinsicForecast(player_id="q1", position=Position.QB, current_points=250, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="q2", position=Position.QB, current_points=200, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="r1", position=Position.RB, current_points=150, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="r2", position=Position.RB, current_points=100, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="w1", position=Position.WR, current_points=160, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="w2", position=Position.WR, current_points=120, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="w3", position=Position.WR, current_points=90, year_2=future, year_3=future),
        PlayerIntrinsicForecast(player_id="t1", position=Position.TE, current_points=80, year_2=future, year_3=future),
    )
    values = build_intrinsic_shapley_estimates(forecasts, rules=_rules(), permutations=256, seed=99)
    assert len(values) == len(forecasts)
    assert all(item.value >= item.year_1_shapley for item in values)
