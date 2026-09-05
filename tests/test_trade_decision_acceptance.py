from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.models import PlayerAsset
from fsffl.trade_decision.acceptance import (
    AcceptanceEvidenceItem,
    AcceptanceEvidenceKind,
    AcceptanceEvidenceSet,
    AcceptanceModelStatus,
    AcceptanceProbabilityEstimate,
    TradeAcceptanceView,
    build_unestimated_acceptance_view,
)
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="p1",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="a", sends=(PlayerAsset(player_id="pa"),)),
        side_b=TradeLeg(team_id="b", sends=(PlayerAsset(player_id="pb"),)),
    )


def _evidence(*, observed_at: datetime = AS_OF) -> AcceptanceEvidenceSet:
    return AcceptanceEvidenceSet(
        proposal_id="p1",
        focal_team_id="a",
        counterparty_team_id="b",
        as_of=AS_OF,
        items=(
            AcceptanceEvidenceItem(
                evidence_id="e1",
                kind=AcceptanceEvidenceKind.LEAGUE_TRANSACTION,
                observed_at=observed_at,
                source="league-history",
            ),
        ),
    )


def test_unestimated_view_preserves_missing_model_authority() -> None:
    view = build_unestimated_acceptance_view(
        _proposal(),
        accepting_team_id="b",
        evidence=_evidence(),
    )

    assert view.estimate is None
    assert view.status == AcceptanceModelStatus.NOT_ESTIMATED
    assert view.accepting_team_id == "b"


def test_future_acceptance_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="future observations"):
        _evidence(observed_at=AS_OF + timedelta(seconds=1))


def test_acceptance_estimate_requires_ordered_interval_and_governed_status() -> None:
    with pytest.raises(ValueError, match="interval"):
        AcceptanceProbabilityEstimate(
            proposal_id="p1",
            accepting_team_id="b",
            probability_mean=0.5,
            probability_p10=0.7,
            probability_p90=0.8,
            as_of=AS_OF,
            evidence_count=1,
            status=AcceptanceModelStatus.CHALLENGER,
            model_version="m1",
            evidence_model_version="e1",
        )

    with pytest.raises(ValueError, match="NOT_ESTIMATED"):
        AcceptanceProbabilityEstimate(
            proposal_id="p1",
            accepting_team_id="b",
            probability_mean=0.5,
            probability_p10=0.2,
            probability_p90=0.8,
            as_of=AS_OF,
            evidence_count=1,
            status=AcceptanceModelStatus.NOT_ESTIMATED,
            model_version="m1",
            evidence_model_version="e1",
        )


def test_acceptance_view_rejects_team_or_status_mismatch() -> None:
    estimate = AcceptanceProbabilityEstimate(
        proposal_id="p1",
        accepting_team_id="b",
        probability_mean=0.5,
        probability_p10=0.2,
        probability_p90=0.8,
        as_of=AS_OF,
        evidence_count=1,
        status=AcceptanceModelStatus.CHALLENGER,
        model_version="m1",
        evidence_model_version="e1",
    )

    with pytest.raises(ValueError, match="status"):
        TradeAcceptanceView(
            proposal_id="p1",
            accepting_team_id="b",
            evidence=_evidence(),
            estimate=estimate,
            status=AcceptanceModelStatus.PROVISIONAL_GOVERNED,
        )

    with pytest.raises(ValueError, match="accepting team"):
        build_unestimated_acceptance_view(
            _proposal(),
            accepting_team_id="c",
            evidence=_evidence(),
        )
