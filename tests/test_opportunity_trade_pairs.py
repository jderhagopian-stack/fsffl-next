from datetime import UTC, datetime

from fsffl.opportunity.trade_pairs import (
    TradePairSearchPolicy,
    generate_bilateral_trade_proposals,
)
from fsffl.opportunity.trade_universe import TradePackageSeed, canonical_package_id
from fsffl.state.models import PlayerAsset


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _seed(team_id: str, player_id: str) -> TradePackageSeed:
    asset = PlayerAsset(player_id=player_id)
    assets = (asset,)
    return TradePackageSeed(
        team_id=team_id,
        assets=assets,
        canonical_id=canonical_package_id(team_id, assets),
    )


def test_trade_pair_generation_is_deterministic_and_identity_aligned() -> None:
    focal = (_seed("a", "a2"), _seed("a", "a1"))
    counterparty = (_seed("b", "b2"), _seed("b", "b1"))

    result = generate_bilateral_trade_proposals(
        focal,
        counterparty,
        as_of=AS_OF,
        policy=TradePairSearchPolicy(max_candidate_pairs=10),
    )

    assert result.total_possible_pairs == 4
    assert not result.truncated
    assert [seed.point_id for seed in result.proposals] == sorted(
        seed.point_id for seed in result.proposals
    )
    assert all(seed.proposal.proposal_id == seed.point_id for seed in result.proposals)


def test_trade_pair_generation_surfaces_truncation() -> None:
    focal = (_seed("a", "a1"), _seed("a", "a2"), _seed("a", "a3"))
    counterparty = (_seed("b", "b1"), _seed("b", "b2"))

    result = generate_bilateral_trade_proposals(
        focal,
        counterparty,
        as_of=AS_OF,
        policy=TradePairSearchPolicy(max_candidate_pairs=2),
    )

    assert result.total_possible_pairs == 6
    assert len(result.proposals) == 2
    assert result.truncated


def test_trade_pair_generation_rejects_same_team_on_both_sides() -> None:
    try:
        generate_bilateral_trade_proposals(
            (_seed("a", "a1"),),
            (_seed("a", "a2"),),
            as_of=AS_OF,
        )
    except ValueError as exc:
        assert "distinct teams" in str(exc)
    else:
        raise AssertionError("expected same-team rejection")


def test_trade_pair_generation_rejects_naive_time() -> None:
    try:
        generate_bilateral_trade_proposals(
            (_seed("a", "a1"),),
            (_seed("b", "b1"),),
            as_of=datetime(2026, 9, 5),
        )
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected timezone validation failure")
