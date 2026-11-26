"""Positive completed-action evidence for additional search hypotheses.

No learned preference, absence penalty, acceptance model, age backfill or Value.
"""
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ObservedAcquisitionInterest:
    kind: str
    position: str | None
    trade_count: int
    event_ids: tuple[str, ...]


def observed_acquisition_interests(profile, *, as_of):
    if profile is None or profile.as_of>as_of:return ()
    evidence=defaultdict(dict)
    def add(event_id,at,assets,*,dated_positions):
        seen=set()
        for a in assets:
            key=('pick',None) if a.kind=='pick' else (
                ('position',a.position) if a.kind=='player' and dated_positions and a.position else None)
            if key is not None and key not in seen:
                evidence[key][event_id]=at;seen.add(key)
    for case in profile.historical_trade_cases:
        if (case.owner_id!=profile.owner_id or case.league_family_id!=profile.league_family_id
                or max(case.completed_at,case.evidence_as_of)>as_of):continue
        add(case.event_id,case.completed_at,case.acquired_assets,dated_positions=True)
    current=profile.current_season_activity
    if current is not None and current.cutoff<=as_of:
        for move in current.trade_examples:
            event=move.event
            if (event.kind!='trade' or event.owner_id!=profile.owner_id or event.league_family_id!=profile.league_family_id
                    or max(move.completed_at,move.observed_at)>as_of):continue
            # Current player labels cannot establish historical positions/ages.
            add(event.event_id,move.completed_at,event.acquired,dated_positions=False)
    return tuple(ObservedAcquisitionInterest(kind,position,len(events),tuple(
        sorted(events,key=lambda event:(events[event],event),reverse=True)[:3]))
        for (kind,position),events in sorted(evidence.items(),key=lambda pair:(pair[0][0],pair[0][1] or '')))
