from __future__ import annotations

from collections.abc import Iterable

from fsffl.team_utility.competitive_state import (
    classify_calculated_competitive_state,
    derive_league_relative_competitive_state_policy,
)
from fsffl.team_utility.utility import CalculatedCompetitiveState, OwnerStrategicPosture

from .runtime import UserRuntimeContext


_POSTURE_LABELS = {
    OwnerStrategicPosture.DEFAULT_CALCULATED: "Use calculated state",
    OwnerStrategicPosture.WIN_NOW: "Push to contend",
    OwnerStrategicPosture.BALANCED: "Balanced",
    OwnerStrategicPosture.RETOOL: "Retool",
    OwnerStrategicPosture.REBUILD: "Rebuild",
}


def calculated_competitive_state(runtime: UserRuntimeContext) -> CalculatedCompetitiveState:
    """Read the current governed NEXT-4 competitive-state interpretation.

    Owner intent is deliberately absent from this function. The calculated state is
    reconstructed from the already-authoritative Simulation result and the same
    league-relative policy used by NEXT-4; it is never overwritten by search posture.
    """

    league_state = runtime.league_state
    simulation = runtime.simulation_analytics
    team_id = runtime.selected_team_id
    if league_state is None or simulation is None or team_id is None:
        return CalculatedCompetitiveState.UNKNOWN
    outcome = next(
        (row for row in simulation.simulation_result.outcomes if row.team_id == team_id),
        None,
    )
    if outcome is None:
        return CalculatedCompetitiveState.UNKNOWN
    policy = derive_league_relative_competitive_state_policy(
        simulation.simulation_result.outcomes,
        as_of=league_state.as_of,
    )
    return classify_calculated_competitive_state(
        outcome,
        policy,
        as_of=league_state.as_of,
    )


def default_posture_for_state(state: CalculatedCompetitiveState) -> OwnerStrategicPosture:
    """Translate calculated state into an explicit search lens without changing it."""

    return {
        CalculatedCompetitiveState.CONTENDER: OwnerStrategicPosture.WIN_NOW,
        CalculatedCompetitiveState.COMPETITIVE: OwnerStrategicPosture.BALANCED,
        CalculatedCompetitiveState.DEVELOPING: OwnerStrategicPosture.RETOOL,
        CalculatedCompetitiveState.REBUILDING: OwnerStrategicPosture.REBUILD,
        CalculatedCompetitiveState.UNKNOWN: OwnerStrategicPosture.BALANCED,
    }[state]


def resolve_search_posture(
    requested: OwnerStrategicPosture,
    calculated_state: CalculatedCompetitiveState,
) -> OwnerStrategicPosture:
    if requested is OwnerStrategicPosture.DEFAULT_CALCULATED:
        return default_posture_for_state(calculated_state)
    return requested


def _float(row: dict[str, object], key: str, default: float) -> float:
    value = row.get(key)
    return float(value) if value is not None else default


def _receive_age(row: dict[str, object]) -> float:
    receive = row.get("receive") or []
    if not receive or not isinstance(receive[0], dict):
        return float("inf")
    age = receive[0].get("age_years")
    return float(age) if age is not None else float("inf")


def _lane_order(
    candidates: list[dict[str, object]],
    posture: OwnerStrategicPosture,
) -> tuple[list[int], ...]:
    indices = list(range(len(candidates)))
    market = sorted(indices, key=lambda i: (_float(candidates[i], "market_gap_ratio", float("inf")), i))
    premium = sorted(indices, key=lambda i: (-_float(candidates[i], "target_fsffl_value", float("-inf")), i))
    need = sorted(indices, key=lambda i: (_float(candidates[i], "focal_position_strength_index", float("inf")), i))
    counterparty = sorted(indices, key=lambda i: (_float(candidates[i], "counterparty_receive_position_strength_index", float("inf")), i))
    youth = sorted(indices, key=lambda i: (_receive_age(candidates[i]), -_float(candidates[i], "target_fsffl_value", float("-inf")), i))
    structure = sorted(indices, key=lambda i: (-len(candidates[i].get("send") or []), _float(candidates[i], "market_gap_ratio", float("inf")), i))

    if posture is OwnerStrategicPosture.WIN_NOW:
        return need, premium, market, counterparty, structure
    if posture is OwnerStrategicPosture.REBUILD:
        return youth, market, premium, counterparty, structure
    if posture is OwnerStrategicPosture.RETOOL:
        return youth, need, market, premium, counterparty
    return market, need, premium, counterparty, structure


def apply_search_posture(
    candidates: Iterable[dict[str, object]],
    posture: OwnerStrategicPosture,
) -> list[dict[str, object]]:
    """Reorder discovery after broad candidate generation using explicit search intent.

    The closest market match remains row zero so the market-match spotlight keeps its
    literal meaning. The remaining rows are round-robin admissions from posture-specific
    categorical lanes. No metrics are blended into a score and no Value/Decision truth
    is changed.
    """

    rows = list(candidates)
    if len(rows) <= 1:
        return rows
    lanes = _lane_order(rows, posture)
    ordered = [0]
    seen = {0}
    cursors = [0] * len(lanes)
    while len(ordered) < len(rows):
        progressed = False
        for lane_index, lane in enumerate(lanes):
            while cursors[lane_index] < len(lane) and lane[cursors[lane_index]] in seen:
                cursors[lane_index] += 1
            if cursors[lane_index] >= len(lane):
                continue
            index = lane[cursors[lane_index]]
            cursors[lane_index] += 1
            seen.add(index)
            ordered.append(index)
            progressed = True
        if not progressed:
            break
    return [rows[index] for index in ordered]


def posture_payload(
    runtime: UserRuntimeContext,
    requested: OwnerStrategicPosture,
) -> dict[str, object]:
    calculated = calculated_competitive_state(runtime)
    effective = resolve_search_posture(requested, calculated)
    return {
        "calculated_competitive_state": calculated.value,
        "requested_posture": requested.value,
        "effective_posture": effective.value,
        "label": _POSTURE_LABELS[requested],
        "available_postures": [
            {"value": posture.value, "label": _POSTURE_LABELS[posture]}
            for posture in OwnerStrategicPosture
        ],
        "authority": (
            "Calculated competitive state remains governed NEXT-4 truth. Owner strategic posture "
            "is an explicit Trade Finder search lens only; it does not change Market Value, "
            "competitive state, Decision truth, or acceptance probability."
        ),
    }
