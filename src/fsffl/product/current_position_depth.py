from __future__ import annotations

from typing import Literal

from pydantic import Field

from fsffl.forecast.season_comparison import (
    build_participation_adjusted_outlook, outlook_evidence_labels,
)
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState, Position, RosterSlot
from fsffl.team_utility.lineup import optimize_team_lineup
from fsffl.team_utility.models import LineupAssignment


CURRENT_POSITION_DEPTH_MODEL_VERSION = (
    "league-atlas-current-position-depth-v3:shared-participation-outlook:"
    "completed-actuals-plus-ros:configured-slot-attribution"
)

_CURRENT_SLOT_ORDER: tuple[RosterSlot, ...] = (
    RosterSlot.QB,
    RosterSlot.RB,
    RosterSlot.WR,
    RosterSlot.TE,
    RosterSlot.FLEX,
    RosterSlot.SUPERFLEX,
    RosterSlot.K,
    RosterSlot.DST,
)

_SLOT_ELIGIBILITY: dict[RosterSlot, frozenset[Position]] = {
    RosterSlot.QB: frozenset({Position.QB}),
    RosterSlot.RB: frozenset({Position.RB}),
    RosterSlot.WR: frozenset({Position.WR}),
    RosterSlot.TE: frozenset({Position.TE}),
    RosterSlot.FLEX: frozenset({Position.RB, Position.WR, Position.TE}),
    RosterSlot.SUPERFLEX: frozenset(
        {Position.QB, Position.RB, Position.WR, Position.TE}
    ),
    RosterSlot.K: frozenset({Position.K}),
    RosterSlot.DST: frozenset({Position.DST}),
}


class CurrentPositionSlotDefinition(FrozenModel):
    slot: RosterSlot
    configured_count: int
    eligible_positions: tuple[Position, ...]
    status: Literal["ready", "unavailable"]
    reason: str | None = None
    incomplete_team_ids: tuple[str, ...] = ()


class CurrentPositionSlotStrength(FrozenModel):
    team_id: str
    slot: RosterSlot
    configured_count: int
    starter_count: int
    expected_points: float | None = None
    league_average_expected_points: float | None = None
    strength_index: float | None = None
    league_rank: int | None = None
    team_count: int
    status: Literal["ready", "unavailable"]
    reason: str | None = None


class CurrentPositionPlayerEvidence(FrozenModel):
    team_id: str
    player_id: str
    position: Position
    roster_slot: RosterSlot
    season_outlook_points: float | None = None
    season_outlook_source: str | None = None
    season_outlook_model_version: str | None = None
    assigned_slot: RosterSlot | None = None
    assigned_slot_index: int | None = None
    season_outlook_failure: str | None = None
    ros_basis: str | None = None
    low_confidence: bool = False
    participation_basis: str | None = None
    participation_assumption: bool = False
    participation_reason: str | None = None
    participation_source: str | None = None
    participation_source_version: str | None = None
    participation_observed_at: str | None = None
    ros_model_version: str | None = None
    ros_as_of: str | None = None


class CurrentPositionDepthContract(FrozenModel):
    status: Literal["ready", "partial", "unavailable"]
    league_id: str
    league_state_id: str
    completed_through_week: int | None = None
    evidence_basis: str
    forecast_as_of: str | None = None
    slot_order: tuple[RosterSlot, ...]
    slots: tuple[CurrentPositionSlotDefinition, ...]
    strengths: tuple[CurrentPositionSlotStrength, ...]
    players: tuple[CurrentPositionPlayerEvidence, ...]
    reason: str | None = None
    model_version: str = CURRENT_POSITION_DEPTH_MODEL_VERSION
    player_coverage_failures: dict[str, str] = Field(default_factory=dict)


def configured_current_slots(
    league_state: LeagueState,
) -> tuple[tuple[RosterSlot, int], ...]:
    """Return configured supported starter-slot types in league-defined order."""

    counts: dict[RosterSlot, int] = {}
    for requirement in league_state.league.rules.lineup:
        if requirement.count <= 0 or requirement.slot not in _SLOT_ELIGIBILITY:
            continue
        counts[requirement.slot] = counts.get(requirement.slot, 0) + requirement.count
    return tuple(
        (slot, counts[slot])
        for slot in _CURRENT_SLOT_ORDER
        if slot in counts
    )


def _unavailable_contract(
    league_state: LeagueState,
    *,
    reason: str,
    evidence_basis: str = "unavailable",
    completed_through_week: int | None = None,
    season_outlook_failures: dict[str, str] | None = None,
) -> CurrentPositionDepthContract:
    configured = configured_current_slots(league_state)
    slots = tuple(
        CurrentPositionSlotDefinition(
            slot=slot,
            configured_count=count,
            eligible_positions=tuple(
                sorted(_SLOT_ELIGIBILITY[slot], key=lambda item: item.value)
            ),
            status="unavailable",
            reason=reason,
        )
        for slot, count in configured
    )
    strengths = tuple(
        CurrentPositionSlotStrength(
            team_id=team.team_id,
            slot=slot,
            configured_count=count,
            starter_count=0,
            team_count=len(league_state.teams),
            status="unavailable",
            reason=reason,
        )
        for team in sorted(league_state.teams, key=lambda item: item.team_id)
        for slot, count in configured
    )
    players = tuple(
        CurrentPositionPlayerEvidence(
            team_id=team_state.team_id,
            player_id=entry.player_id,
            position=next(
                player.position
                for player in league_state.players
                if player.player_id == entry.player_id
            ),
            roster_slot=entry.slot,
            season_outlook_failure=(season_outlook_failures or {}).get(entry.player_id),
        )
        for team_state in sorted(
            league_state.team_states, key=lambda item: item.team_id
        )
        for entry in team_state.roster
    )
    return CurrentPositionDepthContract(
        status="unavailable",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        completed_through_week=completed_through_week,
        evidence_basis=evidence_basis,
        slot_order=tuple(slot for slot, _ in configured),
        slots=slots,
        strengths=strengths,
        players=players,
        reason=reason,
        player_coverage_failures=dict(season_outlook_failures or {}),
    )


def unavailable_current_position_depth(
    league_state: LeagueState,
    *,
    reason: str,
) -> CurrentPositionDepthContract:
    return _unavailable_contract(league_state, reason=reason)


def build_current_position_depth_from_outlook(
    league_state: LeagueState,
    *,
    season_outlook: tuple[ForecastObservation, ...],
    evidence_basis: str,
    completed_through_week: int,
    season_outlook_failures: dict[str, str] | None = None,
    player_outlook_evidence: dict[str, dict[str, object]] | None = None,
) -> CurrentPositionDepthContract:
    """Build Current Position & Depth from governed season-outlook evidence.

    The lineup is optimized jointly under the league's real slot rules. Strength is
    then attributed to the configured lineup slot, not back to the player's actual
    position. Depth/player evidence remains separate from the slot-strength numerator.
    """

    configured = configured_current_slots(league_state)
    if not configured:
        return _unavailable_contract(
            league_state,
            reason="League has no supported configured starting lineup slots.",
            evidence_basis=evidence_basis,
            completed_through_week=completed_through_week,
        )

    outlook = tuple(
        item
        for item in season_outlook
        if item.metric == ForecastMetric.FANTASY_POINTS
        and item.horizon == ForecastHorizon.SEASON
    )
    if not outlook:
        return _unavailable_contract(
            league_state,
            reason="Governed completed-actuals + ROS season outlook is unavailable.",
            evidence_basis=evidence_basis,
            completed_through_week=completed_through_week,
            season_outlook_failures=season_outlook_failures,
        )

    forecast_as_of = max(item.as_of for item in outlook)
    lineup_as_of = max(league_state.as_of, forecast_as_of)
    ordered_teams = tuple(sorted(league_state.teams, key=lambda item: item.team_id))
    lineups = {
        team.team_id: optimize_team_lineup(
            league_state,
            outlook,
            team_id=team.team_id,
            as_of=lineup_as_of,
            horizon=ForecastHorizon.SEASON,
            allow_unfilled_slots=True,
            model_version="league-atlas-current-lineup-v1:completed-actuals-plus-ros",
        )
        for team in ordered_teams
    }

    assignment_totals: dict[tuple[str, RosterSlot], tuple[int, float]] = {}
    assignment_by_player: dict[tuple[str, str], LineupAssignment] = {}
    for team in ordered_teams:
        lineup = lineups[team.team_id]
        for assignment in lineup.assignments:
            key = (team.team_id, assignment.slot)
            count, points = assignment_totals.get(key, (0, 0.0))
            assignment_totals[key] = (
                count + 1,
                points + float(assignment.expected_points),
            )
            assignment_by_player[(team.team_id, assignment.player_id)] = assignment

    slot_definitions: list[CurrentPositionSlotDefinition] = []
    strengths: list[CurrentPositionSlotStrength] = []
    team_count = len(ordered_teams)

    for slot, configured_count in configured:
        counts = {
            team.team_id: assignment_totals.get((team.team_id, slot), (0, 0.0))[0]
            for team in ordered_teams
        }
        incomplete = tuple(
            team_id
            for team_id, starter_count in counts.items()
            if starter_count < configured_count
        )
        if incomplete:
            reason = (
                "Governed Current outlook cannot fill every configured "
                f"{slot.value} slot for all league teams; missing evidence is not scored as zero."
            )
            slot_definitions.append(
                CurrentPositionSlotDefinition(
                    slot=slot,
                    configured_count=configured_count,
                    eligible_positions=tuple(
                        sorted(_SLOT_ELIGIBILITY[slot], key=lambda item: item.value)
                    ),
                    status="unavailable",
                    reason=reason,
                    incomplete_team_ids=incomplete,
                )
            )
            for team in ordered_teams:
                strengths.append(
                    CurrentPositionSlotStrength(
                        team_id=team.team_id,
                        slot=slot,
                        configured_count=configured_count,
                        starter_count=counts[team.team_id],
                        team_count=team_count,
                        status="unavailable",
                        reason=reason,
                    )
                )
            continue

        rows = [
            (
                team.team_id,
                assignment_totals.get((team.team_id, slot), (0, 0.0))[0],
                assignment_totals.get((team.team_id, slot), (0, 0.0))[1],
            )
            for team in ordered_teams
        ]
        league_average = (
            sum(points for _, _, points in rows) / team_count
            if team_count
            else 0.0
        )
        ordered = sorted(rows, key=lambda item: (-item[2], item[0]))
        rank_by_team = {
            team_id: rank
            for rank, (team_id, _, _) in enumerate(ordered, start=1)
        }
        slot_definitions.append(
            CurrentPositionSlotDefinition(
                slot=slot,
                configured_count=configured_count,
                eligible_positions=tuple(
                    sorted(_SLOT_ELIGIBILITY[slot], key=lambda item: item.value)
                ),
                status="ready",
            )
        )
        for team_id, starter_count, expected_points in rows:
            strengths.append(
                CurrentPositionSlotStrength(
                    team_id=team_id,
                    slot=slot,
                    configured_count=configured_count,
                    starter_count=starter_count,
                    expected_points=expected_points,
                    league_average_expected_points=league_average,
                    strength_index=(
                        100.0 * expected_points / league_average
                        if league_average > 0
                        else None
                    ),
                    league_rank=rank_by_team[team_id],
                    team_count=team_count,
                    status="ready",
                )
            )

    latest_outlook: dict[str, ForecastObservation] = {}
    for observation in outlook:
        prior = latest_outlook.get(observation.player_id)
        if prior is None or (
            observation.as_of,
            observation.model_version,
            observation.source,
        ) > (
            prior.as_of,
            prior.model_version,
            prior.source,
        ):
            latest_outlook[observation.player_id] = observation

    players_by_id = {player.player_id: player for player in league_state.players}
    player_rows: list[CurrentPositionPlayerEvidence] = []
    for team_state in sorted(league_state.team_states, key=lambda item: item.team_id):
        for entry in team_state.roster:
            player = players_by_id[entry.player_id]
            observation = latest_outlook.get(entry.player_id)
            assignment = assignment_by_player.get(
                (team_state.team_id, entry.player_id)
            )
            player_rows.append(
                CurrentPositionPlayerEvidence(
                    team_id=team_state.team_id,
                    player_id=entry.player_id,
                    position=player.position,
                    roster_slot=entry.slot,
                    **{key: value for key, value in (player_outlook_evidence or {}).get(entry.player_id, {}).items()
                       if key in {"ros_basis", "low_confidence", "participation_basis",
                                  "participation_assumption", "participation_reason", "participation_source",
                                  "participation_source_version", "participation_observed_at",
                                  "ros_model_version", "ros_as_of"}},
                    season_outlook_failure=(season_outlook_failures or {}).get(entry.player_id),
                    season_outlook_points=(
                        float(observation.distribution.mean)
                        if observation is not None
                        else None
                    ),
                    season_outlook_source=(
                        observation.source if observation is not None else None
                    ),
                    season_outlook_model_version=(
                        observation.model_version if observation is not None else None
                    ),
                    assigned_slot=(
                        assignment.slot if assignment is not None else None
                    ),
                    assigned_slot_index=(
                        assignment.slot_index if assignment is not None else None
                    ),
                )
            )

    ready_count = sum(1 for item in slot_definitions if item.status == "ready")
    status: Literal["ready", "partial", "unavailable"]
    if ready_count == len(slot_definitions):
        status = "ready"
    elif ready_count:
        status = "partial"
    else:
        status = "unavailable"

    return CurrentPositionDepthContract(
        status=status,
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        completed_through_week=completed_through_week,
        evidence_basis=evidence_basis,
        forecast_as_of=forecast_as_of.isoformat(),
        slot_order=tuple(slot for slot, _ in configured),
        slots=tuple(slot_definitions),
        strengths=tuple(
            sorted(strengths, key=lambda item: (item.team_id, item.slot.value))
        ),
        players=tuple(
            sorted(player_rows, key=lambda item: (item.team_id, item.player_id))
        ),
        player_coverage_failures=dict(season_outlook_failures or {}),
        reason=(
            None
            if status == "ready"
            else "One or more configured lineup slots lack complete governed Current outlook authority."
        ),
    )


def build_governed_current_position_depth(
    league_state: LeagueState,
    *,
    preseason_season_forecasts: tuple[ForecastObservation, ...],
    history_writer=None,
    stats_source=None,
    clock=None,
) -> CurrentPositionDepthContract:
    """Resolve the accepted governed Current authority and build slot strength."""

    try:
        governed, participation, _ = build_participation_adjusted_outlook(
            league_state,
            preseason_forecasts=preseason_season_forecasts,
            history_store=history_writer,
            stats_source=stats_source, clock=clock,
        )
    except Exception as exc:
        return _unavailable_contract(
            league_state,
            reason=(
                "Governed completed-actuals + ROS Current authority is unavailable: "
                f"{type(exc).__name__}: {exc}"
            ),
        )

    return build_current_position_depth_from_outlook(
        league_state,
        season_outlook=governed.season_outlook,
        evidence_basis=governed.evidence_basis,
        completed_through_week=governed.completed_through_week,
        season_outlook_failures=getattr(governed, "season_outlook_failures", {}),
        player_outlook_evidence={
            row.player_id: {
                **outlook_evidence_labels(row, governed.evidence_basis, participation.get(row.player_id)),
                "ros_model_version": row.model_version,
                "ros_as_of": row.as_of.isoformat(),
            }
            for row in getattr(governed, "forward_forecasts", ())
        },
    )
