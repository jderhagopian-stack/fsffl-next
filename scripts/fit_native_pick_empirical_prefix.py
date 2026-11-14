"""Research class-balanced actual-draft native prefix, with explicit backoff.

Fits only already observed source windows. Calendar filtering is by the required
prefix length; missing outcomes remain distinct from identified forecast backoff.
"""
from collections import defaultdict
from math import fsum,isfinite

from fsffl.value.native_pick_research import NativePickAnnualOutcome,NativePickJointScenario,NativePickSlotForecast


def _validated_rows(case, prefix_years, max_slots):
    if (type(case['draft_class']) is not int or not 1900 <= case['draft_class'] <= 2300
        or not isinstance(case['source_case_id'], str) or not case['source_case_id'].strip()):
        raise ValueError('explicit draft class and source case identity required')
    rows = case['selections']
    if any(type(row['rank']) is not int for row in rows) or sorted(row['rank'] for row in rows) != list(range(1,max_slots+1)):
        raise ValueError('complete original selection coordinates required')
    for row in rows:
        if len(row['annual']) < prefix_years or any(
            v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v))
            for v in row['annual']
        ):
            raise ValueError('finite or explicitly missing source outcomes required')
        if row.get('assumed_seasons') and (not row.get('assumption_ref') or not row.get('source_fingerprints')):
            raise ValueError('absence assumptions require provenance')
    return {row['rank']:row for row in rows}


def fit(document,*,release_season,draft_season,prefix_years=3,max_slots=36,excluded_classes=()):
    coord=document['economic_coordinate'];teams=coord['rules']['team_count']
    if (any(type(v) is not int for v in (release_season,draft_season,prefix_years,max_slots,teams))
        or not 1900 <= release_season <= draft_season <= 2298
        or prefix_years not in (1,2,3) or max_slots<1 or teams<1):
        raise ValueError('supported prefix/calendar/capacity required')
    if coord.get('scoring_coordinate')!='connected_league_fantasy_points' or not coord.get('source_fingerprints'):
        raise ValueError('connected native scoring and source lineage required')
    classes=defaultdict(list);seen=set()
    for c in document['source_cases']:
        rows=_validated_rows(c,prefix_years,max_slots)
        key=c['draft_class'],c['source_case_id']
        if key in seen:raise ValueError('duplicate draft evidence')
        seen.add(key)
        year=c['draft_class']
        if year not in excluded_classes and year+prefix_years-1<release_season:classes[year].append(rows)
    fallback=[];fallback_seen=set();fallback_classes=set()
    for c in document['fallback_cases']:
        rows=_validated_rows(c,prefix_years,max_slots)
        key=c['draft_class'],c['source_case_id']
        if key in fallback_seen:raise ValueError('duplicate fallback source case')
        fallback_seen.add(key)
        if c['draft_class'] in excluded_classes or c['draft_class']+prefix_years-1>=release_season:continue
        fallback_classes.add(c['draft_class'])
        if len(fallback_classes)>1:raise ValueError('one explicit frozen fallback class required')
        fallback.append(rows)
    if not classes:raise ValueError('no mature source prefix classes')
    results=[]
    for rank in range(1,max_slots+1):
        samples=[];missing=0.
        for year,cases in classes.items():
            for case in cases:
                p=1/len(classes)/len(cases);vs=case[rank]['annual'][:prefix_years]
                if any(v is None for v in vs):missing+=p
                else:samples.append((p,vs))
        ready=not missing or (bool(fallback) and all(all(v is not None for v in c[rank]['annual'][:prefix_years]) for c in fallback))
        if missing and ready:samples.extend((missing/len(fallback),c[rank]['annual'][:prefix_years]) for c in fallback)
        forecast=mean=None
        if ready:
            assert abs(fsum(p for p,_ in samples)-1)<1e-9
            forecast=NativePickSlotForecast(slot_in_round=(rank-1)%teams+1,scenarios=tuple(NativePickJointScenario(probability=p,
                annual=tuple(NativePickAnnualOutcome(season=draft_season+i,raw_shapley=v) for i,v in enumerate(vs))) for p,vs in samples)).model_dump(mode='json')
            mean=[fsum(p*vs[i] for p,vs in samples) for i in range(prefix_years)]
        results.append({'rank':rank,'forecast':forecast,'annual_mean':mean,'backoff_mass':missing})
    return {'production_eligible':False,'status':'actual_draft_empirical_prefix_research','model_version':'native_pick_actual_draft_prefix_research_v1',
        'release_season':release_season,'draft_season':draft_season,'source_classes':sorted(classes),'source_draft_count':sum(len(c) for c in classes.values()),'prefix_years':prefix_years,
        'class_weighting':'equal_class_then_equal_draft_frequency','slots':results,'economic_coordinate':coord}
