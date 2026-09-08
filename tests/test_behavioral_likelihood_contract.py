from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fsffl.behavioral import (
    BehavioralDriverKind,
    BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection,
    BehavioralLikelihoodDriver,
    BehavioralLikelihoodEstimate,
)


AS_OF = datetime(2026, 9, 7, tzinfo=UTC)


def test_inferred_behavioral_estimate_can_be_useful_without_fake_probability() -> None:
    estimate = BehavioralLikelihoodEstimate(
        owner_id="owner-1",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.INFERRED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        observed_trade_count=12,
        drivers=(
            BehavioralLikelihoodDriver(
                kind=BehavioralDriverKind.OWNER_HISTORY,
                direction=BehavioralLikelihoodDirection.ELEVATED,
                description="Owner has repeatedly consolidated assets in prior trades.",
                evidence_level=BehavioralEvidenceLevel.OBSERVED,
            ),
            BehavioralLikelihoodDriver(
                kind=BehavioralDriverKind.COMPETITIVE_STATE,
                direction=BehavioralLikelihoodDirection.ELEVATED,
                description="Current calculated contender state makes consolidation directionally plausible.",
                evidence_level=BehavioralEvidenceLevel.INFERRED,
            ),
        ),
    )
    assert estimate.direction == BehavioralLikelihoodDirection.ELEVATED
    assert estimate.acceptance_probability is None
    assert estimate.observed_trade_count == 12


def test_uncalibrated_behavioral_estimate_cannot_claim_acceptance_probability() -> None:
    with pytest.raises(ValidationError, match="numeric acceptance probability requires calibrated behavioral evidence"):
        BehavioralLikelihoodEstimate(
            owner_id="owner-1",
            as_of=AS_OF,
            evidence_level=BehavioralEvidenceLevel.INFERRED,
            direction=BehavioralLikelihoodDirection.ELEVATED,
            acceptance_probability=0.60,
        )


def test_calibrated_behavioral_estimate_requires_probability_interval_and_provenance() -> None:
    estimate = BehavioralLikelihoodEstimate(
        owner_id="owner-1",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.CALIBRATED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        acceptance_probability=0.58,
        probability_interval_low=0.46,
        probability_interval_high=0.69,
        calibration_model_version="behavioral-acceptance-calibration-v1",
    )
    assert estimate.acceptance_probability == 0.58
    assert estimate.probability_interval_low == 0.46
    assert estimate.probability_interval_high == 0.69


def test_behavioral_likelihood_contract_does_not_own_value_or_recommendation_authority() -> None:
    source = open("src/fsffl/behavioral/likelihood.py", encoding="utf-8").read()
    assert "never owns market Value or recommendation authority" in source
    assert "market_price" not in source
    assert "recommendation_authority" not in source
