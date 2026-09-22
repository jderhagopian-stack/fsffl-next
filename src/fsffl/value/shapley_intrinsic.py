from __future__ import annotations

import bisect
import math
import random
from functools import lru_cache
from dataclasses import dataclass
from typing import Mapping

from fsffl.state.models import LeagueRules, Position, RosterSlot

FROZEN_SHAPLEY_PERMUTATIONS = 2048
FROZEN_INTRINSIC_DISCOUNT = 0.85
FROZEN_SHAPLEY_SEED = 20260915
SHAPLEY_INTRINSIC_MODEL_VERSION = "intrinsic-shapley-i1-v1"
POSITIONS = ("QB", "RB", "WR", "TE")
POSITION_INDEX = {position: index for index, position in enumerate(POSITIONS)}
STATE_NAMES = ("out", "depth", "usable", "starter", "premium", "elite")


def subset_caps_from_rules(rules: LeagueRules) -> tuple[tuple[tuple[int, ...], int], ...]:
    direct = {position: 0 for position in POSITIONS}
    flex = 0
    superflex = 0
    for requirement in rules.lineup:
        if requirement.slot.value in direct:
            direct[requirement.slot.value] += requirement.count
        elif requirement.slot == RosterSlot.FLEX:
            flex += requirement.count
        elif requirement.slot == RosterSlot.SUPERFLEX:
            superflex += requirement.count
    caps: list[tuple[tuple[int, ...], int]] = []
    for mask in range(1, 1 << 4):
        capacity = rules.team_count * sum(
            direct[POSITIONS[index]] for index in range(4) if mask & (1 << index)
        )
        if any(mask & (1 << POSITION_INDEX[position]) for position in ("RB", "WR", "TE")):
            capacity += rules.team_count * flex
        # Superflex admits all four governed offensive positions.
        capacity += rules.team_count * superflex
        indices = tuple(index for index in range(4) if mask & (1 << index))
        caps.append((indices, capacity))
    return tuple(caps)


ReplacementPlan = tuple[int | None, float | None, str | None] | None


@lru_cache(maxsize=None)
def _valid_counts_cached(
    caps: tuple[tuple[tuple[int, ...], int], ...],
    counts: tuple[int, int, int, int],
) -> bool:
    """Memoize lineup-feasibility checks without changing Shapley semantics.

    A 335-player / 2048-permutation cold build revisits the same small set of
    position-count states millions of times.  Feasibility depends only on the
    frozen league caps and integer position counts, so this cache removes
    redundant structural work while preserving the exact permutation stream and
    marginal-value mathematics.
    """

    return all(
        sum(counts[index] for index in indices) <= cap
        for indices, cap in caps
    )


@lru_cache(maxsize=None)
def _replacement_options_cached(
    caps: tuple[tuple[tuple[int, ...], int], ...],
    counts: tuple[int, int, int, int],
    incoming: int,
) -> tuple[bool, tuple[int, ...]]:
    add_counts = list(counts)
    add_counts[incoming] += 1
    if _valid_counts_cached(caps, tuple(add_counts)):
        return True, ()

    outgoing_options: list[int] = []
    for outgoing in range(4):
        if counts[outgoing] <= 0:
            continue
        swap_counts = list(counts)
        swap_counts[outgoing] -= 1
        swap_counts[incoming] += 1
        if _valid_counts_cached(caps, tuple(swap_counts)):
            outgoing_options.append(outgoing)
    return False, tuple(outgoing_options)


class _Basis:
    def __init__(self, caps: tuple[tuple[tuple[int, ...], int], ...]) -> None:
        self.caps = caps
        self.counts = [0, 0, 0, 0]
        self.by_position: list[list[tuple[float, str]]] = [[] for _ in range(4)]
        self.total = 0.0

    def _valid_counts(self, counts: list[int]) -> bool:
        return _valid_counts_cached(
            self.caps,
            (counts[0], counts[1], counts[2], counts[3]),
        )

    def _can_add(self, position_index: int) -> bool:
        can_add, _ = _replacement_options_cached(
            self.caps,
            (self.counts[0], self.counts[1], self.counts[2], self.counts[3]),
            position_index,
        )
        return can_add

    def _can_swap(self, outgoing: int, incoming: int) -> bool:
        if self.counts[outgoing] <= 0:
            return False
        can_add, outgoing_options = _replacement_options_cached(
            self.caps,
            (self.counts[0], self.counts[1], self.counts[2], self.counts[3]),
            incoming,
        )
        return (not can_add) and outgoing in outgoing_options

    def replacement_plan(self, position: str) -> ReplacementPlan:
        """Return the lineup-feasibility plan for an incoming position.

        The plan depends only on the current basis and incoming position, not on the
        candidate scenario weight. Future-state Shapley evaluates multiple weights
        for that identical basis, so resolving the plan once avoids repeating the
        same structural feasibility search without changing any economic semantics.
        """

        incoming = POSITION_INDEX[position]
        can_add, outgoing_options = _replacement_options_cached(
            self.caps,
            (self.counts[0], self.counts[1], self.counts[2], self.counts[3]),
            incoming,
        )
        if can_add:
            return (None, None, None)
        best: tuple[float, str, int] | None = None
        for outgoing in outgoing_options:
            if not self.by_position[outgoing]:
                continue
            old_weight, old_id = self.by_position[outgoing][0]
            option = (old_weight, old_id, outgoing)
            if best is None or option < best:
                best = option
        if best is None:
            return None
        old_weight, old_id, outgoing = best
        return (outgoing, old_weight, old_id)

    @staticmethod
    def marginal_from_plan(weight: float, plan: ReplacementPlan) -> tuple[float, ReplacementPlan]:
        candidate = max(0.0, float(weight))
        if candidate <= 0 or plan is None:
            return 0.0, None
        if plan[0] is None:
            return candidate, plan
        outgoing, old_weight, old_id = plan
        assert outgoing is not None and old_weight is not None and old_id is not None
        if candidate <= old_weight + 1e-12:
            return 0.0, None
        return candidate - old_weight, plan

    def marginal(self, position: str, weight: float) -> tuple[float, ReplacementPlan]:
        return self.marginal_from_plan(weight, self.replacement_plan(position))

    def add_with_plan(
        self,
        player_id: str,
        position: str,
        weight: float,
        plan: ReplacementPlan,
    ) -> float:
        delta, replacement = self.marginal_from_plan(weight, plan)
        candidate = max(0.0, float(weight)); incoming = POSITION_INDEX[position]
        if replacement is None:
            return 0.0
        if replacement[0] is None:
            bisect.insort(self.by_position[incoming], (candidate, player_id))
            self.counts[incoming] += 1; self.total += candidate
            return candidate
        outgoing, old_weight, old_id = replacement
        assert outgoing is not None and old_weight is not None and old_id is not None
        self.by_position[outgoing].pop(0)
        self.counts[outgoing] -= 1; self.total -= old_weight
        bisect.insort(self.by_position[incoming], (candidate, player_id))
        self.counts[incoming] += 1; self.total += candidate
        return delta

    def add(self, player_id: str, position: str, weight: float) -> float:
        return self.add_with_plan(
            player_id,
            position,
            weight,
            self.replacement_plan(position),
        )


def full_game_value(
    players: list[tuple[str, str, float]],
    caps: tuple[tuple[tuple[int, ...], int], ...],
) -> float:
    basis = _Basis(caps)
    for player_id, position, weight in sorted(players, key=lambda row: (-row[2], row[0])):
        basis.add(player_id, position, weight)
    return basis.total


@dataclass(frozen=True)
class ShapleyScenarioResult:
    estimates: Mapping[str, tuple[float, ...]]
    standard_errors: Mapping[str, tuple[float, ...]]
    full_value: float
    efficiency_residual: float
    permutations: int
    seed: int


def monte_carlo_shapley_scenarios(
    players: list[tuple[str, str, float]],
    scenario_values: Mapping[str, tuple[float, ...]],
    caps: tuple[tuple[tuple[int, ...], int], ...],
    *,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
    seed: int = FROZEN_SHAPLEY_SEED,
) -> ShapleyScenarioResult:
    rng = random.Random(seed)
    player_ids = [row[0] for row in players]
    by_id = {player_id: (position, float(weight)) for player_id, position, weight in players}
    sums = {player_id: [0.0] * len(scenario_values[player_id]) for player_id in player_ids}
    sums_sq = {player_id: [0.0] * len(scenario_values[player_id]) for player_id in player_ids}

    for _ in range(permutations):
        order = player_ids[:]; rng.shuffle(order); basis = _Basis(caps)
        for player_id in order:
            position, baseline = by_id[player_id]
            plan = basis.replacement_plan(position)
            for index, scenario in enumerate(scenario_values[player_id]):
                marginal, _ = basis.marginal_from_plan(scenario, plan)
                sums[player_id][index] += marginal
                sums_sq[player_id][index] += marginal * marginal
            basis.add_with_plan(player_id, position, baseline, plan)

    estimates = {
        player_id: tuple(value / permutations for value in values)
        for player_id, values in sums.items()
    }
    standard_errors: dict[str, tuple[float, ...]] = {}
    for player_id in player_ids:
        row: list[float] = []
        for total, total_sq in zip(sums[player_id], sums_sq[player_id], strict=True):
            mean = total / permutations
            variance = max(0.0, (total_sq - permutations * mean * mean) / (permutations - 1)) if permutations > 1 else 0.0
            row.append(math.sqrt(variance / permutations))
        standard_errors[player_id] = tuple(row)

    full = full_game_value(players, caps)
    phi_sum = sum(estimates[player_id][0] for player_id in player_ids)
    return ShapleyScenarioResult(
        estimates=estimates,
        standard_errors=standard_errors,
        full_value=full,
        efficiency_residual=phi_sum - full,
        permutations=permutations,
        seed=seed,
    )


@dataclass(frozen=True)
class FutureStateForecast:
    probabilities: Mapping[str, float]
    state_means: Mapping[str, float]
    anticipated_points: float


@dataclass(frozen=True)
class PlayerIntrinsicForecast:
    player_id: str
    position: Position
    current_points: float
    year_2: FutureStateForecast
    year_3: FutureStateForecast


@dataclass(frozen=True)
class IntrinsicShapleyEstimate:
    player_id: str
    value: float
    year_1_shapley: float
    year_2_expected_shapley: float
    year_3_expected_shapley: float
    model_version: str = SHAPLEY_INTRINSIC_MODEL_VERSION


def build_intrinsic_shapley_estimates(
    forecasts: tuple[PlayerIntrinsicForecast, ...],
    *,
    rules: LeagueRules,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
    seed: int = FROZEN_SHAPLEY_SEED,
) -> tuple[IntrinsicShapleyEstimate, ...]:
    """Frozen three-year Shapley deployment economy consuming Forecast outputs.

    Holding cost is intentionally absent (B4). No roster fit, team utility, owner,
    market or trade inputs are accepted by this function.
    """

    caps = subset_caps_from_rules(rules)
    by_id = {forecast.player_id: forecast for forecast in forecasts}
    horizon_results: dict[int, ShapleyScenarioResult] = {}

    for horizon in (0, 1, 2):
        if horizon == 0:
            players = [
                (forecast.player_id, forecast.position.value, max(0.0, forecast.current_points))
                for forecast in forecasts
            ]
            scenarios = {player_id: (weight,) for player_id, _position, weight in players}
        else:
            players = []
            scenarios: dict[str, tuple[float, ...]] = {}
            for forecast in forecasts:
                future = forecast.year_2 if horizon == 1 else forecast.year_3
                players.append((forecast.player_id, forecast.position.value, max(0.0, future.anticipated_points)))
                scenarios[forecast.player_id] = (
                    max(0.0, future.anticipated_points),
                    *(max(0.0, float(future.state_means[state])) for state in STATE_NAMES),
                )
        horizon_results[horizon] = monte_carlo_shapley_scenarios(
            players,
            scenarios,
            caps,
            permutations=permutations,
            seed=seed + horizon,
        )

    output: list[IntrinsicShapleyEstimate] = []
    for player_id in sorted(by_id):
        forecast = by_id[player_id]
        year_1 = horizon_results[0].estimates[player_id][0]
        expected_future: list[float] = []
        for horizon, future in ((1, forecast.year_2), (2, forecast.year_3)):
            values = horizon_results[horizon].estimates[player_id]
            expected = sum(
                float(future.probabilities[state]) * values[1 + STATE_NAMES.index(state)]
                for state in STATE_NAMES
            )
            expected_future.append(expected)
        total = year_1 + FROZEN_INTRINSIC_DISCOUNT * expected_future[0] + (FROZEN_INTRINSIC_DISCOUNT ** 2) * expected_future[1]
        output.append(
            IntrinsicShapleyEstimate(
                player_id=player_id,
                value=total,
                year_1_shapley=year_1,
                year_2_expected_shapley=expected_future[0],
                year_3_expected_shapley=expected_future[1],
            )
        )
    return tuple(output)
