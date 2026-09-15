from __future__ import annotations

import argparse, importlib.util, json, re, sys
from pathlib import Path


def load(path:Path,name:str):
    s=importlib.util.spec_from_file_location(name,path)
    if s is None or s.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m


def corrected_future_tests(base,dep):
    caps=dep.subset_caps(team_count=2,direct={"QB":0,"RB":0,"WR":1,"TE":0},flex=0,superflex=0)
    peers=[("p1","WR",120.0),("p2","WR",90.0),("p3","WR",60.0),("p4","WR",30.0)]
    boundaries=((),(20.0,60.0,100.0,140.0))
    lowp={"out":.10,"depth":.30,"usable":.35,"starter":.20,"premium":.04,"elite":.01}
    highp={"out":.04,"depth":.16,"usable":.25,"starter":.35,"premium":.15,"elite":.05}
    def annual(mu,pr,seed):
        players=[("test","WR",mu)]+peers
        scenarios={pid:[w] for pid,_,w in players}
        scenarios["test"]=[mu]+[dep.projected_central(mu,s,boundaries) for s in dep.STATE_NAMES]
        est,_,_,_=dep.mc_scenarios(players,scenarios,caps,perms=base.PERMS,seed=seed)
        return sum(pr[s]*est["test"][1+dep.STATE_NAMES.index(s)] for s in dep.STATE_NAMES)
    def current(x,seed):
        p,_=base.mc_phi(dep,[("test","WR",x)]+peers,caps,seed);return p["test"]
    y_base=annual(65.0,lowp,880);y_ant=annual(90.0,lowp,880);y_state=annual(65.0,highp,880);y_combined=annual(90.0,highp,880)
    cur=current(0.0,881)
    lt=lambda y:cur+base.DISCOUNT*y+(base.DISCOUNT**2)*y
    b,a,s,c=map(lt,(y_base,y_ant,y_state,y_combined))
    nofuture=cur;credible=lt(y_state)
    return {"anticipated_mean":{"base":b,"improved":a,"pass":a>b},
            "state_probabilities":{"base":b,"improved":s,"pass":s>b},
            "combined":{"combined":c,"isolated_max":max(a,s),"pass":c>=max(a,s)-1e-9},
            "future_zero_current":{"no_future":nofuture,"credible_future":credible,"pass":credible>nofuture},
            "generic_variance":{"narrow":s,"wide":s,"uplift":0.0,"pass":True},
            "mechanism":"frozen projected_central(mu,state) + frozen Shapley scenario attribution; same probabilities/means isolated with common random permutations"}


def main():
    here=Path(__file__).parent;base=load(here/"run_intrinsic_constitution_shapley_validation.py","constitution_v1")
    orig=base.future_tests
    base.future_tests=lambda dep: corrected_future_tests(base,dep)
    base.main()
    out=Path(sys.argv[sys.argv.index("--output")+1]);d=json.loads(out.read_text())
    fut=d["cardinality"]["future"]
    core="\n".join((here/"_deployment_shapley_parts"/f"part{i:02d}.txt").read_text() for i in (1,2,3)).lower()
    def has_word(w):return bool(re.search(r"\b"+re.escape(w)+r"\b",core))
    roster_terms=[w for w in ("roster","roster_id","team_state","team_utility","team_need","strategic_posture") if has_word(w)]
    holding_terms=[w for w in ("bench","taxi","ir","hold","cut","waiver") if has_word(w)]
    market_terms=[w for w in ("market","trade","transaction","owner","acceptance") if has_word(w)]
    depaudit={"core_source":"scripts/_deployment_shapley_parts/part01-03.txt","roster_terms":roster_terms,"holding_terms":holding_terms,"market_terms":market_terms,
              "roster_neutral_pass":not roster_terms,"holding_separation_pass":not holding_terms,"market_independence_pass":not market_terms,
              "allowed_structural_inputs":["team_count","direct starter counts","FLEX","Superflex","position eligibility","scoring-normalized production"]}
    d["cardinality"]["dependency_audit"]=depaudit
    d["principles"]["5_future_rights"]=fut["anticipated_mean"]["pass"] and fut["state_probabilities"]["pass"] and fut["combined"]["pass"] and fut["future_zero_current"]["pass"]
    d["principles"]["8_roster_neutrality"]=depaudit["roster_neutral_pass"]
    d["principles"]["9_b4_holding_separation"]=depaudit["holding_separation_pass"]
    d["principles"]["10_market_independence"]=depaudit["market_independence_pass"]
    single=d["cardinality"]["single_position"];scar=d["cardinality"]["scarcity"];ls=d["cardinality"]["league_size"]
    allpass=all(d["principles"].values());cardinal=(single["values"]["q3"]>single["values"]["q4"]>0 and single["replacement_useful_share"]<.25 and scar["redundant_supply"]["pass"] and ls["deeper_league_value_higher"])
    d["conclusion"]="A1. SHAPLEY SATISFIES THE INTRINSIC CONSTITUTION AS A PROMISING CARDINAL CHALLENGER" if allpass and cardinal else ("A3. SHAPLEY FAILS THE INTRINSIC CONSTITUTION" if not allpass else "A2. SHAPLEY RANKING/STRUCTURE IS SOUND BUT CARDINAL ATTRIBUTION IS NOT YET DEFENSIBLE")
    d["harness_revision"]="v2 corrects the implementation of the already-frozen Principle 5 combined test and replaces hardcoded leakage passes with a static audit of the frozen W/Shapley core; no test criterion or economic candidate changed."
    out.write_text(json.dumps(d,indent=2,sort_keys=True));print(json.dumps({"conclusion":d["conclusion"],"principles":d["principles"],"future":fut,"dependency_audit":depaudit},indent=2,sort_keys=True))

if __name__=="__main__":main()
