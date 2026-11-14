"""Coverage audits must preserve the drafted universe and identify censoring."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('pick_audit',Path('scripts/audit_native_pick_evidence.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def files(tmp_path):
    panel=tmp_path/'panel.csv';identity=tmp_path/'identity.csv';draft=tmp_path/'draft.json';replay=tmp_path/'replay.json'
    with panel.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['player_id','season','fantasy_points','entry_season']);w.writeheader()
        for pid,years,entry in [('00-0000001',(2020,2021,2022),2019),('00-0000002',(2020,),2020)]:
            for year in years:w.writerow(dict(player_id=pid,season=year,fantasy_points=0,entry_season=entry))
    with identity.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['sleeper_id','gsis_id']);w.writeheader()
        for a,b in [('one','00-0000001'),('two','00-0000002'),('none','NA'),('NA','00-0000001')]:
            w.writerow(dict(sleeper_id=a,gsis_id=b))
    rows=[dict(draft_id='d',season='2020',pick_no=i+1,round=1,player_id=p) for i,p in enumerate(('one','two','none'))]
    draft.write_text(json.dumps(rows))
    data={'panel_sha256':hashlib.sha256(panel.read_bytes()).hexdigest(),'cases':[{'superflex':True,'rules':{},
        'annual':{'2020':{'00-0000001':0,'00-0000002':0},'2021':{'00-0000001':0},'2022':{'00-0000001':0}}}]}
    replay.write_text(json.dumps(data));return panel,identity,draft,replay


def test_zeros_missing_and_right_censoring_remain_distinct_and_veterans_remain(tmp_path):
    paths=files(tmp_path);out=module.audit(*paths,complete_through=2022)
    rows=out['cases'][0]['drafts']['2020']
    assert rows['selections']==3
    assert rows['identity']=={'unique_identity':2,'veteran_selection':1,'rookie_selection':1,'missing_identity':1}
    assert rows['observed_horizon_coverage']['3']=={'fully_observed':1,'season_rows_missing_not_zero':1,'identity_unresolved':1}
    assert rows['observed_horizon_coverage']['7']=={'right_censored':2,'identity_unresolved':1}
    assert out['production_eligible'] is False


def test_exclusions_are_explicit_configuration_not_hardcoded_league_semantics(tmp_path):
    paths=files(tmp_path)
    out=module.audit(*paths,complete_through=2022,excluded_draft_seasons=(2020,))
    assert out['selection_count']==0 and out['excluded_draft_seasons']=={'2020':3}
    assert module.audit(*paths,complete_through=2022)['selection_count']==3


@pytest.mark.parametrize('mutation',['panel_duplicate','draft_duplicate','wrong_hash','invalid_native','coverage'])
def test_inconsistent_sources_fail_instead_of_silently_forming_training_rows(tmp_path,mutation):
    paths=files(tmp_path);panel,identity,draft,replay=paths
    if mutation=='panel_duplicate':
        with panel.open('a') as f:f.write('00-0000001,2020,0,2019\n')
    elif mutation=='draft_duplicate':
        rows=json.loads(draft.read_text());draft.write_text(json.dumps(rows+[rows[0]]))
    elif mutation=='wrong_hash':
        d=json.loads(replay.read_text());d['panel_sha256']='other';replay.write_text(json.dumps(d))
    elif mutation=='invalid_native':
        d=json.loads(replay.read_text());d['cases'][0]['annual']['2020']['00-0000001']=None;replay.write_text(json.dumps(d))
    with pytest.raises(ValueError):module.audit(*paths,complete_through=2023 if mutation=='coverage' else 2022)
