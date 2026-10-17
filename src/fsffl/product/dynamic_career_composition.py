"""Hosted bridge from live roster evidence into the full Career cohort.

This module reuses the accepted P0 live adapter and future scorer. It never
changes the frozen 335 reference rows. Until the accepted Y4-Y7 and terminal
feature contracts provide a candidate row, the candidate remains an explicit
Career coverage failure after its Y1-Y3 full-cohort Shapley calculation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Callable, Mapping

from fsffl.memory_attribution import sample_rss_phase

from fsffl.forecast.future_contract import FutureForecastContract
from fsffl.forecast.long_horizon_contract import (
    LongHorizonForecastAuthorityContract,
    LongHorizonPolicyForecast,
)
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar_from_forecast_contract,
)
from fsffl.value.shapley_intrinsic_contract import build_shapley_intrinsic_contract
from fsffl.value.career_forward_intrinsic import build_career_forward_intrinsic_shadow
from fsffl.value.career_forward_intrinsic import append_dynamic_career_estimates
from fsffl.value.career_tail import CareerTailAuthority, build_career_tail_authority
from fsffl.value.long_term_intrinsic import build_long_term_intrinsic_shadow
from fsffl.product.foundation4_shadow_inputs import (
    provide_foundation4_long_horizon_forecast_contract_for_rules,
    provide_foundation4_terminal_features,
)

from .foundation4_career_forward_runtime import ExpandedCareerContractResult
from .p0_live_candidate_runtime import (
    P0LiveCandidateResult,
    build_live_p0_rostered_candidate_forecasts,
    recorded_status_based_zero_ros_evidence,
    STATUS_BASED_YEAR_ONE_SCORING_VERSION,
)
from .private_beta_shapley_runtime import _year_one_forecasts
from .runtime import UserRuntimeContext
from .foundation4_cohort import align_foundation4_cohort
from .resource_coordinator import reclaim_before_heavy_allocation
from fsffl.value.shapley_intrinsic import clear_shapley_execution_caches


@dataclass(frozen=True)
class DynamicCareerComponents:
    """Accepted Foundation 4 rows produced for dynamic candidates."""

    y4_y7: Mapping[str, tuple[LongHorizonPolicyForecast, ...]]
    y8_plus: Mapping[str, CareerTailAuthority]
    failures: Mapping[str, str]


DynamicCareerMaterializer = Callable[
    [UserRuntimeContext, P0LiveCandidateResult, tuple[str, ...]],
    DynamicCareerComponents,
]

# Sleeper's catalog and stats endpoints have no durable revision token and are
# currently acquired only when the dynamic Career builder runs. Bound how long
# a reusable dynamic result can hide corrected provider inputs without polling
# those endpoints on every request.
DYNAMIC_CAREER_SOURCE_REFRESH_INTERVAL = timedelta(hours=6)


def _reclaim_career_stage(label: str) -> None:
    """Release completed-stage scratch before the next allocation boundary."""
    clear_shapley_execution_caches()
    reclaim_before_heavy_allocation(label=label)


def _scalar_provenance(values: Mapping[str, object]) -> dict[str, object]:
    """Encode structured source provenance inside the scalar contract schema."""
    return {
        key: value
        if value is None or isinstance(value, (str, bool, int, float))
        else json.dumps(value, sort_keys=True, separators=(",", ":"))
        for key, value in values.items()
    }


def _merge_candidate_inputs(
    *,
    base_year_one,
    base_future: FutureForecastContract,
    candidate: P0LiveCandidateResult,
    rules,
) -> tuple[tuple, FutureForecastContract, tuple[str, ...], object | None]:
    failures = dict(candidate.failures)
    if candidate.future is None:
        return tuple(base_year_one), base_future, tuple(sorted(failures)), None

    candidate_future = candidate.future.contract
    dynamic_ids = set(candidate.candidate_source_rows) - set(failures)
    y1_ids = set(candidate.year_one_league) & set(candidate.year_one_standard)
    future_ids = {
        row.player_id for row in candidate_future.forecasts
    }
    ready_ids = dynamic_ids & y1_ids & future_ids
    for player_id in dynamic_ids - ready_ids:
        failures.setdefault(
            player_id,
            "accepted P0 future contract lacks complete Year-1 and Y2/Y3 rows",
        )
    expanded_current = None
    if ready_ids:
        frozen_ids = set(base_future.player_ids)
        if ready_ids & frozen_ids:
            raise ValueError("dynamic Career candidate overlaps accepted future cohort")
        years = tuple(
            candidate.year_one_league[player_id]
            for player_id in sorted(ready_ids)
        )
        future_rows = tuple(base_future.forecasts) + tuple(
            row for row in candidate_future.forecasts if row.player_id in ready_ids
        )
        expanded_future = FutureForecastContract(
            evaluation_season=base_future.evaluation_season,
            scoring_coordinate=base_future.scoring_coordinate,
            forecast_model_version=(
                f"{base_future.forecast_model_version}+{candidate_future.forecast_model_version}"
            ),
            forecast_source="accepted-base-plus-dynamic-rostered-p0",
            forecasts=future_rows,
            provenance={
                **_scalar_provenance(base_future.provenance),
                "dynamic_candidate_count": len(ready_ids),
                "dynamic_candidate_ids": json.dumps(
                    sorted(ready_ids), separators=(",", ":")
                ),
            },
        )
        expanded_year_one = tuple(base_year_one) + years
        calendar = compose_live_intrinsic_calendar_from_forecast_contract(
            live_year_one_forecasts=expanded_year_one,
            future_contract=expanded_future,
        )
        # Run the actual full-cohort Shapley composer before reporting later Career
        # component gaps. This ensures candidates are never valued in isolation.
        expanded_current = build_shapley_intrinsic_contract(
            build_live_calendar_shapley_estimates(calendar, rules=rules)
        )
    return tuple(base_year_one), base_future, tuple(sorted(failures)), expanded_current


def _compose_dynamic_career_contract(
    *,
    context: UserRuntimeContext,
    frozen_reference,
    expanded_current,
    candidate_ids: tuple[str, ...],
    components: DynamicCareerComponents,
):
    """Apply accepted Y4-Y7 and Y8+ authorities to the full expanded Shapley game."""
    state = context.league_state
    if state is None or expanded_current is None:
        raise ValueError("dynamic Career composition requires exact State and full Shapley result")
    expected = set(candidate_ids)
    component_ids = set(components.y4_y7)
    tail_ids = set(components.y8_plus)
    failures = dict(components.failures)
    unexpected = (component_ids | tail_ids | set(failures)) - expected
    if unexpected:
        raise ValueError(
            "Foundation 4 dynamic materializer returned players outside the exact-State "
            f"candidate batch: {', '.join(sorted(unexpected))}"
        )
    for player_id in expected - component_ids - set(failures):
        failures[player_id] = "accepted Foundation 4 materializer returned no complete Y4-Y7 contract"
    for player_id in expected - tail_ids - set(failures):
        failures[player_id] = "accepted Foundation 4 materializer returned no Y8+ tail authority"
    ready = expected - set(failures)
    if not ready:
        return None, failures
    if ready != component_ids & tail_ids:
        raise ValueError("dynamic Foundation 4 materializer returned an unaccounted candidate")

    frozen_long = provide_foundation4_long_horizon_forecast_contract_for_rules(
        state.league.rules
    )
    base_ids = {row.player_id for row in frozen_reference.estimates}
    if {row.player_id for row in expanded_current.estimates} != base_ids | ready:
        raise ValueError("expanded Current differs from the selected reference plus dynamic cohort")
    frozen_long, terminal_features = align_foundation4_cohort(
        player_ids=base_ids, long_forecast=frozen_long,
        terminal_features=provide_foundation4_terminal_features(),
    )
    candidate_long_rows = tuple(
        row for player_id in sorted(ready) for row in components.y4_y7[player_id]
    )
    if set(failures) & (component_ids | tail_ids):
        raise ValueError("Foundation 4 materializer returned components for a failed player")
    long_contract = LongHorizonForecastAuthorityContract.model_validate(
        {
            **frozen_long.model_dump(exclude={"provenance"}),
            "forecasts": tuple(frozen_long.forecasts) + candidate_long_rows,
            "provenance": {
                **_scalar_provenance(frozen_long.provenance),
                "dynamic_candidate_ids": json.dumps(
                    sorted(ready), separators=(",", ":")
                ),
                "dynamic_materializer": "accepted-foundation4-dynamic-candidate-materializer",
            },
        }
    )
    long_term = build_long_term_intrinsic_shadow(
        long_contract, rules=state.league.rules
    )
    tails: dict[str, CareerTailAuthority] = {
        player_id: build_career_tail_authority(
            terminal_features[player_id], rules=state.league.rules
        )
        for player_id in sorted(terminal_features)
    }
    tails.update({player_id: components.y8_plus[player_id] for player_id in ready})
    expanded = build_career_forward_intrinsic_shadow(
        expanded_current, long_term, tails
    )
    # Expanded-cohort Shapley reallocates marginal values across all game
    # members. The accepted frozen cohort remains the numerical parity
    # reference; append only the dynamic roster rows from the expanded result.
    return append_dynamic_career_estimates(
        frozen_reference,
        expanded,
        candidate_player_ids=ready,
    ), failures


def dynamic_career_fingerprint(
    context: UserRuntimeContext,
    *,
    projection_history_reader=None,
    now: datetime | None = None,
    include_freshness_epoch: bool = True,
) -> str:
    """Resolve the governed source-capture identity without provider polling.

    Explicit Forecast publication advances its precise capture cutoff even when
    numeric Forecast/ROS rows are unchanged. The durable expansion separately
    binds every consumed live input through its producer-recorded manifest.
    Reads/restarts reuse that frozen capture; clock age is refresh-due metadata.
    """
    if context.league_state is None:
        raise ValueError("dynamic Career fingerprint requires canonical State")
    evaluated_at = now or context.career_fingerprint_evaluation_as_of or max(
        context.league_state.as_of,
        getattr(getattr(context.forecast_evidence, "runtime_result", None),
                "evaluation_as_of", None) or context.league_state.as_of,
    )
    if evaluated_at.tzinfo is None:
        raise ValueError("dynamic Career fingerprint clock must be timezone-aware")
    freshness_epoch = int(
        evaluated_at.astimezone(UTC).timestamp()
        // DYNAMIC_CAREER_SOURCE_REFRESH_INTERVAL.total_seconds()
    )
    evidence = context.forecast_evidence
    ros_revisions = ()
    if projection_history_reader is not None and (context.league_state.completed_through_week or 0) < 18:
        from fsffl.forecast.projection_history import career_ros_projection_selector

        ros_revisions = projection_history_reader.latest_revision_fingerprints(
            career_ros_projection_selector(
                season=context.league_state.league.season,
                completed_through_week=context.league_state.completed_through_week or 0,
                as_of=evaluated_at.astimezone(UTC),
            )
        )
    payload = {
        "state_id": context.league_state.state_id,
        "completed_through_week": context.league_state.completed_through_week,
        "forecast_model": getattr(evidence, "model_version", None),
        "forecast_rows": [
            (row.player_id, row.metric.value, float(row.distribution.mean), row.model_version)
            for row in getattr(evidence, "raw_forecasts", ())
        ],
        "projection_history_revisions": ros_revisions,
        "contract": "dynamic-rostered-p0-career-bridge-v4:captured-live-inputs",
    }
    status_receipts = recorded_status_based_zero_ros_evidence(
        context.league_state, as_of=evaluated_at,
    )
    if status_receipts:
        payload["official_nfl_status_scoring"] = STATUS_BASED_YEAR_ONE_SCORING_VERSION
        payload["official_nfl_status_receipts"] = [
            (player_id, row.source_version)
            for player_id, row in sorted(status_receipts.items())
        ]
    from fsffl.providers.nfl_status_evidence import recorded_nfl_role_receipts
    roles = recorded_nfl_role_receipts(context.league_state, as_of=evaluated_at)
    if roles:
        payload["official_nfl_role_receipts"] = [
            (player_id, row.fingerprint) for player_id, row in sorted(roles.items())
        ]
    if include_freshness_epoch:
        payload["live_source_freshness_epoch"] = freshness_epoch
        # Explicit refresh creates a new source capture even when numeric
        # Forecast/ROS rows are unchanged. Browser reads and restarts do not.
        payload["published_source_capture"] = evaluated_at.astimezone(UTC).isoformat()
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_dynamic_rostered_career_contract(
    context: UserRuntimeContext,
    frozen_reference,
    *,
    current_intrinsic_loader,
    materializer: DynamicCareerMaterializer | None = None,
    candidate_builder: Callable[..., P0LiveCandidateResult] = (
        build_live_p0_rostered_candidate_forecasts
    ),
) -> ExpandedCareerContractResult:
    """Run live Y1 and accepted Y2/Y3 scoring, then isolate later Career gaps."""
    state = context.league_state
    if state is None:
        raise ValueError("dynamic Career bridge requires canonical State")

    # Reuse the configured accepted preseason authority, then the exact same
    # future contract builder as the hosted Shapley loader.
    try:
        _reclaim_career_stage("career-before-reference-year-one")
        with sample_rss_phase("career.reference_year_one"):
            year_one_evidence = current_intrinsic_loader._year_one_loader(state)
        if year_one_evidence.evidence_basis != "preseason_baseline":
            raise ValueError("dynamic Career bridge requires accepted preseason base cohort")
        base_year_one = _year_one_forecasts(year_one_evidence)
        reference_kwargs = {}
        from .i1_player_scoring import APPROVED_UNDEFINED_WR_PLAYER_ID
        if any(entry.player_id == APPROVED_UNDEFINED_WR_PLAYER_ID
               for team in state.team_states for entry in team.roster):
            from fsffl.forecast.league_scoring import derive_league_scoring_result
            from .i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
            supplement = getattr(getattr(year_one_evidence, "runtime_result", None),
                                 "first_party_fumbles_lost_supplement", None)
            reference_standard = derive_league_scoring_result(
                year_one_evidence.raw_forecasts,
                rules=state.league.rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING}),
                supplemental_observations=tuple(getattr(supplement, "observations", ())),
            ).authoritative_forecasts
            reference_kwargs = dict(reference_standard_year_one=reference_standard,
                                    reference_league_year_one=base_year_one)
        _reclaim_career_stage("career-before-current-inputs-and-p0")
        with sample_rss_phase("career.current_inputs_and_p0"):
            live = candidate_builder(
                state,
                projection_history_as_of=context.career_fingerprint_evaluation_as_of,
                **reference_kwargs,
            )
    except Exception as exc:
        # Dynamic acquisition is an optional extension to the already-built
        # frozen Career contract. Preserve that contract and expose each
        # supported roster subject as explicitly unresolved on batch failure.
        base_ids = {row.player_id for row in frozen_reference.estimates}
        candidates = sorted({
            entry.player_id
            for team in state.team_states
            for entry in team.roster
            if entry.player_id not in base_ids
            and entry.player_id in {p.player_id for p in state.players
                                    if p.position.value in {"QB", "RB", "WR", "TE"}}
        })
        detail = f"dynamic P0 acquisition failed: {type(exc).__name__}: {exc}"
        return ExpandedCareerContractResult(
            contract=None,
            failures={player_id: detail for player_id in candidates},
        )
    failures = dict(live.failures)
    def result(contract=None, failures=None):
        return ExpandedCareerContractResult(
            contract=contract, failures=failures or {},
            source_manifest=dict(getattr(live, "source_manifest", {})),
        )
    future = live.future
    if future is None:
        return result(contract=None, failures=failures)
    future_rows = {
        (row.player_id, int(row.year_index)): row
        for row in future.contract.forecasts
    }
    frozen_ids = {row.player_id for row in base_year_one}
    if frozen_ids & set(live.candidate_source_rows):
        raise ValueError("dynamic Career candidate overlaps accepted future cohort")
    eligible = {
        player_id
        for player_id in live.candidate_source_rows
        if player_id not in failures
        and player_id in live.year_one_league
        and player_id in live.year_one_standard
        and (player_id, 2) in future_rows
        and (player_id, 3) in future_rows
    }
    for player_id in set(live.candidate_source_rows) - eligible - set(failures):
        failures[player_id] = (
            "accepted P0 candidate lacks canonical full-season Year-1 and Y2/Y3 rows"
        )
    if not eligible:
        return result(contract=None, failures=failures)
    if materializer is None:
        for player_id in sorted(eligible):
            failures[player_id] = (
                "accepted Foundation 4 dynamic materializer input bundle is not configured "
                "for the hosted process (route/development modules, frozen route inputs, "
                "and point-in-time historical panel)"
            )
        return result(contract=None, failures=failures)
    # ROS acquisition/scoring is complete. Career consumes the retained
    # candidate source, Y1, future and failure contracts; it never consumes
    # the whole-league ROS intermediate. Release this local working-set
    # reference without mutating the builder's result or its evidence.
    live = replace(live, ros_runtime=None)
    try:
        _reclaim_career_stage("career-before-dynamic-foundation4")
        with sample_rss_phase("career.foundation4_materialization"):
            components = materializer(context, live, tuple(sorted(eligible)))
    except Exception as exc:
        # The materializer is allowed to fail per candidate; a batch-level
        # infrastructure/configuration error is reflected on each eligible row.
        detail = f"accepted Foundation 4 dynamic materializer failed: {type(exc).__name__}: {exc}"
        return result(
            contract=None,
            failures={**failures, **{player_id: detail for player_id in sorted(eligible)}},
        )
    unexpected_components = (
        set(components.y4_y7) | set(components.y8_plus) | set(components.failures)
    ) - eligible
    if unexpected_components:
        raise ValueError(
            "Foundation 4 dynamic materializer returned players outside the eligible "
            "exact-State batch: " + ", ".join(sorted(unexpected_components))
        )
    complete = eligible & set(components.y4_y7) & set(components.y8_plus)
    complete -= set(components.failures)
    for player_id in eligible - complete:
        failures[player_id] = components.failures.get(
            player_id,
            "accepted Foundation 4 materializer returned an incomplete Y4-Y7/Y8+ contract",
        )
    if not complete:
        return result(contract=None, failures=failures)

    # The large future scenario graph is needed only for downstream Shapley.
    # Do not keep it resident alongside Foundation 4's fit workspaces.
    _reclaim_career_stage("career-foundation4-complete")
    base_future = current_intrinsic_loader._resolve_future_contract(
        league_state=state,
        evidence=year_one_evidence,
        year_one=base_year_one,
    )
    if set(base_future.player_ids) & set(live.candidate_source_rows):
        raise ValueError("dynamic Career candidate overlaps accepted future cohort")

    # Materialize accepted Foundation 4 components before expanding the
    # Shapley cohort. This keeps the wide materializer's RSS bounded and means
    # candidates missing later Career inputs never perturb another player's
    # full-cohort Shapley calculation.
    candidate_future = future.contract.model_copy(
        update={
            "forecasts": tuple(
                row for row in future.contract.forecasts if row.player_id in complete
            )
        }
    )
    composition_candidate = replace(
        live,
        candidate_ids=tuple(sorted(complete)),
        candidate_source_rows={
            player_id: live.candidate_source_rows[player_id]
            for player_id in complete
        },
        year_one_standard={
            player_id: live.year_one_standard[player_id] for player_id in complete
        },
        year_one_league={
            player_id: live.year_one_league[player_id] for player_id in complete
        },
        future=replace(future, contract=candidate_future),
        failures={},
    )
    _reclaim_career_stage("career-before-expanded-shapley")
    _, _, composition_failures, expanded_current = _merge_candidate_inputs(
        base_year_one=base_year_one,
        base_future=base_future,
        candidate=composition_candidate,
        rules=state.league.rules,
    )
    if composition_failures or expanded_current is None:
        raise ValueError(
            "complete dynamic Career inputs failed full-cohort Shapley composition: "
            + ", ".join(composition_failures)
        )
    complete_components = DynamicCareerComponents(
        y4_y7={player_id: components.y4_y7[player_id] for player_id in complete},
        y8_plus={player_id: components.y8_plus[player_id] for player_id in complete},
        failures={},
    )
    _reclaim_career_stage("career-before-final-composition")
    expanded, component_failures = _compose_dynamic_career_contract(
        context=context,
        frozen_reference=frozen_reference,
        expanded_current=expanded_current,
        candidate_ids=tuple(sorted(complete)),
        components=complete_components,
    )
    failures.update(component_failures)
    return result(contract=expanded, failures=failures)
