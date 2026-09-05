from datetime import UTC, datetime, timedelta

import pytest

from fsffl.team_utility.competitive_state import (
    CompetitiveStatePolicy,
    classify_calculated_competitive_state,
)
from fsffl.team_utility.simulation import TeamCompetitiveOutcome
from fsffl.team_utility.utility import CalculatedCompetitiveState


AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)


def outcome(playoff: float, first: float) -> TeamCompetitiveOutcome:
    return TeamCompetitiveOutcome(
        team_id="team:1",
        expected_wins=7.5,
        wins_stddev=2.0,
        playoff_probability=playoff,
        first_place_probability=first,
        simulation_count=50_000,
        simulation_model_version="sim-v1",
    )


def policy() -> CompetitiveStatePolicy:
    return CompetitiveStatePolicy(
        developing_playoff_min=0.20,
        competitive_playoff_min=0.50,
        contender_playoff_min=0.75,
        contender_first_place_min=0.20,
        model_version="state-policy-test-v1",
        evidence_through=AS_OF - timedelta(days=1),
        provenance="synthetic test policy",
    )


def test_state_classification_requires_both_contender_conditions() -> None:
    assert classify_calculated_competitive_state(outcome(0.80, 0.25), policy(), as_of=AS_OF) == CalculatedCompetitiveState.CONTENDER
    assert classify_calculated_competitive_state(outcome(0.80, 0.10), policy(), as_of=AS_OF) == CalculatedCompetitiveState.COMPETITIVE


def test_state_classification_preserves_ordered_lower_states() -> None:
    assert classify_calculated_competitive_state(outcome(0.60, 0.05), policy(), as_of=AS_OF) == CalculatedCompetitiveState.COMPETITIVE
    assert classify_calculated_competitive_state(outcome(0.30, 0.02), policy(), as_of=AS_OF) == CalculatedCompetitiveState.DEVELOPING
    assert classify_calculated_competitive_state(outcome(0.10, 0.01), policy(), as_of=AS_OF) == CalculatedCompetitiveState.REBUILDING


def test_policy_rejects_future_evidence() -> None:
    future = policy().model_copy(update={"evidence_through": AS_OF + timedelta(seconds=1)})
    with pytest.raises(ValueError, match="future"):
        classify_calculated_competitive_state(outcome(0.80, 0.25), future, as_of=AS_OF)


def test_policy_thresholds_must_be_monotone() -> None:
    with pytest.raises(ValueError, match="increase"):
        CompetitiveStatePolicy(
            developing_playoff_min=0.60,
            competitive_playoff_min=0.50,
            contender_playoff_min=0.75,
            contender_first_place_min=0.20,
            model_version="bad",
            evidence_through=AS_OF,
            provenance="test",
        )
