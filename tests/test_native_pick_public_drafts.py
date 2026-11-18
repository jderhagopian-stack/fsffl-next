from copy import deepcopy

import pytest

from scripts.audit_native_pick_public_drafts import audit


def source():
    league=dict(league_id='l',franchise_count=12,player_copies=1,idp=False,best_ball=False,salary_cap=False,
        scoring_flags='1_ppr',qb_type='2QB/SF',qb_count='1-2')
    rows=[dict(league_id='l',overall=i,round=str((i-1)//12+1),pick=str((i-1)%12+1),
        player_id=str(i),player_name=f'Player {i}',pos='WR',timestamp='2019-05-07T00:00:00+00:00') for i in range(1,49)]
    return [league],rows


def run(leagues,rows):return audit(leagues,rows,season=2019,source_fingerprints=['pinned'],not_before='2019-04-28T00:00:00+00:00',cutoff='2019-09-01T00:00:00+00:00')


def test_all_36_slots_retained_and_quarterback_formats_separate_without_mutation():
    leagues,rows=source();before=deepcopy((leagues,rows));r=run(leagues,rows)
    assert r['production_eligible'] is False and [x['rank'] for x in r['accepted'][0]['selections']]==list(range(1,37))
    assert r['accepted'][0]['format']=='superflex' and (leagues,rows)==before
    leagues[0].update(qb_type='1QB',qb_count='1');assert run(leagues,rows)['accepted'][0]['format']=='one_qb'


@pytest.mark.parametrize('change',['missing','duplicate_rank','duplicate_player','startup','date','naive','round','te_premium','unknown_qb','placeholder','missing_name','pre_nfl_draft','malformed_round'])
def test_unsupported_league_is_explicitly_excluded_without_rank_compression(change):
    leagues,rows=source()
    if change=='missing':rows.pop(20)
    if change=='duplicate_rank':rows[-1]['overall']=1
    if change=='duplicate_player':rows[-1]['player_id']='1'
    if change=='startup':rows.extend(deepcopy(rows))
    if change=='pre_nfl_draft':rows[0]['timestamp']='2019-04-01T00:00:00+00:00'
    if change=='date':rows[0]['timestamp']='2020-05-07T00:00:00+00:00'
    if change=='naive':rows[0]['timestamp']='2019-05-07T00:00:00'
    if change=='malformed_round':rows[-1]['round']=None
    if change=='round':rows[-1]['round']='3'
    if change=='te_premium':leagues[0]['scoring_flags']='1_ppr, TEPrem'
    if change=='placeholder':rows[-1]['player_id']='0000'
    if change=='missing_name':rows[-1]['player_name']=None
    if change=='unknown_qb':leagues[0]['qb_count']=None
    r=run(leagues,rows);assert not r['accepted'] and len(r['excluded'])==1


def test_orphan_duplicate_metadata_and_missing_lineage_rejected():
    ls,rows=source()
    with pytest.raises(ValueError):run([],rows)
    with pytest.raises(ValueError):run(ls+ls,rows)
    with pytest.raises(ValueError):audit(ls,rows,season=2019,source_fingerprints=[],not_before='2019-04-28T00:00:00+00:00',cutoff='2019-09-01T00:00:00+00:00')
