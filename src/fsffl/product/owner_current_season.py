"""Cheap read-only owner view of canonical current facts; no source acquisition."""
from fsffl.trade_decision.contextual_precedents import current_record_context


def asset_labels(state):
    labels={}
    for p in state.players:
        labels[p.player_id]=p.full_name
        for ref in p.provider_refs:
            if ref.provider=='sleeper':labels[f'sleeper:player:{ref.external_id}']=p.full_name
    return labels


def action_labels(assets, labels):
    return [labels.get(a.asset_ref,'Unlisted player') if a.kind=='player'
        else f'{a.pick_season} Round {a.pick_round}' if a.kind=='pick' else f'{a.faab_amount} FAAB' for a in assets]


def current_owner_view(state, team_id, profile):
    teams={t.team_id:t.display_name for t in state.teams}
    picks={p.pick_id:p for p in state.draft_picks}
    holdings=sorted((picks[o.pick_id] for o in state.pick_ownership
        if o.owner_team_id==team_id and o.pick_id in picks and picks[o.pick_id].season>=state.league.season),
        key=lambda p:(p.season,p.round,p.pick_id))
    unconfirmed = state.unconfirmed_pick_ids()
    labels=asset_labels(state)
    activity=profile.current_season_activity
    provider_ids={r.external_id for r in state.league.provider_refs if r.provider=='sleeper'}
    if activity is not None and (activity.league_external_id not in provider_ids
            or activity.season!=state.league.season or activity.cutoff>state.as_of):activity=None
    resume=profile.franchise_resume
    drafts=[d.model_dump(mode='json') for d in resume.draft_selections if d.season==state.league.season] if resume else []
    moves=[];insights=[]
    if activity:
        for m in activity.recent_moves:
            moves.append({'event_id':m.event.event_id,'kind':m.event.kind.value,
                'created_at':m.event.occurred_at.isoformat(),'completed_at':m.completed_at.isoformat(),
                'received':action_labels(m.event.acquired,labels),'sent':action_labels(m.event.disposed,labels)})
        got,sent=activity.picks_acquired_in_trades,activity.picks_sent_in_trades
        if got!=sent:
            insights.append(f'Trades this season have {"added" if got>sent else "used"} {abs(got-sent)} net draft pick'+('s' if abs(got-sent)!=1 else '')+'.')
        elif got:
            insights.append(f'This season’s trades have brought in {got} picks and sent out {sent}.')
        current=next((t for t in state.team_states if t.team_id==team_id),None)
        roster={r.player_id for r in current.roster} if current else set()
        ref_to_id={f'sleeper:player:{ref.external_id}':p.player_id for p in state.players
            for ref in p.provider_refs if ref.provider=='sleeper'}
        added=[]
        for m in activity.recent_moves:
            for a in m.event.acquired:
                if a.kind=='player' and ref_to_id.get(a.asset_ref) in roster and labels.get(a.asset_ref) not in added:
                    added.append(labels[a.asset_ref])
        if added:insights.append('Recent additions still on the roster: '+', '.join(added[:3])+'.')
    firsts=[p for p in holdings if p.round==1]
    if firsts:
        year=min(p.season for p in firsts);n=sum(p.season==year for p in firsts)
        insights.append(f'Holds {n} first-round pick'+('s' if n!=1 else '')+f' in {year}.')
    return {'pick_window_notice':state.rookie_pick_window.notice if state.rookie_pick_window else None,
        'state_id':state.state_id,'as_of':state.as_of.isoformat(),'season':state.league.season,
        'record':current_record_context(state,team_id),'record_basis':'completed_head_to_head_games',
        'picks':[{'pick_id':p.pick_id,'season':p.season,'round':p.round,
            'available':p.pick_id not in unconfirmed,'verified_slot':p.verified_slot,'owner_team_id':team_id,'original_team_id':p.original_team_id,
            'original_team':teams.get(p.original_team_id,p.original_team_id)} for p in holdings],
        'draft_selections':drafts,'activity_as_of':activity.cutoff.isoformat() if activity else None,
        'activity_observed_at':activity.observed_at.isoformat() if activity else None,
        'missing_completion_count':activity.missing_completion_count if activity else None,
        'counts':{'trades':activity.trade_count,'waivers':activity.waiver_count,'free_agents':activity.free_agent_count} if activity else None,
        'recent_moves':moves,'insights':insights[:3]}
