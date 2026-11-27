"""Translate published Simulation evidence to an already released Value prior."""
from types import MappingProxyType

from fsffl.state.settled_draft_order import settled_origin_order

from fsffl.value.native_pick_prior import NativePickPriorRelease
from fsffl.value.origin_aware_pick import AUTHORITATIVE_SIMULATION_COUNT
from .origin_aware_pick_value_runtime import build_origin_probability_evidence_from_simulation
from fsffl.forecast.future_pick_position_prior import (
    FUTURE_PICK_POSITION_POLICY, FUTURE_PICK_POSITION_AVAILABLE_AT, FuturePickPositionPrior,
)


def published_pick_values(runtime, release: NativePickPriorRelease | None, simulation_fingerprint: str | None,
                          *, projection_policy: str | None = None):
    values = {name: {} for name in ("three_year", "career")}
    sources = {}
    state = runtime.league_state
    analytics = runtime.simulation_analytics
    if (release is None or state is None
        or not runtime.publication_generation_id
        or not release.supports(state.league.rules, season=state.league.season, as_of=state.as_of)):
        return values, sources
    probabilities = {}
    if (analytics is not None and analytics.league_view.context.league_state_id == state.state_id
        and analytics.simulation_result.simulation_input_fingerprint == simulation_fingerprint
        and analytics.simulation_result.simulation_count == AUTHORITATIVE_SIMULATION_COUNT):
        probabilities = {row.original_team_id: row for row in build_origin_probability_evidence_from_simulation(
            analytics.simulation_result, next_draft_season=release.draft_season)}
    later_enabled = (projection_policy == FUTURE_PICK_POSITION_POLICY
                     and state.as_of >= FUTURE_PICK_POSITION_AVAILABLE_AT)
    owners = {p.pick_id: p.owner_team_id for p in state.pick_ownership}
    release_id = release.release_id
    order = settled_origin_order(state, release.draft_season)
    future_references = {}
    for pick in state.draft_picks:
        if (pick.season < release.draft_season or not 1 <= pick.round <= release.round_count
            or pick.pick_id not in owners):
            continue
        ranges = {}
        origin = order.get(pick.original_team_id) if pick.season == release.draft_season else None
        if origin:
            if origin.slot is None or origin.conflicts(pick.verified_slot):
                continue
            for horizon in values:
                values[horizon][pick.pick_id] = release.slot_point(round_number=pick.round,
                    slot=origin.slot, draft_season=pick.season, horizon=horizon)
            probability_basis = "settled_league_rule"
            slot_model = "settled_non_playoff_max_pf_v1"
            source_simulation = None
        elif pick.season == release.draft_season:
            evidence = probabilities.get(pick.original_team_id)
            if evidence is None:
                continue
            for horizon in values:
                values[horizon][pick.pick_id] = release.value(round_number=pick.round, probabilities=evidence, horizon=horizon)
            probability_basis = "published_simulation"
            slot_model = evidence.draft_order_projection_model_version
            source_simulation = simulation_fingerprint
        else:
            if not later_enabled:
                continue
            prior = FuturePickPositionPrior(draft_season=pick.season, team_count=release.team_count)
            for horizon in values:
                key = (pick.season, pick.round, horizon)
                if key not in future_references:
                    future_references[key] = release.future_round_reference(prior=prior, round_number=pick.round, horizon=horizon)
                mean, low, high = future_references[key]
                values[horizon][pick.pick_id] = mean
                ranges[horizon + '_slot_low'] = low
                ranges[horizon + '_slot_high'] = high
            probability_basis = "exchangeable_future_slot_prior"
            slot_model = prior.model_version
            source_simulation = None
        sources[pick.pick_id] = MappingProxyType({
            **({"rule_slot": origin.slot, "official_slot": pick.verified_slot} if origin else {}),
            "release_id": release_id, "model_version": release.model_version,
            "status": release.status, "comparison_policy": release.comparison_policy,
            "original_team_id": pick.original_team_id, "owner_team_id": owners[pick.pick_id],
            "draft_season": pick.season, "round": pick.round,
            "simulation_input_fingerprint": source_simulation,
            "probability_basis": probability_basis, "position_model_version": slot_model,
            "class_assumption": "unchanged_released_cohort_prior_no_known_class_adjustment",
            "range_basis": "possible_slot_reference_values_not_predictive_interval" if ranges else None,
            **ranges,
            "three_year_point_basis": ("calendar_structural_zero" if pick.season > release.evaluation_season + 2
                                       else "empirical_expected_native_contribution"),
            "career_point_basis": "model_reference_not_predictive_distribution",
        })
    return values, sources
