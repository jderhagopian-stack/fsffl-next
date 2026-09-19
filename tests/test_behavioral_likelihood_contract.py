from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fsffl.behavioral import (
    BehavioralDriverKind,
    BehavioralEvidenceLevel,
    BehavioralLikelihoodDirection,
    BehavioralLikelihoodDriver,
    BehavioralLikelihoodEstimate,
    BehavioralProbabilityBasis,
)


AS_OF = datetime(2026, 9, 7, tzinfo=UTC)


def test_inferred_behavioral_estimate_can_carry_probability_with_visible_uncertainty() -> None:
    estimate = BehavioralLikelihoodEstimate(
        owner_id="owner-1",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.INFERRED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        observed_trade_count=12,
        acceptance_probability=0.60,
        probability_interval_low=0.39,
        probability_interval_high=0.77,
        probability_basis=BehavioralProbabilityBasis.INFERRED,
        probability_method="bounded-contextual-inference",
        confidence_score=0.42,
        inference_model_version="behavioral-inference-v1",
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
    assert estimate.acceptance_probability == 0.60
    assert estimate.probability_basis == BehavioralProbabilityBasis.INFERRED
    assert estimate.confidence_score == 0.42
    assert estimate.observed_trade_count == 12


def test_inferred_probability_requires_interval_confidence_and_method_provenance() -> None:
    with pytest.raises(ValidationError, match="complete uncertainty interval"):
        BehavioralLikelihoodEstimate(
            owner_id="owner-1",
            as_of=AS_OF,
            evidence_level=BehavioralEvidenceLevel.INFERRED,
            acceptance_probability=0.60,
            probability_basis=BehavioralProbabilityBasis.INFERRED,
            probability_method="bounded-contextual-inference",
            confidence_score=0.42,
            inference_model_version="behavioral-inference-v1",
        )

    with pytest.raises(ValidationError, match="explicit confidence_score"):
        BehavioralLikelihoodEstimate(
            owner_id="owner-1",
            as_of=AS_OF,
            evidence_level=BehavioralEvidenceLevel.INFERRED,
            acceptance_probability=0.60,
            probability_interval_low=0.39,
            probability_interval_high=0.77,
            probability_basis=BehavioralProbabilityBasis.INFERRED,
            probability_method="bounded-contextual-inference",
            inference_model_version="behavioral-inference-v1",
        )


def test_inferred_probability_cannot_claim_calibration_provenance() -> None:
    with pytest.raises(ValidationError, match="cannot claim calibration provenance"):
        BehavioralLikelihoodEstimate(
            owner_id="owner-1",
            as_of=AS_OF,
            evidence_level=BehavioralEvidenceLevel.INFERRED,
            acceptance_probability=0.60,
            probability_interval_low=0.39,
            probability_interval_high=0.77,
            probability_basis=BehavioralProbabilityBasis.INFERRED,
            probability_method="bounded-contextual-inference",
            confidence_score=0.42,
            inference_model_version="behavioral-inference-v1",
            calibration_model_version="not-actually-calibrated",
        )


def test_calibrated_behavioral_estimate_remains_a_stronger_evidence_class() -> None:
    estimate = BehavioralLikelihoodEstimate(
        owner_id="owner-1",
        as_of=AS_OF,
        evidence_level=BehavioralEvidenceLevel.CALIBRATED,
        direction=BehavioralLikelihoodDirection.ELEVATED,
        acceptance_probability=0.58,
        probability_interval_low=0.46,
        probability_interval_high=0.69,
        probability_basis=BehavioralProbabilityBasis.CALIBRATED,
        probability_method="historically-backtested-acceptance-model",
        confidence_score=0.78,
        calibration_model_version="behavioral-acceptance-calibration-v1",
    )
    assert estimate.acceptance_probability == 0.58
    assert estimate.probability_interval_low == 0.46
    assert estimate.probability_interval_high == 0.69
    assert estimate.probability_basis == BehavioralProbabilityBasis.CALIBRATED


def test_behavioral_likelihood_contract_does_not_own_universal_value_or_recommendation_authority() -> None:
    source = open("src/fsffl/behavioral/likelihood.py", encoding="utf-8").read()
    assert "never owns universal market Value or recommendation authority" in source
    assert "market_price" not in source
    assert "recommendation_authority" not in source
