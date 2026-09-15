from __future__ import annotations

import argparse, importlib.util, json, math, random, resource, statistics, sys, time
from collections import defaultdict
from pathlib import Path

BUDGETS=(128,256,512,1024,2048)
PRIMARY_BUDGET=1024
REFERENCE_BUDGET=2048
MIN_REL=5.0
DISCOUNT=0.85
SEED_BASE=20260914
POSITIONS=("QB","RB","WR","TE")


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0

def quantile(xs,p):
    xs=sorted(xs)
    if not xs:return 0.0
    z=p*(len(xs)-1);lo=int(math.floor(z));hi=int(math.ceil(z))
    if lo==hi:return xs[lo]
    f=z-lo;return xs[lo]*(1-f)+xs[hi]*f

def corr(xs,ys):
    xs=list(xs);ys=list(ys)
    if len(xs)<2:return 0.0
    mx,my=mean(xs),mean(ys);dx=[x-mx for x in xs];dy=[y-my for y in ys]
    den=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return sum(a*b for a,b in zip(dx,dy))/den if den>1e-12 else 0.0

def ranks(vals):
    order=sorted(range(len(vals)),key=lambda i:(vals[i],i));out=[0.0]*len(vals);i=0
    while i<len(order):
        j=i+1
        while j<len(order) and vals[order[j]]==vals[order[i]]:j+=1
        r=(i+j-1)/2+1
        for k in order[i:j]:out[k]=r
        i=j
    return out

def spearman(xs,ys):return corr(ranks(xs),ranks(ys)) if len(xs)>=2 else 0.0

def age_band(pos,age):
    if age is None:return "unknown"
    if pos=="QB":return "young" if age<=25 else ("prime" if age<=31 else "aging")
    return "young" if age<=23 else ("prime" if age<=27 else "aging")
def mem_mib():return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024.0


def mc_ladder(players,caps,deployment,seed):
    rng=random.Random(seed);ids=[p[0] for p in players];byid={pid:(pos,float(w)) for pid,pos,w in players}
    sums={pid:0.0 for pid in ids};sumsq={pid:0.0 for pid in ids}
    out={};t0=time.perf_counter();full=deployment.full_game_value(players,caps)
    for r in range(1,REFERENCE_BUDGET+1):
        order=ids[:];rng.shuffle(order);b=deployment.Basis(caps)
        for pid in order:
            pos,w=byid[pid];d=b.add(pid,pos,w);sums[pid]+=d;sumsq[pid]+=d*d
        if r in BUDGETS:
            est={pid:sums[pid]/r for pid in ids};se={}
            for pid in ids:
                m=est[pid];var=max(0.0,(sumsq[pid]-r*m*m)/(r-1)) if r>1 else 0.0;se[pid]=math.sqrt(var/r)
            out[r]={"est":est,"se":se,"runtime":time.perf_counter()-t0,"rss_mib":mem_mib(),
                    "full":full,"eff_resid":sum(est.values())-full}
    return out


def precision_track(examples,holdout_seasons,deployment):
    caps=deployment.subset_caps();cases=[];track_start=time.perf_counter()
    for season in holdout_seasons:
        supply=[e for e in examples if e.season==season]
        for h in (0,1,2):
            players=[(e.player_id,e.position,max(0.0,float(e.means[h]))) for e in supply]
            ladder=mc_ladder(players,caps,deployment,SEED_BASE+season*10+h)
            cases.append({"season":season,"horizon":h+1,"n":len(players),"ladder":ladder})
    metrics={}
    for b in BUDGETS:
        abs_se=[];rel_se=[];eff=[];case_runtime=[];rss=[];rel_change=[]
        prev=BUDGETS[BUDGETS.index(b)-1] if BUDGETS.index(b)>0 else None
        cohort_spearman=defaultdict(list);close_pair=[];refb=REFERENCE_BUDGET
        for c in cases:
            cur=c["ladder"][b];ref=c["ladder"][refb]
            abs_se.extend(cur["se"].values())
            for pid,v in cur["est"].items():
                if abs(v)>=MIN_REL:rel_se.append(cur["se"][pid]/abs(v))
                if prev is not None:
                    pv=c["ladder"][prev]["est"][pid]
                    if abs(v)>=MIN_REL:rel_change.append(abs(v-pv)/max(MIN_REL,abs(v)))
            eff.append(abs(cur["eff_resid"])/max(1.0,abs(cur["full"])));case_runtime.append(cur["runtime"]);rss.append(cur["rss_mib"])
            refvals=[v for v in ref["est"].values() if v>1e-12]
            if refvals:
                q20,q80=quantile(refvals,.2),quantile(refvals,.8);cohorts={"low":[],"middle":[],"top":[]}
                for pid,rv in ref["est"].items():
                    if rv<=1e-12:continue
                    co="low" if rv<=q20 else ("top" if rv>=q80 else "middle");cohorts[co].append(pid)
                for co,pids in cohorts.items():
                    if len(pids)>=3:cohort_spearman[co].append(spearman([cur["est"][p] for p in pids],[ref["est"][p] for p in pids]))
                ordered=sorted(((v,p) for p,v in ref["est"].items() if v>=MIN_REL),reverse=True)
                for (v1,p1),(v2,p2) in zip(ordered,ordered[1:]):
                    if v1>0 and abs(v1-v2)/v1<=0.10:
                        ref_sign=1 if v1>v2 else (0 if v1==v2 else -1);cv1,cv2=cur["est"][p1],cur["est"][p2];cur_sign=1 if cv1>cv2 else (0 if cv1==cv2 else -1);close_pair.append(1.0 if cur_sign==ref_sign else 0.0)
        metrics[str(b)]={
            "absolute_se":{"p50":quantile(abs_se,.5),"p90":quantile(abs_se,.9),"p95":quantile(abs_se,.95)},
            "relative_se_ge5":{"p50":quantile(rel_se,.5),"p90":quantile(rel_se,.9),"p95":quantile(rel_se,.95),"n":len(rel_se)},
            "relative_change_from_previous_ge5":None if prev is None else {"from":prev,"p50":quantile(rel_change,.5),"p90":quantile(rel_change,.9),"p95":quantile(rel_change,.95),"n":len(rel_change)},
            "rank_vs_2048":{co:{"median":quantile(v,.5),"p10":quantile(v,.1),"n_cases":len(v)} for co,v in cohort_spearman.items()},
            "close_pair_order_agreement":mean(close_pair),"close_pair_n":len(close_pair),
            "max_relative_efficiency_residual":max(eff) if eff else 0.0,"sum_case_runtime_seconds":sum(case_runtime),"max_peak_rss_mib":max(rss) if rss else 0.0}
    m=metrics[str(PRIMARY_BUDGET)];chg=m["relative_change_from_previous_ge5"]
    ranks_ok=all(m["rank_vs_2048"].get(co,{}).get("median",0)>=0.995 for co in ("top","middle","low")) and min(m["rank_vs_2048"].get(co,{}).get("median",0) for co in ("top","middle","low"))>=0.990
    statistical=(m["relative_se_ge5"]["p95"]<=0.10 and m["absolute_se"]["p95"]<=2.0 and chg and chg["p95"]<=0.10 and ranks_ok and m["close_pair_order_agreement"]>=0.90 and m["max_relative_efficiency_residual"]<=1e-8);practical=(m["sum_case_runtime_seconds"]<=1800 and m["max_peak_rss_mib"]<=7168)
    r=metrics[str(REFERENCE_BUDGET)];rchg=r["relative_change_from_previous_ge5"];rranks=all(r["rank_vs_2048"].get(co,{}).get("median",1)>=0.995 for co in ("top","middle","low"))
    refstat=(r["relative_se_ge5"]["p95"]<=0.10 and r["absolute_se"]["p95"]<=2.0 and rchg and rchg["p95"]<=0.10 and rranks and r["close_pair_order_agreement"]>=0.90 and r["max_relative_efficiency_residual"]<=1e-8);refpractical=(r["sum_case_runtime_seconds"]<=1800 and r["max_peak_rss_mib"]<=7168)
    if statistical and practical:decision="P1. SHAPLEY IS COMPUTATIONALLY PRACTICAL AT A FIXED BUDGET";selected=1024
    elif refstat and refpractical:decision="P1. SHAPLEY IS COMPUTATIONALLY PRACTICAL AT A FIXED BUDGET";selected=2048
    elif statistical or refstat:decision="P2. SHAPLEY IS COMPUTATIONALLY VALID BUT TOO EXPENSIVE FOR PRACTICAL USE";selected=1024 if statistical else 2048
    else:decision="P3. SHAPLEY REMAINS TOO UNSTABLE FOR PLAYER-LEVEL CARDINAL USE";selected=None
    return {"protocol":{"budgets":BUDGETS,"primary_budget":PRIMARY_BUDGET,"reference_budget":REFERENCE_BUDGET,"min_relative_denominator":MIN_REL},"metrics":metrics,"decision":decision,"selected_budget":selected,"wall_seconds":time.perf_counter()-track_start,"case_count":len(cases)}


def realized_season_shapley(panel,deployment,needed_seasons):
    caps=deployment.subset_caps();byseason=defaultdict(list);needed=set(needed_seasons)
    for r in panel:
        if r.position in POSITIONS and int(r.season) in needed:byseason[int(r.season)].append(r)
    out={};diag={}
    for season,rows in sorted(byseason.items()):
        players=[(r.player_id,r.position,max(0.0,float(r.points))) for r in rows];ladder=mc_ladder(players,caps,deployment,SEED_BASE+50000+season);ref=ladder[REFERENCE_BUDGET]
        for pid,v in ref["est"].items():out[(season,pid)]=v
        diag[str(season)]={"n":len(players),"runtime_seconds":ref["runtime"],"p95_se":quantile(ref["se"].values(),.95),"efficiency_residual":ref["eff_resid"]}
    return out,diag


def ols_desc(xs,ys):
    xs=list(xs);ys=list(ys)
    if len(xs)<2:return {"intercept":0.0,"slope":0.0}
    mx,my=mean(xs),mean(ys);den=sum((x-mx)**2 for x in xs);slope=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den if den>1e-12 else 0.0
    return {"intercept":my-slope*mx,"slope":slope}
def compare_metrics(rows,key,ref="target"):
    xs=[r[key] for r in rows];ys=[r[ref] for r in rows];diff=[x-y for x,y in zip(xs,ys)]
    return {"n":len(rows),"mae":mean(abs(d) for d in diff),"mean_bias":mean(diff),"median_bias":quantile(diff,.5),"pearson":corr(xs,ys),"spearman":spearman(xs,ys),"ols_y_on_x":ols_desc(xs,ys)}
def deciles(rows,key):
    ordered=sorted(rows,key=lambda r:r["target"]);n=len(ordered);out=[]
    for d in range(10):
        a=int(d*n/10);b=int((d+1)*n/10);g=ordered[a:b]
        if g:out.append({"decile":d+1,"n":len(g),"target_mean":mean(r["target"] for r in g),"value_mean":mean(r[key] for r in g),"bias":mean(r[key]-r["target"] for r in g)})
    return out
def subgroup_rows(rows):
    targets=[r["target"] for r in rows];q25,q50,q90=quantile(targets,.25),quantile(targets,.5),quantile(targets,.9);groups={p:[r for r in rows if r["position"]==p] for p in POSITIONS}
    groups.update({"elite":[r for r in rows if r["target"]>=q90],"fringe":[r for r in rows if r["target"]<=q25],"developmental":[r for r in rows if age_band(r["position"],r.get("age"))=="young" and r["target"]<q50],"young":[r for r in rows if age_band(r["position"],r.get("age"))=="young"],"prime":[r for r in rows if age_band(r["position"],r.get("age"))=="prime"],"aging":[r for r in rows if age_band(r["position"],r.get("age"))=="aging"]})
    out={}
    for name,g in groups.items():
        if not g:continue
        out[name]={"n":len(g),"forecast_shapley_mean":mean(r["forecast_shapley"] for r in g),"phi_y1_mean":mean(r.get("phi_y1",0) for r in g),"realized_h3_mean":mean(r["realized_h3"] for r in g),"realized_h6_mean":mean(r["realized_h6"] for r in g),"target_mean":mean(r["target"] for r in g),"A_mae":mean(abs(r["A"]-r["target"]) for r in g),"forecast_vs_realized_h3_mae":mean(abs(r["forecast_shapley"]-r["realized_h3"]) for r in g),"realized_h6_vs_target_mae":mean(abs(r["realized_h6"]-r["target"]) for r in g),"career_uplift_forecast_mean":mean(r["forecast_shapley"]-r.get("phi_y1",0) for r in g)}
    return out


def target_track(panel,frozen_rows,deployment):
    needed=sorted({int(r["season"])+off for r in frozen_rows for off in range(6)});phi,season_diag=realized_season_shapley(panel,deployment,needed);panel_keys={(int(r.season),r.player_id):r for r in panel};rows=[];coverage=defaultdict(int)
    for fr in frozen_rows:
        season=int(fr["season"]);pid=fr["player_id"];h3=h6=0.0;avail=0
        for off in range(6):
            if (season+off,pid) in panel_keys:avail+=1
            v=phi.get((season+off,pid),0.0)
            if off<3:h3+=(DISCOUNT**off)*v
            h6+=(DISCOUNT**off)*v
        coverage[str(avail)]+=1;rows.append({"season":season,"player_id":pid,"position":fr["position"],"age":fr.get("age"),"experience":fr.get("experience"),"target":float(fr["target"]),"A":float(fr["A"]),"Hard":float(fr["Hard"]),"forecast_shapley":float(fr["Shapley"]),"phi_y1":float(fr.get("phi_y1",0.0)),"realized_h3":h3,"realized_h6":h6,"available_future_rows":avail})
    comps={k:compare_metrics(rows,k) for k in ("forecast_shapley","realized_h3","realized_h6","A","Hard")}
    direct={"forecast_error_component":{"mae":mean(abs(r["forecast_shapley"]-r["realized_h3"]) for r in rows),"mean_signed":mean(r["forecast_shapley"]-r["realized_h3"] for r in rows),"median_signed":quantile([r["forecast_shapley"]-r["realized_h3"] for r in rows],.5),"correlation":corr([r["forecast_shapley"] for r in rows],[r["realized_h3"] for r in rows])},"horizon_component":{"mae":mean(abs(r["realized_h3"]-r["realized_h6"]) for r in rows),"mean_signed":mean(r["realized_h3"]-r["realized_h6"] for r in rows),"median_signed":quantile([r["realized_h3"]-r["realized_h6"] for r in rows],.5),"correlation":corr([r["realized_h3"] for r in rows],[r["realized_h6"] for r in rows])},"attribution_object_component":{"mae":mean(abs(r["realized_h6"]-r["target"]) for r in rows),"mean_signed":mean(r["realized_h6"]-r["target"] for r in rows),"median_signed":quantile([r["realized_h6"]-r["target"] for r in rows],.5),"correlation":corr([r["realized_h6"] for r in rows],[r["target"] for r in rows])}}
    sub=subgroup_rows(rows);tension={"fringe":sub.get("fringe",{}),"developmental":sub.get("developmental",{}),"explanation_inputs":{"full_supply_bottom_quintile_share_from_pr139":0.0051,"cohort_difference":"full-supply Y1 bottom quintile is a within-season system-share cohort; historical fringe is bottom quartile of six-year target among scored holdouts","career_aggregation":"forecast_shapley includes Y2/Y3 state-weighted gross deployment attribution; phi_y1 is reported separately"}}
    f_mae=direct["forecast_error_component"]["mae"];h_mae=direct["horizon_component"]["mae"];o_mae=direct["attribution_object_component"]["mae"]
    if comps["realized_h6"]["pearson"]>=0.50 and o_mae>max(f_mae,h_mae)*1.25:decision="T3. THE ESTABLISHED HISTORICAL TARGET IS NOT A VALID PRIMARY CARDINAL TARGET FOR THE NEW INTRINSIC DEFINITION"
    elif f_mae+h_mae>o_mae*1.5:decision="T2. FORECAST / HORIZON MISMATCH EXPLAINS MOST OF THE HISTORICAL FAILURE"
    elif o_mae>0 and (f_mae>0.5*o_mae or h_mae>0.5*o_mae):decision="T4. MIXED FAILURE"
    else:decision="T5. INSUFFICIENT EVIDENCE"
    return {"decision":decision,"metrics_vs_target":comps,"direct_components":direct,"deciles":{k:deciles(rows,k) for k in ("forecast_shapley","realized_h3","realized_h6","A")},"subgroups":sub,"coverage_future_rows":dict(coverage),"season_realized_shapley_diagnostics":season_diag,"low_end_tension":tension,"rows":rows}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--model-a-rows",type=Path,required=True);ap.add_argument("--qb-results",type=Path,required=True);ap.add_argument("--frozen-pr139-rows",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).parent;deployment=load_module(here/"run_deployment_shapley_intrinsic_research.py","decomp_deployment");legacy=load_module(here/"run_fundamental_intrinsic_residual_calibration.py","decomp_legacy");parity=load_module(here/"run_fundamental_intrinsic_production_parity.py","decomp_parity")
    examples,_=parity.build_examples(panel_path=args.career_panel,model_rows_path=args.model_a_rows,qb_results_path=args.qb_results,legacy=legacy);frozen_rows=json.loads(args.frozen_pr139_rows.read_text());panel=legacy.load_rows(args.career_panel);seasons=sorted({int(r["season"]) for r in frozen_rows});p=precision_track(examples,seasons,deployment);t=target_track(panel,frozen_rows,deployment)
    if p["decision"].startswith("P3"):final="C. SHAPLEY ECONOMICS REMAIN PLAUSIBLE BUT COMPUTATION IS THE BLOCKER" if t["decision"].startswith("T3") else "D. INSUFFICIENT EVIDENCE"
    elif p["decision"].startswith("P2"):final="C. SHAPLEY ECONOMICS REMAIN PLAUSIBLE BUT COMPUTATION IS THE BLOCKER" if t["decision"].startswith(("T2","T3")) else "D. INSUFFICIENT EVIDENCE"
    else:final="A. CONTINUE SHAPLEY RESEARCH" if t["decision"].startswith(("T2","T3")) else ("B. REJECT SHAPLEY AS THE ATTRIBUTION RULE" if t["decision"].startswith("T1") else "D. INSUFFICIENT EVIDENCE")
    target_audit={"formula":"target=sum_{offset=0..5} 0.85^offset * [(12*marginal_at_x(actual_points, actual_baseline)+0.5*actual_points)/13] for available positive realized seasons","marginal_logic":"marginal_at_x is expected max(0, actual_points - weakest eligible anonymous lineup-slot baseline); baselines are season-specific and derived from actual QB/RB/WR/TE production pools, direct slots, FLEX and Superflex","plain_english":"THE ESTABLISHED HISTORICAL TARGET MEASURES six-season discounted realized marginal deployed surplus above an anonymous weakest-eligible starter baseline, with a small raw-production floor; it is not a gross player-right value.","horizon":6,"discount":0.85,"low_end":"When marginal surplus is zero, only 0.5*x/13 = x/26 survives, so low-end production is intentionally compressed toward zero.","developmental":"Developmental value enters only if the player later realizes positive points in available future seasons; there is no ex-ante option value beyond realized future production.","position":"Position enters through eligibility and position-specific weakest-slot baseline; FLEX/Superflex alter the eligible slot layers.","continuation":"No fitted continuation is inside the target itself; it sums observed realized seasons that exist within the six-year window."}
    payload={"study":"shapley-precision-target-decomposition-v1","governance":"research-only; frozen Shapley candidate; holding=0; no market/team/owner inputs","Track_P":p,"Track_T":{k:v for k,v in t.items() if k!="rows"},"historical_target_audit":target_audit,"final_recommendation":final,"leakage":{"market":False,"league_market":False,"transactions":False,"owner":False,"actual_rosters":False,"team_needs":False,"holding":False,"rescaling":False,"new_attribution_rule":False}}
    (args.output_dir/"shapley_precision_target_decomposition.json").write_text(json.dumps(payload,indent=2,sort_keys=True));(args.output_dir/"shapley_target_decomposition_rows.json").write_text(json.dumps(t["rows"],indent=2,sort_keys=True));print(json.dumps({"Track_P":p["decision"],"Track_T":t["decision"],"final":final,"p1024":p["metrics"]["1024"],"t_components":t["direct_components"],"subgroups":t["subgroups"]},indent=2,sort_keys=True))

if __name__=="__main__":main()
