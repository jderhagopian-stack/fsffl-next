from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.trade_decision.decision_quality_weight_robustness import (
    DecisionQualityWeightRobustnessEnvelope,
)

from .historical_trade import GovernedGradePolicy


class HistoricalGradeEnvelope(FrozenModel):
    """Presentation translation of an authoritative Decision robustness envelope.

    Analytics does not choose weights, normalize football evidence, or invent a
    center score. It only maps Decision-owned score ranges through an explicit
    governed grade policy.
    """

    weight_family_id: str
    weight_family_version: str
    score_lower: float
    center_score_lower: float
    center_score_upper: float
    score_upper: float
    center_possible_letters: tuple[str, ...]
    possible_letters: tuple[str, ...]
    letter_invariant: bool
    grade_policy_id: str
    grade_policy_version: str
    model_version: str = "historical-grade-envelope-v1"

    @model_validator(mode="after")
    def validate_envelope(self) -> "HistoricalGradeEnvelope":
        if not (
            0
            <= self.score_lower
            <= self.center_score_lower
            <= self.center_score_upper
            <= self.score_upper
            <= 100
        ):
            raise ValueError("historical grade envelope score bounds are inconsistent")
        if not self.center_possible_letters or not self.possible_letters:
            raise ValueError("historical grade envelope requires translated letters")
        if self.letter_invariant != (len(self.possible_letters) == 1):
            raise ValueError("letter_invariant must reflect the complete possible-letter range")
        return self


def translate_weight_robustness_to_grade_envelope(
    *,
    envelope: DecisionQualityWeightRobustnessEnvelope,
    grade_policy: GovernedGradePolicy,
    model_version: str = "historical-grade-envelope-v1",
) -> HistoricalGradeEnvelope:
    """Translate Decision score uncertainty without selecting a hidden weighting."""

    center_letters = grade_policy.letters_for_range(
        envelope.center_score_minimum,
        envelope.center_score_maximum,
    )
    possible_letters = grade_policy.letters_for_range(
        envelope.score_lower,
        envelope.score_upper,
    )
    return HistoricalGradeEnvelope(
        weight_family_id=envelope.family_id,
        weight_family_version=envelope.family_version,
        score_lower=envelope.score_lower,
        center_score_lower=envelope.center_score_minimum,
        center_score_upper=envelope.center_score_maximum,
        score_upper=envelope.score_upper,
        center_possible_letters=center_letters,
        possible_letters=possible_letters,
        letter_invariant=len(possible_letters) == 1,
        grade_policy_id=grade_policy.policy_id,
        grade_policy_version=grade_policy.model_version,
        model_version=model_version,
    )
