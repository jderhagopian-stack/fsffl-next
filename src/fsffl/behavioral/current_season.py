"""Bounded current-provider receipts in the existing owner profile publication."""
from collections import Counter
from .models import OwnerCurrentSeasonActivity, OwnerBehaviorProfile


def attach_current_season_activity(profiles, *, history, season, cutoff):
    observed=getattr(history,'observed_at',None)
    if observed is None or observed<cutoff:
        return profiles
    moves=tuple(m for m in getattr(history,'current_completed_moves',())
        if m.completed_at<=cutoff and m.event.league_external_id==history.current_league_external_id
        and m.event.season==season and m.event.league_family_id==history.league_family_id)
    result=[]
    for p in profiles:
        rows=sorted((m for m in moves if m.event.owner_id==p.owner_id),
            key=lambda m:(m.completed_at,m.event.event_id),reverse=True)
        counts=Counter(m.event.kind for m in rows)
        ids={m.event.event_id for m in rows}
        missing=sum(e.owner_id==p.owner_id and e.season==season and e.league_external_id==history.current_league_external_id
            and e.occurred_at<=cutoff and e.event_id not in ids for e in history.events)
        trades=[m for m in rows if m.event.kind=='trade']
        activity=OwnerCurrentSeasonActivity(league_external_id=history.current_league_external_id,
            season=season,cutoff=cutoff,observed_at=observed,trade_count=counts['trade'],
            missing_completion_count=missing,
            waiver_count=counts['waiver'],free_agent_count=counts['free_agent'],
            picks_acquired_in_trades=sum(a.kind=='pick' for m in trades for a in m.event.acquired),
            picks_sent_in_trades=sum(a.kind=='pick' for m in trades for a in m.event.disposed),
            recent_moves=tuple(rows[:12]),trade_examples=tuple(trades[:64]))
        result.append(OwnerBehaviorProfile.model_validate({**p.model_dump(),'current_season_activity':activity}))
    return tuple(result)
