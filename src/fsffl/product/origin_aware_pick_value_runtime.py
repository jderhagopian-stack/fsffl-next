from __future__ import annotations

from fsffl.state.models import LeagueState
from fsffl.team_utility.simulation import RegularSeasonSimulationResult
from fsffl.value.historical_pick import HistoricalDraftSlotObservation
from fsffl.value.models import ValueScale
from fsffl.value.origin_aware_pick import (
    GenericPickValuePrior,
    OriginAwarePickValueResult,
    OriginPickProbabilityEvidence,
    OriginSlotProbabilityEvidence,
    build_origin_aware_pick_values,
)


def build_origin_probability_evidence_from_simulation(
    simulation: RegularSeasonSimulationResult,
    *,
    next_draft_season: int,
) -> tuple[OriginPickProbabilityEvidence, ...]:
    """Translate Simulation-owned slot distributions into Value-neutral evidence.

    Product/runtime orchestration is the authority boundary allowed to depend on
    both NEXT-4 Simulation and NEXT-3 Value. No probability or economic math is
    introduced here.
    """

    rows: list[OriginPickProbabilityEvidence] = []
    seen_origins: set[str] = set()
    for distribution in simulation.future_pick_distributions:
        if distribution.draft_season != next_draft_season:
            continue
        if distribution.original_team_id in seen_origins:
            raise ValueError(
                "Simulation future-pick distributions require unique origin teams"
            )
        if distribution.simulation_count != simulation.simulation_count:
            raise ValueError(
                "origin distribution Simulation count must match canonical result"
            )
        seen_origins.add(distribution.original_team_id)
        rows.append(
            OriginPickProbabilityEvidence(
                draft_season=distribution.draft_season,
                original_team_id=distribution.original_team_id,
                slot_probabilities=tuple(
                    OriginSlotProbabilityEvidence(
                        slot_in_round=item.slot_in_round,
                        probability=item.probability,
                    )
                    for item in distribution.slot_probabilities
                    if item.probability > 0
                ),
                expected_slot=distribution.expected_slot,
                median_slot=distribution.median_slot,
                early_probability=distribution.early_probability,
                mid_probability=distribution.mid_probability,
                late_probability=distribution.late_probability,
                simulation_count=distribution.simulation_count,
                simulation_model_version=distribution.simulation_model_version,
                simulation_input_fingerprint=simulation.simulation_input_fingerprint,
                draft_order_policy_id=distribution.draft_order_policy_id,
                draft_order_policy_version=distribution.draft_order_policy_version,
                draft_order_policy_authority=(
                    distribution.draft_order_policy_authority
                ),
                draft_order_projection_model_version=(
                    distribution.draft_order_projection_model_version
                ),
                provenance=distribution.provenance,
            )
        )
    return tuple(sorted(rows, key=lambda item: item.original_team_id))


def build_origin_aware_pick_values_from_simulation(
    league_state: LeagueState,
    simulation: RegularSeasonSimulationResult,
    *,
    slot_value_observations: tuple[HistoricalDraftSlotObservation, ...],
    slot_value_scale: ValueScale,
    generic_priors: tuple[GenericPickValuePrior, ...] = (),
) -> tuple[OriginAwarePickValueResult, ...]:
    """Coordinate Simulation probability evidence with Value-owned economics."""

    evidence = build_origin_probability_evidence_from_simulation(
        simulation,
        next_draft_season=league_state.league.season + 1,
    )
    return build_origin_aware_pick_values(
        league_state,
        evidence,
        slot_value_observations=slot_value_observations,
        slot_value_scale=slot_value_scale,
        generic_priors=generic_priors,
    )
