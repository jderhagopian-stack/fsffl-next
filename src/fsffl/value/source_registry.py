from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .calibration import DataRightsClass


class MarketSignalKind(StrEnum):
    REVEALED_TRANSACTION = "revealed_transaction"
    CONSENSUS_RANKING = "consensus_ranking"
    CROWD_PREFERENCE = "crowd_preference"
    MARKET_INDEX = "market_index"
    LEAGUE_RULE = "league_rule"
    OTHER = "other"


class MarketSourceStatus(StrEnum):
    ELIGIBLE = "eligible"
    COMPARATOR_ONLY = "comparator_only"
    RESEARCH_CANDIDATE = "research_candidate"
    BLOCKED = "blocked"


class MarketSourceDefinition(FrozenModel):
    """Governed description of one broader-market evidence source.

    Source definitions make signal meaning, lineage, and rights explicit so an
    ensemble cannot accidentally grant multiple votes to derivative copies of
    the same underlying evidence.
    """

    source_id: str
    display_name: str
    signal_kind: MarketSignalKind
    rights_class: DataRightsClass
    status: MarketSourceStatus
    parent_source_ids: tuple[str, ...] = ()
    notes: str | None = None

    @model_validator(mode="after")
    def validate_definition(self) -> "MarketSourceDefinition":
        required = (self.source_id, self.display_name)
        if any(not value.strip() for value in required):
            raise ValueError("market source identifiers cannot be blank")
        if any(not parent.strip() for parent in self.parent_source_ids):
            raise ValueError("parent source identifiers cannot be blank")
        if self.source_id in self.parent_source_ids:
            raise ValueError("market source cannot depend on itself")
        if len(self.parent_source_ids) != len(set(self.parent_source_ids)):
            raise ValueError("parent source identifiers must be unique")
        if self.notes is not None and not self.notes.strip():
            raise ValueError("notes cannot be blank")
        return self


class MarketSourceRegistry(FrozenModel):
    sources: tuple[MarketSourceDefinition, ...]
    registry_version: str

    @model_validator(mode="after")
    def validate_registry(self) -> "MarketSourceRegistry":
        if not self.registry_version.strip():
            raise ValueError("registry_version cannot be blank")
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("market source ids must be unique")
        known = set(ids)
        for source in self.sources:
            missing = set(source.parent_source_ids) - known
            if missing:
                raise ValueError(f"unknown parent market sources: {sorted(missing)}")
        self._validate_acyclic()
        return self

    def _validate_acyclic(self) -> None:
        parents = {source.source_id: source.parent_source_ids for source in self.sources}
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(source_id: str) -> None:
            if source_id in visited:
                return
            if source_id in visiting:
                raise ValueError("market source dependency graph must be acyclic")
            visiting.add(source_id)
            for parent in parents[source_id]:
                visit(parent)
            visiting.remove(source_id)
            visited.add(source_id)

        for source_id in parents:
            visit(source_id)

    def authoritative_candidates(self) -> tuple[MarketSourceDefinition, ...]:
        return tuple(source for source in self.sources if source.status == MarketSourceStatus.ELIGIBLE)

    def independent_roots(self, source_id: str) -> tuple[str, ...]:
        """Return ultimate evidence roots for lineage-aware ensemble accounting."""
        by_id = {source.source_id: source for source in self.sources}
        if source_id not in by_id:
            raise ValueError("unknown market source")

        def roots(current: str) -> set[str]:
            parents = by_id[current].parent_source_ids
            if not parents:
                return {current}
            result: set[str] = set()
            for parent in parents:
                result.update(roots(parent))
            return result

        return tuple(sorted(roots(source_id)))
