from __future__ import annotations

import math
from typing import Literal

from fsffl.value.shapley_intrinsic_contract import (
    RAW_INTRINSIC_QUANTITY,
    SHAPLEY_INTRINSIC_CONTRACT_VERSION,
    SHAPLEY_INTRINSIC_MODEL_VERSION,
    ShapleyIntrinsicContract,
    ShapleyIntrinsicAvailability,
    discounted_three_year_shapley_value,
)
from fsffl.state.models import FrozenModel, LeagueState, Position
from fsffl.value.career_forward_intrinsic import (
    CAREER_FORWARD_AGGREGATION,
    CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
    CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
    CAREER_FORWARD_RAW_QUANTITY,
    CareerForwardIntrinsicShadowContract,
)
from fsffl.value.shapley_intrinsic import FROZEN_INTRINSIC_DISCOUNT


DYNASTY_POSITION_ROOM_MODEL_VERSION = "analytics-dynasty-position-room-career-forward-v1"
DYNASTY_ROOM_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)
THREE_YEAR_POSITION_ROOM_MODEL_VERSION = (
    "analytics-position-room-three-year-intrinsic-v2:career-current-annual-extension"
)


class ThreeYearIntrinsicPlayerValue(FrozenModel):
    """One raw, exact-State 3-Year value and its accepted component source."""

    player_id: str
    position: Position
    raw_intrinsic_value: float
    source: Literal[
        "standalone_three_year_shapley",
        "career_current_y1_y3_discounted_extension",
    ]


class DynastyPositionRoom(FrozenModel):
    """Team-position allocation of governed holistic career-forward raw authority."""

    team_id: str
    position: Position
    room_raw: float | None
    rostered_player_count: int | None
    league_rank: int | None
    strength_index: float | None
    team_count: int
    coverage_count: int
    evidence_complete: bool
    league_state_id: str | None
    model_version: str = DYNASTY_POSITION_ROOM_MODEL_VERSION


def build_dynasty_position_rooms(
    league_state: LeagueState,
    *,
    career_forward: CareerForwardIntrinsicShadowContract | None = None,
    evidence_state_id: str | None = None,
    positions: tuple[Position, ...] = DYNASTY_ROOM_POSITIONS,
) -> tuple[DynastyPositionRoom, ...]:
    """Aggregate raw career-forward references over canonical positional rooms.

    Each canonically rostered player contributes once at their actual position,
    irrespective of lineup or roster slot. Missing roster, player, position, or
    same-State Foundation 4 evidence is never imputed as zero. League rank/index
    are emitted only when every team's room for that position is complete.
    """

    contract_valid = (
        career_forward is not None
        and career_forward.evaluation_season == league_state.league.season
        and career_forward.raw_quantity == CAREER_FORWARD_RAW_QUANTITY
        and career_forward.aggregation == CAREER_FORWARD_AGGREGATION
        and not career_forward.display_scaling_applied
        and not career_forward.market_inputs_used
        and evidence_state_id == league_state.state_id
        and bool(evidence_state_id)
    )
    values = (
        {row.player_id: (row.position, row.raw_career_forward_reference)
         for row in career_forward.estimates}
        if contract_valid and career_forward is not None else {}
    )
    return _position_rooms(
        league_state, values=values,
        contract_valid=contract_valid, evidence_state_id=evidence_state_id,
        positions=positions, model_version=DYNASTY_POSITION_ROOM_MODEL_VERSION,
    )


def build_three_year_position_rooms(
    league_state: LeagueState, *, intrinsic: ShapleyIntrinsicContract | None,
    evidence_state_id: str | None,
    career_forward: CareerForwardIntrinsicShadowContract | None = None,
    career_evidence_state_id: str | None = None,
    positions: tuple[Position, ...] = DYNASTY_ROOM_POSITIONS,
) -> tuple[DynastyPositionRoom, ...]:
    """Allocate raw 3-Year Shapley values with exact-State roster gap recovery.

    Existing stand-alone discounted 3-Year values always win unchanged. Only a
    current-State roster gap may be derived from the completed Career object's
    retained raw Current Y1-Y3 Shapley components, using the same Value-owned
    discount function. Later Career horizons and the Career total never enter.
    """
    player_values = build_three_year_intrinsic_player_values(
        league_state,
        intrinsic=intrinsic,
        evidence_state_id=evidence_state_id,
        career_forward=career_forward,
        career_evidence_state_id=career_evidence_state_id,
    )
    values = {
        row.player_id: (row.position, row.raw_intrinsic_value)
        for row in player_values
    }
    evidence_valid = bool(player_values)
    return _position_rooms(
        league_state, values=values, contract_valid=evidence_valid,
        evidence_state_id=(league_state.state_id if evidence_valid else None),
        positions=positions,
        model_version=THREE_YEAR_POSITION_ROOM_MODEL_VERSION,
    )


def build_three_year_intrinsic_player_values(
    league_state: LeagueState, *, intrinsic: ShapleyIntrinsicContract | None,
    evidence_state_id: str | None,
    career_forward: CareerForwardIntrinsicShadowContract | None = None,
    career_evidence_state_id: str | None = None,
) -> tuple[ThreeYearIntrinsicPlayerValue, ...]:
    """Return accepted stand-alone values plus missing roster values if proven."""
    players = {row.player_id: row for row in league_state.players}
    standalone_valid = (
        intrinsic is not None
        and intrinsic.status == ShapleyIntrinsicAvailability.READY
        and intrinsic.contract_version == SHAPLEY_INTRINSIC_CONTRACT_VERSION
        and intrinsic.intrinsic_model_version == SHAPLEY_INTRINSIC_MODEL_VERSION
        and intrinsic.evaluation_season == league_state.league.season
        and intrinsic.target_years == tuple(
            league_state.league.season + offset for offset in range(3)
        )
        and intrinsic.quantity_semantics == RAW_INTRINSIC_QUANTITY
        and math.isclose(
            intrinsic.discount, FROZEN_INTRINSIC_DISCOUNT,
            rel_tol=0.0, abs_tol=1e-12,
        )
        and not intrinsic.display_scaling_applied
        and not intrinsic.diagnostic_h1_included
        and bool(evidence_state_id)
        and evidence_state_id == league_state.state_id
    )
    standalone_rows = intrinsic.estimates if standalone_valid and intrinsic is not None else ()
    standalone_ids = [row.player_id for row in standalone_rows]
    standalone_ambiguous = len(set(standalone_ids)) != len(standalone_ids)
    if standalone_ambiguous:
        standalone_rows = ()

    output: dict[str, ThreeYearIntrinsicPlayerValue] = {}
    for row in standalone_rows:
        player = players.get(row.player_id)
        if player is None or player.position not in DYNASTY_ROOM_POSITIONS:
            continue
        if not math.isfinite(row.raw_intrinsic_value):
            continue
        output[row.player_id] = ThreeYearIntrinsicPlayerValue(
            player_id=row.player_id,
            position=player.position,
            raw_intrinsic_value=float(row.raw_intrinsic_value),
            source="standalone_three_year_shapley",
        )

    career_valid = (
        standalone_valid
        and not standalone_ambiguous
        and career_forward is not None
        and career_forward.status == "shadow_ready"
        and career_forward.contract_version == CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION
        and career_forward.model_version == CAREER_FORWARD_INTRINSIC_MODEL_VERSION
        and career_forward.evaluation_season == league_state.league.season
        and career_forward.current_intrinsic_contract_version
            == SHAPLEY_INTRINSIC_CONTRACT_VERSION
        and career_forward.raw_quantity == CAREER_FORWARD_RAW_QUANTITY
        and career_forward.aggregation == CAREER_FORWARD_AGGREGATION
        and not career_forward.display_scaling_applied
        and not career_forward.market_inputs_used
        and not career_forward.authoritative_for_current_intrinsic
        and not career_forward.current_intrinsic_replaced
        and bool(career_evidence_state_id)
        and career_evidence_state_id == league_state.state_id
    )
    if not career_valid or career_forward is None:
        return tuple(output[key] for key in sorted(output))

    rostered_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    career_rows = {row.player_id: row for row in career_forward.estimates}
    if len(career_rows) != len(career_forward.estimates):
        return tuple(output[key] for key in sorted(output))

    # Extension is strictly additive for absent cohort identities. An existing
    # but malformed stand-alone row is not silently replaced by another source.
    standalone_present_ids = set(standalone_ids) if standalone_valid else set()
    for player_id in sorted(rostered_ids - standalone_present_ids - set(output)):
        player = players.get(player_id)
        estimate = career_rows.get(player_id)
        if (
            player is None
            or player.position not in DYNASTY_ROOM_POSITIONS
            or estimate is None
            or estimate.position != player.position
            or estimate.raw_quantity != CAREER_FORWARD_RAW_QUANTITY
            or estimate.aggregation != CAREER_FORWARD_AGGREGATION
            or estimate.discounting_applied
            or estimate.display_index_arithmetic_used
            or estimate.market_inputs_used
            or estimate.current_intrinsic_replaced
        ):
            continue
        annual = estimate.uncertainty.current_y1_y3
        if tuple(item.year_index for item in annual) != (1, 2, 3):
            continue
        if tuple(item.target_season for item in annual) != tuple(
            league_state.league.season + offset for offset in range(3)
        ):
            continue
        contributions = tuple(float(item.raw_shapley_contribution) for item in annual)
        if not all(math.isfinite(value) for value in contributions):
            continue
        current_total = sum(contributions)
        if (
            not math.isfinite(estimate.current_intrinsic_raw_y1_y3)
            or not math.isclose(
                current_total,
                estimate.current_intrinsic_raw_y1_y3,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        ):
            continue
        try:
            raw_three_year = discounted_three_year_shapley_value(contributions)
        except ValueError:
            continue
        output[player_id] = ThreeYearIntrinsicPlayerValue(
            player_id=player_id,
            position=player.position,
            raw_intrinsic_value=raw_three_year,
            source="career_current_y1_y3_discounted_extension",
        )
    return tuple(output[key] for key in sorted(output))


def three_year_source_reconciles_career_components(
    league_state: LeagueState,
    *,
    intrinsic: ShapleyIntrinsicContract | None,
    evidence_state_id: str | None,
    career_forward: CareerForwardIntrinsicShadowContract | None,
    career_evidence_state_id: str | None,
) -> bool:
    """Prove that one exact-State 3-Year source matches Career's Current rows.

    This is used when creating a publication manifest. It lets the manifest bind
    both input fingerprints to one generation; it never loads or resolves inputs.
    """
    if (
        intrinsic is None
        or intrinsic.status != ShapleyIntrinsicAvailability.READY
        or intrinsic.contract_version != SHAPLEY_INTRINSIC_CONTRACT_VERSION
        or intrinsic.intrinsic_model_version != SHAPLEY_INTRINSIC_MODEL_VERSION
        or intrinsic.evaluation_season != league_state.league.season
        or intrinsic.target_years != tuple(
            league_state.league.season + offset for offset in range(3)
        )
        or intrinsic.quantity_semantics != RAW_INTRINSIC_QUANTITY
        or not math.isclose(
            intrinsic.discount, FROZEN_INTRINSIC_DISCOUNT,
            rel_tol=0.0, abs_tol=1e-12,
        )
        or intrinsic.display_scaling_applied
        or intrinsic.diagnostic_h1_included
        or not evidence_state_id
        or evidence_state_id != league_state.state_id
        or career_forward is None
        or career_forward.status != "shadow_ready"
        or career_forward.contract_version != CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION
        or career_forward.model_version != CAREER_FORWARD_INTRINSIC_MODEL_VERSION
        or career_forward.evaluation_season != league_state.league.season
        or career_forward.current_intrinsic_contract_version
            != SHAPLEY_INTRINSIC_CONTRACT_VERSION
        or career_forward.raw_quantity != CAREER_FORWARD_RAW_QUANTITY
        or career_forward.aggregation != CAREER_FORWARD_AGGREGATION
        or career_forward.display_scaling_applied
        or career_forward.market_inputs_used
        or career_forward.authoritative_for_current_intrinsic
        or career_forward.current_intrinsic_replaced
        or not career_evidence_state_id
        or career_evidence_state_id != league_state.state_id
    ):
        return False

    career_rows = {row.player_id: row for row in career_forward.estimates}
    if (
        len(career_rows) != len(career_forward.estimates)
        or career_forward.player_count != len(career_forward.estimates)
    ):
        return False
    intrinsic_ids = {row.player_id for row in intrinsic.estimates}
    coverage = getattr(intrinsic, "coverage", None)
    if (
        not intrinsic_ids
        or len(intrinsic_ids) != len(intrinsic.estimates)
        or coverage is None
        or getattr(coverage, "player_count", None) != len(intrinsic.estimates)
    ):
        return False
    shared_count = 0
    for row in intrinsic.estimates:
        estimate = career_rows.get(row.player_id)
        if estimate is None:
            continue
        shared_count += 1
        if (
            estimate.raw_quantity != CAREER_FORWARD_RAW_QUANTITY
            or estimate.aggregation != CAREER_FORWARD_AGGREGATION
            or estimate.discounting_applied
            or estimate.display_index_arithmetic_used
            or estimate.market_inputs_used
            or estimate.current_intrinsic_replaced
        ):
            return False
        try:
            annual = estimate.uncertainty.current_y1_y3
            if (
                tuple(item.year_index for item in annual) != (1, 2, 3)
                or tuple(item.target_season for item in annual)
                != tuple(league_state.league.season + offset for offset in range(3))
            ):
                return False
            contributions = tuple(
                float(item.raw_shapley_contribution) for item in annual
            )
            raw_current = float(estimate.current_intrinsic_raw_y1_y3)
            raw_three_year = float(row.raw_intrinsic_value)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return False
        if not all(math.isfinite(value) for value in contributions):
            return False
        if (
            not math.isfinite(raw_current)
            or not math.isclose(
                sum(contributions), raw_current,
                rel_tol=0.0, abs_tol=1e-9,
            )
            or not math.isfinite(raw_three_year)
        ):
            return False
        try:
            rebuilt = discounted_three_year_shapley_value(contributions)
        except ValueError:
            return False
        if not math.isclose(rebuilt, raw_three_year, rel_tol=0.0, abs_tol=1e-9):
            return False
    return shared_count > 0


def _position_rooms(
    league_state: LeagueState, *, values: dict[str, tuple[Position, float]],
    contract_valid: bool, evidence_state_id: str | None,
    positions: tuple[Position, ...], model_version: str,
) -> tuple[DynastyPositionRoom, ...]:
    teams = tuple(sorted(league_state.teams, key=lambda item: item.team_id))
    states = {item.team_id: item for item in league_state.team_states}
    players = {item.player_id: item for item in league_state.players}
    team_rosters: dict[str, tuple[tuple[str, Position], ...] | None] = {}
    for team in teams:
        team_state = states.get(team.team_id)
        if team_state is None:
            team_rosters[team.team_id] = None
            continue
        roster: list[tuple[str, Position]] = []
        for entry in team_state.roster:
            player = players.get(entry.player_id)
            if player is None:
                roster = []
                team_rosters[team.team_id] = None
                break
            roster.append((player.player_id, player.position))
        else:
            team_rosters[team.team_id] = tuple(roster)

    output: list[DynastyPositionRoom] = []
    for position in positions:
        partial: dict[str, tuple[int, float | None] | None] = {}
        for team in teams:
            roster = team_rosters.get(team.team_id)
            if roster is None:
                partial[team.team_id] = None
                continue
            members = tuple((pid, actual) for pid, actual in roster if actual == position)
            total = 0.0
            complete = contract_valid
            for player_id, actual_position in members:
                estimate = values.get(player_id)
                if (
                    estimate is None
                    or estimate[0] != actual_position
                    or not math.isfinite(estimate[1])
                ):
                    complete = False
                    break
                total += estimate[1]
            partial[team.team_id] = (len(members), total if complete else None)

        complete_totals = {
            team_id: row[1]
            for team_id, row in partial.items()
            if row is not None and row[1] is not None
        }
        league_complete = len(complete_totals) == len(teams) and bool(teams)
        average = (
            sum(complete_totals.values()) / len(complete_totals)
            if league_complete
            else None
        )
        ordered = sorted(complete_totals.items(), key=lambda item: (-item[1], item[0]))
        ranks: dict[str, int] = {}
        previous_value: float | None = None
        previous_rank = 0
        for index, (team_id, value) in enumerate(ordered, start=1):
            if previous_value is None or value != previous_value:
                previous_rank = index
                previous_value = value
            ranks[team_id] = previous_rank

        for team in teams:
            room = partial.get(team.team_id)
            room_raw = room[1] if room is not None else None
            strength_index = (
                (100.0 * room_raw / average)
                if league_complete and average is not None and average > 0 and room_raw is not None
                else None
            )
            output.append(
                DynastyPositionRoom(
                    team_id=team.team_id,
                    position=position,
                    room_raw=room_raw,
                    rostered_player_count=(room[0] if room is not None else None),
                    league_rank=(ranks.get(team.team_id) if league_complete else None),
                    strength_index=strength_index,
                    team_count=len(teams),
                    coverage_count=len(complete_totals),
                    evidence_complete=room is not None and room_raw is not None,
                    league_state_id=(evidence_state_id if room_raw is not None else None),
                    model_version=model_version,
                )
            )
    return tuple(output)
