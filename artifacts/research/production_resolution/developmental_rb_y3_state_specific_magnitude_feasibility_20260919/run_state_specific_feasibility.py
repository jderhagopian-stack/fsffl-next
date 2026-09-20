import json, math, hashlib
from pathlib import Path
import numpy as np, pandas as pd

OUT=Path('/mnt/data/fsffl_state_specific_feasibility_20260919'); OUT.mkdir(exist_ok=True)
BASE=Path('/mnt/data/fsffl_dev_rb_continuous_cal_20260919/ROW_LEVEL_EVALUATION_SCORES.csv')
HIST=Path('/mnt/data/fsffl_diag/historical_predictions.csv')
PANEL=Path('/mnt/data/fsffl_phase2/future-state-phase2/phase2_player_season_panel.csv')
SEED=20260920
STATES=['depth','usable','starter','premium','elite']
UPPER={'starter','premium','elite'}
LOWER={'depth','usable'}

# Reuse exact governed row reconstruction from prior stage.
import importlib.util
spec=importlib.util.spec_from_file_location('revalfit','/mnt/data/fsffl_revalidate_fit.py')
import sys
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)

base=pd.read_csv(BASE)
base=base[base.candidate=='C1'].copy().sort_values(['source_season','player_id']).reset_index(drop=True)
hist=pd.read_csv(HIST)
control=hist[(hist.position=='RB')&(hist.horizon==3)&(hist.career_stage=='developmental')&hist.source_season.between(2014,2022)].copy().sort_values(['source_season','player_id']).reset_index(drop=True)
keys=['source_season','player_id','position','horizon']
merged=base.merge(control,on=keys,suffixes=('_stage','_hist'),how='outer',indicator=True)
parity_fields=['source_points','source_percentile','target_points','p_active','pred_D1','p_out','p_depth','p_usable','p_starter','p_premium','p_elite','d1_mean_depth','d1_mean_usable','d1_mean_starter','d1_mean_premium','d1_mean_elite']
parity={}
for f in parity_fields:
    a=pd.to_numeric(merged[f+'_stage'],errors='coerce').to_numpy(float); b=pd.to_numeric(merged[f+'_hist'],errors='coerce').to_numpy(float)
    parity[f]=float(np.nanmax(np.abs(a-b))) if len(a) else None

active=base[base.target_state!='out'].copy()
mean_col={s:f'd1_mean_{s}' for s in STATES}
active['d1_state_mean']=active.apply(lambda r:r[mean_col[r.target_state]],axis=1)
active['log1p_resid']=np.log1p(active.target_points)-np.log1p(active.d1_state_mean)
active['abs_log1p_resid']=active.log1p_resid.abs()
active['realized_ret']=active.target_points/active.source_points.replace(0,np.nan)
active['d1_state_ret']=active.d1_state_mean/active.source_points.replace(0,np.nan)
active['ret_bias']=active.d1_state_ret-active.realized_ret
active['pool_group']=np.where(active.target_state.isin(UPPER),'upper','lower')

# Reconstruct exact governed rows to quantify training support available before each origin.
panel=pd.read_csv(PANEL)
rows=mod.build_rows(panel,2023)
train_support=[]
for origin in range(2014,2023):
    tr=rows[(rows.position=='RB')&(rows.horizon==3)&(rows.career_stage=='developmental')&(rows.source_season<origin)&(rows.source_season+3<=origin-1)&(rows.target_state!='out')].copy()
    for s in STATES:
        g=tr[tr.target_state==s]
        train_support.append({'origin':origin,'state':s,'train_active_n':len(g),'train_unique_players':g.player_id.nunique(),'train_source_years':g.source_season.nunique(),'train_pct_min':float(g.source_percentile.min()) if len(g) else np.nan,'train_pct_max':float(g.source_percentile.max()) if len(g) else np.nan})
train_support=pd.DataFrame(train_support)

# Evaluation support matrix and summary.
def kish_ess(series):
    vc=series.value_counts().to_numpy(float)
    return float((vc.sum()**2)/(vc@vc)) if len(vc) else 0.0
support_origin=[]
for origin in range(2014,2023):
    for s in STATES:
        g=active[(active.origin==origin)&(active.target_state==s)]
        support_origin.append({'origin':origin,'state':s,'eval_n':len(g),'eval_unique_players':g.player_id.nunique(),'pct_min':float(g.source_percentile.min()) if len(g) else np.nan,'pct_max':float(g.source_percentile.max()) if len(g) else np.nan})
support_origin=pd.DataFrame(support_origin).merge(train_support,on=['origin','state'],how='left')

support=[]
for s,g in active.groupby('target_state'):
    vc=g.player_id.value_counts(normalize=True)
    support.append({
        'state':s,'n':len(g),'unique_players':g.player_id.nunique(),'origins':g.origin.nunique(),
        'player_kish_ess':kish_ess(g.player_id),'origin_kish_ess':kish_ess(g.origin),
        'max_player_rows':int(g.player_id.value_counts().max()),'max_player_share':float(vc.max()),'top5_player_share':float(vc.head(5).sum()),
        'pct_min':float(g.source_percentile.min()),'pct_p10':float(g.source_percentile.quantile(.10)),'pct_p25':float(g.source_percentile.quantile(.25)),'pct_median':float(g.source_percentile.median()),'pct_p75':float(g.source_percentile.quantile(.75)),'pct_p90':float(g.source_percentile.quantile(.90)),'pct_max':float(g.source_percentile.max()),
        'target_points_mean':float(g.target_points.mean()),'target_points_sd':float(g.target_points.std()),'log1p_resid_sd':float(g.log1p_resid.std())
    })
support=pd.DataFrame(support).sort_values('state')

# Descriptive magnitude slices only.
bins=[-1e-12,.50,.75,.90,1.0000001]; labels=['p0_50','p50_75','p75_90','p90_100']
active['mag_slice']=pd.cut(active.source_percentile,bins=bins,labels=labels,right=False)
coverage=active.groupby(['target_state','mag_slice'],observed=True).agg(n=('player_id','size'),unique_players=('player_id','nunique'),realized_points_mean=('target_points','mean'),d1_state_points_mean=('d1_state_mean','mean'),log1p_resid_mean=('log1p_resid','mean'),log1p_resid_sd=('log1p_resid','std')).reset_index()

# Weighted regression helpers.
def weighted_slope(x,y,w):
    x=np.asarray(x,float); y=np.asarray(y,float); w=np.asarray(w,float)
    m=np.isfinite(x)&np.isfinite(y)&np.isfinite(w)&(w>0); x=x[m]; y=y[m]; w=w[m]
    if len(x)<3:return np.nan
    sw=w.sum(); xm=np.sum(w*x)/sw; ym=np.sum(w*y)/sw; den=np.sum(w*(x-xm)**2)
    return float(np.sum(w*(x-xm)*(y-ym))/den) if den>1e-12 else np.nan

def weighted_quad(x,y,w):
    x=np.asarray(x,float); y=np.asarray(y,float); w=np.asarray(w,float)
    m=np.isfinite(x)&np.isfinite(y)&np.isfinite(w)&(w>0); x=x[m]; y=y[m]; w=w[m]
    if len(x)<5:return (np.nan,np.nan)
    X=np.column_stack([np.ones(len(x)),x,x*x]); sw=np.sqrt(w)
    b=np.linalg.lstsq(X*sw[:,None],y*sw,rcond=None)[0]
    return float(b[1]),float(b[2])

def two_way_boot_slope(df,ycol,reps=5000,seed=SEED,quad=False):
    players=pd.Categorical(df.player_id).codes; origins=pd.Categorical(df.origin).codes
    np_=players.max()+1; no=origins.max()+1; rng=np.random.default_rng(seed); vals=[]
    x=df.source_percentile.to_numpy(float)-.5; y=df[ycol].to_numpy(float)
    for _ in range(reps):
        w=rng.exponential(1,np_)[players]*rng.exponential(1,no)[origins]
        vals.append(weighted_quad(x,y,w)[1] if quad else weighted_slope(x,y,w))
    a=np.asarray(vals,float); q=np.nanquantile(a,[.025,.5,.975])
    return float(np.nanmean(a)),float(q[0]),float(q[2]),float(np.nanmean(a>0))

# State-specific responses, origin stability, LOO and player influence.
state_resp=[]; origin_slopes=[]; loo_rows=[]; player_influence=[]
for s in STATES:
    g=active[active.target_state==s].copy(); x=g.source_percentile-.5
    slope=weighted_slope(x,g.log1p_resid,np.ones(len(g)))
    bs,blo,bhi,ppos=two_way_boot_slope(g,'log1p_resid',seed=SEED+STATES.index(s)*101)
    qmean,qlo,qhi,qpos=two_way_boot_slope(g,'log1p_resid',seed=SEED+777+STATES.index(s)*101,quad=True)
    absmean,abslo,abshi,abspos=two_way_boot_slope(g,'abs_log1p_resid',seed=SEED+1777+STATES.index(s)*101)
    elig=0; same=0; sls=[]
    for o,go in g.groupby('origin'):
        span=float(go.source_percentile.max()-go.source_percentile.min()) if len(go) else 0
        sl=np.nan
        if len(go)>=5 and span>=.25:
            sl=weighted_slope(go.source_percentile-.5,go.log1p_resid,np.ones(len(go))); elig+=1
            if np.sign(sl)==np.sign(slope): same+=1
            sls.append(sl)
        origin_slopes.append({'state':s,'origin':int(o),'n':len(go),'unique_players':go.player_id.nunique(),'pct_span':span,'slope':sl,'mean_log1p_resid':float(go.log1p_resid.mean())})
    loos=[]
    for o in sorted(g.origin.unique()):
        q=g[g.origin!=o]; sl=weighted_slope(q.source_percentile-.5,q.log1p_resid,np.ones(len(q))); loos.append(sl); loo_rows.append({'state':s,'omit_origin':int(o),'slope':sl})
    pinf=[]
    for p in g.player_id.unique():
        q=g[g.player_id!=p]
        if len(q)>=5: pinf.append(weighted_slope(q.source_percentile-.5,q.log1p_resid,np.ones(len(q))))
    state_resp.append({'state':s,'n':len(g),'pooled_slope':slope,'bootstrap_slope_mean':bs,'slope_ci_low':blo,'slope_ci_high':bhi,'bootstrap_p_positive':ppos,'quadratic_coef_mean':qmean,'quadratic_ci_low':qlo,'quadratic_ci_high':qhi,'eligible_origin_slopes':elig,'origin_same_sign_share':same/elig if elig else np.nan,'origin_slope_median':float(np.nanmedian(sls)) if sls else np.nan,'origin_slope_min':float(np.nanmin(sls)) if sls else np.nan,'origin_slope_max':float(np.nanmax(sls)) if sls else np.nan,'loo_slope_min':float(np.nanmin(loos)),'loo_slope_max':float(np.nanmax(loos)),'loo_sign_flip':bool(any(np.sign(v)!=np.sign(slope) for v in loos if np.isfinite(v))),'player_loo_slope_min':float(np.nanmin(pinf)),'player_loo_slope_max':float(np.nanmax(pinf)),'player_loo_sign_flip':bool(any(np.sign(v)!=np.sign(slope) for v in pinf if np.isfinite(v))),'abs_resid_slope_mean':absmean,'abs_resid_slope_ci_low':abslo,'abs_resid_slope_ci_high':abshi,'residual_sd':float(g.log1p_resid.std())})
state_resp=pd.DataFrame(state_resp)
origin_slopes=pd.DataFrame(origin_slopes); loo_rows=pd.DataFrame(loo_rows)

# Partial pooling: canonical economic grouping upper vs lower positive states.
group_rows=[]; group_origin=[]; group_loo=[]
for grp in ['upper','lower']:
    g=active[active.pool_group==grp].copy(); slope=weighted_slope(g.source_percentile-.5,g.log1p_resid,np.ones(len(g)))
    bm,bl,bh,pp=two_way_boot_slope(g,'log1p_resid',seed=SEED+3000+(0 if grp=='upper' else 1))
    for o,go in g.groupby('origin'):
        sl=weighted_slope(go.source_percentile-.5,go.log1p_resid,np.ones(len(go)))
        group_origin.append({'group':grp,'origin':int(o),'n':len(go),'slope':sl})
    loos=[]
    for o in sorted(g.origin.unique()):
        q=g[g.origin!=o]; sl=weighted_slope(q.source_percentile-.5,q.log1p_resid,np.ones(len(q))); loos.append(sl); group_loo.append({'group':grp,'omit_origin':int(o),'slope':sl})
    group_rows.append({'group':grp,'states':'starter,premium,elite' if grp=='upper' else 'depth,usable','n':len(g),'unique_players':g.player_id.nunique(),'pooled_slope':slope,'bootstrap_slope_mean':bm,'slope_ci_low':bl,'slope_ci_high':bh,'bootstrap_p_positive':pp,'origin_same_sign_share':np.mean(np.sign([r['slope'] for r in group_origin if r['group']==grp])==np.sign(slope)),'loo_slope_min':float(np.min(loos)),'loo_slope_max':float(np.max(loos))})
group_rows=pd.DataFrame(group_rows); group_origin=pd.DataFrame(group_origin); group_loo=pd.DataFrame(group_loo)

# Two-way bootstrap the lower-upper slope difference directly.
rng=np.random.default_rng(SEED+4000); players=pd.Categorical(active.player_id).codes; origins=pd.Categorical(active.origin).codes; np_=players.max()+1; no=origins.max()+1
idxu=np.where(active.pool_group.to_numpy()=='upper')[0]; idxl=np.where(active.pool_group.to_numpy()=='lower')[0]
diffs=[]
for _ in range(5000):
    w=rng.exponential(1,np_)[players]*rng.exponential(1,no)[origins]
    su=weighted_slope(active.source_percentile.to_numpy()[idxu]-.5,active.log1p_resid.to_numpy()[idxu],w[idxu]); sl=weighted_slope(active.source_percentile.to_numpy()[idxl]-.5,active.log1p_resid.to_numpy()[idxl],w[idxl]); diffs.append(sl-su)
diffs=np.asarray(diffs); dq=np.quantile(diffs,[.025,.5,.975])
# origin-specific difference
piv=group_origin.pivot(index='origin',columns='group',values='slope'); piv['lower_minus_upper']=piv['lower']-piv['upper']; piv=piv.reset_index()
# LOO difference
pl=group_loo.pivot(index='omit_origin',columns='group',values='slope'); pl['lower_minus_upper']=pl['lower']-pl['upper']; pl=pl.reset_index()
partial=pd.DataFrame([{'contrast':'lower_minus_upper_slope','bootstrap_mean':float(diffs.mean()),'ci_low':float(dq[0]),'ci_high':float(dq[2]),'p_negative':float(np.mean(diffs<0)),'origins_negative':int((piv.lower_minus_upper<0).sum()),'origins_total':len(piv),'origin_diff_min':float(piv.lower_minus_upper.min()),'origin_diff_max':float(piv.lower_minus_upper.max()),'loo_diff_min':float(pl.lower_minus_upper.min()),'loo_diff_max':float(pl.lower_minus_upper.max()),'loo_sign_flip':bool((pl.lower_minus_upper>=0).any())}])

# Pairwise within-group slope contrast uncertainty (shows why fully separate curves are not identified).
pair_rows=[]
# reuse state bootstrap arrays with consistent draws for pair contrasts
rng=np.random.default_rng(SEED+5000); players=pd.Categorical(active.player_id).codes; origins=pd.Categorical(active.origin).codes; np_=players.max()+1; no=origins.max()+1
state_indices={s:np.where(active.target_state.to_numpy()==s)[0] for s in STATES}; boots={s:[] for s in STATES}
for _ in range(5000):
    w=rng.exponential(1,np_)[players]*rng.exponential(1,no)[origins]
    for s,idx in state_indices.items(): boots[s].append(weighted_slope(active.source_percentile.to_numpy()[idx]-.5,active.log1p_resid.to_numpy()[idx],w[idx]))
for a,b in [('elite','premium'),('elite','starter'),('premium','starter'),('usable','depth')]:
    d=np.asarray(boots[a])-np.asarray(boots[b]); q=np.quantile(d,[.025,.5,.975]); pair_rows.append({'state_a':a,'state_b':b,'slope_diff_mean':float(d.mean()),'ci_low':float(q[0]),'ci_high':float(q[2]),'distinguishable':bool(q[0]>0 or q[2]<0)})
pairwise=pd.DataFrame(pair_rows)

# Scale diagnostics: magnitude dependence of absolute residual, plus state baseline dispersion.
scale=state_resp[['state','n','residual_sd','abs_resid_slope_mean','abs_resid_slope_ci_low','abs_resid_slope_ci_high']].copy()
scale['magnitude_dependent_scale_supported']=(scale.abs_resid_slope_ci_low>0)|(scale.abs_resid_slope_ci_high<0)

# State ordering constraint analysis from frozen D1 means.
mean_cols=['d1_mean_depth','d1_mean_usable','d1_mean_starter','d1_mean_premium','d1_mean_elite']
a=base[mean_cols].to_numpy(float); ratio=a[:,1:]/np.where(a[:,:-1]>0,a[:,:-1],np.nan)
ordering=pd.DataFrame({'boundary':['depth<usable','usable<starter','starter<premium','premium<elite'],'min_D1_ratio':np.nanmin(ratio,axis=0),'p01_D1_ratio':np.nanquantile(ratio,.01,axis=0),'median_D1_ratio':np.nanmedian(ratio,axis=0)})

# Cross-position bounded context. Only supported dev/established D1 routes.
def add_resid(df):
    q=df[df.target_state!='out'].copy(); q['d1_state_mean']=q.apply(lambda r:r[f'd1_mean_{r.target_state}'],axis=1); q['log1p_resid']=np.log1p(q.target_points)-np.log1p(q.d1_state_mean); q['pool_group']=np.where(q.target_state.isin(list(UPPER)),'upper','lower'); return q
h3=add_resid(hist[(hist.horizon==3)&hist.source_season.between(2014,2022)])
cross=[]
for (p,st),g in h3[(h3.position.isin(['QB','WR','TE']))&(h3.career_stage.isin(['developmental','established']))].groupby(['position','career_stage']):
    up=g[g.pool_group=='upper']; lo=g[g.pool_group=='lower']
    if len(up)<20 or len(lo)<20: continue
    su=weighted_slope(up.source_percentile-.5,up.log1p_resid,np.ones(len(up))); sl=weighted_slope(lo.source_percentile-.5,lo.log1p_resid,np.ones(len(lo)))
    # origin contrast signs
    dif=[]
    for o in sorted(g.source_season.unique()):
        gu=up[up.source_season==o]; gl=lo[lo.source_season==o]
        if len(gu)>=5 and len(gl)>=5:
            a1=weighted_slope(gu.source_percentile-.5,gu.log1p_resid,np.ones(len(gu))); a2=weighted_slope(gl.source_percentile-.5,gl.log1p_resid,np.ones(len(gl))); dif.append(a2-a1)
    cross.append({'position':p,'career_stage':st,'active_n':len(g),'upper_n':len(up),'lower_n':len(lo),'upper_slope':su,'lower_slope':sl,'lower_minus_upper':sl-su,'eligible_origin_contrasts':len(dif),'negative_contrast_share':float(np.mean(np.asarray(dif)<0)) if dif else np.nan})
cross=pd.DataFrame(cross)

# Future candidate boundary in prose/JSON: no fitting.
future={
 'status':'FEASIBILITY_ONLY_NOT_FIT',
 'recommended_family':'partial_pooling_two_group_location_calibration',
 'continuous_coordinate':'source_percentile centered continuously; no percentile thresholds as states or fitting strata',
 'state_pooling':{
   'upper_group':['starter','premium','elite'],
   'lower_group':['depth','usable'],
   'rationale':'upper-vs-lower magnitude-slope contrast is negative in all 9 origins and clustered CI excludes zero; within-group pairwise state-slope contrasts do not exclude zero'
 },
 'minimum_structure':'global bounded continuous log-multiplier curve plus one regularized lower-group intercept deviation and one regularized lower-group magnitude-slope deviation; upper group is reference. No independent five-state curves.',
 'regularization':'L2/shrinkage on lower-group deviations toward the shared curve; exact penalty must be preregistered before fitting and must not be tuned to 2026 or tail slices.',
 'ordering_constraint':'preserve D1 state order by using a common multiplier within each group and constrain lower-group multiplier <= upper-group multiplier across u; within-group ordering is inherited from D1.',
 'scale':'do not add magnitude-dependent scale in the first challenger; this feasibility study finds no state with clustered evidence of systematic residual-scale change versus magnitude. State-level dispersion differs and should remain a reported uncertainty diagnostic.',
 'parameters_per_origin':['shared curve intercept','shared curve continuous-magnitude slope','lower-group intercept deviation','lower-group continuous-magnitude slope deviation'],
 'frozen_probabilities':True,
 'prospective_confirmation':'source-2023 -> target-2026 remains untouched'
}

promotion={
 'full_cell_proper_score':'CRPS improvement or preservation with player/source-year clustered CI and >=6/9 origins improved; no LOO sign reversal',
 'continuous_calibration':'integrated magnitude-conditioned calibration error improves overall and separately in upper/lower state groups',
 'state_specific':'upper/lower conditional-production calibration must improve without reversing state ordering',
 'mae_no_harm':'raw-point MAE guardrail and source_percentile<0.75 no-harm',
 'temporal':'origin-level stability, moving source-year block bootstrap, LOO robustness, most-influential player/origin diagnostics',
 'distribution':'valid probabilities; coherent ordered positive-state supports; coverage reported',
 'probabilities':'D1 state probabilities remain unchanged',
 'tails':'p75/p90/p95 secondary diagnostics only',
 'prospective':'source-2023 -> target-2026 evaluated only after complete 2026 outcomes'
}

classification={
 'classification':'B. PARTIAL-POOLING STRUCTURE IS IDENTIFIABLE, FULL STATE-SPECIFIC CURVES ARE NOT',
 'basis':[
   'All five positive states are observed in all nine origins, but individual state samples are modest (73-127 active rows) and independent magnitude-slope signs are unstable for elite, premium, starter, and usable; depth alone shows a clearly negative clustered slope but remains sparse.',
   'A canonical economic pooling into upper states (starter/premium/elite) and lower states (usable/depth) is strongly supported: lower-minus-upper slope difference is negative in all 9 origins, remains negative under every leave-one-origin-out check, and has a two-way clustered bootstrap 95% interval below zero.',
   'Within-group pairwise state-slope contrasts have intervals spanning zero, so five independent curves would manufacture precision not supported by the history.',
   'Residual dispersion differs substantially by state, but no state shows a clustered magnitude-dependent residual-scale slope excluding zero; a first future challenger need not jointly parameterize scale.',
   'The proposed future challenger is therefore a shared continuous curve plus a regularized lower-state deviation, with frozen D1 state probabilities and state-ordering constraints. It is specified only as a later candidate boundary and is not fit here.'
 ],
 'production_authority_changed':False,'challenger_fit':False,'pr147_modified':False,'main_modified':False,'merge':False,'deploy':False
}

# Persist outputs.
support_origin.to_csv(OUT/'STATE_BY_ORIGIN_SUPPORT_MATRIX.csv',index=False)
support.to_csv(OUT/'STATE_SUPPORT_SUMMARY.csv',index=False)
coverage.to_csv(OUT/'MAGNITUDE_COVERAGE_BY_STATE.csv',index=False)
state_resp.to_csv(OUT/'STATE_SPECIFIC_MAGNITUDE_RESPONSE.csv',index=False)
origin_slopes.to_csv(OUT/'ORIGIN_STATE_RESPONSE_SLOPES.csv',index=False)
loo_rows.to_csv(OUT/'LEAVE_ONE_ORIGIN_OUT_STATE_RESPONSE.csv',index=False)
pd.DataFrame(pair_rows).to_csv(OUT/'WITHIN_GROUP_STATE_CONTRASTS.csv',index=False)
group_rows.to_csv(OUT/'PARTIAL_POOLING_GROUP_RESPONSE.csv',index=False)
piv.to_csv(OUT/'PARTIAL_POOLING_ORIGIN_CONTRAST.csv',index=False)
pl.to_csv(OUT/'PARTIAL_POOLING_LEAVE_ONE_ORIGIN_OUT.csv',index=False)
partial.to_csv(OUT/'PARTIAL_POOLING_IDENTIFIABILITY.csv',index=False)
scale.to_csv(OUT/'RESIDUAL_SCALE_FEASIBILITY.csv',index=False)
ordering.to_csv(OUT/'STATE_ORDERING_CONSTRAINT_ANALYSIS.csv',index=False)
cross.to_csv(OUT/'CROSS_POSITION_STATE_HETEROGENEITY_CONTEXT.csv',index=False)
(OUT/'MINIMUM_VIABLE_FUTURE_CHALLENGER.json').write_text(json.dumps(future,indent=2))
(OUT/'FUTURE_PROMOTION_GATES.json').write_text(json.dumps(promotion,indent=2))
(OUT/'FINAL_CLASSIFICATION.json').write_text(json.dumps(classification,indent=2))

parity_manifest={
 'schema_version':'fsffl-dev-rb-y3-state-specific-feasibility-v1',
 'starting_research_head':'ca43806782898ff4050a4e067fed8fccfcaf1cde',
 'historical_predictions_sha256':hashlib.sha256(HIST.read_bytes()).hexdigest(),
 'row_level_stage_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
 'panel_sha256':hashlib.sha256(PANEL.read_bytes()).hexdigest(),
 'canonical_eval_rows':int(len(base)),'active_eval_rows':int(len(active)),'origins':sorted(map(int,base.origin.unique())),
 'merge_indicator':merged._merge.value_counts().to_dict(),'max_abs_parity_diff':parity,
 'parity_pass':bool((merged._merge=='both').all() and max(parity.values())<1e-10),
 'state_counts':active.target_state.value_counts().to_dict(),
 'challenger_fit':False,'production_authority_change':False,'pr147_change':False,'main_change':False,'merge':False,'deploy':False
}
(OUT/'PROVENANCE_PARITY_MANIFEST.json').write_text(json.dumps(parity_manifest,indent=2))

method='''# FSFFL NEXT - State-specific magnitude identifiability / feasibility method\n\nThis stage does not fit a Forecast challenger. It analyzes the exact frozen D1 Y3 developmental-RB walk-forward coordinate.\n\nPrimary response diagnostic is log1p(realized target points) - log1p(frozen D1 mean for the realized positive future state), regressed descriptively on continuous source percentile. State-specific slopes use player x source-year Bayesian bootstrap uncertainty. Origin-level slopes require at least 5 realized-state rows and source-percentile span >=0.25. Leave-one-origin-out and leave-one-player-out influence are reported.\n\nPartial-pooling feasibility is tested on the canonical economic ordering only: upper positive states = starter/premium/elite; lower positive states = depth/usable. This grouping is not based on p90 signs or a source-magnitude threshold. Evidence for pooling is the continuous lower-minus-upper magnitude-response contrast, its clustered uncertainty, origin recurrence, and leave-one-origin-out stability. Within-group state contrasts are also reported; intervals spanning zero argue against separate curves.\n\nResidual-scale feasibility uses the absolute log1p residual versus continuous magnitude with the same clustered uncertainty. A future candidate is not required to parameterize magnitude-dependent scale unless this relationship is supported.\n\nEffective support is reported as nominal N, unique players, Kish ESS by repeated-player counts, Kish ESS by origin counts, magnitude coverage, and repeated-player concentration.\n'''
(OUT/'FEASIBILITY_METHOD.md').write_text(method)

conclusion=f'''# Final research conclusion\n\n{classification['classification']}\n\nThe history supports a partial-pooling response, not five independent state curves. Across the canonical 2014-2022 Y3 developmental-RB coordinate, all five positive states are represented in every origin, but state-level samples remain modest. Individual elite/premium/starter slopes are not separately identified; usable is directionally negative but uncertain; depth is negative but sparse.\n\nThe economically coherent upper-vs-lower grouping is materially more stable. Upper states (starter/premium/elite) have a pooled magnitude slope near flat/slightly positive, while lower states (usable/depth) have a negative slope. The lower-minus-upper contrast is negative in all nine origins, survives every leave-one-origin-out check, and has a clustered interval below zero. Pairwise differences inside the upper group and inside the lower group do not exclude zero, so independent five-state curves would overstate precision.\n\nResidual dispersion is state-dependent but does not show a reliable magnitude trend within any state under clustered uncertainty. The minimum viable later challenger can therefore be location-first: a shared continuous magnitude curve plus a regularized lower-state deviation, with D1 probabilities frozen and explicit state-ordering constraints. No challenger was fit in this task.\n'''
(OUT/'FINAL_RESEARCH_CONCLUSION.md').write_text(conclusion)
print('wrote',len(list(OUT.iterdir())),'files to',OUT)
print(json.dumps(classification,indent=2))
print('\npartial pooling',partial.to_dict(orient='records')[0])