from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from fsffl.forecast.current_runtime import build_current_live_forecasts
from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.state.models import League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState, PlayerStatus, Position, Provenance, ProviderRef, RosterSlot, ScoringRule, Team, TeamState
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

TARGETS = {
    "Josh Allen", "Drake Maye", "Lamar Jackson", "Sam Darnold", "Dak Prescott",
    "Bijan Robinson", "Quinshon Judkins", "Derrick Henry", "Rhamondre Stevenson", "Tyler Allgeier", "Jonathon Brooks",
    "CeeDee Lamb", "Jaxon Smith-Njigba", "Tee Higgins", "Zay Flowers", "DeVonta Smith", "KC Concepcion", "Troy Franklin",
    "Brock Bowers", "Trey McBride", "Kyle Pitts", "Dallas Goedert", "Ja'Tavion Sanders",
}
MARGINAL_PARENT = {"QB": 0.3871444919318217, "RB": 0.8331440075912998, "WR": 1.2203433929069816, "TE": 0.524078124792527}
MARGINAL_CELLS = {
    ("QB","aging"):0.32059492902728265,("QB","prime"):0.34369566471024227,("QB","young"):0.5599666747839029,
    ("RB","aging"):0.42266041101187035,("RB","prime"):0.6653287143434072,("RB","young"):1.6907478099955262,
    ("WR","aging"):0.5027415706599537,("WR","prime"):1.5999515419859334,("WR","young"):1.6525176079831827,
    ("TE","aging"):0.5661341876515611,("TE","prime"):0.5231794205960082,("TE","young"):0.4860200342662496,
}
DISCOUNT=0.85


def load_challenge():
    path=Path(__file__).with_name("run_intrinsic_marginal_franchise_challenge.py")
    spec=importlib.util.spec_from_file_location("current_marginal_impl", path)
    if spec is None or spec.loader is None: raise RuntimeError(path)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m


def integer(value, minimum=0):
    try:v=int(value)
    except (TypeError,ValueError):return None
    return v if v>=minimum else None


def floating(value):
    try:v=float(value)
    except (TypeError,ValueError):return None
    return v if v>=0 else None


def build_state():
    now=datetime.now(UTC)
    with urlopen("https://api.sleeper.app/v1/players/nfl",timeout=30) as response: raw_players=json.load(response)
    provenance=Provenance(source="sleeper:players:nfl:current-marginal-sanity",retrieved_at=now,effective_at=now)
    positions={"QB":Position.QB,"RB":Position.RB,"WR":Position.WR,"TE":Position.TE}
    players=[];states=[]
    for external_id,raw in raw_players.items():
        pos=positions.get(str(raw.get("position") or "").upper());team=str(raw.get("team") or "").upper().strip()
        if pos is None or not team:continue
        name=str(raw.get("full_name") or " ".join(filter(None,[raw.get("first_name"),raw.get("last_name")])) or external_id)
        pid=f"sleeper:player:{external_id}"
        players.append(Player(player_id=pid,full_name=name,position=pos,nfl_team=team,provider_refs=(ProviderRef(provider="sleeper",external_id=str(external_id)),)))
        states.append(PlayerState(player_id=pid,as_of=now,age_years=floating(raw.get("age")),experience_years=integer(raw.get("years_exp"),0),draft_year=integer(raw.get("draft_year"),1900),draft_round=integer(raw.get("draft_round"),1),draft_number=integer(raw.get("draft_number"),1),nfl_team=team,status=PlayerStatus.ACTIVE if str(raw.get("status") or "").lower()=="active" else PlayerStatus.UNKNOWN,provenance=provenance))
    teams=tuple(Team(team_id=f"t{i}",league_id="sanity",display_name=f"T{i}") for i in range(12));team_states=tuple(TeamState(team_id=t.team_id,roster=()) for t in teams)
    rules=LeagueRules(team_count=12,roster_size=18,lineup=(LineupRequirement(slot=RosterSlot.QB,count=1),LineupRequirement(slot=RosterSlot.RB,count=2),LineupRequirement(slot=RosterSlot.WR,count=3),LineupRequirement(slot=RosterSlot.TE,count=1),LineupRequirement(slot=RosterSlot.FLEX,count=1),LineupRequirement(slot=RosterSlot.SUPERFLEX,count=1)),scoring=(ScoringRule(stat="pass_yd",points=.04),ScoringRule(stat="pass_td",points=4),ScoringRule(stat="pass_int",points=-2),ScoringRule(stat="rush_yd",points=.1),ScoringRule(stat="rush_td",points=6),ScoringRule(stat="rec",points=.5),ScoringRule(stat="rec_yd",points=.1),ScoringRule(stat="rec_td",points=6),ScoringRule(stat="fum_lost",points=-2)))
    return LeagueState(league=League(league_id="sanity",name="sanity",season=2026,rules=rules),as_of=now,teams=teams,team_states=team_states,players=tuple(players),player_states=tuple(states),provenance=(provenance,))


def rank_map(values):
    rows=sorted(values.items(),key=lambda kv:(kv[1],kv[0]));n=len(rows);out={}
    for i,(pid,_v) in enumerate(rows):out[pid]=(i+.5)/n
    return out


def main():
    ch=load_challenge();state=build_state();live=build_current_live_forecasts(state,minimum_independent_sources=2)
    state=state.model_copy(update={"as_of":live.evaluation_as_of,"player_states":tuple(ps.model_copy(update={"as_of":live.evaluation_as_of}) for ps in state.player_states)})
    bounded=build_non_qb_bounded_paths(state,season_forecasts=live.fantasy_point_forecasts);qb=build_qb_career_state_forecasts(state,season_forecasts=live.fantasy_point_forecasts)
    inc=build_current_intrinsic_values_v2(state,season_forecasts=live.fantasy_point_forecasts,base_forecast_model_version=live.model_version,bounded_paths=bounded,qb_career_states=qb)
    players={p.player_id:p for p in state.players};states={s.player_id:s for s in state.player_states};est={e.player_id:e for e in inc.estimates}
    pools={p:tuple(sorted(max(0.0,e.horizons[0].forecast_mean) for e in inc.estimates if e.position==p)) for p in (Position.QB,Position.RB,Position.WR,Position.TE)}
    baselines,_=ch.baselines_from_pools(pools)
    challenger={}
    for e in inc.estimates:
        pos=e.position.value;age=states.get(e.player_id).age_years if states.get(e.player_id) else None
        band=ch.age_band(pos,age);cf=MARGINAL_CELLS.get((pos,band),MARGINAL_PARENT[pos])
        base=sum((DISCOUNT**i)*ch.expected_marginal(h.forecast_mean,h.forecast_stddev,baselines[pos]) for i,h in enumerate(e.horizons))
        base+=(DISCOUNT**3)*ch.expected_marginal(e.horizons[2].forecast_mean,e.horizons[2].forecast_stddev,baselines[pos])*cf
        challenger[e.player_id]=max(0.0,base)
    apex=max(challenger.values()) or 1.0
    inc_rank=rank_map({pid:e.fundamental_value for pid,e in est.items()});chal_rank=rank_map(challenger)
    rows=[]
    for pid,e in est.items():
        p=players[pid]
        if p.full_name not in TARGETS:continue
        s=states.get(pid);means=[h.forecast_mean for h in e.horizons];sds=[h.forecast_stddev for h in e.horizons]
        rows.append({"player":p.full_name,"position":p.position.value,"age":None if s is None else s.age_years,"experience":None if s is None else s.experience_years,"y1":means[0],"y2":means[1],"y3":means[2],"forecast_sd":sds,"incumbent_raw":e.fundamental_value,"incumbent_display":e.display_value,"incumbent_rank_percentile":inc_rank[pid],"challenger_raw":challenger[pid],"challenger_display_linear_apex":round(10000*challenger[pid]/apex),"challenger_rank_percentile":chal_rank[pid],"rank_delta_percentile":chal_rank[pid]-inc_rank[pid]})
    rows.sort(key=lambda r:(-r["challenger_raw"],r["player"]))
    payload={"evaluation_as_of":live.evaluation_as_of.isoformat(),"sources":list(live.successful_source_ids),"failed_sources":list(live.failed_sources),"full_pool_n":len(inc.estimates),"challenger_current_apex_raw":apex,"challenger_display_note":"temporary linear 0-10000 normalization where current full-pool apex=10000; not a promoted production scale","rows":rows}
    out=Path("artifacts/current-marginal-sanity");out.mkdir(parents=True,exist_ok=True);(out/"current_marginal_franchise_sanity.json").write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload,indent=2,sort_keys=True))

if __name__=="__main__":main()
