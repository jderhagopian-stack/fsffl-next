from __future__ import annotations

import argparse, json, math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from fsffl.forecast.integrated_i1 import fit_state_boundaries, state_for_points, age_band, experience_band
from fsffl.state.models import Position

POSITIONS=("QB","RB","WR","TE")
HORIZONS=(1,2,3)
MIN_SOURCE_SEASON=2005
MAX_SOURCE_SEASON=2022


def pos_enum(p:str)->Position:
    return Position[p]


def safe_mean(v):
    a=np.asarray(list(v),dtype=float)
    a=a[np.isfinite(a)]
    return float(a.mean()) if len(a) else float('nan')


def ols_cluster(y, X, cluster):
    y=np.asarray(y,dtype=float); X=np.asarray(X,dtype=float); cluster=np.asarray(cluster)
    ok=np.isfinite(y) & np.all(np.isfinite(X),axis=1)
    y=y[ok]; X=X[ok]; cluster=cluster[ok]
    if len(y)<40 or X.shape[1]==0 or np.nanstd(X[:, -1])<1e-8:
        return {"n":int(len(y)),"coef":None,"se":None,"ci_low":None,"ci_high":None,"p":None}
    Xc=sm.add_constant(X,has_constant='add')
    model=sm.OLS(y,Xc).fit()
    try:
        rob=model.get_robustcov_results(cov_type='cluster',groups=cluster)
    except Exception:
        rob=model.get_robustcov_results(cov_type='HC3')
    idx=Xc.shape[1]-1
    coef=float(rob.params[idx]); se=float(rob.bse[idx]); p=float(rob.pvalues[idx])
    return {"n":int(len(y)),"coef":coef,"se":se,"ci_low":coef-1.96*se,"ci_high":coef+1.96*se,"p":p}


def spearman_ci(x,y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    ok=np.isfinite(x)&np.isfinite(y); x=x[ok]; y=y[ok]
    if len(x)<30 or np.nanstd(x)<1e-8 or np.nanstd(y)<1e-8:
        return {"n":int(len(x)),"rho":None,"p":None}
    r,p=stats.spearmanr(x,y)
    return {"n":int(len(x)),"rho":float(r),"p":float(p)}


def exact_age_bin(position, age):
    if not np.isfinite(age): return "unknown"
    a=int(math.floor(age))
    if position=="QB":
        if a<=25: return "<=25"
        if a<=31: return "26-31"
        if a<=34: return "32-34"
        if a<=37: return "35-37"
        if a<=40: return "38-40"
        return "41+"
    else:
        if a<=23: return "<=23"
        if a<=27: return "24-27"
        if a<=29: return "28-29"
        if a<=31: return "30-31"
        return "32+"


def lookup_empirical(table_counts, keys, min_n=30):
    for key in keys:
        vals=table_counts.get(key)
        if vals is not None and vals[0]>=min_n:
            return vals[1]/vals[0], vals[0], key
    for key in keys:
        vals=table_counts.get(key)
        if vals is not None and vals[0]>0:
            return vals[1]/vals[0], vals[0], key
    return float('nan'),0,None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--panel',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--rows-output',required=True)
    args=ap.parse_args()

    df=pd.read_csv(args.panel)
    df=df[df.position.isin(POSITIONS)].copy()
    df['season']=df.season.astype(int)
    df['fantasy_points']=pd.to_numeric(df.fantasy_points,errors='coerce').fillna(0.0)
    df['age_years']=pd.to_numeric(df.age_years,errors='coerce')
    df['experience_years']=pd.to_numeric(df.experience_years,errors='coerce').fillna(0).astype(int)
    df['role_band']=df.role_band.fillna('unknown')
    df['opportunity_per_game']=pd.to_numeric(df.opportunity_per_game,errors='coerce')
    key_to_idx={(str(r.player_id),int(r.season)):i for i,r in df.iterrows()}
    by_season={int(s):g.copy() for s,g in df.groupby('season')}
    max_data_season=int(df.season.max())

    source_info={}
    cutoff_cache={}
    for t in range(MIN_SOURCE_SEASON-1, MAX_SOURCE_SEASON+1):
        prior=df[df.season<t]
        if prior.empty: continue
        bounds={}; state_stats={}
        for p in POSITIONS:
            vals=prior.loc[(prior.position==p)&(prior.fantasy_points>0),'fantasy_points'].tolist()
            if len(vals)<20: continue
            b=fit_state_boundaries(vals); bounds[p]=b
            pp=prior[prior.position==p].copy()
            pp['state']=[state_for_points(v,b) for v in pp.fantasy_points]
            for st,g in pp.groupby('state'):
                arr=g.fantasy_points.to_numpy(dtype=float)
                mu=float(arr.mean()); sd=float(arr.std(ddof=1)) if len(arr)>1 else 0.0
                if sd<1e-6: sd=max(1.0,abs(mu)*0.25)
                state_stats[(p,st)]=(len(arr),mu,sd)
        cutoff_cache[t]=(bounds,state_stats)
        cur=by_season.get(t)
        if cur is None: continue
        for _,r in cur.iterrows():
            p=r.position
            if p not in bounds: continue
            st=state_for_points(float(r.fantasy_points),bounds[p])
            stat=state_stats.get((p,st))
            if not stat or stat[0]<10: continue
            n,mu,sd=stat
            z=(float(r.fantasy_points)-mu)/sd
            ab=age_band(pos_enum(p), float(r.age_years) if np.isfinite(r.age_years) else None)
            eb=experience_band(int(r.experience_years))
            source_info[(str(r.player_id),t)]={
                'position':p,'state':st,'state_mean':mu,'state_sd':sd,'resid_z':float(z),
                'age_band':ab,'exp_band':eb,'exp_cap':min(15,int(r.experience_years)),
                'role_band':r.role_band,'age':float(r.age_years) if np.isfinite(r.age_years) else np.nan,
                'experience':int(r.experience_years),'points':float(r.fantasy_points),
            }

    eval_rows=[]
    for t in range(MIN_SOURCE_SEASON,MAX_SOURCE_SEASON+1):
        cur=by_season.get(t)
        if cur is None or t not in cutoff_cache: continue
        bounds,state_stats=cutoff_cache[t]
        horizon_targets={}
        survival_tables={}
        for h in HORIZONS:
            target_stats=defaultdict(list)
            count_tables=defaultdict(lambda:[0,0])
            hist=df[df.season<=t-h]
            for _,sr in hist.iterrows():
                p=sr.position
                if p not in bounds: continue
                sst=state_for_points(float(sr.fantasy_points),bounds[p])
                ab=age_band(pos_enum(p), float(sr.age_years) if np.isfinite(sr.age_years) else None)
                eb=experience_band(int(sr.experience_years)); ec=min(15,int(sr.experience_years))
                target_idx=key_to_idx.get((str(sr.player_id),int(sr.season)+h))
                present=target_idx is not None
                keys=[(p,sst,ab,ec,h),(p,sst,ab,eb,h),(p,sst,ab,h),(p,sst,h),(p,h)]
                for k in keys:
                    count_tables[k][0]+=1; count_tables[k][1]+=int(present)
                if present:
                    tr=df.loc[target_idx]
                    tst=state_for_points(float(tr.fantasy_points),bounds[p])
                    target_stats[(p,tst)].append(float(tr.fantasy_points))
            target_summary={}
            for k,vals in target_stats.items():
                a=np.asarray(vals,dtype=float); mu=float(a.mean()); sd=float(a.std(ddof=1)) if len(a)>1 else 0.0
                if sd<1e-6: sd=max(1.0,abs(mu)*0.25)
                target_summary[k]=(len(a),mu,sd)
            horizon_targets[h]=target_summary; survival_tables[h]=count_tables

        for _,r in cur.iterrows():
            pid=str(r.player_id); info=source_info.get((pid,t))
            if not info: continue
            prior_info=source_info.get((pid,t-1))
            prior_z=np.nan
            if prior_info is not None and prior_info['position']==info['position']:
                prior_z=prior_info['resid_z']
            streak2='insufficient'
            if np.isfinite(prior_z):
                if prior_z>0 and info['resid_z']>0: streak2='over'
                elif prior_z<0 and info['resid_z']<0: streak2='under'
                else: streak2='mixed'
            avg2=(prior_z+info['resid_z'])/2 if np.isfinite(prior_z) else np.nan
            terminal3=np.nan
            if t+3<=max_data_season:
                any_future=any((pid,t+j) in key_to_idx for j in (1,2,3))
                terminal3=float(not any_future)

            for h in HORIZONS:
                if t+h>max_data_season: continue
                p=info['position']; sst=info['state']; ab=info['age_band']; eb=info['exp_band']; ec=info['exp_cap']
                expected_surv,ntrain,scope=lookup_empirical(survival_tables[h],[(p,sst,ab,ec,h),(p,sst,ab,eb,h),(p,sst,ab,h),(p,sst,h),(p,h)],min_n=30)
                target_idx=key_to_idx.get((pid,t+h)); present=target_idx is not None
                target_points=0.0; target_state='missing'; target_z=np.nan; target_role='missing'; role_loss=np.nan
                if present:
                    tr=df.loc[target_idx]; target_points=float(tr.fantasy_points); target_role=tr.role_band
                    target_state=state_for_points(target_points,bounds[p])
                    ts=horizon_targets[h].get((p,target_state))
                    if ts and ts[0]>=10:
                        target_z=(target_points-ts[1])/ts[2]
                    if info['role_band']=='established' and target_role in ('weak','established'):
                        role_loss=float(target_role=='weak')
                eval_rows.append({
                    'source_season':t,'player_id':pid,'position':p,'horizon':h,
                    'age':info['age'],'age_floor':math.floor(info['age']) if np.isfinite(info['age']) else np.nan,
                    'age_band':ab,'exact_age_bin':exact_age_bin(p,info['age']),
                    'experience':info['experience'],'exp_band':eb,'exp_cap':ec,
                    'source_state':sst,'source_points':info['points'],'current_resid_z':info['resid_z'],
                    'prior_resid_z':prior_z,'avg2_resid_z':avg2,'streak2':streak2,
                    'source_role_band':info['role_band'],'target_present':int(present),'expected_survival':expected_surv,
                    'survival_train_n':ntrain,'survival_scope':str(scope),'survival_resid':int(present)-expected_surv if np.isfinite(expected_surv) else np.nan,
                    'target_points':target_points,'target_state':target_state,'target_resid_z':target_z,
                    'target_role_band':target_role,'role_loss':role_loss,'terminal_nonreturn_3y':terminal3,
                })

    ev=pd.DataFrame(eval_rows)
    Path(args.rows_output).parent.mkdir(parents=True,exist_ok=True)
    ev.to_csv(args.rows_output,index=False)

    results={
        'study':'future-state-resolution-phase2-empirical-v1',
        'status':'PHASE 2 DIAGNOSTIC ONLY — NO CHALLENGER DESIGNED OR TUNED',
        'source_seasons':[MIN_SOURCE_SEASON,MAX_SOURCE_SEASON],
        'horizons':[1,2,3],
        'rows':int(len(ev)),
        'definitions':{
            'within_state_residual':'source fantasy points minus the position/state mean estimated only from seasons before the source season, divided by the corresponding historical state SD',
            'target_residual':'realized target fantasy points minus the PIT horizon/position/realized-state mean, conditional on a target production row being present',
            'persistence':'target-season production row present; missing row is not treated as confirmed retirement',
            'role_loss':'source role established and target row present but target contemporaneous opportunity band is weak',
            'terminal_nonreturn_3y':'no production row in any of the next three seasons; a retirement/career-end proxy, not a transaction-level retirement label',
        },
        'q1_within_state_residual':{},'q2_age_experience':{},'q3_repeated_residual':{},'limitations':[]
    }

    q1={}
    for p in POSITIONS:
        q1[p]={}
        for stage in ('young','prime','aging'):
            q1[p][stage]={}
            for h in HORIZONS:
                g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==h)&ev.target_resid_z.notna()]
                sp=spearman_ci(g.current_resid_z,g.target_resid_z)
                ol=ols_cluster(g.target_resid_z, g[['current_resid_z']].to_numpy(), g.source_season.to_numpy())
                q1[p][stage][str(h)]={'spearman':sp,'slope':ol,'mean_current_z':safe_mean(g.current_resid_z),'mean_target_z':safe_mean(g.target_resid_z)}
        q1[p]['all']={}
        for h in HORIZONS:
            g=ev[(ev.position==p)&(ev.horizon==h)&ev.target_resid_z.notna()]
            q1[p]['all'][str(h)]={'spearman':spearman_ci(g.current_resid_z,g.target_resid_z),'slope':ols_cluster(g.target_resid_z,g[['current_resid_z']].to_numpy(),g.source_season.to_numpy())}
    results['q1_within_state_residual']=q1

    q2={'age_slopes':{},'extreme_age_bins':{},'experience_cap':{}}
    for p in POSITIONS:
        q2['age_slopes'][p]={}; q2['extreme_age_bins'][p]={}
        for stage in ('young','prime','aging'):
            q2['age_slopes'][p][stage]={}
            for h in HORIZONS:
                g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==h)&ev.age.notna()&ev.survival_resid.notna()].copy()
                if len(g):
                    age_center=g.age-g.age.mean()
                    X=np.column_stack([g.current_resid_z.to_numpy(),g.exp_cap.to_numpy(),age_center.to_numpy()])
                    surv=ols_cluster(g.survival_resid,X,g.source_season)
                    ga=g[g.target_resid_z.notna()].copy()
                    if len(ga):
                        age_center2=ga.age-ga.age.mean()
                        X2=np.column_stack([ga.current_resid_z.to_numpy(),ga.exp_cap.to_numpy(),age_center2.to_numpy()])
                        prod=ols_cluster(ga.target_resid_z,X2,ga.source_season)
                    else: prod={'n':0,'coef':None,'se':None,'ci_low':None,'ci_high':None,'p':None}
                else:
                    surv=prod={'n':0,'coef':None,'se':None,'ci_low':None,'ci_high':None,'p':None}
                q2['age_slopes'][p][stage][str(h)]={'survival_residual_per_age_year':surv,'conditional_target_z_per_age_year':prod}
        for h in HORIZONS:
            bins={}
            gp=ev[(ev.position==p)&(ev.horizon==h)]
            for b,g in gp.groupby('exact_age_bin'):
                if b=='unknown': continue
                active=g.target_present.mean() if len(g) else np.nan
                exp=g.expected_survival.mean() if len(g) else np.nan
                gz=g[g.target_resid_z.notna()]
                bins[str(b)]={'n':int(len(g)),'active_rate':float(active),'expected_active_rate':float(exp),'active_gap':float(active-exp),'active_target_z_mean':safe_mean(gz.target_resid_z),'active_target_z_n':int(len(gz))}
            q2['extreme_age_bins'][p][str(h)]=bins
        q2['experience_cap'][p]={}
        for h in HORIZONS:
            g=ev[(ev.position==p)&(ev.horizon==h)&(ev.experience>=15)&ev.survival_resid.notna()].copy()
            if len(g):
                extra=(g.experience-15).to_numpy(dtype=float)
                X=np.column_stack([g.current_resid_z.to_numpy(),g.age.fillna(g.age.median()).to_numpy(),extra])
                surv=ols_cluster(g.survival_resid,X,g.source_season)
                ga=g[g.target_resid_z.notna()].copy()
                if len(ga):
                    extra2=(ga.experience-15).to_numpy(dtype=float)
                    X2=np.column_stack([ga.current_resid_z.to_numpy(),ga.age.fillna(ga.age.median()).to_numpy(),extra2])
                    prod=ols_cluster(ga.target_resid_z,X2,ga.source_season)
                else: prod={'n':0,'coef':None,'se':None,'ci_low':None,'ci_high':None,'p':None}
            else: surv=prod={'n':0,'coef':None,'se':None,'ci_low':None,'ci_high':None,'p':None}
            q2['experience_cap'][p][str(h)]={'survival_residual_per_year_beyond_15':surv,'conditional_target_z_per_year_beyond_15':prod}
    results['q2_age_experience']=q2

    q3={'incremental_prior_residual':{},'streaks':{},'terminal_nonreturn_3y':{}}
    for p in POSITIONS:
        q3['incremental_prior_residual'][p]={}; q3['streaks'][p]={}; q3['terminal_nonreturn_3y'][p]={}
        for stage in ('young','prime','aging'):
            q3['incremental_prior_residual'][p][stage]={}; q3['streaks'][p][stage]={}
            for h in HORIZONS:
                g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==h)&ev.prior_resid_z.notna()].copy()
                surv=ols_cluster(g.survival_resid, g[['current_resid_z','prior_resid_z']].to_numpy(), g.source_season)
                ga=g[g.target_resid_z.notna()]
                prod=ols_cluster(ga.target_resid_z, ga[['current_resid_z','prior_resid_z']].to_numpy(), ga.source_season)
                gr=g[g.role_loss.notna()]
                role=ols_cluster(gr.role_loss, gr[['current_resid_z','prior_resid_z']].to_numpy(), gr.source_season)
                q3['incremental_prior_residual'][p][stage][str(h)]={'survival_prior_z_coef':surv,'conditional_production_prior_z_coef':prod,'role_loss_prior_z_coef':role}
                streak={}
                for lab,gg in g[g.streak2.isin(['over','mixed','under'])].groupby('streak2'):
                    gz=gg[gg.target_resid_z.notna()]; rr=gg[gg.role_loss.notna()]
                    streak[lab]={'n':int(len(gg)),'active_rate':float(gg.target_present.mean()),'expected_active_rate':float(gg.expected_survival.mean()),'survival_gap':float((gg.target_present-gg.expected_survival).mean()),'active_target_z_mean':safe_mean(gz.target_resid_z),'active_target_z_n':int(len(gz)),'role_loss_rate':safe_mean(rr.role_loss),'role_loss_n':int(len(rr))}
                q3['streaks'][p][stage][str(h)]=streak
            g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==1)&ev.prior_resid_z.notna()&ev.terminal_nonreturn_3y.notna()].copy()
            term=ols_cluster(g.terminal_nonreturn_3y,g[['current_resid_z','prior_resid_z']].to_numpy(),g.source_season)
            groups={}
            for lab,gg in g[g.streak2.isin(['over','mixed','under'])].groupby('streak2'):
                groups[lab]={'n':int(len(gg)),'terminal_nonreturn_rate':float(gg.terminal_nonreturn_3y.mean())}
            q3['terminal_nonreturn_3y'][p][stage]={'prior_z_coef':term,'streaks':groups}
    results['q3_repeated_residual']=q3

    results['limitations']=[
        'The source contains production and usage, not transaction-level retirement declarations; terminal non-return is therefore a career-end proxy, not a confirmed retirement label.',
        'A missing target production row is evaluated separately from conditional production and is not automatically called retirement.',
        'Exact-age and repeated-residual regressions are diagnostic association tests only; they are not candidate model specifications and no coefficient is promoted or tuned.',
        'Early seasons have less prior evidence; empirical expectations use a fixed minimum-support fallback hierarchy.',
        'Role loss is defined by a contemporaneous within-position opportunity band, not depth-chart or snap-route evidence.'
    ]

    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(results,indent=2,sort_keys=True))
    print(json.dumps({'rows':len(ev),'source_seasons':[int(ev.source_season.min()),int(ev.source_season.max())],'positions':ev.position.value_counts().to_dict()},indent=2))

if __name__=='__main__': main()
