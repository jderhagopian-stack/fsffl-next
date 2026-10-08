from datetime import datetime, timezone

import pytest

from fsffl.research.intrinsic_value_empirical import (
    EconomicBehaviorScenario,
    EconomicUsefulnessCheck,
    MarketIndependenceDiagnostic,
    TimePreferenceConfounder,
    TimePreferenceIdentificationResult,
)


def test_time_preference_cannot_claim_identification_without_required_controls() -> None:
    with pytest.raises(ValueError, match="required confounders"):
        TimePreferenceIdentificationResult(
            fold_id="fold-1",
            estimate=0.82,
            confounders_controlled=(TimePreferenceConfounder.CURRENT_PRODUCTION,),
            identified=True,
        )


def test_time_preference_can_be_identified_only_after_core_confounders_are_controlled() -> None:
    result = TimePreferenceIdentificationResult(
        fold_id="fold-1",
        estimate=0.82,
        standard_error=0.04,
        confounders_controlled=(
            TimePreferenceConfounder.AGE_CAREER_STAGE,
            TimePreferenceConfounder.POSITION_SCARCITY,
            TimePreferenceConfounder.LIQUIDITY,
            TimePreferenceConfounder.DRAFT_CLASS_STRENGTH,
            TimePreferenceConfounder.CURRENT_PRODUCTION,
            TimePreferenceConfounder.FORECAST_UNCERTAINTY,
        ),
        identified=True,
    )
    assert result.identified is True


def test_market_independence_diagnostic_requires_material_disagreement_measure() -> None:
    diagnostic = MarketIndependenceDiagnostic(
        fold_id="fold-1",
        sample_size=100,
        pearson_correlation=0.72,
        rank_correlation=0.69,
        mean_absolute_standardized_residual=0.41,
        material_disagreement_rate=0.23,
        market_adds_incremental_downstream_information=True,
    )
    assert diagnostic.material_disagreement_rate == 0.23
    assert diagnostic.market_adds_incremental_downstream_information is True


def test_economic_usefulness_check_requires_explanation() -> None:
    with pytest.raises(ValueError, match="require an explanation"):
        EconomicUsefulnessCheck(
            scenario=EconomicBehaviorScenario.ELITE_QB_LONGEVITY,
            fold_id="fold-1",
            passed=True,
            explanation="",
        )
