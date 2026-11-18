"""Research conditional drafted-rookie mean, not a preselection pick forecast.

Uses only original NFL draft position/capital. Poisson regression is a positive
mean link for continuous native contributions, NOT a Poisson outcome distribution.
No Career prediction, outcome variance, joint path or production promotion.
"""
from __future__ import annotations

from math import exp, fsum, isfinite, log1p

import numpy as np
from sklearn.linear_model import PoissonRegressor

POSITIONS = ('QB', 'RB', 'WR', 'TE')
ALPHAS = (.01, .1, 1., 10.)


def features(rows):
    result=[]
    for row in rows:
        if row['position'] not in POSITIONS or isinstance(row['nfl_pick'],bool) or not isinstance(row['nfl_pick'],int) or row['nfl_pick']<1:
            raise ValueError('original NFL draft position and positive overall pick required')
        one=[float(row['position']==p) for p in POSITIONS]
        result.append(one+[x*log1p(row['nfl_pick']) for x in one])
    return np.asarray(result,dtype=float)


def _fit(rows, alpha):
    x=features(rows);y=np.asarray([r['raw_three_year'] for r in rows],dtype=float)
    center=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1
    if not any(y):
        return dict(constant=0.,n=len(rows))
    model=PoissonRegressor(alpha=alpha,max_iter=500,tol=1e-7).fit((x-center)/scale,y)
    return dict(coefficients=model.coef_.tolist(),intercept=float(model.intercept_),
        center=center.tolist(),scale=scale.tolist(),n=len(rows),alpha=alpha)


def predict(model, rows):
    if 'constant' in model:return [model['constant'] for _ in rows]
    x=(features(rows)-np.asarray(model['center']))/np.asarray(model['scale'])
    result=[exp(float(v)) for v in x@np.asarray(model['coefficients'])+model['intercept']]
    if any(not isfinite(x) for x in result):raise ValueError('conditional means must be finite')
    return result


def evaluate(case, *, target_season, validation_seasons=(2017,2018,2019,2020)):
    coordinate=case['economic_coordinate']
    if any(not coordinate.get(k) for k in ('rules','scoring_signature','native_model_version','panel_sha256')):
        raise ValueError('exact economic coordinate required')
    rows=case['entrants'];seen=set();lookup={}
    for row in rows:
        key=row['player_id'],row['entry_season']
        if key in seen:raise ValueError('duplicate NFL entrant identity')
        seen.add(key);lookup[key]=row
        features([row])
        y=row['raw_three_year'];basis=row['label_basis']
        if basis not in ('observed','research_assumed_source_absence','unknown'):
            raise ValueError('explicit observed/assumed/unknown label basis required')
        if y is not None and (not isfinite(y) or y<0 or basis=='unknown'):
            raise ValueError('finite nonnegative native game label with explicit basis required')
        if y is None and basis!='unknown':raise ValueError('missing outcome cannot be labelled complete')
        if basis=='research_assumed_source_absence' and not row.get('assumption_ref'):
            raise ValueError('assumed labels need a research reference')
    drafts=case['draft_selections'];draft_keys=[(r['draft_season'],r['rank']) for r in drafts]
    if len(draft_keys)!=len(set(draft_keys)):raise ValueError('duplicate fantasy selection')
    def training(year):
        return [r for r in rows if r['entry_season']+2<year and r['raw_three_year'] is not None]
    def targets(year):
        # Conditional-on-selection diagnostic: actual identity is NOT claimed known pre-draft.
        result=[];missing=[]
        for selection in drafts:
            if selection['draft_season']!=year:continue
            row=lookup.get((selection['player_id'],year))
            if row is None or row['label_basis']!='observed':
                missing.append(selection['rank']);continue
            result.append({**row,'rank':selection['rank']})
        return result,missing
    folds=[]
    for year in validation_seasons:
        if year+2>=target_season:raise ValueError('validation labels must mature before target season')
        train=training(year);target,missing=targets(year)
        if not train or not target:continue
        metrics=[]
        for alpha in ALPHAS:
            means=predict(_fit(train,alpha),target)
            metrics.append(dict(alpha=alpha,absolute_error_sum=fsum(abs(p-r['raw_three_year']) for p,r in zip(means,target))))
        folds.append(dict(year=year,training_classes=sorted({r['entry_season'] for r in train}),
            targets=len(target),unscored_ranks=missing,metrics=metrics))
    if not folds:raise ValueError('chronological model-selection evidence required')
    totals={a:fsum(next(m['absolute_error_sum'] for m in f['metrics'] if m['alpha']==a) for f in folds) for a in ALPHAS}
    alpha=min(ALPHAS,key=lambda a:totals[a])
    train=training(target_season);target,missing=targets(target_season)
    model=_fit(train,alpha);means=predict(model,target) if target else []
    predictions=[]
    for row,mean in zip(target,means):
        cohort=[r['raw_three_year'] for r in train if r['position']==row['position']]
        predictions.append(dict(rank=row['rank'],player_id=row['player_id'],position=row['position'],
            nfl_pick=row['nfl_pick'],observed=row['raw_three_year'],capital_mean=mean,
            position_mean=fsum(cohort)/len(cohort) if cohort else None))
    return dict(status='research_conditional_drafted_rookie_mean_not_preselection_pick_forecast',production_eligible=False,
        target_season=target_season,features='original_NFL_position_and_log_overall_pick_with_position_interactions',
        selected_alpha=alpha,selection_folds=folds,training_classes=sorted({r['entry_season'] for r in train}),
        training_count=len(train),assumed_training_count=sum(r['label_basis']!='observed' for r in train),
        target_count=len(target),unscored_ranks=missing,predictions=predictions,model=model,
        capital_mae=fsum(abs(r['capital_mean']-r['observed']) for r in predictions)/len(predictions) if predictions else None,
        position_mae=fsum(abs(r['position_mean']-r['observed']) for r in predictions)/len(predictions) if predictions and all(r['position_mean'] is not None for r in predictions) else None,
        economic_coordinate=coordinate,predictive_intervals_available=False,career_available=False)
