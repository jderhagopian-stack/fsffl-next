from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_trade_readiness import (
    HistoricalAssetEvidence,
    HistoricalAssetEvidenceStatus,
    HistoricalEvidenceMode,
    assess_historical_trade_valuation_readiness,
    historical_trade_asset_key,
    summarize_historical_trade_readiness,
)
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset, Provenance


def provenance() -> Provenance:
    at = datetime(2023, 4, 10, tzinfo=UTC)
    return Provenance(source="historical-ledger", retrieved_at=at, effective_at=at)


def evidence_for(
    key: str,
    *,
    model_version: str = "pit-value-v1",
    mode: HistoricalEvidenceMode = HistoricalEvidenceMode.EXACT,
) -> HistoricalAssetEvidence:
    return HistoricalAssetEvidence(
        asset_key=key,
        status=HistoricalAssetEvidenceStatus.AVAILABLE,
        reason="authoritative PIT value reconstructed",
        model_version=model_version,
        mode=mode,
    )


def josh_allen_record() -> HistoricalTradeRecord:
    return HistoricalTradeRecord(
        transaction_id="950954472107368448",
        league_id="916435661161451520",
        completed_at=datetime(2023, 4, 10, 0, 48, 43, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(
                team_id="roster-1",
                sends=(
                    PickAsset(pick_id="2023-r1-original-roster-1"),
                    PickAsset(pick_id="2025-r1-original-roster-1"),
                    PlayerAsset(player_id="5849"),
                    PlayerAsset(player_id="7670"),
                ),
            ),
            HistoricalTradeLeg(
                team_id="roster-2",
                sends=(
                    PickAsset(pick_id="2025-r2-original-roster-5"),
                    PlayerAsset(player_id="4984"),
                ),
            ),
        ),
        provenance=provenance(),
    )


def test_josh_allen_regression_exposes_missing_2025_pick_coordinates_without_dropping_them() -> None:
    record = josh_allen_record()
    supplied = []
    for leg in record.legs:
        for ordinal, asset in enumerate(leg.sends):
            key = historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset)
            if isinstance(asset, PlayerAsset) or (
                isinstance(asset, PickAsset) and asset.pick_id.startswith("2023-")
            ):
                supplied.append(evidence_for(key))

    readiness = assess_historical_trade_valuation_readiness(record, evidence=tuple(supplied))

    assert readiness.complete is False
    assert readiness.grade_eligible is False
    assert len(readiness.missing_asset_keys) == 2
    assert any("2025-r1-original-roster-1" in key for key in readiness.missing_asset_keys)
    assert any("2025-r2-original-roster-5" in key for key in readiness.missing_asset_keys)


def test_probabilistic_future_pick_coordinates_are_usable_not_blockers() -> None:
    record = josh_allen_record()
    supplied = []
    for leg in record.legs:
        for ordinal, asset in enumerate(leg.sends):
            key = historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset)
            mode = (
                HistoricalEvidenceMode.PROBABILISTIC
                if isinstance(asset, PickAsset) and asset.pick_id.startswith("2025-")
                else HistoricalEvidenceMode.EXACT
            )
            supplied.append(evidence_for(key, mode=mode))

    readiness = assess_historical_trade_valuation_readiness(record, evidence=tuple(supplied))

    assert readiness.complete is True
    assert readiness.grade_eligible is True
    assert readiness.missing_asset_keys == ()
    assert len(readiness.probabilistic_asset_keys) == 2


def test_sensitivity_only_pick_can_advance_to_decision_robustness_analysis() -> None:
    record = HistoricalTradeRecord(
        transaction_id="sensitivity-pick",
        league_id="league",
        completed_at=datetime(2023, 5, 11, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="weak-future-pick"),)),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id="p1"),)),
        ),
        provenance=provenance(),
    )
    pick_key = historical_trade_asset_key(team_id="A", ordinal=0, asset=record.legs[0].sends[0])
    player_key = historical_trade_asset_key(team_id="B", ordinal=0, asset=record.legs[1].sends[0])

    readiness = assess_historical_trade_valuation_readiness(
        record,
        evidence=(
            evidence_for(pick_key, mode=HistoricalEvidenceMode.SENSITIVITY_ONLY, model_version="broad-pick-range-v1"),
            evidence_for(player_key),
        ),
    )

    assert readiness.complete is True
    assert readiness.grade_eligible is True
    assert readiness.sensitivity_only_asset_keys == (pick_key,)


def test_incidental_faab_can_be_bounded_nuisance_without_claiming_exact_exchange_rate() -> None:
    record = HistoricalTradeRecord(
        transaction_id="draft-day-faab-regression",
        league_id="league",
        completed_at=datetime(2023, 5, 11, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="pick-a"),)),
            HistoricalTradeLeg(team_id="B", sends=(FaabAsset(amount=25),)),
        ),
        provenance=provenance(),
    )
    pick_key = historical_trade_asset_key(team_id="A", ordinal=0, asset=record.legs[0].sends[0])
    faab_key = historical_trade_asset_key(team_id="B", ordinal=0, asset=record.legs[1].sends[0])

    readiness = assess_historical_trade_valuation_readiness(
        record,
        evidence=(
            evidence_for(pick_key),
            evidence_for(faab_key, mode=HistoricalEvidenceMode.BOUNDED_NUISANCE, model_version="faab-nuisance-v1"),
        ),
    )

    assert readiness.complete is True
    assert readiness.grade_eligible is True
    assert readiness.bounded_nuisance_asset_keys == (faab_key,)


def test_missing_faab_still_blocks_until_a_governed_nuisance_policy_is_supplied() -> None:
    record = HistoricalTradeRecord(
        transaction_id="missing-faab",
        league_id="league",
        completed_at=datetime(2023, 5, 11, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="pick-a"),)),
            HistoricalTradeLeg(team_id="B", sends=(FaabAsset(amount=25),)),
        ),
        provenance=provenance(),
    )
    pick_key = historical_trade_asset_key(team_id="A", ordinal=0, asset=record.legs[0].sends[0])
    readiness = assess_historical_trade_valuation_readiness(record, evidence=(evidence_for(pick_key),))
    assert readiness.grade_eligible is False
    assert len(readiness.missing_asset_keys) == 1


def test_explicit_exclusion_still_blocks_quantitative_grading() -> None:
    record = HistoricalTradeRecord(
        transaction_id="excluded-asset",
        league_id="league",
        completed_at=datetime(2023, 5, 11, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
            HistoricalTradeLeg(team_id="B", sends=(PickAsset(pick_id="p2"),)),
        ),
        provenance=provenance(),
    )
    player_key = historical_trade_asset_key(team_id="A", ordinal=0, asset=record.legs[0].sends[0])
    pick_key = historical_trade_asset_key(team_id="B", ordinal=0, asset=record.legs[1].sends[0])

    readiness = assess_historical_trade_valuation_readiness(
        record,
        evidence=(
            evidence_for(player_key),
            HistoricalAssetEvidence(
                asset_key=pick_key,
                status=HistoricalAssetEvidenceStatus.EXCLUDED,
                reason="outside governed rookie-draft scope",
            ),
        ),
    )

    assert readiness.grade_eligible is False
    assert readiness.excluded_asset_keys == (pick_key,)


def test_batch_summary_counts_uncertainty_separately_from_blockers() -> None:
    uncertain_record = HistoricalTradeRecord(
        transaction_id="usable-uncertain",
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="future-pick"),)),
            HistoricalTradeLeg(team_id="B", sends=(FaabAsset(amount=10),)),
        ),
        provenance=provenance(),
    )
    pkey = historical_trade_asset_key(team_id="A", ordinal=0, asset=uncertain_record.legs[0].sends[0])
    fkey = historical_trade_asset_key(team_id="B", ordinal=0, asset=uncertain_record.legs[1].sends[0])
    usable = assess_historical_trade_valuation_readiness(
        uncertain_record,
        evidence=(
            evidence_for(pkey, mode=HistoricalEvidenceMode.PROBABILISTIC),
            evidence_for(fkey, mode=HistoricalEvidenceMode.BOUNDED_NUISANCE),
        ),
    )

    sensitivity_record = HistoricalTradeRecord(
        transaction_id="usable-sensitivity",
        league_id="league",
        completed_at=datetime(2024, 1, 2, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="weak-pick"),)),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
        ),
        provenance=provenance(),
    )
    skey = historical_trade_asset_key(team_id="A", ordinal=0, asset=sensitivity_record.legs[0].sends[0])
    spkey = historical_trade_asset_key(team_id="B", ordinal=0, asset=sensitivity_record.legs[1].sends[0])
    sensitivity = assess_historical_trade_valuation_readiness(
        sensitivity_record,
        evidence=(
            evidence_for(skey, mode=HistoricalEvidenceMode.SENSITIVITY_ONLY),
            evidence_for(spkey),
        ),
    )

    blocked_record = HistoricalTradeRecord(
        transaction_id="blocked-trade",
        league_id="league",
        completed_at=datetime(2024, 1, 3, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
            HistoricalTradeLeg(team_id="B", sends=(PickAsset(pick_id="missing"),)),
        ),
        provenance=provenance(),
    )
    bkey = historical_trade_asset_key(team_id="A", ordinal=0, asset=blocked_record.legs[0].sends[0])
    blocked = assess_historical_trade_valuation_readiness(blocked_record, evidence=(evidence_for(bkey),))

    summary = summarize_historical_trade_readiness((usable, sensitivity, blocked))
    assert summary.trade_count == 3
    assert summary.complete_trade_count == 2
    assert summary.blocked_trade_count == 1
    assert summary.probabilistic_trade_count == 1
    assert summary.bounded_nuisance_trade_count == 1
    assert summary.sensitivity_only_trade_count == 1
    assert summary.missing_asset_count_by_kind == (("pick", 1),)


def test_rejects_evidence_for_asset_not_in_trade() -> None:
    record = HistoricalTradeRecord(
        transaction_id="unexpected",
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
        ),
        provenance=provenance(),
    )

    with pytest.raises(ValueError, match="outside the trade"):
        assess_historical_trade_valuation_readiness(
            record,
            evidence=(evidence_for("A:99:player:not-in-trade"),),
        )
