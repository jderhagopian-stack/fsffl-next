from datetime import UTC, date, datetime

import pytest

from fsffl.state.historical_coverage import HistoricalSeasonIdentity
from fsffl.state.historical_supplemental_evidence import (
    HistoricalSupplementalEvidenceReceipt,
    HistoricalSupplementalPlayerMovement,
    SupplementalDatePrecision,
    SupplementalEvidenceSource,
    SupplementalFindingStatus,
    SupplementalPlayerMovementKind,
    reconcile_supplemental_player_movements,
)
from fsffl.state.retrospective_season_audit import (
    RetrospectiveSeasonAudit,
    RetrospectiveSeasonIssue,
)

SEASON = HistoricalSeasonIdentity(
    league_family_id="family-1",
    league_id="provider-league-2023",
    season=2023,
)
EVENT_AT = datetime(2023, 7, 27, 12, tzinfo=UTC)


def provider_issue(*, player="source-player-1", roster="7", completed_at=EVENT_AT):
    return RetrospectiveSeasonIssue(
        code="post_event_player_missing",
        transaction_id="waiver-1",
        completed_at=completed_at,
        event_type="waiver",
        asset_id=player,
        provider_roster_id=roster,
    )


def provider_audit(issue=None):
    issues = (issue or provider_issue(),)
    return RetrospectiveSeasonAudit(
        provider_league_id=SEASON.league_id,
        season=SEASON.season,
        source_revision="git-blob:source-revision",
        source_sha256="a" * 64,
        original_rules_sha256="b" * 64,
        team_count=12,
        completed_events_examined=1,
        completed_trades_examined=0,
        player_movements_examined=1,
        pick_movements_examined=0,
        faab_transfers_examined=0,
        waiver_bids_examined=1,
        completed_timestamp_tie_groups=0,
        issues=issues,
        status="incomplete_source_history",
    )


def movement(*, player="source-player-1", roster="7", event_date=date(2023, 8, 23),
             kind=SupplementalPlayerMovementKind.DROPPED_TO_WAIVERS,
             precision=SupplementalDatePrecision.DATE_ONLY, effective_at=None):
    receipt = HistoricalSupplementalEvidenceReceipt(
        evidence_id="supplement-1",
        source=SupplementalEvidenceSource.USER_SUPPLIED_SCREENSHOT,
        source_fingerprint_sha256="c" * 64,
        received_at=datetime(2026, 11, 1, tzinfo=UTC),
        source_reference="private evidence reference",
    )
    return HistoricalSupplementalPlayerMovement(
        season=SEASON,
        provider="sleeper",
        source_player_id=player,
        player_id="canonical-player-1",
        provider_roster_id=roster,
        kind=kind,
        effective_date=event_date,
        date_precision=precision,
        effective_at=effective_at,
        receipt=receipt,
    )


def test_later_matching_drop_supports_gap_without_mutating_provider_audit():
    audit = provider_audit()
    result = reconcile_supplemental_player_movements(audit, (movement(),))
    assert result.provider_audit is audit
    assert result.provider_audit.status == "incomplete_source_history"
    assert result.provider_audit.issues == audit.issues
    assert result.findings[0].status == SupplementalFindingStatus.SUPPORTED_RETROSPECTIVELY
    assert result.findings[0].evidence_ids == ("supplement-1",)
    assert result.eligible_for_pit_decision_grade is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"player": "different-player"},
        {"roster": "8"},
        {"kind": SupplementalPlayerMovementKind.ADDED_TO_ROSTER},
    ],
)
def test_nonmatching_or_nonlater_movement_does_not_support_gap(kwargs):
    result = reconcile_supplemental_player_movements(provider_audit(), (movement(**kwargs),))
    assert result.findings[0].status == SupplementalFindingStatus.UNRESOLVED


@pytest.mark.parametrize("event_date", [date(2023, 7, 26), date(2023, 7, 28)])
def test_date_only_evidence_with_adjacent_utc_day_is_ambiguous(event_date):
    result = reconcile_supplemental_player_movements(
        provider_audit(), (movement(event_date=event_date),)
    )
    assert result.findings[0].status == SupplementalFindingStatus.AMBIGUOUS


def test_same_day_date_only_evidence_is_ambiguous():
    same_day = movement(event_date=EVENT_AT.date())
    result = reconcile_supplemental_player_movements(provider_audit(), (same_day,))
    assert result.findings[0].status == SupplementalFindingStatus.AMBIGUOUS


def test_exact_timestamp_after_provider_event_on_same_day_supports_gap():
    exact = movement(
        event_date=EVENT_AT.date(),
        precision=SupplementalDatePrecision.EXACT_TIMESTAMP,
        effective_at=datetime(2023, 7, 27, 13, tzinfo=UTC),
    )
    result = reconcile_supplemental_player_movements(provider_audit(), (exact,))
    assert result.findings[0].status == SupplementalFindingStatus.SUPPORTED_RETROSPECTIVELY


def test_exact_timestamp_tie_is_ambiguous():
    exact = movement(
        event_date=EVENT_AT.date(),
        precision=SupplementalDatePrecision.EXACT_TIMESTAMP,
        effective_at=EVENT_AT,
    )
    result = reconcile_supplemental_player_movements(provider_audit(), (exact,))
    assert result.findings[0].status == SupplementalFindingStatus.AMBIGUOUS


def test_multiple_distinct_later_drop_dates_are_ambiguous():
    first = movement()
    second = movement(
        event_date=date(2023, 8, 24),
        # A distinct evidence record is required for an independent claim.
    ).model_copy(update={
        "receipt": first.receipt.model_copy(update={"evidence_id": "supplement-2"})
    })
    result = reconcile_supplemental_player_movements(provider_audit(), (first, second))
    assert result.findings[0].status == SupplementalFindingStatus.AMBIGUOUS
    assert result.findings[0].evidence_ids == ("supplement-1", "supplement-2")


def test_cross_season_supplement_is_rejected():
    wrong_season = movement().model_copy(update={
        "season": SEASON.model_copy(update={"season": 2024})
    })
    with pytest.raises(ValueError, match="another provider season"):
        reconcile_supplemental_player_movements(provider_audit(), (wrong_season,))


def test_date_only_contract_rejects_exact_time():
    with pytest.raises(ValueError, match="date-only"):
        movement(
            precision=SupplementalDatePrecision.DATE_ONLY,
            effective_at=datetime(2023, 8, 23, 12, tzinfo=UTC),
        )
