from datetime import datetime, timezone

import pytest

from fsffl.state.models import PlayerAsset, PickAsset
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.opportunity.strategic_packages import StrategicPackageLane, StrategicSearchBounds, generate_strategic_packages

NOW=datetime(2026,11,11,tzinfo=timezone.utc)

def inventory(team,n=30):
    return TeamTradeInventory(team_id=team,assets=tuple(PlayerAsset(player_id=f'{team}-{i}') for i in range(n)))


def test_bounded_before_combinations_and_all_shapes(monkeypatch):
    import fsffl.opportunity.strategic_packages as module
    original=module.enumerate_trade_packages; counts=[]
    def bounded(inventory,**kwargs):
        counts.append(len(inventory.assets));assert len(inventory.assets)<=6
        return original(inventory,**kwargs)
    monkeypatch.setattr(module,'enumerate_trade_packages',bounded)
    lanes=tuple(StrategicPackageLane(name,inventory('a'),inventory(f'b{i}'))
        for name in ('roster','horizon','ranks') for i in range(11))
    first,diag=generate_strategic_packages(lanes,as_of=NOW)
    second,again=generate_strategic_packages(lanes,as_of=NOW)
    assert first==second and diag==again
    assert len(first)==80
    assert len({s.seed.point_id for s in first})==80
    assert diag['pair_visits']<=640
    assert diag['counterparties_visited']==11
    assert set(diag['shapes'])=={'1_for_1','2_for_1','1_for_2','2_for_2'}
    assert diag['stopped_at_budget'] and not diag['exhaustive_league_search']
    assert counts and max(counts)==6


def test_target_received_pick_is_pinned_before_seed_cap():
    pick=PickAsset(pick_id='future')
    other=inventory('b').model_copy(update={'assets':(*inventory('b').assets,pick)})
    seeds,diag=generate_strategic_packages((StrategicPackageLane('target',inventory('a'),other,pick),),as_of=NOW)
    assert seeds
    assert all(pick in s.seed.proposal.side_b.sends for s in seeds)
    assert all(all(a.player_id.startswith('a-') for a in s.seed.proposal.side_a.sends) for s in seeds)


def test_empty_inventory_and_duplicate_visits_stay_bounded():
    lanes=tuple(StrategicPackageLane(str(i),inventory('a',2),inventory('b',2)) for i in range(10))
    seeds,diag=generate_strategic_packages(lanes,as_of=NOW,bounds=StrategicSearchBounds(max_pair_visits=5))
    assert len(seeds)<=5 and diag['pair_visits']==5
    assert diag['duplicate_pair_visits']>0
    assert not generate_strategic_packages((StrategicPackageLane('empty',inventory('a',0),inventory('b')),),as_of=NOW)[0]
    with pytest.raises(ValueError): generate_strategic_packages((lanes[0],lanes[0]),as_of=NOW)
    with pytest.raises(ValueError): generate_strategic_packages(lanes,as_of=NOW.replace(tzinfo=None))
