from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.trade_decision.historical_robustness import (
    HistoricalDecisionRobustness,
    HistoricalDecisionRobustnessStatus,
)
from fsffl.runtime.historical_trade_readiness import HistoricalTradeValuationReadiness

from .historical_grade_envelope import HistoricalGradeEnvelope


class HistoricalConclusionStatus(StrEnum):
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    READY_FOR_DECISION = "ready_for_decision"
    DECISION_INCOMPLETE = "decision_incomplete"
    DECISION_SENSITIVE = "decision_sensitive"
    READY_FOR_GRADE_ENVELOPE = "ready_for_grade_envelope"
    GRADE_SENSITIVE = "grade_sensitive"
    ROBUST_GRADE = "robust_grade"


class HistoricalTradeConclusion(FrozenModel):
    transaction_id: str
    status: HistoricalConclusionStatus
    reason: str
    possible_letters: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_conclusion(self) -> "HistoricalTradeConclusion":
        if not self.transaction_id.strip() or not self.reason.strip():
            raise ValueError("historical conclusion identifiers/reason cannot be blank")
        if self.status == HistoricalConclusionStatus.ROBUST_GRADE and len(self.possible_letters) != 1:
            raise ValueError("robust grade requires exactly one possible letter")
        if self.status == HistoricalConclusionStatus.GRADE_SENSITIVE and len(self.possible_letters) < 2:
            raise ValueError("grade-sensitive conclusion requires multiple possible letters")
        if self.status not in {
            HistoricalConclusionStatus.ROBUST_GRADE,
            HistoricalConclusionStatus.GRADE_SENSITIVE,
        } and self.possible_letters:
            raise ValueError("letters may only be attached after grade-envelope evaluation")
        return self


class HistoricalConclusionBatch(FrozenModel):
    trade_count: int
    status_counts: tuple[tuple[HistoricalConclusionStatus, int], ...]
    rows: tuple[HistoricalTradeConclusion, ...]

    @model_validator(mode="after")
    def validate_batch(self) -> "HistoricalConclusionBatch":
        if self.trade_count != len(self.rows):
            raise ValueError("historical conclusion trade_count must match rows")
        if len({row.transaction_id for row in self.rows}) != len(self.rows):
            raise ValueError("historical conclusion batch requires unique transactions")
        expected = tuple(sorted(Counter(row.status for row in self.rows).items(), key=lambda item: item[0].value))
        if self.status_counts != expected:
            raise ValueError("historical conclusion status_counts must match rows")
        return self


def conclude_historical_trade(
    readiness: HistoricalTradeValuationReadiness,
    *,
    robustness: HistoricalDecisionRobustness | None = None,
    grade_envelope: HistoricalGradeEnvelope | None = None,
) -> HistoricalTradeConclusion:
    """Return the furthest defensible historical conclusion without inventing truth."""

    if robustness is not None and robustness.proposal_id != readiness.transaction_id:
        raise ValueError("Decision robustness must match readiness transaction_id")
    if grade_envelope is not None and robustness is None:
        raise ValueError("grade envelope requires Decision robustness")

    transaction_id = readiness.transaction_id
    if not readiness.grade_eligible:
        if robustness is not None or grade_envelope is not None:
            raise ValueError("blocked trade cannot carry downstream Decision/grade results")
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.EVIDENCE_INCOMPLETE,
            reason="one or more material assets still lacks usable point-in-time evidence",
        )

    if robustness is None:
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.READY_FOR_DECISION,
            reason="asset evidence is usable; Decision robustness has not yet been run",
        )

    if robustness.status == HistoricalDecisionRobustnessStatus.INCOMPLETE:
        if grade_envelope is not None:
            raise ValueError("incomplete Decision cannot carry a grade envelope")
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.DECISION_INCOMPLETE,
            reason="one or more plausible point-in-time scenarios still lacks complete Decision evidence",
        )

    if robustness.status == HistoricalDecisionRobustnessStatus.SENSITIVE:
        if grade_envelope is not None:
            raise ValueError("Decision-sensitive trade cannot carry a final grade envelope")
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.DECISION_SENSITIVE,
            reason="plausible point-in-time scenarios change the Decision conclusion",
        )

    if grade_envelope is None:
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.READY_FOR_GRADE_ENVELOPE,
            reason="Decision conclusion is stable; grade robustness remains to be tested",
        )

    if grade_envelope.letter_invariant:
        return HistoricalTradeConclusion(
            transaction_id=transaction_id,
            status=HistoricalConclusionStatus.ROBUST_GRADE,
            reason="Decision and letter grade are stable across the supplied uncertainty ranges",
            possible_letters=grade_envelope.possible_letters,
        )

    return HistoricalTradeConclusion(
        transaction_id=transaction_id,
        status=HistoricalConclusionStatus.GRADE_SENSITIVE,
        reason="Decision direction is stable, but the letter grade changes across plausible weights/evidence",
        possible_letters=grade_envelope.possible_letters,
    )


def summarize_historical_conclusions(
    readiness_rows: Sequence[HistoricalTradeValuationReadiness],
    *,
    robustness_by_transaction_id: Mapping[str, HistoricalDecisionRobustness] | None = None,
    grade_envelope_by_transaction_id: Mapping[str, HistoricalGradeEnvelope] | None = None,
) -> HistoricalConclusionBatch:
    robustness_map = dict(robustness_by_transaction_id or {})
    envelope_map = dict(grade_envelope_by_transaction_id or {})
    transaction_ids = {row.transaction_id for row in readiness_rows}
    unexpected = (set(robustness_map) | set(envelope_map)) - transaction_ids
    if unexpected:
        raise ValueError(f"historical conclusion inputs contain unknown transactions: {sorted(unexpected)}")

    rows = tuple(
        conclude_historical_trade(
            readiness,
            robustness=robustness_map.get(readiness.transaction_id),
            grade_envelope=envelope_map.get(readiness.transaction_id),
        )
        for readiness in sorted(readiness_rows, key=lambda item: item.transaction_id)
    )
    counts = tuple(sorted(Counter(row.status for row in rows).items(), key=lambda item: item[0].value))
    return HistoricalConclusionBatch(trade_count=len(rows), status_counts=counts, rows=rows)
