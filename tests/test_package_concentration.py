from datetime import UTC, datetime

from fsffl.state.models import PickAsset, PlayerAsset
from fsffl.trade_decision import BilateralTradeProposal, TradeLeg, summarize_package_concentration
from fsffl.trade_decision.package_concentration import PackageConcentrationStatus


def test_one_for_many_concentration_is_exposed_without_applying_a_premium() -> None:
    proposal = BilateralTradeProposal(
        proposal_id="p1",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        side_a=TradeLeg(team_id="a", sends=(PlayerAsset(player_id="lamar"),)),
        side_b=TradeLeg(
            team_id="b",
            sends=(
                PlayerAsset(player_id="stroud"),
                PlayerAsset(player_id="hubbard"),
                PickAsset(pick_id="2027-r2"),
            ),
        ),
    )
    result = summarize_package_concentration(
        proposal,
        {"lamar": 6000.0, "stroud": 4200.0, "hubbard": 1100.0, "2027-r2": 900.0},
    )

    assert result.side_a.status == PackageConcentrationStatus.COMPLETE
    assert result.side_a.asset_count == 1
    assert result.side_a.largest_asset_share == 1.0
    assert result.side_a.largest_asset_id == "lamar"
    assert result.side_b.asset_count == 3
    assert result.side_b.total_market_value == 6200.0
    assert result.side_b.largest_asset_id == "stroud"
    assert result.side_b.largest_asset_share == 4200.0 / 6200.0


def test_missing_asset_value_fails_closed_instead_of_treating_asset_as_zero() -> None:
    proposal = BilateralTradeProposal(
        proposal_id="p2",
        as_of=datetime(2026, 9, 7, tzinfo=UTC),
        side_a=TradeLeg(team_id="a", sends=(PlayerAsset(player_id="elite"),)),
        side_b=TradeLeg(
            team_id="b",
            sends=(PlayerAsset(player_id="known"), PickAsset(pick_id="unmapped-pick")),
        ),
    )
    result = summarize_package_concentration(proposal, {"elite": 5000.0, "known": 3500.0})
    assert result.side_a.status == PackageConcentrationStatus.COMPLETE
    assert result.side_b.status == PackageConcentrationStatus.INCOMPLETE
    assert result.side_b.mapped_asset_count == 1
    assert result.side_b.total_market_value is None
