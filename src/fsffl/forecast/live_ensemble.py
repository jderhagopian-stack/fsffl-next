from __future__ import annotations

from collections import defaultdict
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
    excluded_undercovered_groups: int = 0
    model_version: str = "next2-live-ensemble-governance-v2"


def _group_key(observation: ForecastObservation) -> tuple[object, ...]:
    return (
        observation.player_id,
        observation.position,
        observation.horizon,
        observation.metric,
        observation.period_start,
        observation.period_end,
        observation.as_of,
    )


def build_authoritative_live_ensemble(
    batches: tuple[LiveForecastSourceBatch, ...],
    *,
    minimum_independent_sources: int = 2,
    model_version: str = "next2-live-equal-weight-v1",
) -> tuple[tuple[ForecastObservation, ...], LiveEnsembleCoverage]:
    """Build the governed current-season NEXT-2 ensemble.

    Production authority remains the existing equal-weight ensemble. This wrapper
    governs which live source batches may vote and requires the minimum independent
    source count for *each individual player/metric group*, not merely somewhere in
    the overall feed. Aggregate sources are excluded whenever named component
    sources are present, preventing a consensus product from re-voting underlying
    evidence. Missing providers are renormalized only within sufficiently covered
    groups.
    """

    if minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources must be positive")
    ids = [batch.source_id for batch in batches]
    if len(ids) != len(set(ids)):
        raise ValueError("live forecast source ids must be unique")

    independent_batches = {
        batch.source_id: batch
        for batch in batches
        if batch.role == LiveSourceRole.INDEPENDENT_PROJECTION and batch.observations
    }
    independent = tuple(sorted(independent_batches))
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
        if batch.role == LiveSourceRole.AGGREGATE and present.intersection(batch.component_source_ids):
            excluded_aggregates.append(batch.source_id)
            continue
        active.append(batch)

    independent_sources_by_group: dict[tuple[object, ...], set[str]] = defaultdict(set)
    for source_id, batch in independent_batches.items():
        for observation in batch.observations:
            if observation.source != source_id:
                raise ValueError(
                    f"observation source {observation.source!r} does not match batch {source_id!r}"
                )
            independent_sources_by_group[_group_key(observation)].add(source_id)

    eligible_groups = {
        key
        for key, source_ids in independent_sources_by_group.items()
        if len(source_ids) >= minimum_independent_sources
    }
    excluded_undercovered_groups = len(independent_sources_by_group) - len(eligible_groups)

    observations: list[ForecastObservation] = []
    for batch in active:
        for observation in batch.observations:
            if observation.source != batch.source_id:
                raise ValueError(
                    f"observation source {observation.source!r} does not match batch {batch.source_id!r}"
                )
            if _group_key(observation) in eligible_groups:
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
        excluded_undercovered_groups=excluded_undercovered_groups,
    )
    return ensemble, coverage
