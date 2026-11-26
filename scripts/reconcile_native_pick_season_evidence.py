"""Reconcile missing native training labels against supplied regular-season rows.

A second source's missing row is corroborated absence, never an observed zero.
This diagnostic does not score stats, fill native labels or infer retirement.
"""
from collections import Counter
import csv
import hashlib
import re


def load_regular_season_source(path, *, season, expected_sha256):
    payload=path.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=expected_sha256:
        raise ValueError('season source fingerprint mismatch')
    with path.open(newline='') as handle:
        reader=csv.DictReader(handle)
        if not {'player_id','season','season_type'}.issubset(reader.fieldnames or []):
            raise ValueError('regular-season source schema missing')
        identities=set();unresolved=0
        for row in reader:
            if int(row['season'])!=season or row['season_type']!='REG':
                raise ValueError('season source mixes calendar or season types')
            pid=row['player_id']
            if not re.fullmatch(r'00-\d{7}',pid):
                unresolved+=1
                continue
            if pid in identities:raise ValueError('duplicate player-season source row')
            identities.add(pid)
    return dict(season=season,sha256=expected_sha256,player_ids=frozenset(identities),
                unresolved_identity_rows=unresolved)


def reconcile(gaps, sources):
    """Accept explicit native-label gaps, preserving every distinct player-season."""
    by_year={s['season']:s for s in sources}
    if len(by_year)!=len(sources):raise ValueError('duplicate season source')
    seen=set();rows=[]
    for gap in gaps:
        key=gap['player_id'],gap['season']
        if key in seen:raise ValueError('duplicate native-label gap')
        seen.add(key)
        if not key[0] or not re.fullmatch(r'00-\d{7}',key[0]):
            raise ValueError('gap needs canonical player identity')
        source=by_year.get(key[1])
        status=('source_snapshot_unavailable' if source is None else
                'stats_row_present_native_label_unresolved' if key[0] in source['player_ids'] else
                'corroborated_source_absence_not_verified_zero')
        rows.append(dict(player_id=key[0],season=key[1],status=status,
                         source_sha256=source['sha256'] if source else None,
                         source_unresolved_identity_rows=source.get('unresolved_identity_rows',0) if source else None,
                         native_label=None,label_filled=False))
    return dict(status='research_source_reconciliation_not_zero_certification',production_eligible=False,
                counts=dict(Counter(x['status'] for x in rows)),rows=rows)
