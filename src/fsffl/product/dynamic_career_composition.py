"""Hosted bridge from live roster evidence into the full Career cohort.

This module reuses the accepted P0 live adapter and future scorer. It never
changes the frozen 335 reference rows. Until the accepted Y4-Y7 and terminal
feature contracts provide a candidate row, the candidate remains an explicit
Career coverage failure after its Y1-Y3 full-cohort Shapley calculation.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

from fsffl.forecast.future_contract import FutureForecastContract
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar_from_forecast_contract,
)
from fsffl.value.shapley_intrinsic_contract import build_shapley_intrinsic_contract

from .foundation4_career_forward_runtime import ExpandedCareerContractResult
from .p0_live_candidate_runtime import (
    P0LiveCandidateResult,
    build_live_p0_rostered_candidate_forecasts,
)
from .private_beta_shapley_runtime import _year_one_forecasts
from .runtime import UserRuntimeContext


def _merge_candidate_inputs(
    *,
    base_year_one,
    base_future: FutureForecastContract,
    candidate: P0LiveCandidateResult,
    rules,
) -> tuple[tuple, FutureForecastContract, tuple[str, ...]]:
    failures = dict(candidate.failures)
    if candidate.future is None:
        return tuple(base_year_one), base_future, tuple(sorted(failures))

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
                **base_future.provenance,
                "dynamic_candidate_count": len(ready_ids),
                "dynamic_candidate_ids": sorted(ready_ids),
            },
        )
        expanded_year_one = tuple(base_year_one) + years
        calendar = compose_live_intrinsic_calendar_from_forecast_contract(
            live_year_one_forecasts=expanded_year_one,
            future_contract=expanded_future,
        )
        # Run the actual full-cohort Shapley composer before reporting later Career
        # component gaps. This ensures candidates are never valued in isolation.
        build_shapley_intrinsic_contract(
            build_live_calendar_shapley_estimates(calendar, rules=rules)
        )
    return tuple(base_year_one), base_future, tuple(sorted(failures))


def dynamic_career_fingerprint(context: UserRuntimeContext) -> str:
    """Bind persisted Career results to exact State and existing live evidence."""
    if context.league_state is None:
        raise ValueError("dynamic Career fingerprint requires canonical State")
    evidence = context.forecast_evidence
    payload = {
        "state_id": context.league_state.state_id,
        "completed_through_week": context.league_state.completed_through_week,
        "forecast_model": evidence.model_version if evidence is not None else None,
        "forecast_rows": [
            (row.player_id, row.metric.value, float(row.distribution.mean), row.model_version)
            for row in (evidence.raw_forecasts if evidence is not None else ())
        ],
        "contract": "dynamic-rostered-p0-career-bridge-v1",
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_dynamic_rostered_career_contract(
    context: UserRuntimeContext,
    frozen_reference,
    *,
    current_intrinsic_loader,
    candidate_builder: Callable[..., P0LiveCandidateResult] = (
        build_live_p0_rostered_candidate_forecasts
    ),
) -> ExpandedCareerContractResult:
    """Run live Y1 and accepted Y2/Y3 scoring, then isolate later Career gaps."""
    del frozen_reference  # The accepted base inputs come from the configured loader.
    state = context.league_state
    if state is None:
        raise ValueError("dynamic Career bridge requires canonical State")

    # Reuse the configured accepted preseason authority, then the exact same
    # future contract builder as the hosted Shapley loader.
    year_one_evidence = current_intrinsic_loader._year_one_loader(state)
    if year_one_evidence.evidence_basis != "preseason_baseline":
        raise ValueError("dynamic Career bridge requires accepted preseason base cohort")
    base_year_one = _year_one_forecasts(year_one_evidence)
    base_future = current_intrinsic_loader._resolve_future_contract(
        league_state=state,
        evidence=year_one_evidence,
        year_one=base_year_one,
    )
    live = candidate_builder(state)
    _, _, composition_failures = _merge_candidate_inputs(
        base_year_one=base_year_one,
        base_future=base_future,
        candidate=live,
        rules=state.league.rules,
    )
    failures = dict(live.failures)
    failures.update({player_id: "accepted Y1/Y2/Y3 inputs could not enter full-cohort Shapley" for player_id in composition_failures if player_id not in failures})
    composed = (
        set(live.candidate_source_rows)
        - set(failures)
    )
    for player_id in sorted(composed):
        failures[player_id] = (
            "missing accepted dynamic Career component contract: candidate-specific "
            "Y4-Y7 LongHorizonForecastAuthorityContract rows and Y8+ CareerTailFeatures "
            "in the frozen FSFFL scoring coordinate; the hosted Foundation 4 providers "
            "currently expose those contracts only for the frozen 335 IDs"
        )
    return ExpandedCareerContractResult(contract=None, failures=failures)
