from datetime import UTC, datetime, timedelta

from fsffl.opportunity.models import ActionAuthority, CandidateReason, EvidenceCompleteness
from fsffl.opportunity.waiver_evaluation import (
    WaiverOpportunityDisposition,
    assess_waiver_materiality,
    candidate_from_waiver_evaluation,
)
from fsffl.team_utility.scenario import (
    AssetPortfolioDelta,
    CompetitiveOutcomeDelta,
    RosterResilienceDelta,
    TeamScenarioDelta,
)
from fsffl.trade_decision import CompetitiveMaterialityPolicy, EconomicMaterialityPolicy
from fsffl.value.models import ValueScale


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
SCALE = ValueScale(scale_id="fsffl", version="1", unit_label="points")


def _competitive_policy(*, evidence_through=AS_OF) -> CompetitiveMaterialityPolicy:
    return CompetitiveMaterialityPolicy(
        expected_wins_abs=0.05,
        playoff_probability_abs=0.01,
        first_place_probability_abs=0.005,
        lineup_drop_abs=0.25,
        model_version="competitive-policy-test",
        evidence_through=evidence_through,
        provenance="synthetic-test",
    )


def _economic_policy(scale=SCALE) -> EconomicMaterialityPolicy:
    return EconomicMaterialityPolicy(
        scale=scale,
        mean_value_abs=10.0,
        model_version="economic-policy-test",
        evidence_through=AS_OF,
        provenance="synthetic-test",
    )


def _delta(*, wins=0.2, playoff=0.03, first=0.01, fragility=-0.5, value=25.0):
    return TeamScenarioDelta(
        team_id="a",
        baseline_as_of=AS_OF,
        scenario_as_of=AS_OF,
        competitive=CompetitiveOutcomeDelta(
            expected_wins=wins,
            playoff_probability=playoff,
            first_place_probability=first,
        ),
        resilience=RosterResilienceDelta(
            largest_single_player_lineup_drop=fragility,
            bench_forecasted_count=0,
            unavailable_count=0,
            missing_forecast_count=0,
        ),
        asset_portfolio=AssetPortfolioDelta(mean_value=value, stddev_value=0.0),
        calculated_state_before="competitive",
        calculated_state_after="competitive",
        model_version="test-delta",
    )


def test_uniform_material_gain_can_support_actionable_waiver() -> None:
    assessment = assess_waiver_materiality(
        _delta(),
        as_of=AS_OF,
        competitive_policy=_competitive_policy(),
        economic_policy=_economic_policy(),
        economic_scale=SCALE,
    )
    candidate = candidate_from_waiver_evaluation(
        candidate_id="waiver-1",
        focal_team_id="a",
        league_state_id="state-1",
        as_of=AS_OF,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        assessment=assessment,
    )

    assert assessment.disposition == WaiverOpportunityDisposition.SUPPORT
    assert candidate.action_authority == ActionAuthority.ACTIONABLE


def test_mixed_waiver_tradeoff_stays_review_only() -> None:
    assessment = assess_waiver_materiality(
        _delta(value=-50.0),
        as_of=AS_OF,
        competitive_policy=_competitive_policy(),
        economic_policy=_economic_policy(),
        economic_scale=SCALE,
    )
    candidate = candidate_from_waiver_evaluation(
        candidate_id="waiver-2",
        focal_team_id="a",
        league_state_id="state-1",
        as_of=AS_OF,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        assessment=assessment,
    )

    assert assessment.disposition == WaiverOpportunityDisposition.REVIEW
    assert candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY
    assert CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION in candidate.reasons


def test_missing_economic_policy_withholds_waiver_action() -> None:
    assessment = assess_waiver_materiality(
        _delta(),
        as_of=AS_OF,
        competitive_policy=_competitive_policy(),
    )

    assert assessment.disposition == WaiverOpportunityDisposition.INSUFFICIENT_EVIDENCE


def test_waiver_materiality_rejects_future_policy_evidence() -> None:
    try:
        assess_waiver_materiality(
            _delta(),
            as_of=AS_OF,
            competitive_policy=_competitive_policy(evidence_through=AS_OF + timedelta(days=1)),
            economic_policy=_economic_policy(),
            economic_scale=SCALE,
        )
    except ValueError as exc:
        assert "future evidence" in str(exc)
    else:
        raise AssertionError("expected future-evidence rejection")


def test_waiver_economic_policy_requires_matching_value_scale() -> None:
    other = ValueScale(scale_id="other", version="1", unit_label="other")
    try:
        assess_waiver_materiality(
            _delta(),
            as_of=AS_OF,
            competitive_policy=_competitive_policy(),
            economic_policy=_economic_policy(),
            economic_scale=other,
        )
    except ValueError as exc:
        assert "match scenario value scale" in str(exc)
    else:
        raise AssertionError("expected scale mismatch rejection")
