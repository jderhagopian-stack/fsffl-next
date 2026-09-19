from datetime import UTC, datetime

from fsffl.analytics.league import LeagueAnalyticsView, LeagueTeamAnalyticsRow
from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.opportunity import build_opportunity_analytics_view
from fsffl.analytics.report import LeagueReportData, render_league_report_markdown
from fsffl.opportunity.models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
CONTEXT = AnalyticsContext(
    schema_version="1",
    league_id="l1",
    league_state_id="state-1",
    as_of=AS_OF,
    generated_at=AS_OF,
    lineage=(ModelLineageEntry(component="opportunity", model_version="next6-v1"),),
    warnings=(
        AnalyticsWarning(
            kind=AnalyticsWarningKind.UNKNOWN_ACCEPTANCE,
            code="acceptance-unknown",
            message="Acceptance is not estimated.",
            source_component="trade_decision",
        ),
    ),
)


def _candidate() -> OpportunityCandidate:
    return OpportunityCandidate(
        candidate_id="c1",
        kind=OpportunityKind.TRADE,
        focal_team_id="a",
        league_state_id="state-1",
        as_of=AS_OF,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=ActionAuthority.MARKET_TEST_ONLY,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reasons=(CandidateReason.UNKNOWN_ACCEPTANCE,),
        search_model_version="next6-test",
    )


def test_report_renderer_is_deterministic_and_uses_view_fields() -> None:
    league = LeagueAnalyticsView(
        context=CONTEXT,
        teams=(
            LeagueTeamAnalyticsRow(
                team_id="a",
                display_name="Alpha",
                player_count=18,
                draft_pick_count=3,
                optimized_expected_points=120.5,
                expected_wins=9.2,
                playoff_probability=0.71,
                first_place_probability=0.18,
            ),
        ),
    )
    opportunities = build_opportunity_analytics_view(
        context=CONTEXT,
        candidates=(_candidate(),),
    )
    report = LeagueReportData(
        context=CONTEXT,
        title="League Report",
        league=league,
        teams=(),
        opportunities=opportunities,
    )

    first = render_league_report_markdown(report)
    second = render_league_report_markdown(report)

    assert first == second
    assert "Alpha" in first
    assert "120.50" in first
    assert "71.0%" in first
    assert "Market-test only: **1**" in first
    assert "Acceptance is not estimated." in first
    assert "next6-v1" in first


def test_report_rejects_mismatched_context() -> None:
    other = AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="other-state",
        as_of=AS_OF,
        generated_at=AS_OF,
        lineage=(),
    )
    league = LeagueAnalyticsView(context=other, teams=())
    try:
        LeagueReportData(
            context=CONTEXT,
            title="Bad report",
            league=league,
            teams=(),
        )
    except ValueError as exc:
        assert "share report context" in str(exc)
    else:
        raise AssertionError("expected report-context mismatch rejection")
