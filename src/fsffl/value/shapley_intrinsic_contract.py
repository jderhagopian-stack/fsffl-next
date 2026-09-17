from __future__ import annotations

import math
from enum import StrEnum
from typing import Mapping

from pydantic import Field

from fsffl.forecast.i1_config import FROZEN_I1_REGULARIZATION
from fsffl.forecast.integrated_i1 import I1_MODEL_VERSION
from fsffl.state.models import FrozenModel

from .live_intrinsic_calendar import (
    LIVE_INTRINSIC_CALENDAR_VERSION,
    LiveCalendarShapleyResult,
    LiveThreeYearPlayerCoordinate,
)
from .shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    SHAPLEY_INTRINSIC_MODEL_VERSION,
)

SHAPLEY_INTRINSIC_CONTRACT_VERSION = "intrinsic-shapley-contract-v2:effective-horizon-seeds"
SHAPLEY_INTRINSIC_ENDPOINT_PATH = "/api/value/intrinsic-shapley-v1"
RAW_INTRINSIC_QUANTITY = "raw_governed_shapley_marginal_fantasy_points"


class ShapleyIntrinsicAvailability(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CompletedSourceFactProvenance(FrozenModel):
    """Provider-neutral provenance for the completed-source I1 fact bundle."""

    source_version: str
    schema_version: str | None = None
    providers: tuple[str, ...] = ()
    fact_family_coverage: Mapping[str, bool | float | int | str | None] = Field(default_factory=dict)


class ShapleyHorizonProvenance(FrozenModel):
    authority: str
    source: str
    model_version: str
    source_season: int | None = None
    direct_i1_horizon: int | None = None
    regularization_policy_version: str | None = None
    regularization_c: float | None = None
    diagnostic_only: bool = False
    included_in_intrinsic: bool = True


class ShapleyHorizonUncertainty(FrozenModel):
    forecast_stddev: float | None = None
    state_entropy: float | None = None
    evidence_path: str


class ShapleyIntrinsicHorizonContribution(FrozenModel):
    year_index: int
    target_season: int
    raw_shapley_contribution: float
    discount_factor: float
    discounted_contribution: float
    provenance: ShapleyHorizonProvenance
    uncertainty: ShapleyHorizonUncertainty


class DiagnosticH1Evidence(FrozenModel):
    target_season: int
    anticipated_points: float
    provenance: ShapleyHorizonProvenance
    uncertainty: ShapleyHorizonUncertainty
    included_in_intrinsic: bool = False


class ShapleyIntrinsicPlayerEstimate(FrozenModel):
    player_id: str
    raw_intrinsic_value: float
    contributions: tuple[
        ShapleyIntrinsicHorizonContribution,
        ShapleyIntrinsicHorizonContribution,
        ShapleyIntrinsicHorizonContribution,
    ]
    diagnostic_h1: DiagnosticH1Evidence


class ShapleyIntrinsicCoverage(FrozenModel):
    player_count: int
    year_1_forecast_players: int
    year_2_i1_players: int
    year_3_i1_players: int
    rich_path_players: int
    reduced_or_fallback_players: int
    missing_required_fact_families: tuple[str, ...] = ()


class ShapleyIntrinsicContract(FrozenModel):
    contract_version: str = SHAPLEY_INTRINSIC_CONTRACT_VERSION
    endpoint_path: str = SHAPLEY_INTRINSIC_ENDPOINT_PATH
    status: ShapleyIntrinsicAvailability
    status_reason: str | None = None
    intrinsic_model_version: str = SHAPLEY_INTRINSIC_MODEL_VERSION
    forecast_model_version: str = I1_MODEL_VERSION
    regularization_policy_version: str = FROZEN_I1_REGULARIZATION.version
    regularization_c: float = FROZEN_I1_REGULARIZATION.default_c
    calendar_version: str = LIVE_INTRINSIC_CALENDAR_VERSION
    evaluation_season: int
    completed_source_season: int | None
    target_years: tuple[int, int, int]
    discount: float = FROZEN_INTRINSIC_DISCOUNT
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS
    seed: int = FROZEN_SHAPLEY_SEED
    horizon_seeds: tuple[int, int, int] = (
        FROZEN_SHAPLEY_SEED,
        FROZEN_SHAPLEY_SEED + 1,
        FROZEN_SHAPLEY_SEED + 2,
    )
    quantity_semantics: str = RAW_INTRINSIC_QUANTITY
    display_scaling_applied: bool = False
    diagnostic_h1_included: bool = False
    completed_source_provenance: CompletedSourceFactProvenance | None = None
    coverage: ShapleyIntrinsicCoverage
    estimates: tuple[ShapleyIntrinsicPlayerEstimate, ...] = ()


def _future_provenance(
    coordinate: LiveThreeYearPlayerCoordinate,
    *,
    year_index: int,
) -> tuple[ShapleyHorizonProvenance, ShapleyHorizonUncertainty]:
    item = coordinate.year_2 if year_index == 2 else coordinate.year_3
    return (
        ShapleyHorizonProvenance(
            authority="completed_source_direct_i1",
            source="canonical_completed_source_facts",
            model_version=item.result.model_version,
            source_season=item.source_season,
            direct_i1_horizon=item.horizon,
            regularization_policy_version=item.regularization_policy_version,
            regularization_c=item.regularization_c,
            diagnostic_only=False,
            included_in_intrinsic=True,
        ),
        ShapleyHorizonUncertainty(
            state_entropy=item.state_entropy,
            evidence_path=item.result.evidence_path,
        ),
    )


def build_shapley_intrinsic_contract(
    result: LiveCalendarShapleyResult,
    *,
    completed_source_provenance: CompletedSourceFactProvenance | None = None,
    missing_required_fact_families: tuple[str, ...] = (),
) -> ShapleyIntrinsicContract:
    """Translate frozen calendar/Shapley output into a versioned API contract.

    The raw governed Shapley quantity stays separate from presentation scaling.
    Completed-source h=1 is carried only as diagnostics and never enters the sum.
    """

    calendar = result.calendar
    by_coordinate = {item.player_id: item for item in calendar.forecasts}
    by_estimate = {item.player_id: item for item in result.estimates}
    if set(by_coordinate) != set(by_estimate):
        raise ValueError("calendar and Shapley estimate player sets must match")

    rich_path_players = 0
    reduced_or_fallback_players = 0
    payload: list[ShapleyIntrinsicPlayerEstimate] = []
    for player_id in sorted(by_coordinate):
        coordinate = by_coordinate[player_id]
        estimate = by_estimate[player_id]
        future_paths = (coordinate.year_2.result.evidence_path, coordinate.year_3.result.evidence_path)
        if all(path == "rich" for path in future_paths):
            rich_path_players += 1
        else:
            reduced_or_fallback_players += 1

        year_2_provenance, year_2_uncertainty = _future_provenance(coordinate, year_index=2)
        year_3_provenance, year_3_uncertainty = _future_provenance(coordinate, year_index=3)
        contributions = (
            ShapleyIntrinsicHorizonContribution(
                year_index=1,
                target_season=coordinate.year_1.target_season,
                raw_shapley_contribution=estimate.year_1_shapley,
                discount_factor=1.0,
                discounted_contribution=estimate.year_1_shapley,
                provenance=ShapleyHorizonProvenance(
                    authority=coordinate.year_1.authority,
                    source=coordinate.year_1.source,
                    model_version=coordinate.year_1.model_version,
                    included_in_intrinsic=True,
                ),
                uncertainty=ShapleyHorizonUncertainty(
                    forecast_stddev=coordinate.year_1.stddev,
                    evidence_path="governed_live_forecast",
                ),
            ),
            ShapleyIntrinsicHorizonContribution(
                year_index=2,
                target_season=coordinate.year_2.target_season,
                raw_shapley_contribution=estimate.year_2_expected_shapley,
                discount_factor=result.discount,
                discounted_contribution=result.discount * estimate.year_2_expected_shapley,
                provenance=year_2_provenance,
                uncertainty=year_2_uncertainty,
            ),
            ShapleyIntrinsicHorizonContribution(
                year_index=3,
                target_season=coordinate.year_3.target_season,
                raw_shapley_contribution=estimate.year_3_expected_shapley,
                discount_factor=result.discount**2,
                discounted_contribution=(result.discount**2) * estimate.year_3_expected_shapley,
                provenance=year_3_provenance,
                uncertainty=year_3_uncertainty,
            ),
        )
        reconstructed = sum(item.discounted_contribution for item in contributions)
        if not math.isclose(reconstructed, estimate.value, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(
                f"discounted Shapley contributions do not reconcile for {player_id}: "
                f"{reconstructed} != {estimate.value}"
            )

        diagnostic = coordinate.diagnostic_h1
        payload.append(
            ShapleyIntrinsicPlayerEstimate(
                player_id=player_id,
                raw_intrinsic_value=estimate.value,
                contributions=contributions,
                diagnostic_h1=DiagnosticH1Evidence(
                    target_season=diagnostic.target_season,
                    anticipated_points=diagnostic.result.anticipated_points,
                    provenance=ShapleyHorizonProvenance(
                        authority="completed_source_direct_i1_diagnostic",
                        source="canonical_completed_source_facts",
                        model_version=diagnostic.result.model_version,
                        source_season=diagnostic.source_season,
                        direct_i1_horizon=diagnostic.horizon,
                        regularization_policy_version=diagnostic.regularization_policy_version,
                        regularization_c=diagnostic.regularization_c,
                        diagnostic_only=True,
                        included_in_intrinsic=False,
                    ),
                    uncertainty=ShapleyHorizonUncertainty(
                        state_entropy=diagnostic.state_entropy,
                        evidence_path=diagnostic.result.evidence_path,
                    ),
                    included_in_intrinsic=False,
                ),
            )
        )

    degraded = bool(missing_required_fact_families) or reduced_or_fallback_players > 0
    status = ShapleyIntrinsicAvailability.DEGRADED if degraded else ShapleyIntrinsicAvailability.READY
    reason = None
    if degraded:
        reason = (
            "Authoritative Intrinsic is available through a validated reduced/fallback evidence path; "
            "missing fact-family coverage is explicit and no provider absence is inferred as football state."
        )

    player_count = len(payload)
    return ShapleyIntrinsicContract(
        status=status,
        status_reason=reason,
        evaluation_season=calendar.evaluation_season,
        completed_source_season=calendar.completed_source_season,
        target_years=(calendar.evaluation_season, calendar.evaluation_season + 1, calendar.evaluation_season + 2),
        discount=result.discount,
        permutations=result.permutations,
        seed=result.seed,
        horizon_seeds=(result.seed, result.seed + 1, result.seed + 2),
        completed_source_provenance=completed_source_provenance,
        coverage=ShapleyIntrinsicCoverage(
            player_count=player_count,
            year_1_forecast_players=player_count,
            year_2_i1_players=player_count,
            year_3_i1_players=player_count,
            rich_path_players=rich_path_players,
            reduced_or_fallback_players=reduced_or_fallback_players,
            missing_required_fact_families=tuple(sorted(set(missing_required_fact_families))),
        ),
        estimates=tuple(payload),
    )


def build_unavailable_shapley_intrinsic_contract(
    *,
    evaluation_season: int,
    reason: str,
    missing_required_fact_families: tuple[str, ...],
) -> ShapleyIntrinsicContract:
    if not reason.strip():
        raise ValueError("unavailable Shapley Intrinsic contract requires a reason")
    return ShapleyIntrinsicContract(
        status=ShapleyIntrinsicAvailability.UNAVAILABLE,
        status_reason=reason,
        evaluation_season=evaluation_season,
        completed_source_season=evaluation_season - 1,
        target_years=(evaluation_season, evaluation_season + 1, evaluation_season + 2),
        coverage=ShapleyIntrinsicCoverage(
            player_count=0,
            year_1_forecast_players=0,
            year_2_i1_players=0,
            year_3_i1_players=0,
            rich_path_players=0,
            reduced_or_fallback_players=0,
            missing_required_fact_families=tuple(sorted(set(missing_required_fact_families))),
        ),
        estimates=(),
    )
