from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_pick_batch import HistoricalPickBatchItem, summarize_historical_pick_batch
from fsffl.runtime.historical_trade_readiness import HistoricalEvidenceMode
from fsffl.value.historical_pick import HistoricalPickCoordinateResult
from fsffl.value.models import PickValueEstimate, ValueDistribution, ValueScale


AS_OF = datetime(2024, 5, 1, tzinfo=UTC)
TEST_SCALE = ValueScale(scale_id="test", version="v1", unit_label="test units")


def estimate(asset_id: str) -> PickValueEstimate:
    return PickValueEstimate(
        asset_id=asset_id,
        distribution=ValueDistribution(mean=50.0, stddev=10.0),
        scale=TEST_SCALE,
        as_of=AS_OF,
        draft_season=2025,
        round=1,
        model_version="pick-v1",
        class_strength_model_version="class-v1",
        slot_uncertainty_model_version="slot-v1",
    )


def result(asset_id: str, *, exact: bool, quality: str = "MEDIUM") -> HistoricalPickCoordinateResult:
    return HistoricalPickCoordinateResult(
        estimate=estimate(asset_id),
        status="RECONSTRUCTED",
        evidence_quality=quality,
        exact_slot_used=exact,
        model_version="historical-pick-v1",
    )


def missing() -> HistoricalPickCoordinateResult:
    return HistoricalPickCoordinateResult(
        status="NOT_RECONSTRUCTED_MISSING_SLOT_PROBABILITY_EVIDENCE",
        evidence_quality="INSUFFICIENT",
        model_version="historical-pick-v1",
    )


def test_batch_separates_exact_probabilistic_sensitivity_and_missing() -> None:
    items = (
        HistoricalPickBatchItem(
            transaction_id="t1",
            asset_key="p1",
            result=result("p1", exact=True, quality="HIGH"),
            evidence_mode=HistoricalEvidenceMode.EXACT,
        ),
        HistoricalPickBatchItem(
            transaction_id="t1",
            asset_key="p2",
            result=result("p2", exact=False, quality="MEDIUM"),
            evidence_mode=HistoricalEvidenceMode.PROBABILISTIC,
        ),
        HistoricalPickBatchItem(
            transaction_id="t2",
            asset_key="p3",
            result=result("p3", exact=False, quality="LOW"),
            evidence_mode=HistoricalEvidenceMode.SENSITIVITY_ONLY,
        ),
        HistoricalPickBatchItem(
            transaction_id="t3",
            asset_key="p4",
            result=missing(),
        ),
    )

    summary = summarize_historical_pick_batch(items)

    assert summary.pick_asset_count == 4
    assert summary.transaction_count == 3
    assert summary.reconstructed_pick_count == 3
    assert summary.unreconstructed_pick_count == 1
    assert summary.exact_pick_count == 1
    assert summary.probabilistic_pick_count == 1
    assert summary.sensitivity_only_pick_count == 1
    assert summary.transactions_with_probabilistic_picks == 1
    assert summary.transactions_with_sensitivity_only_picks == 1
    assert summary.transactions_with_unreconstructed_picks == 1
    assert summary.evidence_quality_counts == (("HIGH", 1), ("INSUFFICIENT", 1), ("LOW", 1), ("MEDIUM", 1))


def test_low_quality_probabilistic_pick_is_not_reclassified_as_sensitivity_only() -> None:
    item = HistoricalPickBatchItem(
        transaction_id="t1",
        asset_key="p1",
        result=result("p1", exact=False, quality="LOW"),
        evidence_mode=HistoricalEvidenceMode.PROBABILISTIC,
    )
    summary = summarize_historical_pick_batch((item,))
    assert summary.probabilistic_pick_count == 1
    assert summary.sensitivity_only_pick_count == 0


def test_exact_slot_requires_exact_mode() -> None:
    with pytest.raises(ValueError, match="EXACT"):
        HistoricalPickBatchItem(
            transaction_id="t1",
            asset_key="p1",
            result=result("p1", exact=True),
            evidence_mode=HistoricalEvidenceMode.PROBABILISTIC,
        )


def test_unreconstructed_pick_cannot_claim_usable_mode() -> None:
    with pytest.raises(ValueError, match="cannot declare"):
        HistoricalPickBatchItem(
            transaction_id="t1",
            asset_key="p1",
            result=missing(),
            evidence_mode=HistoricalEvidenceMode.SENSITIVITY_ONLY,
        )
