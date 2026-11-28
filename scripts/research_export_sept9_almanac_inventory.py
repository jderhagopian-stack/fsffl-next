"""Export a compact exact 2026-09-09 roster/pick ledger for editorial review.

The ledger is sourced from the fixed pre-kickoff Sleeper Git archive
plus the completed public transaction journal. No private Supabase rows.
Travis Hunter remains on BING BONG DRIGSY. Output is not a projection.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.research_frozen_2026_hybrid_simulation import (
    ARCHIVE_COMMIT, load_pinned_sources, assemble_vintage_state_and_forecasts
)
from scripts.research_2026_sept9_reconstruction import AS_OF, reconstruct_sept9_sources


def export():
    base=load_pinned_sources()
    corrected, receipt=reconstruct_sept9_sources(base)
    state, forecasts, coverage=assemble_vintage_state_and_forecasts(corrected,state_as_of=AS_OF)
    users={str(u["user_id"]):u for u in corrected["data/users.json"]}
    user_team={str(row["roster_id"]):str(row.get("owner_id")) for row in corrected["data/rosters.json"]}
    player_by_id={p.player_id:p for p in state.players}
    states={x.player_id:x for x in state.player_states}
    picks={p.pick_id:p for p in state.draft_picks}
    ownership={}
    for row in state.pick_ownership:
        if row.pick_id in ownership:
            raise ValueError("pick ownership duplicate")
        ownership[row.pick_id]=row.owner_team_id
    all_ids=set()
    teams=[]
    for team in sorted(state.team_states,key=lambda t:int(t.team_id.rsplit(":",1)[-1])):
        rid=str(int(team.team_id.rsplit(":",1)[-1]))
        user=users.get(user_team.get(rid,""),{})
        name=(user.get("metadata") or {}).get("team_name") or user.get("display_name") or f"Team {rid}"
        members=[]
        for entry in team.roster:
            if entry.player_id in all_ids:raise ValueError("duplicate roster player in export")
            all_ids.add(entry.player_id)
            p=player_by_id.get(entry.player_id)
            if p is None: raise ValueError(f"roster player has no identity: {entry.player_id}")
            ps=states.get(entry.player_id)
            members.append({
                "id":p.player_id,
                "name":p.full_name or p.player_id,
                "position":p.position.value,
                "nfl_team":p.nfl_team,
                "slot":entry.slot.value,
                "age_years":getattr(ps,"age_years",None),
            })
        order={"QB":0,"RB":1,"WR":2,"TE":3}
        slot_order={"QB":0,"RB":1,"WR":1,"TE":1,"FLEX":2,"SUPERFLEX":2,"BENCH":3,"IR":4,"TAXI":5}
        members.sort(key=lambda p:(order.get(p["position"],9),slot_order.get(p["slot"],6),p["name"].casefold()))
        owned_picks=[]
        for key,owner in ownership.items():
            if owner!=team.team_id:continue
            pick=picks[key]
            owned_picks.append({
                "id":key,"season":pick.season,"round":pick.round,
                "original_team_id":pick.original_team_id,
                "original_roster_id":int(pick.original_team_id.rsplit(":",1)[-1]),
            })
        owned_picks.sort(key=lambda x:(x["season"],x["round"],x["original_roster_id"]))
        teams.append({
            "roster_id":int(rid),"team_id":team.team_id,
            "team_name":" ".join(str(name).split()),
            "owner_display_name":user.get("display_name"),
            "players":members,
            "picks":owned_picks,
            "position_counts":dict(Counter(p["position"] for p in members)),
            "slot_counts":dict(Counter(p["slot"] for p in members)),
        })
    if len(all_ids)!=238 or len(ownership)!=108 or len(teams)!=12:
        raise ValueError(f"unexpected exact State  {len(all_ids)}/{len(ownership)}/{len(teams)}")
    if not any(p["id"]=="sleeper:player:12530" and p["slot"]=="BENCH"
               for t in teams if t["roster_id"]==11 for p in t["players"]):
        raise ValueError("Hunter exact roster regression")
    return {
        "status":"verified_reconstructed_sept9_source_ledger",
        "as_of":AS_OF.isoformat(),
        "source_git_commit":ARCHIVE_COMMIT,
        "rostered_players":len(all_ids),"future_picks":len(ownership),
        "teams":teams,
        "source_receipt":{
            "transaction_count":receipt["transactions_applied"],
            "archive_subset_membership_sha256":receipt["sha256_archived_subset_player_ownership"],
            "archive_subset_roster_slots_sha256":receipt["sha256_archived_subset_player_roster_slots"],
            "future_picks_sha256":receipt["sha256_future_picks"],
            "archive_analytics_coverage_defects":receipt["archived_analytics_coverage_defects"],
        },
        "limits":["Preseason reconstructed historical inventory, not full player-forecast coverage",
                  "Preseason external-source licensing restricted to personal research",
                  "Source player-status fields are historical evidence, not an injury prediction"],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=export()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("VERIFIED_ROSTER_EXPORT",result["rostered_players"],result["future_picks"])
    for t in result["teams"]:
        print(f'{t["roster_id"]:2d} {t["team_name"][:23]:23s} {len(t["players"]):2d} players {len(t["picks"]):2d} picks')
if __name__=="__main__":
    main()
