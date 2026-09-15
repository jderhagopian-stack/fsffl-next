from __future__ import annotations

import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path


def read_panel(path: Path):
    rows=[]
    with path.open(newline="",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "player_id":r["player_id"],"season":int(r["season"]),"position":r["position"],
                "points":float(r["fantasy_points"] or 0),"age":float(r["age_years"]) if r.get("age_years") else None,
            })
    return rows


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--career-panel",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    rows=read_panel(a.career_panel);by={(r["player_id"],r["season"]):r for r in rows};seasons=sorted({r["season"] for r in rows});max_season=max(seasons)
    by_player=defaultdict(list)
    for r in rows:by_player[r["player_id"]].append(r["season"])
    for pid in by_player:by_player[pid].sort()
    total=Counter();by_pos=defaultdict(Counter);examples=[]
    for r in rows:
        for h in (1,2):
            target=r["season"]+h
            if target>max_season:
                total["edge_censored"]+=1;by_pos[r["position"]]["edge_censored"]+=1;continue
            total["eligible"]+=1;by_pos[r["position"]]["eligible"]+=1
            nxt=by.get((r["player_id"],target))
            if nxt is not None:
                key="present_zero" if nxt["points"]<=0 else "present_positive"
            else:
                later=[s for s in by_player[r["player_id"]] if s>target]
                if later:
                    key="missing_then_later_return"
                    if len(examples)<50:examples.append({"player_id":r["player_id"],"source_season":r["season"],"target_season":target,"position":r["position"],"next_observed_season":later[0]})
                else:
                    # No later production row is observed. This is persistent panel absence through available history,
                    # not proof of retirement, release, injury, suspension, or career death.
                    key="missing_no_later_row"
            total[key]+=1;by_pos[r["position"]][key]+=1
    def norm(c):
        e=c.get("eligible",0)
        return {k:{"n":int(v),"share_of_eligible":(v/e if e and k!="eligible" and k!="edge_censored" else None)} for k,v in sorted(c.items())}
    payload={
      "panel_seasons":{"min":min(seasons),"max":max_season},
      "semantics":{
        "present_zero":"target-season row exists with explicit zero fantasy production; distinct from missing row",
        "present_positive":"target-season row exists with positive fantasy production",
        "missing_then_later_return":"target row absent but a later-season production row is observed; temporary panel absence is historically observable as a label diagnostic only",
        "missing_no_later_row":"target row absent and no later row is observed through available history; persistent panel absence, but panel alone cannot prove NFL roster exit/career death versus injury, suspension, source missingness, or other causes",
        "edge_censored":"target season lies beyond observed panel history; never a disappearance label"
      },
      "overall":norm(total),"by_position":{p:norm(c) for p,c in sorted(by_pos.items())},"later_return_examples":examples,
      "predictor_leakage_rule":"later return is outcome/diagnostic evidence only and is never used as a predictor"
    }
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2,sort_keys=True));print(json.dumps(payload["overall"],indent=2))
if __name__=="__main__":main()
