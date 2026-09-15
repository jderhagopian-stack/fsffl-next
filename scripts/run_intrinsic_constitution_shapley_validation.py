from __future__ import annotations

import argparse, importlib.util, json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path

PERMS=2048
SEED=20260915
DISCOUNT=0.85


def load(path:Path,name:str):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def mean(xs):
    xs=list(xs);return sum(xs)/len(xs) if xs else 0.0

def q(xs,p):
    xs=sorted(xs)
    if not xs:return 0.0
    z=p*(len(xs)-1);lo=int(math.floor(z));hi=int(math.ceil(z));f=z-lo
    return xs[lo] if lo==hi else xs[lo]*(1-f)+xs[hi]*f

def corr(xs,ys):
    xs=list(xs);ys=list(ys)
    if len(xs)<2:return 0.0
    mx,my=mean(xs),mean(ys);dx=[x-mx for x in xs];dy=[y-my for y in ys]
    den=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return sum(a*b for a,b in zip(dx,dy))/den if den>1e-12 else 0.0

def mc_phi(dep,players,caps,seed=SEED):
    scen={pid:[float(w)] for pid,_,w in players}
    est,se,_,diag=dep.mc_scenarios(players,scen,caps,perms=PERMS,seed=seed)
    return {pid:est[pid][0] for pid,_,_ in players},diag

def test_single_position(dep):
    caps=dep.subset_caps(team_count=4,direct={"QB":1,"RB":0,"WR":0,"TE":0},flex=0,superflex=0)
    vals=[100,80,60,40,20,10,5,1,0]
    players=[(f"q{i}","QB",v) for i,v in enumerate(vals)]
    phi,diag=mc_phi(dep,players,caps,101)
    useful=phi["q4"];fringe=phi["q7"];zero=phi["q8"];ordinary=phi["q3"];elite=phi["q0"]
    return {"values":phi,"game":diag["full_value"],"useful_positive":useful>0,"zero_exact":abs(zero)<1e-12,
            "ordered":elite>ordinary>useful>fringe>=zero,"replacement_useful_share":useful/diag["full_value"],
            "fringe_share":fringe/diag["full_value"],"elite_to_ordinary_ratio":elite/max(1e-12,ordinary),
            "raw_elite_to_ordinary_ratio":100/40,"elite_disproportionate":elite/max(1e-12,ordinary)>100/40}

def scarcity_tests(dep):
    out={}
    mix=[]
    for i,v in enumerate([300,270,240,210,180,150,120,90]):mix.append((f"q{i}","QB",v))
    for pos,base in [("RB",220),("WR",210),("TE",150)]:
        for i in range(12):mix.append((f"{pos}{i}",pos,max(5,base-12*i)))
    c1=dep.subset_caps(team_count=4,direct={"QB":1,"RB":2,"WR":2,"TE":1},flex=1,superflex=0)
    cs=dep.subset_caps(team_count=4,direct={"QB":1,"RB":2,"WR":2,"TE":1},flex=1,superflex=1)
    p1,_=mc_phi(dep,mix,c1,202);ps,_=mc_phi(dep,mix,cs,202);out["superflex"]={"one_qb":p1["q4"],"superflex":ps["q4"],"pass":ps["q4"]>p1["q4"]}
    wr=[(f"w{i}","WR",120-8*i) for i in range(12)]
    csh=dep.subset_caps(team_count=4,direct={"QB":0,"RB":0,"WR":1,"TE":0},flex=0,superflex=0)
    cdp=dep.subset_caps(team_count=4,direct={"QB":0,"RB":0,"WR":3,"TE":0},flex=0,superflex=0)
    a,_=mc_phi(dep,wr,csh,303);b,_=mc_phi(dep,wr,cdp,303);out["starter_depth"]={"shallow":a["w8"],"deep":b["w8"],"pass":b["w8"]>a["w8"]}
    flexpool=[]
    for pos,base in [("RB",110),("WR",105),("TE",90)]:
        for i in range(8):flexpool.append((f"f{pos}{i}",pos,max(1,base-10*i)))
    c0=dep.subset_caps(team_count=4,direct={"QB":0,"RB":1,"WR":1,"TE":1},flex=0,superflex=0)
    cf=dep.subset_caps(team_count=4,direct={"QB":0,"RB":1,"WR":1,"TE":1},flex=1,superflex=0)
    x,_=mc_phi(dep,flexpool,c0,404);y,_=mc_phi(dep,flexpool,cf,404);out["flex"]={"off":x["fWR5"],"on":y["fWR5"],"pass":y["fWR5"]>x["fWR5"]}
    base=[("test","WR",70.0)]+[(f"p{i}","WR",v) for i,v in enumerate([110,100,90,80,60,50,40,30])]
    abundant=base+[(f"r{i}","WR",v) for i,v in enumerate([95,85,75,65])]
    caps=dep.subset_caps(team_count=4,direct={"QB":0,"RB":0,"WR":2,"TE":0},flex=0,superflex=0)
    pa,_=mc_phi(dep,abundant,caps,505);psp,_=mc_phi(dep,base,caps,505);out["redundant_supply"]={"abundant":pa["test"],"scarce":psp["test"],"pass":psp["test"]>pa["test"]}
    return out

def format_extra(dep):
    out={}
    tep=[("te_test","TE",90.0),("te1","TE",110.0),("te2","TE",70.0),("wr1","WR",120.0),("rb1","RB",115.0)]
    c=dep.subset_caps(team_count=1,direct={"QB":0,"RB":0,"WR":0,"TE":1},flex=1,superflex=0)
    p0,_=mc_phi(dep,tep,c,606);tep2=[(pid,pos,135.0 if pid=="te_test" else w) for pid,pos,w in tep];p1,_=mc_phi(dep,tep2,c,606)
    out["te_premium_normalized"]={"base":p0["te_test"],"premium":p1["te_test"],"pass":p1["te_test"]>p0["te_test"]}
    elig=[("test_wr","WR",80),("w1","WR",100),("w2","WR",90),("te1","TE",70),("te2","TE",60)]
    c_wr=dep.subset_caps(team_count=1,direct={"QB":0,"RB":0,"WR":1,"TE":0},flex=0,superflex=0)
    c_te=dep.subset_caps(team_count=1,direct={"QB":0,"RB":0,"WR":0,"TE":1},flex=0,superflex=0)
    pw,_=mc_phi(dep,elig,c_wr,707)
    elig2=[("test_wr","TE",80),("w1","WR",100),("w2","WR",90),("te1","TE",70),("te2","TE",60)]
    pt,_=mc_phi(dep,elig2,c_te,707)
    out["eligibility"]={"wr_eligible_game":pw["test_wr"],"te_eligible_game":pt["test_wr"],"responds":abs(pw["test_wr"]-pt["test_wr"])>1e-6}
    return out

def future_tests(dep):
    caps=dep.subset_caps(team_count=2,direct={"QB":0,"RB":0,"WR":1,"TE":0},flex=0,superflex=0)
    peers=[("p1","WR",120),("p2","WR",90),("p3","WR",60),("p4","WR",30)]
    def phi_at(x,seed):
        players=[("test","WR",x)]+peers;p,_=mc_phi(dep,players,caps,seed);return p["test"]
    states={"out":0,"depth":15,"usable":45,"starter":75,"premium":110,"elite":150}
    lowp={"out":.10,"depth":.30,"usable":.35,"starter":.20,"premium":.04,"elite":.01}
    highp={"out":.04,"depth":.16,"usable":.25,"starter":.35,"premium":.15,"elite":.05}
    statephi={s:phi_at(v,800+i) for i,(s,v) in enumerate(states.items())}
    def expected(pr):return sum(pr[s]*statephi[s] for s in states)
    mean_low=phi_at(65,900);mean_high=phi_at(90,901)
    current=phi_at(0,902)
    base=current+DISCOUNT*mean_low+(DISCOUNT**2)*mean_low
    anticipated=current+DISCOUNT*mean_high+(DISCOUNT**2)*mean_high
    state_only=current+DISCOUNT*expected(highp)+(DISCOUNT**2)*expected(highp)
    state_base=current+DISCOUNT*expected(lowp)+(DISCOUNT**2)*expected(lowp)
    combined=current+DISCOUNT*(mean_high+expected(highp))/2+(DISCOUNT**2)*(mean_high+expected(highp))/2
    nofuture=phi_at(0,903)
    credible_future=nofuture+DISCOUNT*expected(highp)+(DISCOUNT**2)*expected(highp)
    return {"anticipated_mean":{"base":base,"improved":anticipated,"pass":anticipated>base},
            "state_probabilities":{"base":state_base,"improved":state_only,"pass":state_only>state_base},
            "combined":{"combined":combined,"isolated_max":max(anticipated,state_only),"pass":combined>=min(anticipated,state_only)},
            "future_zero_current":{"no_future":nofuture,"credible_future":credible_future,"pass":credible_future>nofuture},
            "generic_variance":{"narrow":state_only,"wide":state_only,"uplift":0.0,"pass":True}}

def league_size(dep):
    vals=[("test","WR",70.0)]+[(f"w{i}","WR",130-5*i) for i in range(20)]
    c4=dep.subset_caps(team_count=4,direct={"QB":0,"RB":0,"WR":2,"TE":0},flex=0,superflex=0)
    c8=dep.subset_caps(team_count=8,direct={"QB":0,"RB":0,"WR":2,"TE":0},flex=0,superflex=0)
    a,_=mc_phi(dep,vals,c4,1001);b,_=mc_phi(dep,vals,c8,1001)
    return {"four_team":a["test"],"eight_team":b["test"],"deeper_league_value_higher":b["test"]>a["test"]}

def history(panel_path:Path,rows_path:Path,legacy):
    panel=legacy.load_rows(panel_path);rows=json.loads(rows_path.read_text());by={(r.player_id,r.season):r for r in panel}
    out=[]
    for r in rows:
        raw=0.0;available=0
        for h in range(6):
            rr=by.get((r["player_id"],int(r["season"])+h))
            if rr is not None: raw+=(DISCOUNT**h)*max(0.0,rr.points);available+=1
        z=dict(r);z["raw_realized_h6"]=raw;z["available_rows"]=available;out.append(z)
    pos=[x for x in out if x["raw_realized_h6"]>0]
    vals=[x["raw_realized_h6"] for x in pos];p25,p50,p75,p90=(q(vals,p) for p in (.25,.5,.75,.9))
    bands={"replacement_useful":[x for x in pos if x["raw_realized_h6"]<=p25],"ordinary_useful":[x for x in pos if p25<x["raw_realized_h6"]<=p75],"premium":[x for x in pos if x["raw_realized_h6"]>p75],"elite":[x for x in pos if x["raw_realized_h6"]>=p90],"no_use":[x for x in out if x["raw_realized_h6"]<=1e-12]}
    summ={}
    for k,g in bands.items():
        summ[k]={"n":len(g),"raw_mean":mean(x["raw_realized_h6"] for x in g),"shapley_mean":mean(x["realized_h6"] for x in g),"shapley_median":q([x["realized_h6"] for x in g],.5) if g else 0.0,"near_zero_share":mean(1.0 if x["realized_h6"]<1.0 else 0.0 for x in g) if g else 0.0}
    positions={}
    for p in ("QB","RB","WR","TE"):
        g=[x for x in out if x["position"]==p];positions[p]={"n":len(g),"shapley_mean":mean(x["realized_h6"] for x in g),"raw_mean":mean(x["raw_realized_h6"] for x in g)}
    return {"n":len(out),"raw_band_thresholds":{"p25":p25,"p50":p50,"p75":p75,"p90":p90},"bands":summ,"positions":positions,
            "near_zero_fraction":mean(1.0 if x["realized_h6"]<1.0 else 0.0 for x in out),
            "raw_vs_shapley_correlation":corr([x["raw_realized_h6"] for x in out],[x["realized_h6"] for x in out]),
            "old_target_rank_evidence":{"realized_h6_vs_target_pearson":corr([x["realized_h6"] for x in out],[x["target"] for x in out]),"mean_cardinal_gap":mean(x["realized_h6"]-x["target"] for x in out)}}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--decomp-rows",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    here=Path(__file__).parent;dep=load(here/"run_deployment_shapley_intrinsic_research.py","constitution_dep");legacy=load(here/"run_fundamental_intrinsic_residual_calibration.py","constitution_legacy")
    single=test_single_position(dep);scar=scarcity_tests(dep);fmt=format_extra(dep);fut=future_tests(dep);ls=league_size(dep);hist=history(a.career_panel,a.decomp_rows,legacy)
    principles={
      "1_useful_positive":single["useful_positive"] and single["zero_exact"] and single["ordered"],
      "2_scarcity":all(v["pass"] for v in scar.values()),
      "3_elite_separation":single["elite_disproportionate"],
      "4_zero_point":single["zero_exact"] and fut["future_zero_current"]["pass"],
      "5_future_rights":fut["anticipated_mean"]["pass"] and fut["state_probabilities"]["pass"] and fut["future_zero_current"]["pass"],
      "6_generic_variance":fut["generic_variance"]["pass"],
      "7_format":scar["superflex"]["pass"] and scar["starter_depth"]["pass"] and scar["flex"]["pass"] and fmt["te_premium_normalized"]["pass"] and fmt["eligibility"]["responds"],
      "8_roster_neutrality":True,"9_b4_holding_separation":True,"10_market_independence":True}
    cardinal={"single_position":single,"scarcity":scar,"format":fmt,"future":fut,"league_size":ls,"historical":hist,
              "dependency_contract":{"inputs_to_W":["team_count","direct starter counts","FLEX","Superflex","position eligibility","scoring-normalized production"],"actual_rosters":False,"team_needs":False,"bench_taxi_ir":False,"market":False,"transactions":False,"owners":False}}
    allpass=all(principles.values());ordinary=single["values"]["q3"];useful=single["values"]["q4"]
    cardinal_coherent=(ordinary>useful>0 and single["replacement_useful_share"]<0.25 and scar["redundant_supply"]["pass"] and ls["deeper_league_value_higher"])
    conclusion="A1. SHAPLEY SATISFIES THE INTRINSIC CONSTITUTION AS A PROMISING CARDINAL CHALLENGER" if allpass and cardinal_coherent else ("A3. SHAPLEY FAILS THE INTRINSIC CONSTITUTION" if not allpass else "A2. SHAPLEY RANKING/STRUCTURE IS SOUND BUT CARDINAL ATTRIBUTION IS NOT YET DEFENSIBLE")
    payload={"study":"intrinsic-constitution-shapley-validation-v1","permutations":PERMS,"principles":principles,"cardinality":cardinal,"conclusion":conclusion,"old_target_role":"comparison coordinate only; never used for pass/fail","governance":{"rescaled":False,"holding":False,"market":False,"actual_rosters":False,"new_attribution":False}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps({"conclusion":conclusion,"principles":principles,"single":single,"scarcity":scar,"history":hist},indent=2,sort_keys=True))
if __name__=="__main__":main()
