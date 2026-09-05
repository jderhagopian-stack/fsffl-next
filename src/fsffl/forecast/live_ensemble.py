from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fsffl.state.models import FrozenModel

from .ensemble import equal_weight_ensemble
from .models import ForecastObservation


class LiveSourceRole(StrEnum):
    INDEPENDENT_PROJECTION = "independent_projection"
    AGGREGATE = "aggregate"


@dataclass(frozen=True)
class LiveForecastSourceBatch:
    source_id: str
    observations: tuple[ForecastObservation, ...]
    role: LiveSourceRole = LiveSourceRole.INDEPENDENT_PROJECTION
    component_source_ids: tuple[str, ...] = ()


class LiveEnsembleCoverage(FrozenModel):
    independent_source_ids: tuple[str, ...]
    excluded_aggregate_source_ids: tuple[str, ...]
    active_source_ids: tuple[str, ...]
    observation_count: int
    minimum_independent_sources: int
    model_version: str = "next2-live-ensemble-governance-v1"


def build_authoritative_live_ensemble(
    batches: tuple[LiveForecastSourceBatch, ...],
    *,
    minimum_independent_sources: int = 2,
    model_version: str = "next2-live-equal-weight-v1",
) -> tuple[tuple[ForecastObservation, ...], LiveEnsembleCoverage]:
    """Build the governed current-season NEXT-2 ensemble.

    Production authority remains the existing equal-weight ensemble. This wrapper
    only governs which live source batches may vote. Aggregate sources are excluded
    whenever any of their named component sources are present, preventing a
    consensus product from re-voting the same underlying evidence.

    Missing providers are naturally renormalized by ``equal_weight_ensemble`` over
    the source observations actually present. At least ``minimum_independent_sources``
    independent live sources must be available before a result is promoted as the
    authoritative live FSFFL ensemble.
    """

    if minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources must be positive")
    ids = [batch.source_id for batch in batches]
    if len(ids) != len(set(ids)):
        raise ValueError("live forecast source ids must be unique")

    independent = tuple(
        sorted(
            batch.source_id
            for batch in batches
            if batch.role == LiveSourceRole.INDEPENDENT_PROJECTION and batch.observations
        )
    )
    if len(independent) < minimum_independent_sources:
        raise ValueError(
            "authoritative live ensemble requires at least "
            f"{minimum_independent_sources} independent sources; found {len(independent)}"
        )

    present = set(independent)
    active: list[LiveForecastSourceBatch] = []
    excluded_aggregates: list[str] = []
    for batch in batches:
        if not batch.observations:
            continue
        if batch.role == LiveSourceRole.AGGREGATE:
            if present.intersection(batch.component_source_ids):
                excluded_aggregates.append(batch.source_id)
                continue
        active.append(batch)

    observations: list[ForecastObservation] = []
    for batch in active:
        for observation in batch.observations:
            if observation.source != batch.source_id:
                raise ValueError(
                    f"observation source {observation.source!r} does not match batch {batch.source_id!r}"
                )
            observations.append(observation)

    ensemble = equal_weight_ensemble(
        tuple(observations),
        source="fsffl:live_equal_weight",
        model_version=model_version,
    )
    coverage = LiveEnsembleCoverage(
        independent_source_ids=independent,
        excluded_aggregate_source_ids=tuple(sorted(excluded_aggregates)),
        active_source_ids=tuple(sorted(batch.source_id for batch in active)),
        observation_count=len(observations),
        minimum_independent_sources=minimum_independent_sources,
    )
    return ensemble, coverage
