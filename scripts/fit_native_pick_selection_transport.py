"""Research selection-frequency × conditional native-outcome transport.

No 1-QB overall rank becomes a Superflex rank. Within-position transport is an
explicit hypothesis. Missing component mass uses an identified empirical same-slot
forecast backoff, never a fabricated historical label or a chosen blend weight.
"""
from collections import Counter,defaultdict
from math import fsum,isfinite

from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority
from fsffl.value.native_pick_research import NativePickAnnualOutcome,NativePickJointScenario,NativePickSlotForecast

POSITIONS=('QB','RB','WR','TE')


def _indexed(case,max_slots,*,outcomes):
    rows=case['selections'];lookup={};counts=Counter()
    if sorted(r['rank'] for r in rows)!=list(range(1,max_slots+1)):
        raise ValueError('complete source slot coordinates required; never compress gaps')
    for row in sorted(rows,key=lambda r:r['rank']):
        if type(row['rank']) is not int or row['position'] not in POSITIONS:raise ValueError('unsupported selection coordinate')
        counts[row['position']]+=1;key=(row['position'],counts[row['position']]);lookup[key]=row
        if outcomes:
            annual=row['annual']
            if len(annual)!=7 or any(v is not None and (isinstance(v,bool) or not isfinite(v)) for v in annual):
                raise ValueError('seven finite-or-explicitly-missing native outcomes required')
            assumed=row.get('assumed_seasons',[])
            if assumed and (not row.get('assumption_ref') or not row.get('source_fingerprints')):
                raise ValueError('training absence assumptions need explicit provenance')
            authority=row.get('career_authority')
            if authority is not None:
                a=CareerForwardModelAuthority.model_validate(authority)
                if any(not isfinite(v) for v in a.model_dump().values()) or any(v is None for v in annual):
                    raise ValueError('Career reference needs complete finite prefix and authority')
    return lookup


def fit(document, *, release_season, draft_season, max_slots=36):
    if type(release_season) is not int or type(draft_season) is not int or draft_season<release_season:
        raise ValueError('explicit prospective release/draft calendar required')
    coordinate=document['economic_coordinate']
    team_count=coordinate.get('rules',{}).get('team_count')
    if type(max_slots) is not int or max_slots<1 or type(team_count) is not int or team_count<1 or max_slots%team_count:
        raise ValueError('positive team capacity and complete rounds required')
    if not coordinate.get('source_fingerprints') or coordinate.get('scoring_coordinate')!='connected_league_fantasy_points':
        raise ValueError('governed connected native coordinate and source lineage required')
    selections=document['selection_cases'];outcomes=document['outcome_cases'];fallback=document['fallback_cases']
    if not selections or not outcomes:raise ValueError('selection and outcome evidence required')
    by_class=defaultdict(list);seen=set()
    for case in selections:
        identity=(case['draft_class'],case['source_case_id'])
        if identity in seen:raise ValueError('duplicate selection source case')
        if type(case['draft_class']) is not int or case['draft_class']>=release_season:
            raise ValueError('selection class must precede release')
        seen.add(identity);by_class[case['draft_class']].append(_indexed(case,max_slots,outcomes=False))
    outcome_classes=[];indexed=[]
    for case in outcomes:
        year=case['draft_class']
        if type(year) is not int or year+6>=release_season or year in outcome_classes:
            raise ValueError('complete independent mature outcome classes required')
        outcome_classes.append(year);indexed.append(_indexed(case,max_slots,outcomes=True))
    fallback_lookup=[];fallback_seen=set();fallback_years=set()
    for case in fallback:
        identity=(case['draft_class'],case['source_case_id'])
        if identity in fallback_seen or type(case['draft_class']) is not int or case['draft_class']+6>=release_season:
            raise ValueError('unique mature fallback source cases required')
        fallback_seen.add(identity);fallback_years.add(case['draft_class'])
        if len(fallback_years)>1:raise ValueError('fallback must identify one frozen empirical class')
        _indexed(case,max_slots,outcomes=True)
        fallback_lookup.append({r['rank']:r for r in case['selections']})
    slot_results=[]
    for rank in range(1,max_slots+1):
        feature_mass=Counter()
        for year,cases in by_class.items():
            for lookup in cases:
                feature=next(k for k,row in lookup.items() if row['rank']==rank)
                feature_mass[feature]+=1/len(by_class)/len(cases)
        annual_samples=[];career_samples=[];missing_annual=missing_career=0.
        for feature,q in feature_mass.items():
            for year,lookup in zip(outcome_classes,indexed):
                row=lookup.get(feature);p=q/len(indexed)
                if row is None or any(v is None for v in row['annual'][:3]):missing_annual+=p
                else:annual_samples.append((p,row['annual'][:3],f'outcome_class:{year}:{feature}'))
                if row is None or row.get('career_authority') is None:missing_career+=p
                else:career_samples.append((p,row['annual'],row['career_authority'],f'outcome_class:{year}:{feature}'))
        fallback_annual=[lookup[rank] for lookup in fallback_lookup]
        annual_ready=not missing_annual or (bool(fallback_annual) and all(all(v is not None for v in r['annual'][:3]) for r in fallback_annual))
        career_ready=not missing_career or (bool(fallback_annual) and all(r.get('career_authority') is not None for r in fallback_annual))
        if missing_annual and annual_ready:
            annual_samples.extend((missing_annual/len(fallback_annual),r['annual'][:3],'explicit_same_slot_empirical_backoff') for r in fallback_annual)
        if missing_career and career_ready:
            career_samples.extend((missing_career/len(fallback_annual),r['annual'],r['career_authority'],'explicit_same_slot_empirical_backoff') for r in fallback_annual)
        forecast=None;authority=None
        if annual_ready:
            assert abs(fsum(p for p,_,_ in annual_samples)-1)<1e-9
            scenarios=tuple(NativePickJointScenario(probability=p,annual=tuple(NativePickAnnualOutcome(season=draft_season+i,raw_shapley=v) for i,v in enumerate(vs))) for p,vs,_ in annual_samples)
            forecast=NativePickSlotForecast(slot_in_round=(rank-1)%team_count+1,scenarios=scenarios).model_dump(mode='json')
        if career_ready:
            assert abs(fsum(p for p,_,_,_ in career_samples)-1)<1e-9
            means={k:fsum(p*a[k] for p,_,a,_ in career_samples) for k in ('low','reference_center','high')}
            authority=CareerForwardModelAuthority(**means,width=means['high']-means['low']).model_dump(mode='json')
        slot_results.append({'rank':rank,'three_year_forecast':forecast,'career_authority':authority,
            'three_year_backoff_mass':missing_annual,'career_backoff_mass':missing_career,
            'career_prefix_reference':[fsum(p*vs[i] for p,vs,_,_ in career_samples) for i in range(7)] if career_ready else None,
            'selection_feature_mass':[{'position':p,'positional_rank':n,'probability':q} for (p,n),q in sorted(feature_mass.items())]})
    return {'status':'selection_frequency_conditional_outcome_transport_research','production_eligible':False,
        'model_version':'native_pick_selection_transport_research_v1','economic_coordinate':coordinate,
        'release_season':release_season,'draft_season':draft_season,'selection_classes':sorted(by_class),
        'selection_source_count':len(selections),'outcome_classes':sorted(outcome_classes),'fallback_source_count':len(fallback),
        'selection_weighting':'equal_class_then_equal_draft_frequency','outcome_weighting':'equal_declared_class_frequency',
        'uncertainty':'empirical_paths_uncalibrated_Career_model_authority_not_confidence','source_limitations':document.get('source_limitations',[]),'slots':slot_results}


def compose_reference(prefix,long_term):
    """Research composition with one shared first-three-year forecast authority.

    Long-term input carries Y1-Y7+terminal. Remove its prefix reference and append
    the canonical empirical prefix without inventing a cumulative distribution.
    """
    core=lambda c:{k:v for k,v in c.items() if k!='source_fingerprints'}
    if (prefix['prefix_years']!=3 or prefix['release_season']!=long_term['release_season']
        or prefix['draft_season']!=long_term['draft_season']
        or core(prefix['economic_coordinate'])!=core(long_term['economic_coordinate'])):
        raise ValueError('shared native coordinate and first3 calendar required')
    ranks=[s['rank'] for s in prefix['slots']]
    if ranks!=list(range(1,len(ranks)+1)) or ranks!=[s['rank'] for s in long_term['slots']]:
        raise ValueError('complete matching slot coordinates required')
    slots=[]
    for p,c in zip(prefix['slots'],long_term['slots']):
        forecast=p['forecast'];means=None;authority=None;annual=None
        if forecast is not None:
            parsed=NativePickSlotForecast.model_validate(forecast);season=prefix['draft_season']
            if any([a.season for a in s.annual]!=list(range(season,season+3)) for s in parsed.scenarios):
                raise ValueError('canonical prefix must cover the exact first3 seasons')
            means=[fsum(s.probability*s.annual[i].raw_shapley for s in parsed.scenarios) for i in range(3)]
            supplied=p.get('annual_mean')
            if supplied is not None and (len(supplied)!=3 or any(
                isinstance(b,bool) or not isinstance(b,(int,float)) or not isfinite(b) or abs(a-b)>1e-8
                for a,b in zip(means,supplied)
            )):
                raise ValueError('prefix mean differs from its source scenarios')
        if means is not None and c['career_authority'] is not None:
            previous=c['career_prefix_reference']
            if len(previous)!=7 or any(not isfinite(v) for v in previous):raise ValueError('complete native long prefix required')
            prior=CareerForwardModelAuthority.model_validate(c['career_authority']);delta=fsum(means)-fsum(previous[:3])
            authority=CareerForwardModelAuthority(low=prior.low+delta,reference_center=prior.reference_center+delta,
                high=prior.high+delta,width=prior.width).model_dump(mode='json');annual=means+previous[3:]
        slots.append({'rank':p['rank'],'three_year_forecast':forecast,'career_authority':authority,
            'career_prefix_reference':annual,'prefix_backoff_mass':p['backoff_mass'],'long_term_backoff_mass':c['career_backoff_mass']})
    coordinate={**prefix['economic_coordinate'],'source_fingerprints':sorted(set(prefix['economic_coordinate']['source_fingerprints']+long_term['economic_coordinate']['source_fingerprints']))}
    return {'production_eligible':False,'status':'horizon_composed_native_pick_reference_research',
        'model_version':'native_pick_empirical_prefix_conditional_long_reference_research_v1','release_season':prefix['release_season'],
        'draft_season':prefix['draft_season'],'prefix_classes':prefix['source_classes'],'long_outcome_classes':long_term['outcome_classes'],
        'source_drafts':prefix['source_draft_count'],'economic_coordinate':coordinate,'slots':slots,'shared_first3_across_horizons':True,
        'uncertainty':'prefix_empirical_paths_uncalibrated_long_term_model_reference_no_cumulative_distribution',
        'source_limitations':long_term.get('source_limitations',[])}
