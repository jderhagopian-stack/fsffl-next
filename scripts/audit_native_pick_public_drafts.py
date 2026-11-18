"""Research-only, read-only normalization of public supplemental draft candidates.

Consumes normalized source records, not a provider API. League metadata filters
are declared; no missing selection is rank-compressed or valued. Four-round
structure is evidence of a supplemental candidate, not proof of rookie eligibility.
"""
from collections import defaultdict
from datetime import datetime


def audit(leagues, selections, *, season, source_fingerprints, not_before, cutoff):
    if type(season) is not int or not source_fingerprints or any(not x.strip() for x in source_fingerprints):
        raise ValueError('exact season and source lineage required')
    limit=datetime.fromisoformat(cutoff);start=datetime.fromisoformat(not_before)
    if limit.tzinfo is None or start.tzinfo is None or start>limit:
        raise ValueError('ordered aware source window required')
    by_league={};groups=defaultdict(list)
    for league in leagues:
        key=str(league['league_id'])
        if key in by_league:raise ValueError('duplicate league identity')
        by_league[key]=league
    for row in selections:
        key=str(row['league_id'])
        if key not in by_league:raise ValueError('selection has no league metadata')
        groups[key].append(row)
    accepted=[];excluded=[]
    for key,league in sorted(by_league.items()):
        rows=groups[key];reasons=[]
        expected={'franchise_count':12,'player_copies':1,'idp':False,'best_ball':False,'salary_cap':False,'scoring_flags':'1_ppr'}
        if any(league.get(k)!=v for k,v in expected.items()):reasons.append('outside_declared_basic_12_team_single_copy_ppr_sample')
        mode={('2QB/SF','1-2'):'superflex',('1QB','1'):'one_qb'}.get((league.get('qb_type'),league.get('qb_count')))
        if mode is None:reasons.append('quarterback_capacity_not_explicitly_supported')
        ranks=[r.get('overall') for r in rows]
        if any(type(x) is not int for x in ranks) or sorted(ranks)!=list(range(1,49)):
            reasons.append('complete_four_round_supplemental_candidate_required')
        dates=[]
        for row in rows:
            try:
                stamp=datetime.fromisoformat(row['timestamp'])
                if stamp.tzinfo is None or stamp.year!=season or not start<=stamp<=limit:raise ValueError()
                dates.append(stamp)
            except (KeyError,TypeError,ValueError):reasons.append('selection_timestamp_outside_declared_window');break
        if not reasons:
            for row in rows:
                rank=row['overall']
                try:position=(int(row['round']),int(row['pick']))
                except (KeyError,TypeError,ValueError):position=None
                if position!=((rank-1)//12+1,(rank-1)%12+1):
                    reasons.append('selection_round_or_slot_mismatch');break
                if (not str(row.get('player_id') or '').strip() or row.get('player_id')=='0000'
                    or not str(row.get('player_name') or '').strip()):
                    reasons.append('selection_identity_missing');break
            if len({r['player_id'] for r in rows})!=len(rows):reasons.append('duplicate_selected_player')
        if reasons:
            excluded.append({'league_id':key,'reasons':sorted(set(reasons))});continue
        accepted.append({'league_id':key,'season':season,'format':mode,'selection_count':len(rows),
            'first_selection_at':min(dates).isoformat(),'last_selection_at':max(dates).isoformat(),
            'selections':[{'rank':r['overall'],'source_player_id':r['player_id'],'source_name':r.get('player_name'),
                'position':r.get('pos')} for r in sorted(rows,key=lambda r:r['overall']) if r['overall']<=36]})
    return {'production_eligible':False,'status':'public_draft_selection_evidence_not_model_admission',
        'source_fingerprints':list(source_fingerprints),'not_before':not_before,'cutoff':cutoff,'accepted':accepted,'excluded':excluded,
        'limitations':['one_draft_class_not_independent_classes','full_ppr_choice_distribution_not_exact_half_ppr',
            'lineup_beyond_qb_not_available_in_summary','four_round_candidate_not_certified_rookie_only',
            'retrospective_public_export_not_immutable_point_in_time_snapshot']}
