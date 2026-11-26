import hashlib

import pytest

from scripts.reconcile_native_pick_season_evidence import load_regular_season_source,reconcile


def source(tmp_path,rows='00-0000001,2020,REG\n'):
    p=tmp_path/'source.csv';p.write_text('player_id,season,season_type\n'+rows)
    return p,hashlib.sha256(p.read_bytes()).hexdigest()


def test_absence_presence_and_unavailable_source_never_fill_native_labels(tmp_path):
    p,h=source(tmp_path);s=load_regular_season_source(p,season=2020,expected_sha256=h)
    gaps=[{'player_id':'00-0000001','season':2020},{'player_id':'00-0000002','season':2020},{'player_id':'00-0000002','season':2021}]
    r=reconcile(gaps,[s])
    assert r['counts']=={'stats_row_present_native_label_unresolved':1,'corroborated_source_absence_not_verified_zero':1,'source_snapshot_unavailable':1}
    assert all(x['native_label'] is None and x['label_filled'] is False for x in r['rows'])
    assert r['production_eligible'] is False


@pytest.mark.parametrize('rows',['00-0000001,2020,POST\n','00-0000001,2021,REG\n','00-0000001,2020,REG\n00-0000001,2020,REG\n'])
def test_mixed_scope_and_duplicates_rejected(tmp_path,rows):
    p,h=source(tmp_path,rows)
    with pytest.raises(ValueError):load_regular_season_source(p,season=2020,expected_sha256=h)


def test_changed_source_fingerprint_rejected(tmp_path):
    p,h=source(tmp_path)
    with pytest.raises(ValueError,match='fingerprint'):load_regular_season_source(p,season=2020,expected_sha256='different')


def test_duplicate_evidence_does_not_inflate_counts(tmp_path):
    p,h=source(tmp_path);s=load_regular_season_source(p,season=2020,expected_sha256=h);g={'player_id':'00-0000002','season':2020}
    with pytest.raises(ValueError,match='gap'):reconcile([g,g],[s])
    with pytest.raises(ValueError,match='source'):reconcile([g],[s,s])


def test_unresolved_source_identities_remain_a_visible_qualification(tmp_path):
    p,h=source(tmp_path,'unknown,2020,REG\n')
    s=load_regular_season_source(p,season=2020,expected_sha256=h)
    r=reconcile([{'player_id':'00-0000002','season':2020}],[s])
    assert s['unresolved_identity_rows']==1
    assert r['rows'][0]['source_unresolved_identity_rows']==1
    assert r['rows'][0]['native_label'] is None
