from __future__ import annotations

from enum import StrEnum

from pydantic import AnyUrl

from fsffl.state.models import FrozenModel


class SourceRole(StrEnum):
    PROJECTION = "projection"
    AGGREGATE = "aggregate"
    RANKING = "ranking"
    OUTCOME = "outcome"
    IDENTITY = "identity"


class AccessStatus(StrEnum):
    APPROVED_RESEARCH = "approved_research"
    INVESTIGATE = "investigate"
    REQUIRES_REVIEW = "requires_review"
    PROHIBITED = "prohibited"


class RightsStatus(StrEnum):
    UNKNOWN = "unknown"
    PERMITTED = "permitted"
    REQUIRES_REVIEW = "requires_review"
    NOT_PERMITTED = "not_permitted"


class HistoricalAvailability(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    ARCHIVED = "archived"
    PROVIDER_QUERY = "provider_query"
    UNKNOWN = "unknown"


class ForecastSourceRecord(FrozenModel):
    source_id: str
    source_name: str
    roles: tuple[SourceRole, ...]
    access_status: AccessStatus
    historical_availability: HistoricalAvailability = HistoricalAvailability.UNKNOWN
    timestamp_semantics: str
    redistribution_status: RightsStatus = RightsStatus.UNKNOWN
    commercial_use_status: RightsStatus = RightsStatus.UNKNOWN
    access_method: str | None = None
    terms_reference: AnyUrl | None = None
    independence_notes: str | None = None
    evidence_notes: str | None = None


class ForecastSourceRegistry:
    """Small explicit registry separating source usability from predictive skill.

    A source being allowed for research does not make it accurate, and a source
    being accurate does not imply that its data may be redistributed or used
    commercially. Those decisions remain separate by design.
    """

    def __init__(self, records: tuple[ForecastSourceRecord, ...] = ()) -> None:
        self._records: dict[str, ForecastSourceRecord] = {}
        for record in records:
            self.register(record)

    def register(self, record: ForecastSourceRecord) -> None:
        if record.source_id in self._records:
            raise ValueError(f"duplicate forecast source_id: {record.source_id}")
        self._records[record.source_id] = record

    def get(self, source_id: str) -> ForecastSourceRecord:
        return self._records[source_id]

    def research_eligible(self) -> tuple[ForecastSourceRecord, ...]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._records.values()
                    if record.access_status == AccessStatus.APPROVED_RESEARCH
                    and record.historical_availability
                    not in {HistoricalAvailability.NONE, HistoricalAvailability.UNKNOWN}
                ),
                key=lambda item: item.source_id,
            )
        )

    def all(self) -> tuple[ForecastSourceRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.source_id))
