from __future__ import annotations

from fsffl.state.models import Position
from fsffl.value.intrinsic_economics import structural_position_economics


def _pools():
    return {
        Position.QB: tuple(360.0 - 7.0 * i for i in range(36)),
        Position.RB: tuple(300.0 - 3.0 * i for i in range(72)),
        Position.WR: tuple(290.0 - 2.0 * i for i in range(96)),
        Position.TE: tuple(220.0 - 3.0 * i for i in range(48)),
    }


def _economics(*, superflex: int):
    return structural_position_economics(
        team_count=12,
        direct_slots={
            Position.QB: 1,
            Position.RB: 2,
            Position.WR: 3,
            Position.TE: 1,
        },
        flex_slots=1,
        superflex_slots=superflex,
        forecast_means=_pools(),
    )


def test_superflex_changes_qb_economics_without_arbitrary_qb_bonus():
    one_qb = _economics(superflex=0)
    superflex = _economics(superflex=1)
    assert one_qb[Position.QB].selected_starters == 12
    assert superflex[Position.QB].selected_starters > 12
    assert superflex[Position.QB].relative_pressure > one_qb[Position.QB].relative_pressure


def test_structural_economics_uses_production_concentration_not_raw_player_count():
    pools = _pools()
    base = structural_position_economics(
        team_count=12,
        direct_slots={Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1},
        flex_slots=1,
        superflex_slots=1,
        forecast_means=pools,
    )
    with_negligible_tail = dict(pools)
    with_negligible_tail[Position.WR] = pools[Position.WR] + tuple(1e-9 for _ in range(500))
    tail = structural_position_economics(
        team_count=12,
        direct_slots={Position.QB: 1, Position.RB: 2, Position.WR: 3, Position.TE: 1},
        flex_slots=1,
        superflex_slots=1,
        forecast_means=with_negligible_tail,
    )
    assert abs(base[Position.WR].effective_supply - tail[Position.WR].effective_supply) < 1e-6
    assert abs(base[Position.WR].relative_pressure - tail[Position.WR].relative_pressure) < 1e-6


def test_structural_factors_are_deterministic_positive_and_pooled():
    economics = _economics(superflex=1)
    assert all(item.relative_pressure > 0 for item in economics.values())
    total_selected = sum(item.selected_starters for item in economics.values())
    total_supply = sum(item.effective_supply for item in economics.values())
    pooled = total_selected / total_supply
    for item in economics.values():
        assert abs(item.relative_pressure - (item.starter_pressure / pooled)) < 1e-12
