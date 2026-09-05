from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Position, RosterSlot

from .models import LineupAssignment, MarginalLineupImpact, OptimizedTeamLineup


_STARTER_ELIGIBILITY: dict[RosterSlot, frozenset[Position]] = {
    RosterSlot.QB: frozenset({Position.QB}),
    RosterSlot.RB: frozenset({Position.RB}),
    RosterSlot.WR: frozenset({Position.WR}),
    RosterSlot.TE: frozenset({Position.TE}),
    RosterSlot.FLEX: frozenset({Position.RB, Position.WR, Position.TE}),
    RosterSlot.SUPERFLEX: frozenset({Position.QB, Position.RB, Position.WR, Position.TE}),
    RosterSlot.K: frozenset({Position.K}),
    RosterSlot.DST: frozenset({Position.DST}),
}

_PRESENTATION_SLOT_PRIORITY = {
    RosterSlot.QB: 0,
    RosterSlot.RB: 1,
    RosterSlot.WR: 2,
    RosterSlot.TE: 3,
    RosterSlot.K: 4,
    RosterSlot.DST: 5,
    RosterSlot.FLEX: 6,
    RosterSlot.SUPERFLEX: 7,
}


def optimize_team_lineup(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    excluded_player_ids: frozenset[str] = frozenset(),
    model_version: str = "next4-lineup-v2",
) -> OptimizedTeamLineup:
    """Maximize expected fantasy points under the league's actual lineup rules.

    NEXT-4 uses the team's real roster and the league's canonical rules. Taxi/IR
    players are unavailable. Missing forecasts are surfaced rather than imputed.

    Equal-point optimal lineups use a deterministic, points-neutral secondary
    ordering: natural position slots are filled before FLEX/SUPERFLEX, and within
    a repeated slot the stronger player receives the lower slot index. This keeps
    presentation intuitive without changing the starter set or optimized points.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not team_id.strip() or not model_version.strip():
        raise ValueError("lineup identifiers cannot be blank")

    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team_state is None:
        raise ValueError("unknown team_id")

    players_by_id = {player.player_id: player for player in league_state.players}
    active_roster_ids: list[str] = []
    unavailable: list[str] = []
    for entry in team_state.roster:
        if entry.player_id in excluded_player_ids:
            continue
        if entry.slot in {RosterSlot.TAXI, RosterSlot.IR}:
            unavailable.append(entry.player_id)
        else:
            active_roster_ids.append(entry.player_id)

    latest_forecast: dict[str, ForecastObservation] = {}
    for observation in forecasts:
        if observation.metric != ForecastMetric.FANTASY_POINTS or observation.horizon != horizon:
            continue
        if observation.as_of > as_of:
            continue
        if observation.player_id not in active_roster_ids:
            continue
        current = latest_forecast.get(observation.player_id)
        if current is None or observation.as_of > current.as_of:
            latest_forecast[observation.player_id] = observation

    missing = sorted(player_id for player_id in active_roster_ids if player_id not in latest_forecast)
    candidate_ids = sorted(player_id for player_id in active_roster_ids if player_id in latest_forecast)

    slots: list[tuple[RosterSlot, int]] = []
    for requirement in league_state.league.rules.lineup:
        if requirement.slot not in _STARTER_ELIGIBILITY:
            continue
        for slot_index in range(1, requirement.count + 1):
            slots.append((requirement.slot, slot_index))

    if not slots:
        raise ValueError("league has no supported starting lineup slots")

    presentation_positions = tuple(
        sorted(
            range(len(slots)),
            key=lambda position: (
                _PRESENTATION_SLOT_PRIORITY[slots[position][0]],
                slots[position][1],
                position,
            ),
        )
    )

    def secondary_key(slot_points: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(slot_points[position] for position in presentation_positions)

    # Dynamic programming over used lineup-slot bitmasks. Each state keeps the
    # authoritative points total plus a points vector by actual slot. The vector
    # is consulted only when totals are exactly equal, using the explicit human
    # presentation order above. It therefore cannot alter lineup value.
    empty_slot_points = tuple(float("-inf") for _ in slots)
    states: dict[int, tuple[float, tuple[float, ...], tuple[tuple[int, str], ...]]] = {
        0: (0.0, empty_slot_points, ())
    }
    for player_id in candidate_ids:
        player = players_by_id[player_id]
        points = latest_forecast[player_id].distribution.mean
        next_states = dict(states)
        for mask, (score, slot_points, assignments) in states.items():
            for slot_position, (slot, _) in enumerate(slots):
                bit = 1 << slot_position
                if mask & bit:
                    continue
                if player.position not in _STARTER_ELIGIBILITY[slot]:
                    continue
                new_mask = mask | bit
                next_slot_points = list(slot_points)
                next_slot_points[slot_position] = points
                candidate = (
                    score + points,
                    tuple(next_slot_points),
                    assignments + ((slot_position, player_id),),
                )
                prior = next_states.get(new_mask)
                if prior is None:
                    next_states[new_mask] = candidate
                    continue
                score_better = candidate[0] > prior[0] + 1e-12
                score_equal = abs(candidate[0] - prior[0]) <= 1e-12
                candidate_secondary = secondary_key(candidate[1])
                prior_secondary = secondary_key(prior[1])
                secondary_better = candidate_secondary > prior_secondary
                stable_id_tiebreak = candidate_secondary == prior_secondary and candidate[2] < prior[2]
                if score_better or (score_equal and (secondary_better or stable_id_tiebreak)):
                    next_states[new_mask] = candidate
        states = next_states

    full_mask = (1 << len(slots)) - 1
    if full_mask not in states:
        raise ValueError("team cannot fill every required lineup slot from eligible forecasted players")

    expected_points, _, chosen = states[full_mask]
    chosen_by_slot = {slot_position: player_id for slot_position, player_id in chosen}
    assignments = tuple(
        LineupAssignment(
            slot=slot,
            slot_index=slot_index,
            player_id=chosen_by_slot[position],
            position=players_by_id[chosen_by_slot[position]].position,
            expected_points=latest_forecast[chosen_by_slot[position]].distribution.mean,
        )
        for position, (slot, slot_index) in enumerate(slots)
    )
    starter_ids = {assignment.player_id for assignment in assignments}
    bench_ids = tuple(sorted(set(candidate_ids) - starter_ids))

    return OptimizedTeamLineup(
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
        assignments=assignments,
        expected_points=expected_points,
        bench_player_ids=bench_ids,
        unavailable_player_ids=tuple(sorted(unavailable)),
        missing_forecast_player_ids=tuple(missing),
        model_version=model_version,
    )


def marginal_lineup_impact(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    player_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    model_version: str = "next4-marginal-lineup-v1",
) -> MarginalLineupImpact:
    """Measure a player's marginal lineup value against the team's real alternative."""

    baseline = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
    )
    without = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
        excluded_player_ids=frozenset({player_id}),
    )
    baseline_starters = {item.player_id for item in baseline.assignments}
    without_starters = {item.player_id for item in without.assignments}
    replacements = tuple(sorted(without_starters - baseline_starters))
    delta = max(0.0, baseline.expected_points - without.expected_points)
    return MarginalLineupImpact(
        team_id=team_id,
        player_id=player_id,
        as_of=as_of,
        horizon=horizon,
        baseline_expected_points=baseline.expected_points,
        without_player_expected_points=without.expected_points,
        marginal_expected_points=delta,
        replacement_player_ids=replacements,
        model_version=model_version,
    )
