from __future__ import annotations

from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot
from fsffl.value.shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FutureStateForecast,
    PlayerIntrinsicForecast,
    build_intrinsic_shapley_estimates,
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
