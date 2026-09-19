from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.historical_pick import HistoricalPickCoordinateResult

from .historical_trade_readiness import HistoricalEvidenceMode


class HistoricalPickBatchItem(FrozenModel):
    """One pick reconstruction attached to a trade-local evidence mode.

    Value owns the coordinate result. Runtime owns only batch orchestration and the
    evidence-mode label already established by the historical workflow.
    """

    transaction_id: str
    asset_key: str
    result: HistoricalPickCoordinateResult
    evidence_mode: HistoricalEvidenceMode | None = None

    @model_validator(mode="after")
    def validate_item(self) -> "HistoricalPickBatchItem":
        if not self.transaction_id.strip() or not self.asset_key.strip():
            raise ValueError("historical pick batch identifiers cannot be blank")
        if self.result.estimate is not None and self.evidence_mode not in {
            HistoricalEvidenceMode.EXACT,
            HistoricalEvidenceMode.PROBABILISTIC,
            HistoricalEvidenceMode.SENSITIVITY_ONLY,
        }:
            raise ValueError("reconstructed historical picks require an exact/probabilistic/sensitivity evidence mode")
        if self.result.estimate is None and self.evidence_mode is not None:
            raise ValueError("unreconstructed historical picks cannot declare a usable evidence mode")
        if self.result.exact_slot_used and self.evidence_mode != HistoricalEvidenceMode.EXACT:
            raise ValueError("exact-slot historical picks must use EXACT evidence mode")
        if not self.result.exact_slot_used and self.result.estimate is not None and self.evidence_mode == HistoricalEvidenceMode.EXACT:
            raise ValueError("unresolved historical picks cannot use EXACT evidence mode")
        return self


class HistoricalPickBatchSummary(FrozenModel):
    pick_asset_count: int
    transaction_count: int
    reconstructed_pick_count: int
    unreconstructed_pick_count: int
    exact_pick_count: int
    probabilistic_pick_count: int
    sensitivity_only_pick_count: int
    evidence_quality_counts: tuple[tuple[str, int], ...]
    status_counts: tuple[tuple[str, int], ...]
    transactions_with_probabilistic_picks: int
    transactions_with_sensitivity_only_picks: int
    transactions_with_unreconstructed_picks: int

    @model_validator(mode="after")
    def validate_counts(self) -> "HistoricalPickBatchSummary":
        values = (
            self.pick_asset_count,
            self.transaction_count,
            self.reconstructed_pick_count,
            self.unreconstructed_pick_count,
            self.exact_pick_count,
            self.probabilistic_pick_count,
            self.sensitivity_only_pick_count,
            self.transactions_with_probabilistic_picks,
            self.transactions_with_sensitivity_only_picks,
            self.transactions_with_unreconstructed_picks,
        )
        if any(value < 0 for value in values):
            raise ValueError("historical pick batch counts cannot be negative")
        if self.reconstructed_pick_count + self.unreconstructed_pick_count != self.pick_asset_count:
            raise ValueError("reconstructed + unreconstructed must equal pick_asset_count")
        if self.exact_pick_count + self.probabilistic_pick_count + self.sensitivity_only_pick_count != self.reconstructed_pick_count:
            raise ValueError("usable evidence modes must partition reconstructed picks")
        return self


def summarize_historical_pick_batch(items: Sequence[HistoricalPickBatchItem]) -> HistoricalPickBatchSummary:
    """Summarize pick evidence strength without changing valuation or eligibility.

    This works for any league. It reports what the supplied historical reconstruction
    actually established; it does not infer slot probabilities, promote low-quality
    evidence, or reinterpret a sensitivity-only range as a precise estimate.
    """

    identities = [(item.transaction_id, item.asset_key) for item in items]
    if len(identities) != len(set(identities)):
        raise ValueError("historical pick batch requires unique trade-local asset identities")

    quality_counts = Counter(item.result.evidence_quality for item in items)
    status_counts = Counter(item.result.status for item in items)
    reconstructed = [item for item in items if item.result.estimate is not None]
    modes = Counter(item.evidence_mode for item in reconstructed)
    transaction_ids = {item.transaction_id for item in items}

    return HistoricalPickBatchSummary(
        pick_asset_count=len(items),
        transaction_count=len(transaction_ids),
        reconstructed_pick_count=len(reconstructed),
        unreconstructed_pick_count=len(items) - len(reconstructed),
        exact_pick_count=modes[HistoricalEvidenceMode.EXACT],
        probabilistic_pick_count=modes[HistoricalEvidenceMode.PROBABILISTIC],
        sensitivity_only_pick_count=modes[HistoricalEvidenceMode.SENSITIVITY_ONLY],
        evidence_quality_counts=tuple(sorted(quality_counts.items())),
        status_counts=tuple(sorted(status_counts.items())),
        transactions_with_probabilistic_picks=len({
            item.transaction_id for item in reconstructed if item.evidence_mode == HistoricalEvidenceMode.PROBABILISTIC
        }),
        transactions_with_sensitivity_only_picks=len({
            item.transaction_id for item in reconstructed if item.evidence_mode == HistoricalEvidenceMode.SENSITIVITY_ONLY
        }),
        transactions_with_unreconstructed_picks=len({
            item.transaction_id for item in items if item.result.estimate is None
        }),
    )
