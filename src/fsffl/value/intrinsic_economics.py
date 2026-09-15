from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Mapping, Sequence

from fsffl.state.models import LeagueState, Position, RosterSlot


INTRINSIC_STRUCTURAL_ECONOMICS_VERSION = "intrinsic-structural-starter-relevance-v2"
_INTRINSIC_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


@dataclass(frozen=True)
class PositionStructuralEconomics:
    position: Position
    selected_starters: int
    effective_supply: float
    starter_pressure: float
    relative_pressure: float


def _effective_supply(values: Sequence[float]) -> float:
    positive = [max(0.0, float(value)) for value in values if float(value) > 0.0]
    if not positive:
        return 0.0
    total = sum(positive)
    squares = sum(value * value for value in positive)
    return (total * total / squares) if squares > 0.0 else 0.0


def production_rank_relevance(
    production: float,
    *,
    forecast_means: Sequence[float],
    starter_demand: int,
) -> float:
    """Return league-wide starter relevance for one production magnitude.

    Players at or above the neutral starter-demand frontier receive full structural
    relevance. Production below that frontier is discounted smoothly as
    `starter_demand / production_rank`. This is a lineup-demand/supply conversion,
    not replacement-value subtraction: no replacement score is removed and no
    team roster, market price, owner, or transaction information is accepted.
    """

    value = max(0.0, float(production))
    if value <= 0.0 or starter_demand <= 0:
        return 0.0
    pool = sorted(max(0.0, float(v)) for v in forecast_means if float(v) > 0.0)
    if not pool:
        return 1.0
    greater = len(pool) - bisect_right(pool, value)
    rank = 1 + greater
    return min(1.0, starter_demand / rank)


def _select_neutral_starters(
    *,
    team_count: int,
    direct_slots: Mapping[Position, int],
    flex_slots: int,
    superflex_slots: int,
    forecast_means: Mapping[Position, Sequence[float]],
) -> dict[Position, int]:
    pools = {
        position: sorted((max(0.0, float(v)) for v in forecast_means.get(position, ())), reverse=True)
        for position in _INTRINSIC_POSITIONS
    }
    used = {position: 0 for position in _INTRINSIC_POSITIONS}
    selected = {position: 0 for position in _INTRINSIC_POSITIONS}

    def take(position: Position) -> bool:
        index = used[position]
        pool = pools[position]
        if index >= len(pool) or pool[index] <= 0.0:
            return False
        used[position] += 1
        selected[position] += 1
        return True

    for position in _INTRINSIC_POSITIONS:
        for _ in range(max(0, team_count * int(direct_slots.get(position, 0)))):
            if not take(position):
                break

    def take_best(eligible: tuple[Position, ...]) -> bool:
        candidates = []
        for position in eligible:
            index = used[position]
            pool = pools[position]
            if index < len(pool) and pool[index] > 0.0:
                candidates.append((pool[index], position.value, position))
        if not candidates:
            return False
        _value, _name, position = max(candidates)
        return take(position)

    for _ in range(max(0, team_count * flex_slots)):
        if not take_best((Position.RB, Position.WR, Position.TE)):
            break
    for _ in range(max(0, team_count * superflex_slots)):
        if not take_best(_INTRINSIC_POSITIONS):
            break
    return selected


def structural_position_economics(
    *,
    team_count: int,
    direct_slots: Mapping[Position, int],
    flex_slots: int,
    superflex_slots: int,
    forecast_means: Mapping[Position, Sequence[float]],
) -> dict[Position, PositionStructuralEconomics]:
    """Materialize neutral starter demand and structural diagnostics.

    `relative_pressure` is retained as an audit/diagnostic field for compatibility,
    but production Intrinsic v6 no longer multiplies every player at a position by
    that uniform factor. Production uses player-specific `production_rank_relevance`.
    """

    if team_count <= 0:
        return {position: PositionStructuralEconomics(position, 0, 0.0, 0.0, 1.0) for position in _INTRINSIC_POSITIONS}
    selected = _select_neutral_starters(
        team_count=team_count,
        direct_slots=direct_slots,
        flex_slots=flex_slots,
        superflex_slots=superflex_slots,
        forecast_means=forecast_means,
    )
    supply = {position: _effective_supply(forecast_means.get(position, ())) for position in _INTRINSIC_POSITIONS}
    total_selected = sum(selected.values())
    total_supply = sum(value for value in supply.values() if value > 0.0)
    pooled_pressure = total_selected / total_supply if total_selected > 0 and total_supply > 0 else 0.0

    result: dict[Position, PositionStructuralEconomics] = {}
    for position in _INTRINSIC_POSITIONS:
        count = selected[position]
        effective = supply[position]
        pressure = count / effective if count > 0 and effective > 0.0 else 0.0
        relative = pressure / pooled_pressure if pressure > 0.0 and pooled_pressure > 0.0 else 1.0
        result[position] = PositionStructuralEconomics(position, count, effective, pressure, relative)
    return result


def structural_position_economics_for_league(
    league_state: LeagueState,
    *,
    forecast_means: Mapping[Position, Sequence[float]],
) -> dict[Position, PositionStructuralEconomics]:
    direct = {position: 0 for position in _INTRINSIC_POSITIONS}
    flex = 0
    superflex = 0
    for requirement in league_state.league.rules.lineup:
        if requirement.slot == RosterSlot.QB:
            direct[Position.QB] += requirement.count
        elif requirement.slot == RosterSlot.RB:
            direct[Position.RB] += requirement.count
        elif requirement.slot == RosterSlot.WR:
            direct[Position.WR] += requirement.count
        elif requirement.slot == RosterSlot.TE:
            direct[Position.TE] += requirement.count
        elif requirement.slot == RosterSlot.FLEX:
            flex += requirement.count
        elif requirement.slot == RosterSlot.SUPERFLEX:
            superflex += requirement.count
    return structural_position_economics(
        team_count=len(league_state.teams),
        direct_slots=direct,
        flex_slots=flex,
        superflex_slots=superflex,
        forecast_means=forecast_means,
    )
