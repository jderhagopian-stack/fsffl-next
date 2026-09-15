from __future__ import annotations

import importlib.util
import json
import math
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from fsffl.forecast.current_runtime import build_current_live_forecasts
from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.state.models import League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState, PlayerStatus, Position, Provenance, ProviderRef, RosterSlot, ScoringRule, Team, TeamState
from fsffl.value.intrinsic_economics import production_rank_relevance
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

DISCOUNT = 0.85
A_CONT = {"QB":3.04477622642943,"RB":4.303817924177665,"WR":6.143984964367542,"TE":5.817300974838888}
A_AGING = {("RB","veteran"):3.950333600958593,("RB","late"):2.7510651150227448,("WR","veteran"):6.004984105473204,("WR","late"):2.6770751749625927,("TE","veteran"):5.618822091672501,("TE","late"):4.858769764287097}
B_PARENT = {"QB":0.3871444919318217,"RB":0.8331440075912998,"WR":1.2203433929069816,"TE":0.524078124792527}
B_CELLS = {("QB","aging"):0.32059492902728265,("QB","prime"):0.34369566471024227,("QB","young"):0.5599666747839029,("RB","aging"):0.42266041101187035,("RB","prime"):0.6653287143434072,("RB","young"):1.6907478099955262,("WR","aging"):0.5027415706599537,("WR","prime"):1.5999515419859334,("WR","young"):1.6525176079831827,("TE","aging"):0.5661341876515611,("TE","prime"):0.5231794205960082,("TE","young"):0.4860200342662496}
C_PARENT = {"QB":0.4714590038033551,"RB":0.9081345298737987,"WR":1.3641198215259032,"TE":0.6477254555706494}
C_CELLS = {("QB","aging"):0.39233029550231113,("QB","prime"):0.4184566071885989,("QB","young"):0.6776872596969185,("RB","aging"):0.4835824105035606,("RB","prime"):0.7307863590508279,("RB","young"):1.8096968456515279,("WR","aging"):0.5869217237802054,("WR","prime"):1.7725459918425073,("WR","young"):1.8408870485582283,("TE","aging"):0.6886848722541996,("TE","prime"):0.6643267043248701,("TE","young"):0.5809375445238778}

PROFILES = [
    ("elite_young_qb","QB",24,(360.,380.,390.),"typical"),
    ("solid_starting_qb","QB",29,(285.,270.,255.),"typical"),
    ("elite_young_rb","RB",23,(330.,305.,275.),"typical"),
    ("elite_young_wr","WR",23,(285.,305.,315.),"typical"),
    ("elite_young_te","TE",23,(235.,250.,260.),"typical"),
    ("aging_productive_rb","RB",31,(260.,195.,125.),"typical"),
    ("developmental_young_wr","WR",22,(105.,155.,205.),"typical"),
    ("young_high_upside_backup_qb","QB",22,(120.,170.,220.),"high_upside"),
    ("fringe_wr","WR",27,(45.,35.,25.),"typical"),
    ("fringe_te","TE",27,(35.,30.,25.),"typical"),
]

def load_challenge():
    path=Path(__file__).with_name("run_intrinsic_marginal_franchise_challenge.py")
    spec=importlib.util.spec_from_file_location("synthetic_followup_marginal",path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def integer(v,minimum=0):
    try:x=int(v)
    except (TypeError,ValueError):return None
    return x if x>=minimum else None

def floating(v):
    try:x=float(v)
    except (TypeError,ValueError):return None
    return x if x>=0 else None

def build_state():
    now=datetime.now(UTC)
    with urlopen("https://api.sleeper.app/v1/players/nfl",timeout=30) as response: raw=json.load(response)
    prov=Provenance(source="sleeper:players:nfl:intrinsic-synthetic-followup",retrieved_at=now,effective_at=now)
    pmap={"QB":Position.QB,"RB":Position.RB,"WR":Position.WR,"TE":Position.TE};players=[];states=[]
    for external_id,r in raw.items():
        pos=pmap.get(str(r.get("position") or "").upper());team=str(r.get("team") or "").upper().strip()
        if pos is None or not team: continue
        name=str(r.get("full_name") or " ".join(filter(None,[r.get("first_name"),r.get("last_name")])) or external_id);pid=f"sleeper:player:{external_id}"
        players.append(Player(player_id=pid,full_name=name,position=pos,nfl_team=team,provider_refs=(ProviderRef(provider="sleeper",external_id=str(external_id)),)))
        states.append(PlayerState(player_id=pid,as_of=now,age_years=floating(r.get("age")),experience_years=integer(r.get("years_exp"),0),draft_year=integer(r.get("draft_year"),1900),draft_round=integer(r.get("draft_round"),1),draft_number=integer(r.get("draft_number"),1),nfl_team=team,status=PlayerStatus.ACTIVE if str(r.get("status") or "").lower()=="active" else PlayerStatus.UNKNOWN,provenance=prov))
    teams=tuple(Team(team_id=f"t{i}",league_id="syn",display_name=f"T{i}") for i in range(12));team_states=tuple(TeamState(team_id=t.team_id,roster=()) for t in teams)
    rules=LeagueRules(team_count=12,roster_size=18,lineup=(LineupRequirement(slot=RosterSlot.QB,count=1),LineupRequirement(slot=RosterSlot.RB,count=2),LineupRequirement(slot=RosterSlot.WR,count=3),LineupRequirement(slot=RosterSlot.TE,count=1),LineupRequirement(slot=RosterSlot.FLEX,count=1),LineupRequirement(slot=RosterSlot.SUPERFLEX,count=1)),scoring=(ScoringRule(stat="pass_yd",points=.04),ScoringRule(stat="pass_td",points=4),ScoringRule(stat="pass_int",points=-2),ScoringRule(stat="rush_yd",points=.1),ScoringRule(stat="rush_td",points=6),ScoringRule(stat="rec",points=.5),ScoringRule(stat="rec_yd",points=.1),ScoringRule(stat="rec_td",points=6),ScoringRule(stat="fum_lost",points=-2)))
    return LeagueState(league=League(league_id="syn",name="synthetic",season=2026,rules=rules),as_of=now,teams=teams,team_states=team_states,players=tuple(players),player_states=tuple(states),provenance=(prov,))

def age_band_b(pos,age):
    if pos=="QB": return "young" if age<=25 else ("prime" if age<=31 else "aging")
    return "young" if age<=23 else ("prime" if age<=27 else "aging")

def age_band_a(pos,age):
    if pos=="QB": return None
    return "young" if age<=23 else ("prime" if age<=26 else ("veteran" if age<=29 else "late"))

def quantile(xs,p):
    ys=sorted(xs)
    if not ys:return 0.0
    z=p*(len(ys)-1);lo=int(math.floor(z));hi=int(math.ceil(z));f=z-lo
    return ys[lo] if lo==hi else ys[lo]*(1-f)+ys[hi]*f

def main():
    ch=load_challenge();state=build_state();live=build_current_live_forecasts(state,minimum_independent_sources=2)
    state=state.model_copy(update={"as_of":live.evaluation_as_of,"player_states":tuple(ps.model_copy(update={"as_of":live.evaluation_as_of}) for ps in state.player_states)})
    bounded=build_non_qb_bounded_paths(state,season_forecasts=live.fantasy_point_forecasts);qb=build_qb_career_state_forecasts(state,season_forecasts=live.fantasy_point_forecasts)
    result=build_current_intrinsic_values_v2(state,season_forecasts=live.fantasy_point_forecasts,base_forecast_model_version=live.model_version,bounded_paths=bounded,qb_career_states=qb)
    pools={p:tuple(sorted(max(0.,e.horizons[0].forecast_mean) for e in result.estimates if e.position==p)) for p in (Position.QB,Position.RB,Position.WR,Position.TE)}
    baselines,_=ch.baselines_from_pools(pools)
    cvs={}
    for pos in (Position.QB,Position.RB,Position.WR,Position.TE):
        vals=[e for e in result.estimates if e.position==pos]
        for h in range(3):
            ratios=[e.horizons[h].forecast_stddev/max(1.,e.horizons[h].forecast_mean) for e in vals if e.horizons[h].forecast_mean>0]
            cvs[(pos.value,h,"typical")]=quantile(ratios,.50)
            cvs[(pos.value,h,"high_upside")]=quantile(ratios,.90)
    rows=[]
    for name,pos,age,means,disp in PROFILES:
        p=Position(pos);pool=pools[p];demand=next(e.structural_starter_demand for e in result.estimates if e.position==p)
        sds=tuple(means[i]*cvs[(pos,i,disp)] for i in range(3))
        acf=A_AGING.get((pos,age_band_a(pos,age)),A_CONT[pos])
        A=sum((DISCOUNT**i)*means[i]*production_rank_relevance(means[i],forecast_means=pool,starter_demand=demand) for i in range(3))
        A+=(DISCOUNT**3)*means[2]*production_rank_relevance(means[2],forecast_means=pool,starter_demand=demand)*acf
        band=age_band_b(pos,age);bcf=B_CELLS.get((pos,band),B_PARENT[pos]);ccf=C_CELLS.get((pos,band),C_PARENT[pos])
        B=sum((DISCOUNT**i)*ch.expected_marginal(means[i],sds[i],baselines[pos]) for i in range(3));B+=(DISCOUNT**3)*ch.expected_marginal(means[2],sds[2],baselines[pos])*bcf
        def c2(mu,sd):
            if sd<=1e-9:
                return (12.*ch.marginal_at_x(mu,baselines[pos])+.5*mu)/13.
            vals=[]
            for z in ch.ZNODES:
                x=max(0.,mu+sd*z);vals.append((12.*ch.marginal_at_x(x,baselines[pos])+.5*x)/13.)
            return ch.mean(vals)
        C=sum((DISCOUNT**i)*c2(means[i],sds[i]) for i in range(3));C+=(DISCOUNT**3)*c2(means[2],sds[2])*ccf
        rows.append({"profile":name,"position":pos,"age":age,"means":means,"sds":sds,"dispersion_source":"position/horizon live full-pool median CV" if disp=="typical" else "position/horizon live full-pool 90th-percentile CV","A_raw_no_pedigree":A,"B_raw":B,"C_raw":C})
    payload={"evaluation_as_of":live.evaluation_as_of.isoformat(),"full_pool_n":len(result.estimates),"sources":list(live.successful_source_ids),"failed_sources":list(live.failed_sources),"profiles":rows,"note":"A uses means because production A does not price variance into mean Intrinsic; B/C integrate each controlled Forecast distribution. No pedigree is assigned to synthetic profiles."}
    out=Path("artifacts/intrinsic-synthetic-followup");out.mkdir(parents=True,exist_ok=True);(out/"intrinsic_three_way_synthetic_followup.json").write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=="__main__":main()
