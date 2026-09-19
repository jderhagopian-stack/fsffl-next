from datetime import UTC, datetime, timedelta

from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.package_transaction_benchmark import benchmark_one_for_many_package_premium
from fsffl.value.package_transaction_evidence import (
    MultiAssetTradeObservation,
    PackageAssetKind,
    PackageAssetLeg,
    PackageTradeSide,
)


CONTEXT = "dynasty:12t:sf:0.5ppr"
SOURCE = "statsguy_market_values"


def _value(asset_id: str, value: float, observed_at: datetime) -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset_id,
        source_id=SOURCE,
        native_scale_id="statsguy-dynasty-value",
        value=value,
        observed_at=observed_at,
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def _leg(asset_id: str, roster_id: int, *, kind: PackageAssetKind = PackageAssetKind.PLAYER) -> PackageAssetLeg:
    return PackageAssetLeg(
        asset_kind=kind,
        receiving_roster_id=roster_id,
        canonical_asset_id=asset_id,
        source_asset_id=asset_id,
        quantity=1.0,
    )


def test_one_for_many_benchmark_uses_only_prior_fresh_market_values() -> None:
    completed = datetime(2026, 8, 15, 12, tzinfo=UTC)
    trade = MultiAssetTradeObservation(
        transaction_id="t1",
        league_id="l1",
        format_context_id=CONTEXT,
        completed_at=completed,
        side_a=PackageTradeSide(roster_id=1, received=(_leg("elite", 1),)),
        side_b=PackageTradeSide(roster_id=2, received=(_leg("piece1", 2), _leg("piece2", 2))),
    )
    history = (
        _value("elite", 6000, completed - timedelta(days=2)),
        _value("piece1", 4000, completed - timedelta(days=2)),
        _value("piece2", 2600, completed - timedelta(days=2)),
        _value("elite", 9000, completed + timedelta(days=1)),
    )
    result = benchmark_one_for_many_package_premium(
        (trade,),
        history,
        source_id=SOURCE,
        market_context_id=CONTEXT,
    )
    assert result.evaluated_trades == 1
    row = result.observations[0]
    assert row.singleton_market_value == 6000
    assert row.package_market_value == 6600
    assert row.package_player_count == 2
    assert row.package_pick_count == 0
    assert row.package_composition == "2p"
    assert round(row.package_value_premium_ratio, 6) == 0.1
    assert round(row.package_largest_asset_share, 6) == round(4000 / 6600, 6)
    assert result.by_composition[0].package_composition == "2p"


def test_player_plus_pick_package_is_retained_as_one_composition_aware_observation() -> None:
    completed = datetime(2026, 8, 20, 12, tzinfo=UTC)
    trade = MultiAssetTradeObservation(
        transaction_id="t-player-pick",
        league_id="l1",
        format_context_id=CONTEXT,
        completed_at=completed,
        side_a=PackageTradeSide(roster_id=1, received=(_leg("elite", 1),)),
        side_b=PackageTradeSide(
            roster_id=2,
            received=(
                _leg("young-player", 2),
                _leg("pick:2027:R1:mid", 2, kind=PackageAssetKind.PICK),
            ),
        ),
    )
    history = (
        _value("elite", 7000, completed - timedelta(days=1)),
        _value("young-player", 4300, completed - timedelta(days=1)),
        _value("pick:2027:R1:mid", 3400, completed - timedelta(days=1)),
    )
    result = benchmark_one_for_many_package_premium(
        (trade,),
        history,
        source_id=SOURCE,
        market_context_id=CONTEXT,
    )
    assert result.evaluated_trades == 1
    row = result.observations[0]
    assert row.package_player_count == 1
    assert row.package_pick_count == 1
    assert row.package_composition == "1p+1pick"
    assert row.package_market_value == 7700
    assert round(row.package_value_premium_ratio, 6) == 0.1
    assert result.by_composition[0].package_composition == "1p+1pick"


def test_stale_or_unmapped_package_evidence_is_not_forced_into_estimate() -> None:
    completed = datetime(2026, 8, 15, 12, tzinfo=UTC)
    trade = MultiAssetTradeObservation(
        transaction_id="t2",
        league_id="l1",
        format_context_id=CONTEXT,
        completed_at=completed,
        side_a=PackageTradeSide(roster_id=1, received=(_leg("elite", 1),)),
        side_b=PackageTradeSide(roster_id=2, received=(_leg("piece1", 2), _leg("piece2", 2))),
    )
    history = (
        _value("elite", 6000, completed - timedelta(days=30)),
        _value("piece1", 4000, completed - timedelta(days=2)),
    )
    result = benchmark_one_for_many_package_premium(
        (trade,),
        history,
        source_id=SOURCE,
        market_context_id=CONTEXT,
        max_snapshot_age_days=14,
    )
    assert result.evaluated_trades == 0
    assert result.skipped_unmapped_or_stale == 1
    assert result.overall_median_premium_ratio is None
