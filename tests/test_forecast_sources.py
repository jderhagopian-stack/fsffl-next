import pytest

from fsffl.forecast.sources import (
    AccessStatus,
    ForecastSourceRecord,
    ForecastSourceRegistry,
    HistoricalAvailability,
    RightsStatus,
    SourceRole,
    first_benchmark_source_registry,
)


def _record(source_id: str, *, access: AccessStatus) -> ForecastSourceRecord:
    return ForecastSourceRecord(
        source_id=source_id,
        source_name=source_id,
        roles=(SourceRole.PROJECTION,),
        access_status=access,
        historical_availability=HistoricalAvailability.ARCHIVED,
        timestamp_semantics="provider-issued timestamp",
        redistribution_status=RightsStatus.REQUIRES_REVIEW,
        commercial_use_status=RightsStatus.REQUIRES_REVIEW,
    )


def test_registry_keeps_research_eligibility_separate_from_rights() -> None:
    registry = ForecastSourceRegistry(
        (
            _record("a", access=AccessStatus.APPROVED_RESEARCH),
            _record("b", access=AccessStatus.INVESTIGATE),
        )
    )
    assert [item.source_id for item in registry.research_eligible()] == ["a"]
    assert registry.get("a").commercial_use_status == RightsStatus.REQUIRES_REVIEW


def test_registry_rejects_duplicate_source_id() -> None:
    with pytest.raises(ValueError, match="duplicate forecast source_id"):
        ForecastSourceRegistry(
            (
                _record("a", access=AccessStatus.APPROVED_RESEARCH),
                _record("a", access=AccessStatus.APPROVED_RESEARCH),
            )
        )


def test_first_benchmark_cohort_is_conservative_about_provider_rights() -> None:
    registry = first_benchmark_source_registry()
    ids = {item.source_id for item in registry.all()}

    assert ids == {
        "nflverse_outcomes",
        "dynastyprocess_fantasypros_archive",
        "razzball",
        "fantasypros",
    }
    assert registry.get("nflverse_outcomes").access_status == AccessStatus.APPROVED_RESEARCH
    assert (
        registry.get("dynastyprocess_fantasypros_archive").access_status
        == AccessStatus.INVESTIGATE
    )
    assert registry.get("fantasypros").commercial_use_status == RightsStatus.REQUIRES_REVIEW
    assert registry.get("razzball").redistribution_status == RightsStatus.REQUIRES_REVIEW


def test_outcome_backbone_is_not_treated_as_projection_vote() -> None:
    record = first_benchmark_source_registry().get("nflverse_outcomes")
    assert SourceRole.OUTCOME in record.roles
    assert SourceRole.PROJECTION not in record.roles
