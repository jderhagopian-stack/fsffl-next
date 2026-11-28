"""Report prose from dated football facts and the league's real transfer path."""
from collections import Counter
from datetime import date

from fsffl.providers.trade_report_results import player_key

# Public news facts only. No franchise, transaction or editorial judgment here.
SEASON_ENDINGS = {
    ("sleeper:player:9226", 2026): (
        date(2026,9,28), "a torn ACL",
        "https://www.nfl.com/news/dolphins-rb-devon-achane-miss-2026-season-acl-tear"),
}


def production_index(state, results):
    identities=Counter(player_key(p.full_name,p.position.value) for p in state.players)
    index={}
    for p in state.players:
        key=player_key(p.full_name,p.position.value)
        if identities[key]==1 and key in results:
            for ref in p.provider_refs:
                if ref.provider=="sleeper":
                    index[f"sleeper:player:{ref.external_id}"]=(key[1],results[key])
    return index


def side_story(move, names, season, cutoff, max_week, index, exits, label, reserves=()):
    e=move.event
    owner=names[e.roster_id]
    players=[a for a in e.acquired if a.kind=="player"]
    picks=[a for a in e.acquired if a.kind=="pick"]
    facts=[]
    performances=[]
    known_out=0
    recent = [row for row in reserves if row[1] <= max_week and
              0 < (e.occurred_at.date()-row[0]).days <= 10]
    previous = max(recent,key=lambda row:row[0],default=None)
    reserve_count = 0
    for a in players:
        name=label(a)
        injury=SEASON_ENDINGS.get((a.asset_ref,season))
        if injury and injury[0] < e.occurred_at.date():
            facts.append(f"{owner} bought {name} for next season. By trade day, {injury[1]} had already ended his year.")
            known_out+=1
            continue
        if previous and a.asset_ref in previous[2]:
            facts.append(f"{owner} took on a wait with {name}. He was on the NFL reserve list in Week {previous[1]}, before the offer.")
            reserve_count+=1
        pos,rows=index.get(a.asset_ref,("",()))
        exit_at=exits.get((e.roster_id,a.asset_ref))
        eligible=[r for r in rows if move.completed_at.date()<r[0]<cutoff.date()
                  and r[1]<=max_week and (not exit_at or r[0]<exit_at.date())]
        if not eligible:
            continue
        yards=sum(r[2] for r in eligible)
        scores=sum(r[3] for r in eligible)
        games=len(eligible)
        unit="passing" if pos=="QB" else "scrimmage"
        td_word="touchdown" if scores==1 else "touchdowns"
        description=(
            f"{name} recorded {yards:,} {unit} yards and {scores} {td_word} in {games} NFL "
            f"{'game' if games==1 else 'games'} after the deal, through Week {eligible[-1][1]}.")
        # Editorial football-production bands, separate from lineup points and dynasty prices.
        per_game=yards/games
        strong = per_game >= (250 if pos=="QB" else 85) or scores/games >= (2 if pos=="QB" else 1)
        useful = per_game >= (180 if pos=="QB" else 45) or scores/games >= (1 if pos=="QB" else .4)
        mark = "ON FIRE" if strong and games>=3 else "NICE" if strong or useful else "FAIR"
        if not useful and games>=3 and per_game < (100 if pos=="QB" else 25) and scores==0:
            mark="OOF"
        performances.append((["OOF","FAIR","NICE","ON FIRE"].index(mark),scores,yards,name,description,mark))
    fallback=None
    if performances:
        best,mark=max(performances)[-2:]
        facts.append(best)
        fallback=(mark, "This call grades the strongest NFL production in the player return. Fantasy starts are unverified.")
    elif players and known_out==len(players) and not picks:
        fallback=("OOF","The entire player return was already out for the season.")
    elif players and reserve_count==len(players):
        fallback=("TOO SOON","The return was on reserve before the offer. A post-trade payoff is still unverified.")
    if picks:
        years=sorted({a.pick_season for a in picks})
        rounds=Counter(a.pick_round for a in picks)
        parts=[f"{n} "+({1:"first",2:"second",3:"third"}.get(r,f"round-{r} pick"))+("s" if n!=1 else "")
               for r,n in sorted(rounds.items())]
        facts.append(f"{owner} took back {' and '.join(parts)} spanning {years[0]}–{years[-1]}." if len(years)>1
                     else f"{owner} took back {' and '.join(parts)} in {years[0]}.")
        if not players and all(y>season for y in years):
            fallback=("TOO SOON","Those picks buy future draft nights. Their players have yet to be selected.")
    if not fallback and not players:
        fallback=("TOO SOON","The season return depends on whom the picks or waiver money eventually bought.")
    if not fallback and move.completed_at.date()==cutoff.date():
        fallback=("TOO SOON","The deal closed today. Neither side has played a full game day since.")
    if not facts:
        assets=", ".join(label(a) for a in e.acquired) or "no incoming assets"
        facts.append(f"{owner} came away with {assets}.")
    onward=next((f"{owner} traded {label(a)} again on {exits[e.roster_id,a.asset_ref].date()}."
                 for a in e.acquired if (e.roster_id,a.asset_ref) in exits),None)
    if onward:
        facts.append(onward)
    return " ".join(facts),fallback


def opening_terms(moves, names, positions, label):
    """Describe the opportunity each side bought at the time; motivations stay conditional."""
    if len(moves)!=2:
        return f"{len(moves)} franchises split this deal."
    a,b=(m.event for m in moves)
    for buyer,seller in ((a,b),(b,a)):
        bought=[x for x in buyer.acquired if x.kind=="player"]
        picks=[x for x in seller.acquired if x.kind=="pick"]
        if bought and picks:
            player=", ".join(label(x) for x in bought)
            if not any(x.kind=="player" for x in seller.acquired):
                return (f"{names[buyer.roster_id]} spent draft capital to get {player}. "
                        f"{names[seller.roster_id]} could use those picks in another trade or take them to the draft.")
            if any(x.kind=="pick" for x in buyer.acquired):
                continue
            other=", ".join(label(x) for x in seller.acquired if x.kind=="player")
            return (f"{names[buyer.roster_id]} added draft capital to land {player}. "
                    f"{names[seller.roster_id]} got {other} to play now and picks to spend later.")
        if bought and seller.acquired and all(x.kind=="faab" for x in seller.acquired):
            return (f"{names[buyer.roster_id]} turned a waiver budget into {', '.join(label(x) for x in bought)}. "
                    f"{names[seller.roster_id]} bought bidding room for the next waiver run.")
    if all(len(e.acquired)==1 and e.acquired[0].kind=="player" for e in (a,b)):
        aa,bb=a.acquired[0],b.acquired[0]
        if any((x.asset_ref,a.season) in SEASON_ENDINGS and
               SEASON_ENDINGS[x.asset_ref,a.season][0]<a.occurred_at.date() for x in (aa,bb)):
            return ""
        pa,pb=positions.get(aa.asset_ref),positions.get(bb.asset_ref)
        if pa and pb and pa!=pb:
            return (f"{names[a.roster_id]} shifted a roster spot from {pb} to {pa} for {label(aa)}. "
                    f"{names[b.roster_id]} took {label(bb)} to fill the other position.")
    return ""
