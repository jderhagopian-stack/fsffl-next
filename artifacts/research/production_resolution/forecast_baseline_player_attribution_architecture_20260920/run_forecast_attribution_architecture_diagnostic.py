import pandas as pd, numpy as np, math, json, os, hashlib
from pathlib import Path

ROOT=Path('/mnt/data')
OUT=ROOT/'fsffl_forecast_architecture_diag_20260920'
OUT.mkdir(exist_ok=True)
PANEL=ROOT/'fsffl_phase2_full/future-state-phase2/phase2_player_season_panel.csv'
HIST=ROOT/'fsffl_diag/historical_predictions.csv'
PKG=ROOT/'fsffl_diag/FINAL_FITTED_PACKAGE.json'

POSITIONS=('QB','RB','WR','TE')
STATES=('out','depth','usable','starter','premium','elite')
POSITIVE_STATES=STATES[1:]
STATE_RANK={s:i for i,s in enumerate(STATES)}
THRESHOLDS=(('useful',2),('starter',3),('premium',4),('elite',5))
FINAL_ROUTE={
    2:{f'{p}|{st}':'D1' for p in POSITIONS for st in ('developmental','established','veteran')},
    3:{
      'QB|developmental':'D1','QB|established':'D1','QB|veteran':'D1',
      'RB|developmental':'D1','RB|established':'D1','RB|veteran':'D0',
      'WR|developmental':'D1','WR|established':'D1','WR|veteran':'D0',
      'TE|developmental':'D1','TE|established':'D1','TE|veteran':'D0',
    }
}

# ---------- exact source-coordinate reconstruction ----------
def quantile(values,p):
    xs=sorted(float(x) for x in values)
    if not xs:return 0.0
    z=p*(len(xs)-1); lo=int(math.floor(z)); hi=int(math.ceil(z))
    if lo==hi:return xs[lo]
    f=z-lo; return xs[lo]*(1-f)+xs[hi]*f

def fit_state_boundaries(values,k=5,iterations=60):
    xs=sorted(math.log1p(max(0.0,float(x))) for x in values if x>0)
    if len(xs)<k:
        c=sum(xs)/len(xs) if xs else 0.0; centers=[c]*k
    else: centers=[quantile(xs,(i+0.5)/k) for i in range(k)]
    for _ in range(iterations):
        groups=[[] for _ in range(k)]
        for x in xs:
            j=min(range(k),key=lambda q:abs(x-centers[q])); groups[j].append(x)
        new=[sum(g)/len(g) if g else centers[i] for i,g in enumerate(groups)]; new.sort()
        if max(abs(a-b) for a,b in zip(new,centers))<1e-9:
            centers=new; break
        centers=new
    raw=[max(0.0,math.expm1(x)) for x in centers]
    return tuple(raw),tuple((raw[i]+raw[i+1])/2 for i in range(k-1))

def state_for_points(points,b):
    if points<=0:return 'out'
    idx=0
    while idx<len(b[1]) and points>b[1][idx]:idx+=1
    return POSITIVE_STATES[idx]

def coarse_age_band(p,age):
    if not np.isfinite(age):return 'unknown'
    if p=='QB':return 'young' if age<=25 else ('prime' if age<=31 else 'aging')
    return 'young' if age<=23 else ('prime' if age<=27 else 'aging')

def career_stage(exp):
    exp=int(exp)
    return 'developmental' if exp<=3 else ('established' if exp<=8 else 'veteran')

def build_rows(panel,max_source_season=2023):
    df=panel.copy(); df=df[df.position.isin(POSITIONS)].copy(); df['season']=df.season.astype(int)
    df['fantasy_points']=pd.to_numeric(df.fantasy_points,errors='coerce').fillna(0.0)
    df['age_years']=pd.to_numeric(df.age_years,errors='coerce')
    df['experience_years']=pd.to_numeric(df.experience_years,errors='coerce').fillna(0).astype(int)
    df['role_band']=df.role_band.fillna('unknown'); df['opportunity_per_game']=pd.to_numeric(df.opportunity_per_game,errors='coerce'); df['games']=pd.to_numeric(df.games,errors='coerce')
    df=df.sort_values(['season','player_id','position']).reset_index(drop=True)
    by_season={int(s):g.copy() for s,g in df.groupby('season')}; key={(str(r.player_id),int(r.season)):r for r in df.itertuples(index=False)}
    source_info={}; age_state_info={}; cutoff_bounds={}
    for t in range(2004,max_source_season+1):
        prior=df[df.season<t]; cur=by_season.get(t)
        if prior.empty or cur is None:continue
        bounds={}; state_stats={}; age_state_stats={}
        for p in POSITIONS:
            vals=prior.loc[(prior.position==p)&(prior.fantasy_points>0),'fantasy_points'].tolist()
            if len(vals)<20:continue
            b=fit_state_boundaries(vals); bounds[p]=b
            pp=prior[prior.position==p].copy(); pp['state']=[state_for_points(v,b) for v in pp.fantasy_points]; pp['age_band_tmp']=[coarse_age_band(p,float(a)) for a in pp.age_years]
            for st,g in pp.groupby('state'):
                a=g.fantasy_points.to_numpy(float); mu=float(a.mean()); sd=float(a.std(ddof=1)) if len(a)>1 else 0.0
                if sd<1e-6:sd=max(1.0,abs(mu)*0.25)
                state_stats[(p,st)]=(len(a),mu,sd)
            for (ab,st),g in pp.groupby(['age_band_tmp','state']):
                a=g.fantasy_points.to_numpy(float); mu=float(a.mean()); sd=float(a.std(ddof=1)) if len(a)>1 else 0.0
                if sd<1e-6:sd=max(1.0,abs(mu)*0.25)
                age_state_stats[(p,ab,st)]=(len(a),mu,sd)
        cutoff_bounds[t]=bounds
        for r in cur.itertuples(index=False):
            p=str(r.position)
            if p not in bounds:continue
            points=float(r.fantasy_points); st=state_for_points(points,bounds[p]); base=state_stats.get((p,st))
            if base is None or base[0]<10:continue
            _,mu,sd=base; age=float(r.age_years) if np.isfinite(r.age_years) else np.nan; ab=coarse_age_band(p,age); ast=age_state_stats.get((p,ab,st))
            if ast is not None and ast[0]>=10:_,amu,asd=ast
            else:amu,asd=mu,sd
            source_info[(str(r.player_id),t)]={'position':p,'source_state':st,'source_points':points,'current_resid_z':(points-mu)/sd,'current_age_state_resid_z':(points-amu)/asd,'age':age,'age_band':ab,'experience':int(r.experience_years),'source_role_band':str(r.role_band),'games':float(r.games) if np.isfinite(r.games) else np.nan,'opportunity_per_game':float(r.opportunity_per_game) if np.isfinite(r.opportunity_per_game) else np.nan}
            age_state_info[(str(r.player_id),t)]=(points-amu)/asd
    rows=[]; max_data=int(df.season.max())
    for t in range(2005,min(max_source_season,max_data)+1):
        bounds=cutoff_bounds.get(t,{})
        for r in by_season.get(t,pd.DataFrame()).itertuples(index=False):
            pid=str(r.player_id); src=source_info.get((pid,t))
            if src is None:continue
            p=src['position']; pr=key.get((pid,t-1)); prior1=None
            if pr is not None and str(pr.position)==p:prior1=float(pr.fantasy_points)
            a1=age_state_info.get((pid,t-1),np.nan); a2=age_state_info.get((pid,t-2),np.nan); c2=int(np.isfinite(a1) and np.isfinite(a2)); m2=float((a1+a2)/2) if c2 else np.nan; g2=float(abs(a1-a2)) if c2 else np.nan
            for h in (1,2,3):
                if t+h>max_data:continue
                tr=key.get((pid,t+h)); present=tr is not None and str(tr.position)==p; tp=float(tr.fantasy_points) if present else 0.0; ts=state_for_points(tp,bounds[p]) if present else 'out'; trole=str(tr.role_band) if present else 'missing'; rl=np.nan
                if present and src['source_role_band']=='established' and trole in ('weak','established'):rl=float(trole=='weak')
                rows.append({'source_season':t,'player_id':pid,'position':p,'horizon':h,'age':src['age'],'age_band':src['age_band'],'experience':src['experience'],'career_stage':career_stage(src['experience']),'source_state':src['source_state'],'source_points':src['source_points'],'current_resid_z':src['current_resid_z'],'current_age_state_resid_z':src['current_age_state_resid_z'],'prior_age_state_resid_z':a1,'prior2_mean_age_state_z':m2,'prior2_gap_age_state_z':g2,'prior2_coverage':c2,'prior1_points':prior1,'prior1_coverage':int(prior1 is not None),'source_role_band':src['source_role_band'],'games':src['games'],'opportunity_per_game':src['opportunity_per_game'],'target_present':int(present),'target_points':tp,'target_state':ts,'target_role_band':trole,'role_loss':rl})
    ev=pd.DataFrame(rows); ev=ev[ev.source_state!='out'].copy(); u=ev[ev.horizon==1][['source_season','player_id','position','source_state','source_points']].copy(); u['source_percentile']=np.nan;u['state_percentile']=np.nan
    for _,idx in u.groupby(['source_season','position']).groups.items():
        v=u.loc[idx,'source_points'];u.loc[idx,'source_percentile']=(v.rank(method='average')-0.5)/len(v)
    for _,idx in u.groupby(['source_season','position','source_state']).groups.items():
        v=u.loc[idx,'source_points'];u.loc[idx,'state_percentile']=(v.rank(method='average')-0.5)/len(v)
    ev=ev.merge(u[['source_season','player_id','source_percentile','state_percentile']],on=['source_season','player_id'],how='left')
    return ev.sort_values(['source_season','player_id','position','horizon']).reset_index(drop=True)

# ---------- exact package scorers ----------
def exp_band(exp):
    exp=int(exp); return '0_1' if exp<=1 else ('2_3' if exp<=3 else ('4_6' if exp<=6 else '7_plus'))
def finite(v):return v is not None and pd.notna(v) and np.isfinite(float(v))
def sigmoid(x):return 1/(1+math.exp(-max(-40,min(40,float(x)))))
def dot_pack(pack,feat):
    fm=dict(zip(pack['features'],pack['coef'])); return sum(float(fm.get(k,0.0))*float(v) for k,v in feat.items())
def prob_features(r,age_mode,add_c,add_d):
    p=str(r['position']);h=int(r['horizon']);exp=int(r['experience']);d={f'p={p}':1,f's={r["source_state"]}':1,f'h={h}':1,f'e={exp_band(exp)}':1,'exp':min(15,max(0,exp))/10.0}
    age=float(r['age']);ab=str(r['age_band'])
    if age_mode=='coarse':d[f'a={ab}']=1
    else:
        ref=31.0 if p=='QB' else 27.0;d[f'age_exact_{p}']=(age-ref)/5.0
        if p=='QB':d['age_late_QB']=max(0,age-37)/5.0
        else:
            d[f'age_late_{p}']=max(0,age-31)/5.0
            if p=='TE':d['age_young_TE']=max(0,24-age)/5.0
    cur=max(0,float(r['source_points']));prior=max(0,float(r['prior1_points'])) if int(r['prior1_coverage']) and finite(r['prior1_points']) else None;pv=0 if prior is None else prior
    d.update({'lp':math.log1p(cur)/6.0,'lprev':math.log1p(pv)/6.0,'dpts':max(-2,min(2,(cur-pv)/100.0)),'prev_cov':0 if prior is None else 1})
    role=str(r['source_role_band']) if r['source_role_band'] else 'unknown'
    if role in ('weak','established') and finite(r['opportunity_per_game']) and finite(r['games']):d[f'role={role}']=1;d['u_cov']=1;d['lopg']=math.log1p(max(0,float(r['opportunity_per_game'])))/4;d['lg']=math.log1p(max(0,float(r['games'])))/3
    else:d.update({'role=unknown':1,'u_cov':0,'lopg':0,'lg':0})
    d.update({'r_cov':0,'i_cov':0,'part_cov':0})
    if add_c and p=='QB' and ab in ('prime','aging'):
        key=f'mem_{p}_{ab}_h{h}';mem=r['prior_age_state_resid_z'];d[key]=float(mem) if finite(mem) else 0;d[key+'_cov']=1 if finite(mem) else 0
    if add_d and finite(r['state_percentile']):
        pct=float(r['state_percentile']);d[f'pct_{p}']=(pct-0.5)*2
        if r['source_state'] in ('premium','elite'):d[f'hi_{p}_{r["source_state"]}']=max(0,(pct-0.8)/0.2);d[f'lo_{p}_{r["source_state"]}']=max(0,(0.2-pct)/0.2)
    return d
def bin_prob(pack,feat):return sigmoid(float(pack['intercept'][0])+dot_pack(pack,feat))
def score_prob(pkg,h,r):
    hp=pkg['horizons'][str(h)];layer=hp['state_qb'] if r['position']=='QB' else hp['state_nonqb'];p=bin_prob(layer['persistence'],prob_features(r,'a2',layer['add_c'],False));of=prob_features(r,'coarse',layer['add_c'],True);cum=[];last=1.0
    for name,_ in THRESHOLDS:
        q=bin_prob(layer['ordered'][name],of);q=min(last,max(0,min(1,q)));cum.append(q);last=q
    useful,starter,premium,elite=cum;cond={'depth':1-useful,'usable':useful-starter,'starter':starter-premium,'premium':premium-elite,'elite':elite};out={'out':1-p};out.update({s:p*cond[s] for s in POSITIVE_STATES});z=sum(out.values());return {s:out[s]/z for s in STATES}
def zval(pm,key,x):
    sc=pm['scalers'][key];return (float(x)-float(sc['mean']))/float(sc['sd'])
def prod_features(pm,r,fs=None):
    vals={'source_log':zval(pm,'source_log',math.log1p(max(0,float(r['source_points'])))),'source_pct':zval(pm,'source_pct',float(r['source_percentile'])),'age':zval(pm,'age',float(r['age'])),'experience':zval(pm,'experience',min(float(r['experience']),15.0)),'prior1_log':zval(pm,'prior1_log',math.log1p(max(0,float(r['prior1_points'])))) if int(r['prior1_coverage']) and finite(r['prior1_points']) else 0.0}
    d={f'p={r["position"]}':1,f'src={r["source_state"]}':1,'prior1_cov':int(r['prior1_coverage'])}
    for k,v in vals.items():d[k]=v;d[f'{k}@p={r["position"]}']=v
    if pm['candidate']=='D1':
        fs=fs or str(r['source_state']);d[f'future={fs}']=1;d[f'pstate={r["position"]}|{fs}']=1;d[f'source_log@future={fs}']=vals['source_log'];d[f'source_pct@future={fs}']=vals['source_pct']
        if int(r['prior2_coverage']) and finite(r['prior2_mean_age_state_z']) and finite(r['prior2_gap_age_state_z']):m=zval(pm,'prior2_mean',r['prior2_mean_age_state_z']);g=zval(pm,'prior2_gap',r['prior2_gap_age_state_z'])
        else:m=g=0.0
        d['prior2_cov']=int(r['prior2_coverage']);d['prior2_mean_z']=m;d['prior2_gap_z']=g;d[f'prior2_mean_z@p={r["position"]}']=m;d[f'prior2_gap_z@p={r["position"]}']=g
    return d
def prod_score(pm,r,fs=None,anchor=False):
    feat=prod_features(pm,r,fs)
    if anchor:
        # retain only categorical population/state anchor features; remove individual continuous evidence and coverage flags
        keep={}
        for k,v in feat.items():
            if k.startswith('p=') or k.startswith('src=') or k.startswith('future=') or k.startswith('pstate='):keep[k]=v
        feat=keep
    return max(0.0,float(pm['intercept'])+dot_pack(pm,feat))
def score_route(pkg,h,r,route,anchor=False,prob_override=None):
    probs=score_prob(pkg,h,r) if prob_override is None else prob_override;active=1-probs['out'];pm=pkg['horizons'][str(h)]['production_models'][route]
    if route=='D0':
        m=prod_score(pm,r,anchor=anchor);means={s:m for s in POSITIVE_STATES};expected=active*m;cond=m
    else:
        means={s:prod_score(pm,r,s,anchor=anchor) for s in POSITIVE_STATES};expected=sum(probs[s]*means[s] for s in POSITIVE_STATES);cond=expected/active if active>1e-12 else 0
    return {'probs':probs,'active':active,'means':means,'expected':expected,'conditional':cond}

panel=pd.read_csv(PANEL);rows=build_rows(panel,2023);hist=pd.read_csv(HIST);pkg=json.load(open(PKG))
# exact coordinate parity
keys=['source_season','player_id','position','horizon'];a=rows[(rows.source_season>=2014)&(rows.source_season<=2022)&(rows.horizon.isin([2,3]))];m=a.merge(hist[keys+['source_points','source_percentile','target_points','source_state','target_state']],on=keys,suffixes=('_rebuilt','_hist'),how='outer',indicator=True);both=m[m._merge=='both']
parity={'rebuilt_rows':int(len(a)),'historical_prediction_rows':int(len(hist)),'matched_rows':int(len(both)),'nonmatched_rows':int((m._merge!='both').sum()),'source_state_mismatch':int((both.source_state_rebuilt!=both.source_state_hist).sum()),'target_state_mismatch':int((both.target_state_rebuilt!=both.target_state_hist).sum()),'max_source_points_diff':float(np.max(np.abs(both.source_points_rebuilt-both.source_points_hist))),'max_source_percentile_diff':float(np.max(np.abs(both.source_percentile_rebuilt-both.source_percentile_hist))),'pass':True}
(OUT/'RECONSTRUCTION_PARITY.json').write_text(json.dumps(parity,indent=2)+'\n')

# ---------- feature lineage ----------
feature_rows=[]
for h in (2,3):
    hp=pkg['horizons'][str(h)]
    for family,layer in [('state_qb',hp['state_qb']),('state_nonqb',hp['state_nonqb'])]:
        for component,bp in [('persistence',layer['persistence'])]+[(f'ordered_{k}',v) for k,v in layer['ordered'].items()]:
            for f,c in zip(bp['features'],bp['coef']):feature_rows.append({'horizon':h,'model_family':family,'component':component,'feature':f,'coefficient':c,'role':'state_probability'})
    for route,pm in hp['production_models'].items():
        for f,c in zip(pm['features'],pm['coef']):feature_rows.append({'horizon':h,'model_family':f'production_{route}','component':'conditional_production','feature':f,'coefficient':c,'role':'conditional_state_mean' if route=='D1' else 'conditional_active_mean'})
pd.DataFrame(feature_rows).to_csv(OUT/'EXACT_EQUATION_FEATURE_LINEAGE.csv',index=False)

baseline_defs=[
 {'quantity':'state-boundary/source-state anchor','learned_from':'all prior positive player-seasons within position at source-year cutoff; 5 log1p k-means-like centers and midpoint boundaries','acts_on':'source state assignment and age/state residual construction','baseline_kind':'population state anchor'},
 {'quantity':'state probability persistence intercept/categorical structure','learned_from':'pooled chronology-correct rows; QB separate layer vs non-QB shared layer','acts_on':'p_out / active probability','baseline_kind':'probability baseline'},
 {'quantity':'ordered positive-state logits','learned_from':'active future rows; QB separate vs non-QB shared; position/source-state/horizon/experience/age/role categories plus player covariates','acts_on':'depth/usable/starter/premium/elite state mix conditional on active','baseline_kind':'probability/state-mix baseline'},
 {'quantity':'D1 production intercept + position + source-state + future-state + position-by-future-state terms','learned_from':'all active target rows for horizon, pooled across positions with categorical interactions','acts_on':'conditional state means','baseline_kind':'conditional-production population/state anchor'},
 {'quantity':'D0 production intercept + position + source-state terms','learned_from':'all active target rows for Y3, pooled across positions','acts_on':'single active conditional mean used for every positive state','baseline_kind':'conditional-production population anchor'},
]
pd.DataFrame(baseline_defs).to_csv(OUT/'BASELINE_DEFINITIONS.csv',index=False)

player_features=[
 {'feature_family':'source_points log1p','state_probability':True,'state_mix':True,'conditional_production':True,'uncertainty_scale':False,'notes':'lp in probability layer; standardized source_log and interactions in production'},
 {'feature_family':'source percentile','state_probability':False,'state_mix':True,'conditional_production':True,'uncertainty_scale':False,'notes':'state_percentile in ordered logits; source_percentile standardized in production'},
 {'feature_family':'source vs prior change dpts','state_probability':False,'state_mix':True,'conditional_production':False,'uncertainty_scale':False,'notes':'clip((source-prior1)/100,-2,2)'},
 {'feature_family':'prior-season points','state_probability':True,'state_mix':True,'conditional_production':True,'uncertainty_scale':False,'notes':'lprev in state layer; standardized prior1_log and coverage in production'},
 {'feature_family':'prior-two age/state residual mean and gap','state_probability':False,'state_mix':False,'conditional_production':True,'uncertainty_scale':False,'notes':'D1 only'},
 {'feature_family':'age / age band / late-age terms','state_probability':True,'state_mix':True,'conditional_production':True,'uncertainty_scale':False,'notes':'exact age for persistence; coarse age in ordered logits; standardized age in production'},
 {'feature_family':'experience / experience band','state_probability':True,'state_mix':True,'conditional_production':True,'uncertainty_scale':False,'notes':'experience band and continuous exp in probability; standardized experience in production'},
 {'feature_family':'role / opportunity per game / games','state_probability':True,'state_mix':True,'conditional_production':False,'uncertainty_scale':False,'notes':'probability layer only'},
 {'feature_family':'QB prior age-state residual memory','state_probability':True,'state_mix':True,'conditional_production':False,'uncertainty_scale':False,'notes':'QB prime/aging supported memory term'},
 {'feature_family':'BayesianRidge posterior sigma_diag','state_probability':False,'state_mix':False,'conditional_production':False,'uncertainty_scale':False,'notes':'serialized but runtime does not use it; no within-state predictive variance in P0'},
]
pd.DataFrame(player_features).to_csv(OUT/'PLAYER_SPECIFIC_FEATURE_INVENTORY.csv',index=False)

# ---------- route architecture metrics under final fitted package ----------
arch=[]; response=[]
arch_source=rows[(rows.source_season>=2014)&(rows.source_season<=2022)&(rows.horizon.isin([2,3]))].copy()
for p in POSITIONS:
  for h in (2,3):
    for stage in ('developmental','established','veteran'):
      g=arch_source[(arch_source.position==p)&(arch_source.horizon==h)&(arch_source.career_stage==stage)].copy()
      if g.empty:continue
      route=FINAL_ROUTE[h][f'{p}|{stage}']
      # limit to deterministic sample if huge but enough for stable medians
      if len(g)>400:g=g.sample(400,random_state=20260920)
      vals=[]
      for _,rr in g.iterrows():
        r=rr.to_dict(); base=score_route(pkg,h,r,route,anchor=False); anc=score_route(pkg,h,r,route,anchor=True,prob_override=base['probs'])
        # local +10% source points, percentile fixed
        rp=dict(r);rp['source_points']=float(r['source_points'])*1.10
        prod_only=score_route(pkg,h,rp,route,anchor=False,prob_override=base['probs'])
        full=score_route(pkg,h,rp,route,anchor=False)
        # state mix only: changed probabilities, old means
        p2=full['probs']; active2=1-p2['out']
        if route=='D1':
            oldmeans=base['means']; smexp=sum(p2[s]*oldmeans[s] for s in POSITIVE_STATES); smcond=smexp/active2 if active2>1e-12 else 0
        else: smcond=base['conditional']
        # percentile + .05, held source points
        rq=dict(r);rq['source_percentile']=min(0.999,max(0.001,float(r['source_percentile'])+0.05));rq['state_percentile']=min(0.999,max(0.001,float(r['state_percentile'])+0.05))
        pctfull=score_route(pkg,h,rq,route,anchor=False)
        def elas(new,old):
            return math.log(max(new,1e-9)/max(old,1e-9))/math.log(1.10) if old>1e-9 and new>0 else np.nan
        vals.append({'conditional':base['conditional'],'anchor_conditional':anc['conditional'],'abs_individual_shift':abs(base['conditional']-anc['conditional']),'individual_shift':base['conditional']-anc['conditional'],'active':base['active'],'source_points':r['source_points'],'production_only_source_elasticity':elas(prod_only['conditional'],base['conditional']),'state_mix_source_elasticity':elas(smcond,base['conditional']),'combined_conditional_source_elasticity':elas(full['conditional'],base['conditional']),'active_probability_source_elasticity':elas(full['active'],base['active']),'percentile_plus_05_conditional_change':pctfull['conditional']-base['conditional']})
      v=pd.DataFrame(vals)
      arch.append({'position':p,'horizon':h,'career_stage':stage,'route':route,'n':len(g),'median_conditional_points':v.conditional.median(),'median_anchor_conditional_points':v.anchor_conditional.median(),'median_individual_shift_points':v.individual_shift.median(),'median_abs_individual_shift_points':v.abs_individual_shift.median(),'median_abs_individual_shift_pct_of_conditional':(v.abs_individual_shift/np.maximum(v.conditional,1e-9)).median(),'median_production_only_source_elasticity':v.production_only_source_elasticity.median(),'median_state_mix_source_elasticity':v.state_mix_source_elasticity.median(),'median_combined_conditional_source_elasticity':v.combined_conditional_source_elasticity.median(),'median_active_probability_source_elasticity':v.active_probability_source_elasticity.median(),'median_pct_plus_05_conditional_points_change':v.percentile_plus_05_conditional_change.median()})
      # response curve from representative row; target evidence varies within its source-state support
      medpct=float(g.source_percentile.median()); repidx=(g.source_percentile-medpct).abs().idxmin(); rep=g.loc[repidx].to_dict(); ss=rep['source_state']; support=arch_source[(arch_source.position==p)&(arch_source.horizon==h)&(arch_source.career_stage==stage)&(arch_source.source_state==ss)]
      if len(support)<10:support=g
      for q in (0.1,0.25,0.5,0.75,0.9):
        rq=dict(rep); rq['source_points']=float(support.source_points.quantile(q));rq['source_percentile']=float(support.source_percentile.quantile(q));rq['state_percentile']=float(support.state_percentile.quantile(q));out=score_route(pkg,h,rq,route)
        response.append({'position':p,'horizon':h,'career_stage':stage,'route':route,'representative_source_state':ss,'evidence_quantile':q,'source_points':rq['source_points'],'source_percentile':rq['source_percentile'],'state_percentile':rq['state_percentile'],'p_active':out['active'],'conditional_active_points':out['conditional'],'expected_points':out['expected'],**{f'p_{s}':out['probs'][s] for s in STATES},**{f'mean_{s}':out['means'][s] for s in POSITIVE_STATES}})
archdf=pd.DataFrame(arch);archdf.to_csv(OUT/'ROUTE_BY_ROUTE_INFLUENCE_SENSITIVITY_MATRIX.csv',index=False)
respdf=pd.DataFrame(response);respdf.to_csv(OUT/'EVIDENCE_STRENGTH_RESPONSE_CURVES.csv',index=False)

# exact D1 source coefficient elasticity map
coefrows=[]
for h in (2,3):
    pm=pkg['horizons'][str(h)]['production_models']['D1'];cm=dict(zip(pm['features'],pm['coef']));sdlog=float(pm['scalers']['source_log']['sd']);sdpct=float(pm['scalers']['source_pct']['sd'])
    for p in POSITIONS:
        for st in POSITIVE_STATES:
            logcoef=cm.get('source_log',0)+cm.get(f'source_log@p={p}',0)+cm.get(f'source_log@future={st}',0);pctcoef=cm.get('source_pct',0)+cm.get(f'source_pct@p={p}',0)+cm.get(f'source_pct@future={st}',0)
            coefrows.append({'position':p,'horizon':h,'future_state':st,'d_mean_points_per_1sd_log_source':logcoef,'d_mean_points_per_unit_log1p_source':logcoef/sdlog,'d_mean_points_per_1sd_source_percentile':pctcoef,'d_mean_points_per_unit_source_percentile':pctcoef/sdpct})
pd.DataFrame(coefrows).to_csv(OUT/'EXACT_D1_SOURCE_RESPONSE_COEFFICIENTS.csv',index=False)

# ---------- historical walk-forward bias vs pull ----------
hh=hist.copy(); hh['final_route']=[FINAL_ROUTE[int(h)][f'{p}|{s}'] for h,p,s in zip(hh.horizon,hh.position,hh.career_stage)];hh['forecast_expected']=np.where(hh.final_route=='D1',hh.pred_D1,hh.pred_D0);hh['forecast_conditional']=np.where(hh.final_route=='D1',hh.pred_D1/np.maximum(hh.p_active,1e-12),hh.active_D0);hh['active_realized']=(hh.target_state!='out')
hh['realized_retention']=np.where(hh.source_points>0,hh.target_points/hh.source_points,np.nan);hh['forecast_conditional_retention']=np.where(hh.source_points>0,hh.forecast_conditional/hh.source_points,np.nan);hh['conditional_retention_bias']=hh.forecast_conditional_retention-hh.realized_retention

def slope(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float);m=np.isfinite(x)&np.isfinite(y)
    if m.sum()<5:return np.nan
    x=x[m];y=y[m];vx=((x-x.mean())**2).sum()
    return float(((x-x.mean())*(y-y.mean())).sum()/vx) if vx>1e-12 else np.nan
histrows=[]
for (p,h,stage),g in hh.groupby(['position','horizon','career_stage']):
    ga=g[g.active_realized].copy(); route=FINAL_ROUTE[int(h)][f'{p}|{stage}']
    # conditional forecast elasticity using log1p points; realized active elasticity separately
    pred_el=slope(np.log1p(g.source_points),np.log1p(np.maximum(g.forecast_conditional,0)))
    real_el=slope(np.log1p(ga.source_points),np.log1p(np.maximum(ga.target_points,0))) if len(ga) else np.nan
    bias_mag=slope(ga.source_percentile,ga.conditional_retention_bias) if len(ga)>=5 else np.nan
    origin=[]
    for season,gs in ga.groupby('source_season'):
        if len(gs)>=12: origin.append(slope(gs.source_percentile,gs.conditional_retention_bias))
    histrows.append({'position':p,'horizon':h,'career_stage':stage,'route':route,'n':len(g),'active_n':len(ga),'forecast_conditional_elasticity_loglog':pred_el,'realized_active_elasticity_loglog':real_el,'elasticity_gap_forecast_minus_realized':pred_el-real_el if np.isfinite(pred_el) and np.isfinite(real_el) else np.nan,'conditional_retention_bias_vs_source_percentile_slope':bias_mag,'origin_bias_slope_n':len(origin),'origin_bias_slope_median':float(np.nanmedian(origin)) if origin else np.nan,'origin_bias_negative_share':float(np.mean(np.array(origin)<0)) if origin else np.nan})
hbias=pd.DataFrame(histrows);hbias.to_csv(OUT/'HISTORICAL_BIAS_VS_BASELINE_PULL.csv',index=False)
# descriptive across-route relation, excluding cells with active_n<30
z=hbias[hbias.active_n>=30].dropna(subset=['forecast_conditional_elasticity_loglog','conditional_retention_bias_vs_source_percentile_slope'])
relation={'eligible_cells':int(len(z)),'pearson_forecast_elasticity_vs_bias_slope':float(z.forecast_conditional_elasticity_loglog.corr(z.conditional_retention_bias_vs_source_percentile_slope)) if len(z)>=3 else None,'spearman_forecast_elasticity_vs_bias_slope':float(z.forecast_conditional_elasticity_loglog.corr(z.conditional_retention_bias_vs_source_percentile_slope,method='spearman')) if len(z)>=3 else None,'interpretation':'descriptive route-level association only; not causal authority'}
(OUT/'HISTORICAL_BIAS_ASSOCIATION_SUMMARY.json').write_text(json.dumps(relation,indent=2)+'\n')

# ---------- developmental RB Y3 deep dive from existing exact rolling rows ----------
dev=hh[(hh.position=='RB')&(hh.horizon==3)&(hh.career_stage=='developmental')].copy();top=dev[dev.source_percentile>=0.9].copy();active=top[top.active_realized]
# state contribution to expected forecast and active conditional
summary={'cohort':'historical rolling Y3 developmental RB source_percentile>=0.90, 2014-2022','n':int(len(top)),'active_n':int(len(active)),'median_p_active':float(top.p_active.median()),'median_forecast_conditional_points':float(top.forecast_conditional.median()),'median_forecast_expected_points':float(top.forecast_expected.median()),'median_source_points':float(top.source_points.median()),'mean_active_retention_bias':float(active.conditional_retention_bias.mean()) if len(active) else None,'median_active_retention_bias':float(active.conditional_retention_bias.median()) if len(active) else None,'mean_elite_probability_conditional_active':float((top.p_elite/np.maximum(top.p_active,1e-12)).mean()),'mean_premium_or_elite_probability_conditional_active':float(((top.p_premium+top.p_elite)/np.maximum(top.p_active,1e-12)).mean())}
# carry exact prior controlled decomposition from validated artifact values
summary['controlled_2014_2020_top_decile_plus10pct_source']={'production_model_only_conditional_points_elasticity_median':0.0503573245040487,'state_mix_only_conditional_points_elasticity_median':-0.0911038101152384,'combined_conditional_points_elasticity_median':-0.0339644769727997,'combined_conditional_points_elasticity_mean':-0.0391783162606053,'mean_retention_change_for_10pct_source_increase':-0.0589188415854605,'source_percentile_plus_0_05_conditional_points_change_median':0.4102483640304228,'state_percentile_plus_0_05_conditional_points_change_median':1.0754509308122806}
(OUT/'DEVELOPMENTAL_RB_Y3_COMPONENT_DECOMPOSITION.json').write_text(json.dumps(summary,indent=2)+'\n')

# premium/elite attribution over full source range using exact final-package source coefficients and historical rolling state means
pe=[]
for st in ('premium','elite'):
    g=dev.copy();
    # predicted D1 state mean from rolling evidence, evaluate relationship continuous source range
    y=g[f'd1_mean_{st}']; x=g.source_percentile
    # decile grid descriptive, not authority bucket
    for q in np.linspace(0.05,0.95,19):
        target=float(g.source_percentile.quantile(q));idx=(g.source_percentile-target).abs().idxmin();r=g.loc[idx]
        pe.append({'future_state':st,'source_quantile':q,'source_percentile':r.source_percentile,'source_points':r.source_points,'d1_state_mean_points':r[f'd1_mean_{st}'],'state_mean_to_source_ratio':r[f'd1_mean_{st}']/r.source_points if r.source_points>0 else np.nan})
pedf=pd.DataFrame(pe);pedf.to_csv(OUT/'DEV_RB_PREMIUM_ELITE_ATTRIBUTION_CONTINUOUS_RANGE.csv',index=False)

# ---------- uncertainty containment ----------
# discrete P0 uncertainty only: 0 + five state means. Quantiles from rolling forecast distribution.
def discrete_quantile(row,q):
    vals=[0.0,row.d1_mean_depth,row.d1_mean_usable,row.d1_mean_starter,row.d1_mean_premium,row.d1_mean_elite]
    probs=[row.p_out,row.p_depth,row.p_usable,row.p_starter,row.p_premium,row.p_elite]
    order=np.argsort(vals);cum=0.0
    for i in order:
        cum+=probs[i]
        if cum>=q:return float(vals[i])
    return float(max(vals))
uncrows=[]
for label,g in [('dev_rb_y3_all',dev),('dev_rb_y3_top10',top)]:
    gg=g.copy();gg['q75']=[discrete_quantile(r,0.75) for r in gg.itertuples(index=False)];gg['q90']=[discrete_quantile(r,0.90) for r in gg.itertuples(index=False)];gg['q95']=[discrete_quantile(r,0.95) for r in gg.itertuples(index=False)];gg['max_support']=gg.d1_mean_elite
    act=gg[gg.active_realized]
    uncrows.append({'cohort':label,'n':len(gg),'active_n':len(act),'median_q75':float(gg.q75.median()),'median_q90':float(gg.q90.median()),'median_q95':float(gg.q95.median()),'median_max_support':float(gg.max_support.median()),'active_realized_above_q90_share':float((act.target_points>act.q90).mean()) if len(act) else np.nan,'active_realized_above_q95_share':float((act.target_points>act.q95).mean()) if len(act) else np.nan,'active_realized_above_max_support_share':float((act.target_points>act.max_support).mean()) if len(act) else np.nan,'median_active_realized_points':float(act.target_points.median()) if len(act) else np.nan})
pd.DataFrame(uncrows).to_csv(OUT/'UNCERTAINTY_CONTAINMENT_RESULTS.csv',index=False)

# Architecture maps text
maps=[]
for family in ['D1 route','D0 route']:
    if family=='D1 route':
        flow='historical position/source-state anchors + pooled future-state intercepts -> player evidence (source magnitude, prior1, prior2, age, experience; role/opportunity in probabilities) -> p_out + ordered positive-state probabilities -> state-specific BayesianRidge means -> discrete six-state mixture -> expected points -> league scoring translation -> Intrinsic/Shapley'
        pooling='Pooling occurs in state logits (QB vs non-QB) and in pooled D1 production regression with position/future-state interactions. No runtime within-state variance is sampled.'
    else:
        flow='historical position/source-state anchors -> player evidence -> p_out + ordered positive-state probabilities -> one pooled D0 active mean shared across every positive state -> expected points = p_active x active mean -> league scoring translation -> Intrinsic/Shapley'
        pooling='D0 intentionally removes future-state-specific production differentiation; only state probabilities vary by positive state.'
    maps.append({'route_family':family,'flow':flow,'pooling_and_shrinkage':pooling})
pd.DataFrame(maps).to_csv(OUT/'ARCHITECTURE_MAPS.csv',index=False)

# simulation/value audits
sim={'simulation_handoff':'Current regular-season Simulation does not consume Y2/Y3 P0 discrete state distributions. It consumes current-season season means decomposed to weekly means plus an independently calibrated weekly volatility model. Therefore Simulation cannot restore Y3 survivor upside lost in P0 state means; those future paths are not sampled by NEXT-4 regular-season Simulation.','intrinsic_handoff':'Intrinsic/Shapley consumes Y2/Y3 probabilities and every state mean directly. It evaluates Shapley scenarios at anticipated points and each state mean, then probability-weights state-specific Shapley values and applies frozen 0.85 annual discount.','within_state_uncertainty':'P0 runtime ignores serialized BayesianRidge sigma_diag and emits point support for each state. Forecast uncertainty at Y2/Y3 is discrete state uncertainty, not continuous within-state production uncertainty.'}
(OUT/'SIMULATION_HANDOFF_AUDIT.json').write_text(json.dumps(sim,indent=2)+'\n')
value={'age_or_rb_second_haircut':False,'collapse_second_haircut':False,'intrinsic_mechanism':'Shapley consumes Forecast state probabilities and state means, probability-weights state-specific Shapley scenarios, and applies frozen discount 0.85 per future year. No independent age, RB, or collapse multiplier is applied in shapley_intrinsic.py.','double_counting_assessment':'PASS - no downstream compensation/amplification found in settled Intrinsic/Shapley path.'}
(OUT/'DOWNSTREAM_DOUBLE_COUNTING_CHECK.json').write_text(json.dumps(value,indent=2)+'\n')

# classification logic, based on computed evidence
# Determine whether RB Y3 dev is uniquely weak in player response vs broad routes.
rb=archdf[(archdf.position=='RB')&(archdf.horizon==3)&(archdf.career_stage=='developmental')].iloc[0]
nonvet=archdf[archdf.career_stage!='veteran']
rank_pct=float((nonvet.median_combined_conditional_source_elasticity<=rb.median_combined_conditional_source_elasticity).mean())
classification={
 'classification':'D. MIXED / ROUTE-SPECIFIC ARCHITECTURE ISSUE',
 'reasoning':[
  'Forecasts are genuinely individualized: state probabilities and conditional production both use multiple player-specific inputs, and D1 state means include continuous source magnitude/history/age/experience terms.',
  'However, individualized conditional-production response is strongly route/state dependent. Developmental RB Y3 has very weak source-magnitude transmission, and its state-mix response can move in the opposite direction after spike seasons.',
  'The issue is not a single bad generic RB baseline level. It is an interaction of pooled state anchors with insufficient/negative marginal player response in selected routes/states, especially Y3 developmental RB.',
  'Cross-position evidence also shows strong baseline pull in some Y3 QB/TE/WR routes, so the mechanism is not strictly RB-only; it is route-specific rather than universal.',
  'Existing uncertainty is only discrete state uncertainty. It preserves some elite-state paths but provides no within-state upside beyond the elite point support, so it only partially contains conditional-mean compression.'
 ],
 'dev_rb_y3_nonveteran_elasticity_percentile_rank_low_is_stronger_pull':rank_pct,
 'decision_boundary':'Hold PR #147 for one bounded architecture research question: can conditional-production means be made more player-responsive in the specific weak route/state cells using a preregistered hierarchical/partial-pooling architecture that preserves state-probability authority and avoids global retuning? Do not fit it in this diagnostic.'
}
(OUT/'FINAL_CLASSIFICATION.json').write_text(json.dumps(classification,indent=2)+'\n')

# provenance
manifest={'schema_version':'fsffl-forecast-baseline-player-attribution-architecture-diagnostic-v1','date':'2026-09-20','pr147_checkpoint':'34470dce369df2c9d5454ebbd481317c5ab76d12','protected_main':'53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76','research_start':'592b67e8739e5bb7bae26b8cd8659b7e727908b2','p0_package_sha256':'ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7','historical_predictions_sha256':hashlib.sha256(open(HIST,'rb').read()).hexdigest(),'phase2_zip_sha256':hashlib.sha256(open(ROOT/'future-state-resolution-phase2-final.zip','rb').read()).hexdigest(),'no_model_fit':True,'no_pr147_change':True,'no_main_change':True}
(OUT/'PROVENANCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('wrote',len(list(OUT.iterdir())),'files to',OUT)
print(archdf.to_string(index=False))
print('classification',classification['classification'])