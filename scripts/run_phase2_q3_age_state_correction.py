from __future__ import annotations

import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from fsffl.forecast.integrated_i1 import fit_state_boundaries, state_for_points, age_band
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
    return float(a.mean()) if len(a) else float("nan")


def ols_cluster(y, X, cluster):
    y=np.asarray(y,dtype=float); X=np.asarray(X,dtype=float); cluster=np.asarray(cluster)
    ok=np.isfinite(y) & np.all(np.isfinite(X),axis=1)
    y=y[ok]; X=X[ok]; cluster=cluster[ok]
    if len(y)<40 or X.shape[1]==0 or np.nanstd(X[:,-1])<1e-8:
        return {"n":int(len(y)),"coef":None,"se":None,"ci_low":None,"ci_high":None,"p":None}
    Xc=sm.add_constant(X,has_constant="add")
    model=sm.OLS(y,Xc).fit()
    try:
        rob=model.get_robustcov_results(cov_type="cluster",groups=cluster)
    except Exception:
        rob=model.get_robustcov_results(cov_type="HC3")
    idx=Xc.shape[1]-1
    coef=float(rob.params[idx]); se=float(rob.bse[idx]); p=float(rob.pvalues[idx])
    return {"n":int(len(y)),"coef":coef,"se":se,"ci_low":coef-1.96*se,"ci_high":coef+1.96*se,"p":p}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--panel",required=True)
    ap.add_argument("--base-rows",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--rows-output",required=True)
    args=ap.parse_args()

    panel=pd.read_csv(args.panel)
    panel=panel[panel.position.isin(POSITIONS)].copy()
    panel["season"]=panel.season.astype(int)
    panel["fantasy_points"]=pd.to_numeric(panel.fantasy_points,errors="coerce").fillna(0.0)
    panel["age_years"]=pd.to_numeric(panel.age_years,errors="coerce")
    panel["experience_years"]=pd.to_numeric(panel.experience_years,errors="coerce").fillna(0).astype(int)
    by_season={int(s):g.copy() for s,g in panel.groupby("season")}

    age_state_info={}
    fallback_rows=0
    total_rows=0
    for t in range(MIN_SOURCE_SEASON-1,MAX_SOURCE_SEASON+1):
        prior=panel[panel.season<t]
        cur=by_season.get(t)
        if prior.empty or cur is None:
            continue
        bounds={}; state_stats={}; age_state_stats={}
        for p in POSITIONS:
            vals=prior.loc[(prior.position==p)&(prior.fantasy_points>0),"fantasy_points"].tolist()
            if len(vals)<20:
                continue
            b=fit_state_boundaries(vals); bounds[p]=b
            pp=prior[prior.position==p].copy()
            pp["state"]=[state_for_points(v,b) for v in pp.fantasy_points]
            pp["age_band"]=[
                age_band(pos_enum(p),float(a) if np.isfinite(a) else None)
                for a in pp.age_years
            ]
            for st,g in pp.groupby("state"):
                arr=g.fantasy_points.to_numpy(dtype=float)
                mu=float(arr.mean()); sd=float(arr.std(ddof=1)) if len(arr)>1 else 0.0
                if sd<1e-6: sd=max(1.0,abs(mu)*0.25)
                state_stats[(p,st)]=(len(arr),mu,sd)
            for (ab,st),g in pp.groupby(["age_band","state"]):
                arr=g.fantasy_points.to_numpy(dtype=float)
                mu=float(arr.mean()); sd=float(arr.std(ddof=1)) if len(arr)>1 else 0.0
                if sd<1e-6: sd=max(1.0,abs(mu)*0.25)
                age_state_stats[(p,ab,st)]=(len(arr),mu,sd)

        for _,r in cur.iterrows():
            p=r.position
            if p not in bounds:
                continue
            st=state_for_points(float(r.fantasy_points),bounds[p])
            ab=age_band(pos_enum(p),float(r.age_years) if np.isfinite(r.age_years) else None)
            stat=state_stats.get((p,st))
            if stat is None or stat[0]<10:
                continue
            astat=age_state_stats.get((p,ab,st))
            if astat is not None and astat[0]>=10:
                _n,mu,sd=astat; scope="position_age_band_state"
            else:
                _n,mu,sd=stat; scope="position_state_fallback"; fallback_rows+=1
            z=(float(r.fantasy_points)-mu)/sd
            age_state_info[(str(r.player_id),t)]=(float(z),scope)
            total_rows+=1

    ev=pd.read_csv(args.base_rows)
    current=[]; prior=[]; scopes=[]; streaks=[]
    for r in ev.itertuples(index=False):
        key=(str(r.player_id),int(r.source_season))
        pkey=(str(r.player_id),int(r.source_season)-1)
        c=age_state_info.get(key); pr=age_state_info.get(pkey)
        cz=float(c[0]) if c else np.nan
        pz=float(pr[0]) if pr else np.nan
        current.append(cz); prior.append(pz); scopes.append(c[1] if c else "missing")
        if np.isfinite(cz) and np.isfinite(pz):
            if cz>0 and pz>0: streaks.append("over")
            elif cz<0 and pz<0: streaks.append("under")
            else: streaks.append("mixed")
        else:
            streaks.append("insufficient")
    ev["current_age_state_resid_z"]=current
    ev["prior_age_state_resid_z"]=prior
    ev["age_state_residual_scope"]=scopes
    ev["streak2_age_state"]=streaks

    q3={"incremental_prior_residual":{},"streaks":{},"terminal_nonreturn_3y":{}}
    for p in POSITIONS:
        q3["incremental_prior_residual"][p]={}; q3["streaks"][p]={}; q3["terminal_nonreturn_3y"][p]={}
        for stage in ("young","prime","aging"):
            q3["incremental_prior_residual"][p][stage]={}; q3["streaks"][p][stage]={}
            for h in HORIZONS:
                g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==h)&ev.prior_age_state_resid_z.notna()].copy()
                surv=ols_cluster(g.survival_resid,g[["current_age_state_resid_z","prior_age_state_resid_z"]].to_numpy(),g.source_season)
                ga=g[g.target_resid_z.notna()]
                prod=ols_cluster(ga.target_resid_z,ga[["current_age_state_resid_z","prior_age_state_resid_z"]].to_numpy(),ga.source_season)
                gr=g[g.role_loss.notna()]
                role=ols_cluster(gr.role_loss,gr[["current_age_state_resid_z","prior_age_state_resid_z"]].to_numpy(),gr.source_season)
                q3["incremental_prior_residual"][p][stage][str(h)]={
                    "survival_prior_age_state_z_coef":surv,
                    "conditional_production_prior_age_state_z_coef":prod,
                    "role_loss_prior_age_state_z_coef":role,
                }
                streak={}
                for lab,gg in g[g.streak2_age_state.isin(["over","mixed","under"])].groupby("streak2_age_state"):
                    gz=gg[gg.target_resid_z.notna()]; rr=gg[gg.role_loss.notna()]
                    streak[lab]={
                        "n":int(len(gg)),
                        "active_rate":float(gg.target_present.mean()),
                        "expected_active_rate":float(gg.expected_survival.mean()),
                        "survival_gap":float((gg.target_present-gg.expected_survival).mean()),
                        "active_target_z_mean":safe_mean(gz.target_resid_z),
                        "active_target_z_n":int(len(gz)),
                        "role_loss_rate":safe_mean(rr.role_loss),
                        "role_loss_n":int(len(rr)),
                    }
                q3["streaks"][p][stage][str(h)]=streak
            g=ev[(ev.position==p)&(ev.age_band==stage)&(ev.horizon==1)&ev.prior_age_state_resid_z.notna()&ev.terminal_nonreturn_3y.notna()].copy()
            term=ols_cluster(g.terminal_nonreturn_3y,g[["current_age_state_resid_z","prior_age_state_resid_z"]].to_numpy(),g.source_season)
            groups={}
            for lab,gg in g[g.streak2_age_state.isin(["over","mixed","under"])].groupby("streak2_age_state"):
                groups[lab]={"n":int(len(gg)),"terminal_nonreturn_rate":float(gg.terminal_nonreturn_3y.mean())}
            q3["terminal_nonreturn_3y"][p][stage]={"prior_age_state_z_coef":term,"streaks":groups}

    result={
        "study":"future-state-resolution-phase2-q3-age-state-correction-v1",
        "status":"PHASE 2 DIAGNOSTIC ONLY — Q3 DEFINITION COMPLIANCE CORRECTION; NO CHALLENGER DESIGNED OR TUNED",
        "definition":"Repeated over/under-performance is measured against a point-in-time position x current-I1-age-band x current-state production mean. Cells with <10 earlier observations use the point-in-time position x state mean.",
        "source_seasons":[MIN_SOURCE_SEASON,MAX_SOURCE_SEASON],
        "fallback_source_season_rows":int(fallback_rows),
        "age_state_source_season_rows":int(total_rows),
        "q3_repeated_age_state_residual":q3,
        "limitations":[
            "This correction changes only Q3 residual normalization. Q1 within-state residual and Q2 age/experience diagnostics remain those from the frozen core run.",
            "The age adjustment uses the current frozen I1 coarse age bands; it does not design a new age representation.",
            "Terminal non-return means no production row in any of the next three seasons and is not a transaction-level retirement label."
        ]
    }
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    ev.to_csv(args.rows_output,index=False)
    print(json.dumps({"rows":int(len(ev)),"q3_usable":int(ev.prior_age_state_resid_z.notna().sum()),"fallback_source_rows":int(fallback_rows)},indent=2))


if __name__=="__main__":
    main()
