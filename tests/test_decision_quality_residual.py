from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality_residual import unresolved_decision_quality_component


def test_unresolved_residual_keeps_full_score_range_and_zero_confidence() -> None:
    component = unresolved_decision_quality_component(
        component_id="liquidity",
        authority_id="unresolved-liquidity-research",
        overlap_group="liquidity",
        as_of=datetime(2022, 8, 9, tzinfo=UTC),
        evidence_through=datetime(2022, 8, 9, tzinfo=UTC),
        model_version="residual-v1",
        provenance="research:explicit-unresolved-channel",
    )
    assert component.score_lower == 0
    assert component.score_center == 50
    assert component.score_upper == 100
    assert component.confidence == 0


def test_unresolved_residual_rejects_future_evidence() -> None:
    with pytest.raises(ValueError, match="future evidence"):
        unresolved_decision_quality_component(
            component_id="liquidity",
            authority_id="unresolved-liquidity-research",
            overlap_group="liquidity",
            as_of=datetime(2022, 8, 9, tzinfo=UTC),
            evidence_through=datetime(2022, 8, 10, tzinfo=UTC),
            model_version="residual-v1",
            provenance="research",
        )
