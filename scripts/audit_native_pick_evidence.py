"""Read-only evidence audit; never fit on complete cases or fill missing seasons.

Consumes explicitly supplied local files. Does not download, recompute Shapley,
connect to persistence, infer retirement, or publish a model. Draft ledger/player
identities are private inputs and must stay outside the public repository.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from math import isfinite
from pathlib import Path
import re


def _year(value):
    if value is None or str(value).strip() in ('','NA','nan','None'):
        return None
    x=float(value)
    return int(x) if x.is_integer() else None


def _fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(panel_path, identity_path, draft_path, replay_path, *, complete_through, excluded_draft_seasons=()):
    """Summarize evidence and missingness without inferring a pick value.

    complete_through is a caller-attested source coverage boundary, not a fact
    derived from a player's last row. Later years are right-censored; an absent
    earlier row is missing, even if the player later disappeared from football.
    """
    with panel_path.open(newline='') as f:panel=list(csv.DictReader(f))
    seasons={int(r['season']) for r in panel}
    if not seasons or complete_through>max(seasons):
        raise ValueError('complete-through exceeds supplied season coverage')
    points={};entry={}
    for r in panel:
        key=(r['player_id'],int(r['season']))
        if key in points:raise ValueError('duplicate player-season panel record')
        points[key]=r['fantasy_points']
        # Do not promote first-observed stat year into verified rookie identity.
        y=_year(r.get('entry_season'))
        if y is not None:
            if r['player_id'] in entry and entry[r['player_id']]!=y:
                raise ValueError('conflicting entry-season identity')
            entry[r['player_id']]=y
    by_sleeper=defaultdict(set)
    with identity_path.open(newline='') as f:
        for r in csv.DictReader(f):
            sid=r['sleeper_id'].strip();gsis=r['gsis_id'].strip()
            if sid not in ('','NA','nan','None') and re.fullmatch(r'00-[0-9]{7}',gsis):
                by_sleeper[sid].add(gsis)
    drafts=json.loads(draft_path.read_text());seen=set();kept=[];excluded=Counter()
    for row in drafts:
        y=int(row['season']);key=(row['draft_id'],int(row['pick_no']))
        if key in seen:raise ValueError('duplicate fantasy draft selection')
        seen.add(key)
        if y in excluded_draft_seasons:excluded[str(y)]+=1
        else:kept.append(row)
    replay=json.loads(replay_path.read_text())
    if replay.get('panel_sha256')!=_fingerprint(panel_path):
        raise ValueError('replay does not match the supplied panel')
    cases=[]
    for case in replay['cases']:
        annual={(pid,int(year)):value for year,rows in case['annual'].items() for pid,value in rows.items()}
        if any(not isinstance(v,(int,float)) or not isfinite(v) for v in annual.values()):
            raise ValueError('native replay contains missing or nonfinite annual values')
        if any(key not in points for key in annual):
            raise ValueError('native replay contains an annual label outside the source panel')
        grouped={}
        for year in sorted({int(r['season']) for r in kept}):
            rows=[r for r in kept if int(r['season'])==year];counts=Counter();horizons={str(n):Counter() for n in (1,2,3,7)}
            for row in rows:
                matches=by_sleeper[row['player_id']]
                if len(matches)!=1:
                    counts['ambiguous_identity' if matches else 'missing_identity']+=1
                    for c in horizons.values():c['identity_unresolved']+=1
                    continue
                pid=next(iter(matches));counts['unique_identity']+=1
                if pid not in entry:counts['entry_identity_unknown']+=1
                elif entry[pid]<year:counts['veteran_selection']+=1
                elif entry[pid]==year:counts['rookie_selection']+=1
                else:counts['entry_identity_conflict']+=1
                for n,c in horizons.items():
                    years=range(year,year+int(n))
                    if year+int(n)-1>complete_through:
                        c['right_censored']+=1
                    elif all((pid,y) in annual for y in years):
                        c['fully_observed']+=1
                    elif all((pid,y) in points for y in years):
                        c['native_replay_missing']+=1
                    else:
                        c['season_rows_missing_not_zero']+=1
            grouped[str(year)]={'selections':len(rows),'identity':dict(counts),
                'observed_horizon_coverage':{n:dict(c) for n,c in horizons.items()}}
        cases.append({'superflex':case['superflex'],'rules':case['rules'],'drafts':grouped})
    return {'status':'research_evidence_audit_not_calibration','production_eligible':False,
        'complete_through_season':complete_through,'panel_seasons':[min(seasons),max(seasons)],
        'rookie_stat_rows':sum(_year(r.get('entry_season'))==int(r['season']) for r in panel),
        'selection_count':len(kept),'excluded_draft_seasons':dict(excluded),'cases':cases,
        'source_sha256':{p.name:_fingerprint(p) for p in (panel_path,identity_path,draft_path,replay_path)},
        'blockers':['Fantasy-slot training currently has only the supplied recent classes; complete-case filtering changes the selection universe and risks survivorship bias.',
            'Missing season rows are not verified zero production or verified career termination.',
            'Recent classes cannot establish complete Career or Y8+ outcomes.',
            'Fixed historical fantasy-point scoring has not been proved compatible with arbitrary current league scoring.',
            'Historical draft format/rules and selection-universe changes require evidence; veteran selections cannot be dropped.',
            'Chronological holdout and a validated native prospective forecast/terminal authority are required before publication.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('panel','identity','drafts','replay','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--complete-through',type=int,required=True)
    p.add_argument('--exclude-season',type=int,action='append',default=[])
    a=p.parse_args();out=audit(a.panel,a.identity,a.drafts,a.replay,complete_through=a.complete_through,
        excluded_draft_seasons=tuple(a.exclude_season))
    a.output.write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k not in ('cases','source_sha256')}))


if __name__=='__main__':main()
