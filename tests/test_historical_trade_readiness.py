from datetime import UTC, datetime

import pytest

from fsffl.runtime.historical_trade_readiness import (
    HistoricalAssetEvidence,
    HistoricalAssetEvidenceStatus,
    assess_historical_trade_valuation_readiness,
    historical_trade_asset_key,
    summarize_historical_trade_readiness,
)
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset, Provenance


def provenance() -> Provenance:
    at = datetime(2023, 4, 10, tzinfo=UTC)
    return Provenance(source="historical-ledger", retrieved_at=at, effective_at=at)


def evidence_for(key: str, *, model_version: str = "pit-value-v1") -> HistoricalAssetEvidence:
    return HistoricalAssetEvidence(
        asset_key=key,
        status=HistoricalAssetEvidenceStatus.AVAILABLE,
        reason="authoritative PIT value reconstructed",
        model_version=model_version,
    )


def test_josh_allen_regression_fails_closed_when_2025_pick_coordinates_are_missing() -> None:
    """April 10, 2023 transaction 950954472107368448 cannot drop unresolved picks.

    The real trade was Josh Allen + a 2025 second for Kyler Murray, Joshua Palmer,
    a 2023 first, and a 2025 first. This test is about evidence completeness only;
    it deliberately does not encode eventual pick slots or hindsight values.
    """

    record = HistoricalTradeRecord(
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
    assert len(readiness.missing_asset_keys) == 2
    assert any("2025-r1-original-roster-1" in key for key in readiness.missing_asset_keys)
    assert any("2025-r2-original-roster-5" in key for key in readiness.missing_asset_keys)
    assert all("2023-r1-original-roster-1" not in key for key in readiness.missing_asset_keys)


def test_faab_is_material_until_governed_value_evidence_says_otherwise() -> None:
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

    readiness = assess_historical_trade_valuation_readiness(
        record,
        evidence=(evidence_for(pick_key),),
    )

    assert readiness.complete is False
    assert len(readiness.missing_asset_keys) == 1
    assert ":faab:25" in readiness.missing_asset_keys[0]


def test_explicit_exclusion_still_blocks_full_quantitative_grading() -> None:
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

    assert readiness.complete is False
    assert readiness.missing_asset_keys == ()
    assert readiness.excluded_asset_keys == (pick_key,)


def test_complete_only_when_every_material_asset_has_authoritative_pit_evidence() -> None:
    record = HistoricalTradeRecord(
        transaction_id="complete",
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"), PickAsset(pick_id="pick-a"))),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
        ),
        provenance=provenance(),
    )
    supplied = []
    for leg in record.legs:
        for ordinal, asset in enumerate(leg.sends):
            supplied.append(
                evidence_for(historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset))
            )

    readiness = assess_historical_trade_valuation_readiness(record, evidence=tuple(supplied))

    assert readiness.complete is True
    assert readiness.missing_asset_keys == ()
    assert readiness.excluded_asset_keys == ()


def test_batch_summary_exposes_blocker_asset_families() -> None:
    complete_record = HistoricalTradeRecord(
        transaction_id="complete-trade",
        league_id="league",
        completed_at=datetime(2024, 1, 1, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
            HistoricalTradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
        ),
        provenance=provenance(),
    )
    complete_evidence = []
    for leg in complete_record.legs:
        for ordinal, asset in enumerate(leg.sends):
            complete_evidence.append(
                evidence_for(historical_trade_asset_key(team_id=leg.team_id, ordinal=ordinal, asset=asset))
            )
    complete = assess_historical_trade_valuation_readiness(complete_record, evidence=tuple(complete_evidence))

    blocked_record = HistoricalTradeRecord(
        transaction_id="blocked-trade",
        league_id="league",
        completed_at=datetime(2024, 1, 2, tzinfo=UTC),
        legs=(
            HistoricalTradeLeg(team_id="A", sends=(PickAsset(pick_id="future-pick"),)),
            HistoricalTradeLeg(team_id="B", sends=(FaabAsset(amount=10),)),
        ),
        provenance=provenance(),
    )
    blocked = assess_historical_trade_valuation_readiness(blocked_record, evidence=())

    summary = summarize_historical_trade_readiness((complete, blocked))

    assert summary.trade_count == 2
    assert summary.complete_trade_count == 1
    assert summary.blocked_trade_count == 1
    assert summary.blocked_transaction_ids == ("blocked-trade",)
    assert summary.missing_asset_count_by_kind == (("faab", 1), ("pick", 1))


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
