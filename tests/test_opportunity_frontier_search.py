from datetime import UTC, datetime

from fsffl.opportunity.frontier import make_frontier_point
from fsffl.opportunity.frontier_search import FrontierSearchPolicy, explore_negotiation_frontier
from fsffl.opportunity.models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)
from fsffl.opportunity.trade_universe import (
    TeamTradeInventory,
    TradePackageSeed,
    TradeSearchBounds,
    canonical_package_id,
    enumerate_trade_packages,
)
from fsffl.state.models import PlayerAsset


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _seed(team_id: str, *assets) -> TradePackageSeed:
    assets = tuple(assets)
    return TradePackageSeed(
        team_id=team_id,
        assets=assets,
        canonical_id=canonical_package_id(team_id, assets),
    )


def _candidate(point_id: str, focal_team_id: str, authority: ActionAuthority) -> OpportunityCandidate:
    reasons = ()
    if authority == ActionAuthority.DIAGNOSTIC_ONLY:
        reasons = (CandidateReason.COUNTERPARTY_DOMINATED,)
    return OpportunityCandidate(
        candidate_id=point_id,
        kind=OpportunityKind.TRADE,
        focal_team_id=focal_team_id,
        league_state_id="state-1",
        as_of=AS_OF,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=authority,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reasons=reasons,
        search_model_version="test",
    )


def test_frontier_search_continues_after_diagnostic_seed() -> None:
    a1 = PlayerAsset(player_id="a1")
    a2 = PlayerAsset(player_id="a2")
    b1 = PlayerAsset(player_id="b1")
    focal_inventory = TeamTradeInventory(team_id="a", assets=(a1, a2))
    counterparty_inventory = TeamTradeInventory(team_id="b", assets=(b1,))
    seed = make_frontier_point(_seed("a", a1), _seed("b", b1))

    visited: list[str] = []

    def evaluator(point):
        visited.append(point.point_id)
        authority = (
            ActionAuthority.DIAGNOSTIC_ONLY
            if point.point_id == seed.point_id
            else ActionAuthority.MARKET_TEST_ONLY
        )
        return _candidate(point.point_id, "a", authority)

    result = explore_negotiation_frontier(
        seed,
        focal_inventory=focal_inventory,
        counterparty_inventory=counterparty_inventory,
        bounds=TradeSearchBounds(max_assets_per_side=2),
        evaluator=evaluator,
        policy=FrontierSearchPolicy(
            max_depth=1,
            max_evaluations=10,
            expand_focal_side=True,
            expand_counterparty_side=False,
        ),
    )

    assert len(result.evaluated) == 2
    assert result.evaluated[0].candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY
    assert result.evaluated[1].candidate.action_authority == ActionAuthority.MARKET_TEST_ONLY
    assert len(visited) == 2
    assert result.exhausted


def test_frontier_search_respects_evaluation_budget() -> None:
    a1 = PlayerAsset(player_id="a1")
    a2 = PlayerAsset(player_id="a2")
    a3 = PlayerAsset(player_id="a3")
    b1 = PlayerAsset(player_id="b1")
    focal_inventory = TeamTradeInventory(team_id="a", assets=(a1, a2, a3))
    counterparty_inventory = TeamTradeInventory(team_id="b", assets=(b1,))
    seed = make_frontier_point(_seed("a", a1), _seed("b", b1))

    result = explore_negotiation_frontier(
        seed,
        focal_inventory=focal_inventory,
        counterparty_inventory=counterparty_inventory,
        bounds=TradeSearchBounds(max_assets_per_side=3),
        evaluator=lambda point: _candidate(
            point.point_id,
            "a",
            ActionAuthority.MARKET_TEST_ONLY,
        ),
        policy=FrontierSearchPolicy(
            max_depth=2,
            max_evaluations=2,
            expand_focal_side=True,
            expand_counterparty_side=False,
        ),
    )

    assert len(result.evaluated) == 2
    assert not result.exhausted


def test_frontier_search_is_reproducible() -> None:
    a1 = PlayerAsset(player_id="a1")
    a2 = PlayerAsset(player_id="a2")
    b1 = PlayerAsset(player_id="b1")
    b2 = PlayerAsset(player_id="b2")
    focal_inventory = TeamTradeInventory(team_id="a", assets=(a1, a2))
    counterparty_inventory = TeamTradeInventory(team_id="b", assets=(b1, b2))
    seed = make_frontier_point(_seed("a", a1), _seed("b", b1))
    policy = FrontierSearchPolicy(max_depth=1, max_evaluations=20)

    def run():
        return explore_negotiation_frontier(
            seed,
            focal_inventory=focal_inventory,
            counterparty_inventory=counterparty_inventory,
            bounds=TradeSearchBounds(max_assets_per_side=2),
            evaluator=lambda point: _candidate(
                point.point_id,
                "a",
                ActionAuthority.MARKET_TEST_ONLY,
            ),
            policy=policy,
        )

    first = run()
    second = run()
    assert [item.point.point_id for item in first.evaluated] == [
        item.point.point_id for item in second.evaluated
    ]


def test_bounded_frontier_can_recover_entire_small_package_cross_product() -> None:
    a1 = PlayerAsset(player_id="a1")
    a2 = PlayerAsset(player_id="a2")
    b1 = PlayerAsset(player_id="b1")
    b2 = PlayerAsset(player_id="b2")
    focal_inventory = TeamTradeInventory(team_id="a", assets=(a1, a2))
    counterparty_inventory = TeamTradeInventory(team_id="b", assets=(b1, b2))
    bounds = TradeSearchBounds(max_assets_per_side=2)

    focal_packages = enumerate_trade_packages(focal_inventory, bounds=bounds)
    counterparty_packages = enumerate_trade_packages(counterparty_inventory, bounds=bounds)
    expected_ids = {
        f"{focal.canonical_id}=>{counterparty.canonical_id}"
        for focal in focal_packages
        for counterparty in counterparty_packages
    }
    assert len(expected_ids) == 9

    seed = make_frontier_point(_seed("a", a1), _seed("b", b1))
    result = explore_negotiation_frontier(
        seed,
        focal_inventory=focal_inventory,
        counterparty_inventory=counterparty_inventory,
        bounds=bounds,
        evaluator=lambda point: _candidate(
            point.point_id,
            "a",
            ActionAuthority.MARKET_TEST_ONLY,
        ),
        policy=FrontierSearchPolicy(max_depth=4, max_evaluations=100),
    )

    observed_ids = {item.point.point_id for item in result.evaluated}
    assert observed_ids == expected_ids
    assert result.exhausted
