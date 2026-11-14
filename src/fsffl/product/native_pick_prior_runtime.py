"""Translate published Simulation evidence to an already released Value prior."""
from types import MappingProxyType

from fsffl.value.native_pick_prior import NativePickPriorRelease
from fsffl.value.origin_aware_pick import AUTHORITATIVE_SIMULATION_COUNT
from .origin_aware_pick_value_runtime import build_origin_probability_evidence_from_simulation


def published_pick_values(runtime, release: NativePickPriorRelease | None, simulation_fingerprint: str | None):
    values = {name: {} for name in ("three_year", "career")}
    sources = {}
    state = runtime.league_state
    analytics = runtime.simulation_analytics
    if (release is None or state is None or analytics is None
        or not runtime.publication_generation_id
        or not release.supports(state.league.rules, season=state.league.season, as_of=state.as_of)
        or analytics.league_view.context.league_state_id != state.state_id
        or analytics.simulation_result.simulation_input_fingerprint != simulation_fingerprint
        or analytics.simulation_result.simulation_count != AUTHORITATIVE_SIMULATION_COUNT):
        return values, sources
    probabilities = {row.original_team_id: row for row in build_origin_probability_evidence_from_simulation(
        analytics.simulation_result, next_draft_season=release.draft_season)}
    owners = {p.pick_id: p.owner_team_id for p in state.pick_ownership}
    release_id = release.release_id
    for pick in state.draft_picks:
        # The initial authority covers unexercised next-season rights only. Never
        # borrow next-year probabilities for later drafts or historical inventory.
        if (pick.season != release.draft_season or not 1 <= pick.round <= release.round_count
            or pick.pick_id not in owners or pick.original_team_id not in probabilities):
            continue
        evidence = probabilities[pick.original_team_id]
        for horizon in values:
            values[horizon][pick.pick_id] = release.value(round_number=pick.round, probabilities=evidence, horizon=horizon)
        sources[pick.pick_id] = MappingProxyType({
            "release_id": release_id, "model_version": release.model_version,
            "status": release.status, "comparison_policy": release.comparison_policy,
            "original_team_id": pick.original_team_id, "owner_team_id": owners[pick.pick_id],
            "draft_season": pick.season, "round": pick.round,
            "simulation_input_fingerprint": simulation_fingerprint,
            "three_year_point_basis": "empirical_expected_native_contribution",
            "career_point_basis": "model_reference_not_predictive_distribution",
        })
    return values, sources
