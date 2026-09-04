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


def first_benchmark_source_registry() -> ForecastSourceRegistry:
    """Return the governed initial cohort for NEXT-2 historical research.

    This catalog is intentionally conservative. Research eligibility, data
    redistribution, commercial use, and predictive quality are independent
    decisions. A source remains INVESTIGATE/REQUIRES_REVIEW until its exact
    historical artifact and governing terms have been verified.
    """

    records = (
        ForecastSourceRecord(
            source_id="nflverse_outcomes",
            source_name="nflverse realized player outcomes / identifiers",
            roles=(SourceRole.OUTCOME, SourceRole.IDENTITY),
            access_status=AccessStatus.APPROVED_RESEARCH,
            historical_availability=HistoricalAvailability.ARCHIVED,
            timestamp_semantics=(
                "Realized historical outcomes and player identifiers. Outcomes are "
                "evaluation targets only and must never be forecast inputs."
            ),
            redistribution_status=RightsStatus.REQUIRES_REVIEW,
            commercial_use_status=RightsStatus.REQUIRES_REVIEW,
            access_method="nflverse/nflreadpy releases",
            terms_reference="https://nflreadpy.nflverse.com/",
            independence_notes="Outcome/identity backbone, not a projection vote.",
            evidence_notes=(
                "nflreadpy documents nflverse data sources and dataset-specific licensing; "
                "verify the license of every concrete dataset before retention or redistribution."
            ),
        ),
        ForecastSourceRecord(
            source_id="dynastyprocess_fantasypros_archive",
            source_name="DynastyProcess archived FantasyPros-derived fantasy data",
            roles=(SourceRole.PROJECTION, SourceRole.AGGREGATE, SourceRole.RANKING),
            access_status=AccessStatus.INVESTIGATE,
            historical_availability=HistoricalAvailability.ARCHIVED,
            timestamp_semantics=(
                "Repository history can provide conservative availability timestamps for "
                "committed snapshots; upstream issue/update time must not be inferred earlier."
            ),
            redistribution_status=RightsStatus.REQUIRES_REVIEW,
            commercial_use_status=RightsStatus.REQUIRES_REVIEW,
            access_method="DynastyProcess data repository and Git history",
            terms_reference="https://github.com/dynastyprocess/data",
            independence_notes=(
                "FantasyPros-derived aggregate is correlated with component projection sources "
                "and must not be treated as an independent vote."
            ),
            evidence_notes=(
                "Repository is open source, but upstream FantasyPros data rights are a separate "
                "question. Treat as research candidate until exact artifact terms are verified."
            ),
        ),
        ForecastSourceRecord(
            source_id="razzball",
            source_name="Razzball fantasy football projections",
            roles=(SourceRole.PROJECTION,),
            access_status=AccessStatus.INVESTIGATE,
            historical_availability=HistoricalAvailability.PARTIAL,
            timestamp_semantics=(
                "Use only dated archived projection artifacts or provider-supported historical "
                "queries; current pages cannot stand in for historical snapshots."
            ),
            redistribution_status=RightsStatus.REQUIRES_REVIEW,
            commercial_use_status=RightsStatus.REQUIRES_REVIEW,
            access_method="public projection pages / potential archives",
            independence_notes="Model lineage and overlap with other sources must be assessed.",
            evidence_notes="Historical completeness and terms require verification before ingest.",
        ),
        ForecastSourceRecord(
            source_id="fantasypros",
            source_name="FantasyPros projections / consensus",
            roles=(SourceRole.PROJECTION, SourceRole.AGGREGATE),
            access_status=AccessStatus.REQUIRES_REVIEW,
            historical_availability=HistoricalAvailability.PROVIDER_QUERY,
            timestamp_semantics=(
                "Use provider-returned season/snapshot metadata or a retained dated artifact; "
                "never backdate a current consensus."
            ),
            redistribution_status=RightsStatus.REQUIRES_REVIEW,
            commercial_use_status=RightsStatus.REQUIRES_REVIEW,
            access_method="FantasyPros API / licensed access",
            independence_notes=(
                "Consensus may contain sources also supplied separately to FSFFL; dependency "
                "must be accounted for during ensemble calibration."
            ),
            evidence_notes="API access and downstream data rights must be verified separately.",
        ),
    )
    return ForecastSourceRegistry(records)
