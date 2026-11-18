"""Research Career reference: mature empirical Y1–Y7 plus accepted Y8+ model.

No current-survivor filtering, new terminal coefficients, fake past forecasts,
Market conversion or cumulative probability interval. Cohort draws remain
research-only until source/profile and forecast transport validation is reviewed.
"""
from math import fsum,isfinite

from fsffl.state.models import LeagueRules
from fsffl.value.career_forward_intrinsic import CareerForwardModelAuthority
from fsffl.value.career_tail import CareerTailFeatures,build_career_tail_authority


def fit(document, *, release_season, max_slots, assumption_ref=None, corroborated_absences=()):
    if type(max_slots) is not int or max_slots<1:raise ValueError('positive integer slot count required')
    if type(release_season) is not int or release_season<1:raise ValueError('positive integer release season required')
    allowed=set()
    for g in corroborated_absences:
        if not assumption_ref or not g.get('source_sha256') or g.get('status')!='corroborated_source_absence_not_verified_zero':
            raise ValueError('missing-season sensitivity requires fingerprinted explicit assumptions')
        key=g['player_id'],g['season']
        if key in allowed:raise ValueError('duplicate absence evidence')
        allowed.add(key)
    outputs=[]
    for case in document['cases']:
        coordinate=case['economic_coordinate'];rules=LeagueRules.model_validate(coordinate['rules'])
        if coordinate.get('scoring_coordinate')!='connected_league_fantasy_points' or not coordinate.get('source_fingerprints'):
            raise ValueError('Career cohort needs the governed scoring coordinate and source lineage')
        rows={};classes=set()
        for row in case['selections']:
            if (type(row.get('draft_season')) is not int or row['draft_season']<1
                or type(row.get('rank')) is not int or row['rank']<1):
                raise ValueError('positive integer class and slot required')
            key=row['draft_season'],row['rank']
            if key in rows:raise ValueError('duplicate class/slot')
            rows[key]=row
            if row['draft_season']+6<release_season:classes.add(row['draft_season'])
        classes=sorted(classes);slots=[]
        for slot in range(1,max_slots+1):
            samples=[];gaps=[]
            for year in classes:
                row=rows.get((year,slot))
                if not row or not row.get('player_id'):
                    gaps.append({'draft_season':year,'reason':'selection_or_identity_missing'});continue
                annual=row.get('native_y1_y7')
                if annual is None or len(annual)!=7:
                    gaps.append({'draft_season':year,'reason':'complete_seven_year_window_required'});continue
                values=[];assumed=[]
                for i,value in enumerate(annual):
                    if value is None and (row['player_id'],year+i) in allowed:
                        value=0.;assumed.append(year+i)
                    if value is not None and (isinstance(value,bool) or not isfinite(value)):
                        raise ValueError('native annual labels must be finite')
                    values.append(value)
                if any(v is None for v in values):
                    gaps.append({'draft_season':year,'reason':'native_season_missing'});continue
                try:
                    features=CareerTailFeatures(player_id=row['player_id'],position=row['position'],
                        age_years=row['origin_age_years'],experience_years=row['origin_experience_years'],
                        current_points=row['origin_connected_points'],prior_points=row.get('prior_connected_points'),
                        current_points_coordinate=coordinate['scoring_coordinate'],prior_points_coordinate=coordinate['scoring_coordinate'])
                except (KeyError,ValueError,TypeError):
                    gaps.append({'draft_season':year,'reason':'terminal_origin_features_missing_or_invalid'});continue
                if any(not isfinite(v) for v in features.feature_vector):raise ValueError('terminal features must be finite')
                terminal=build_career_tail_authority(features,rules=rules)
                prefix=fsum(values)
                authority=CareerForwardModelAuthority(low=prefix+terminal.model_authority_low,
                    reference_center=prefix+terminal.reference_center,high=prefix+terminal.model_authority_high,
                    width=terminal.model_authority_high-terminal.model_authority_low)
                samples.append({'draft_season':year,'player_id':row['player_id'],
                    'prefix_end_season':year+6,'terminal_start_season':year+7,
                    'native_y1_y7':prefix,'authority':authority.model_dump(mode='json'),
                    'assumed_seasons':assumed,'terminal_model_version':terminal.model_version})
            complete=bool(classes) and not gaps
            authority=None
            if complete:
                n=len(samples);means={k:fsum(s['authority'][k]/n for s in samples) for k in ('low','reference_center','high')}
                authority=CareerForwardModelAuthority(**means,width=means['high']-means['low']).model_dump(mode='json')
            slots.append({'rank':slot,'authority':authority,'sample_count':len(samples),'requested_classes':len(classes),
                          'missing':gaps,'samples':samples})
        outputs.append({'economic_coordinate':coordinate,'training_classes':classes,'slots':slots,
                        'source_limitations':case.get('source_limitations',[])})
    return {'status':'mature_first7_plus_accepted_terminal_research_prior','production_eligible':False,
            'model_version':'native_pick_mature_career_reference_research_v1',
            'point_basis':'model_reference','uncertainty':'tail_model_authority_only_not_class_dispersion_or_confidence',
            'assumption_ref':assumption_ref,'cases':outputs}
