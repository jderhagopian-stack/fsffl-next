from datetime import UTC, datetime, timedelta

import pytest

from fsffl.team_utility.competitive_state import (
    CompetitiveStatePolicy,
    classify_calculated_competitive_state,
    derive_league_relative_competitive_state_policy,
)
from fsffl.team_utility.simulation import TeamCompetitiveOutcome
from fsffl.team_utility.utility import CalculatedCompetitiveState


AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)


def outcome(playoff: float, first: float, team_id: str = "team:1") -> TeamCompetitiveOutcome:
    return TeamCompetitiveOutcome(
        team_id=team_id,
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


def test_league_relative_policy_is_derived_from_simulation_distribution() -> None:
    outcomes = tuple(
        outcome(playoff, first, team_id=f"team:{index}")
        for index, (playoff, first) in enumerate(
            (
                (0.10, 0.01),
                (0.20, 0.02),
                (0.30, 0.03),
                (0.40, 0.04),
                (0.50, 0.05),
                (0.60, 0.06),
                (0.70, 0.07),
                (0.80, 0.08),
            ),
            start=1,
        )
    )
    derived = derive_league_relative_competitive_state_policy(outcomes, as_of=AS_OF)
    assert derived.developing_playoff_min == pytest.approx(0.275)
    assert derived.competitive_playoff_min == pytest.approx(0.45)
    assert derived.contender_playoff_min == pytest.approx(0.625)
    assert derived.contender_first_place_min == pytest.approx(0.0625)
    assert "league-relative-quartiles" in derived.model_version
    assert derived.evidence_through == AS_OF


def test_league_relative_policy_populates_all_state_bands_without_changing_outcomes() -> None:
    outcomes = (
        outcome(0.10, 0.01, "rebuild"),
        outcome(0.30, 0.03, "develop"),
        outcome(0.60, 0.05, "competitive"),
        outcome(0.90, 0.20, "contender"),
    )
    derived = derive_league_relative_competitive_state_policy(outcomes, as_of=AS_OF)
    states = {
        row.team_id: classify_calculated_competitive_state(row, derived, as_of=AS_OF)
        for row in outcomes
    }
    assert states["rebuild"] == CalculatedCompetitiveState.REBUILDING
    assert states["develop"] == CalculatedCompetitiveState.DEVELOPING
    assert states["competitive"] == CalculatedCompetitiveState.COMPETITIVE
    assert states["contender"] == CalculatedCompetitiveState.CONTENDER
    assert outcomes[0].playoff_probability == 0.10
    assert outcomes[-1].first_place_probability == 0.20
