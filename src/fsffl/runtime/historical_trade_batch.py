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

from .historical_trade_readiness import HistoricalTradeValuationReadiness


class HistoricalTradeProgressStatus(StrEnum):
    READY_FOR_DECISION = "ready_for_decision"
    READY_FOR_GRADE_ENVELOPE = "ready_for_grade_envelope"
    SENSITIVITY_DEPENDENT = "sensitivity_dependent"
    DECISION_INCOMPLETE = "decision_incomplete"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"


class HistoricalTradeProgress(FrozenModel):
    transaction_id: str
    status: HistoricalTradeProgressStatus
    reason: str
    probabilistic_asset_count: int = 0
    bounded_nuisance_asset_count: int = 0
    sensitivity_only_asset_count: int = 0

    @model_validator(mode="after")
    def validate_progress(self) -> "HistoricalTradeProgress":
        if not self.transaction_id.strip() or not self.reason.strip():
            raise ValueError("historical trade progress identifiers/reason cannot be blank")
        counts = (
            self.probabilistic_asset_count,
            self.bounded_nuisance_asset_count,
            self.sensitivity_only_asset_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("historical trade progress counts cannot be negative")
        return self


class HistoricalTradeBatchProgress(FrozenModel):
    trade_count: int
    status_counts: tuple[tuple[HistoricalTradeProgressStatus, int], ...]
    rows: tuple[HistoricalTradeProgress, ...]

    @model_validator(mode="after")
    def validate_batch(self) -> "HistoricalTradeBatchProgress":
        if self.trade_count != len(self.rows):
            raise ValueError("historical trade batch count must match rows")
        if len({row.transaction_id for row in self.rows}) != len(self.rows):
            raise ValueError("historical trade batch requires unique transaction ids")
        expected = Counter(row.status for row in self.rows)
        if self.status_counts != tuple(sorted(expected.items(), key=lambda item: item[0].value)):
            raise ValueError("historical trade batch status counts must match rows")
        return self


def classify_historical_trade_progress(
    readiness: HistoricalTradeValuationReadiness,
    *,
    robustness: HistoricalDecisionRobustness | None = None,
) -> HistoricalTradeProgress:
    """Classify how far one historical trade can progress without inventing truth.

    Readiness answers whether every material asset has usable PIT evidence.
    Robustness answers whether Decision's qualitative conclusion survives the
    supplied uncertainty scenarios. A ROBUST Decision is only ready for a
    downstream grade-envelope calculation; Runtime does not claim that the letter
    itself is invariant because grade translation belongs to Analytics.
    """

    if robustness is not None and robustness.proposal_id != readiness.transaction_id:
        raise ValueError("historical robustness result must match readiness transaction_id")

    probabilistic_count = len(readiness.probabilistic_asset_keys)
    nuisance_count = len(readiness.bounded_nuisance_asset_keys)
    sensitivity_count = len(readiness.sensitivity_only_asset_keys)

    if not readiness.grade_eligible:
        return HistoricalTradeProgress(
            transaction_id=readiness.transaction_id,
            status=HistoricalTradeProgressStatus.EVIDENCE_INCOMPLETE,
            reason="one or more material trade assets lacks usable PIT evidence",
            probabilistic_asset_count=probabilistic_count,
            bounded_nuisance_asset_count=nuisance_count,
            sensitivity_only_asset_count=sensitivity_count,
        )

    if robustness is None:
        return HistoricalTradeProgress(
            transaction_id=readiness.transaction_id,
            status=HistoricalTradeProgressStatus.READY_FOR_DECISION,
            reason="all material assets have usable PIT evidence; Decision robustness has not yet been evaluated",
            probabilistic_asset_count=probabilistic_count,
            bounded_nuisance_asset_count=nuisance_count,
            sensitivity_only_asset_count=sensitivity_count,
        )

    if robustness.status == HistoricalDecisionRobustnessStatus.ROBUST:
        status = HistoricalTradeProgressStatus.READY_FOR_GRADE_ENVELOPE
        reason = "Decision conclusion is stable across supplied PIT scenarios; downstream grade-envelope robustness remains to be tested"
    elif robustness.status == HistoricalDecisionRobustnessStatus.SENSITIVE:
        status = HistoricalTradeProgressStatus.SENSITIVITY_DEPENDENT
        reason = "plausible PIT uncertainty scenarios change the Decision conclusion"
    else:
        status = HistoricalTradeProgressStatus.DECISION_INCOMPLETE
        reason = "Decision evidence is incomplete in one or more PIT uncertainty scenarios"

    return HistoricalTradeProgress(
        transaction_id=readiness.transaction_id,
        status=status,
        reason=reason,
        probabilistic_asset_count=probabilistic_count,
        bounded_nuisance_asset_count=nuisance_count,
        sensitivity_only_asset_count=sensitivity_count,
    )


def summarize_historical_trade_progress(
    readiness_rows: Sequence[HistoricalTradeValuationReadiness],
    *,
    robustness_by_transaction_id: Mapping[str, HistoricalDecisionRobustness] | None = None,
) -> HistoricalTradeBatchProgress:
    """Build a deterministic league-wide progression matrix.

    Missing robustness results are not failures: those rows are explicitly marked
    READY_FOR_DECISION so batch orchestration can schedule only the work that
    remains. Extra robustness results are rejected to prevent stale/mismatched
    analyses from silently entering the batch.
    """

    robustness_map = dict(robustness_by_transaction_id or {})
    transaction_ids = [row.transaction_id for row in readiness_rows]
    if len(transaction_ids) != len(set(transaction_ids)):
        raise ValueError("historical trade batch requires unique readiness transaction ids")
    unexpected = set(robustness_map) - set(transaction_ids)
    if unexpected:
        raise ValueError(f"robustness results contain unknown transactions: {sorted(unexpected)}")

    rows = tuple(
        classify_historical_trade_progress(
            readiness,
            robustness=robustness_map.get(readiness.transaction_id),
        )
        for readiness in sorted(readiness_rows, key=lambda item: item.transaction_id)
    )
    counts = Counter(row.status for row in rows)
    return HistoricalTradeBatchProgress(
        trade_count=len(rows),
        status_counts=tuple(sorted(counts.items(), key=lambda item: item[0].value)),
        rows=rows,
    )
