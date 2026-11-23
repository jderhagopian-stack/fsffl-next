"""Categorical historical analogues. No acceptance model or economic score."""
from math import isfinite


def _direction(assets):
    assets=tuple(a for a in assets if a.kind in ('player','pick'))
    kinds=frozenset(a.kind for a in assets)
    players=[a for a in assets if a.kind=='player']
    known=all(a.position for a in players)
    positions=frozenset(a.position for a in players if a.position)
    return kinds,positions,known


def current_record_context(state,team_id):
    """Observed regular-season games only; gaps/duplicates remain unavailable."""
    cutoff=getattr(state,'completed_through_week',None)
    league=getattr(state,'league',None);rules=getattr(league,'rules',None)
    end=getattr(rules,'fantasy_regular_season_end_week',None)
    if not isinstance(cutoff,int) or cutoff<1 or not isinstance(end,int):return None
    through=min(cutoff,end);games={}
    for m in getattr(state,'matchups',()):
        if m.week>through or team_id not in (m.team_a_id,m.team_b_id):continue
        if m.provenance.effective_at>state.as_of:return None
        if m.week in games:return None
        if m.team_a_points is None or m.team_b_points is None:return None
        a,b=(m.team_a_points,m.team_b_points)if team_id==m.team_a_id else(m.team_b_points,m.team_a_points)
        if not isfinite(a) or not isfinite(b):return None
        games[m.week]=(a,b)
    if set(games)!=set(range(1,through+1)):return None
    wins=sum(a>b for a,b in games.values());losses=sum(a<b for a,b in games.values())
    # A positive incomplete regular-season week count establishes active regular
    # season context. Zero alone never establishes offseason.
    phase='regular_season' if cutoff<end and state.as_of.year==league.season else 'unknown'
    return {'season':league.season,'wins':wins,'losses':losses,'ties':through-wins-losses,'through_week':through,'phase':phase}


def _balance(wins,losses):return (wins>losses)-(wins<losses)


def relevant_owner_precedents(*,profile,acquired,disposed,player_positions,as_of,current_record=None):
    from fsffl.behavioral.historical_trade_context import HistoricalCaseAsset
    def proposal_assets(items):
        return tuple(HistoricalCaseAsset(kind=a.kind,asset_ref=a.player_id if a.kind=='player'else a.pick_id,
            position=player_positions.get(a.player_id)if a.kind=='player'else None)
            for a in items if a.kind in ('player','pick'))
    incoming=_direction(proposal_assets(acquired));outgoing=_direction(proposal_assets(disposed))
    found=[]
    for case in profile.historical_trade_cases:
        if max(case.completed_at,case.evidence_as_of)>as_of or case.owner_id!=profile.owner_id or case.league_family_id!=profile.league_family_id:continue
        if not case.acquired_assets or not case.disposed_assets:continue
        got=_direction(case.acquired_assets);sent=_direction(case.disposed_assets)
        if incoming[0]!=got[0] or outgoing[0]!=sent[0]:continue
        pick_direction='pick' in (incoming[0]|outgoing[0])
        position_direction=(incoming[2] and outgoing[2] and got[2] and sent[2]
            and incoming[1]==got[1] and outgoing[1]==sent[1] and bool(incoming[1]|outgoing[1]))
        if not pick_direction and not position_direction:continue
        # Known contradictory positions do not qualify just because both sides
        # happened to exchange picks too; missing labels do not invent a match.
        if any(a[1] and b[1] and a[2] and b[2] and a[1]!=b[1]for a,b in ((incoming,got),(outgoing,sent))):continue
        basis=['draft_pick_direction']if pick_direction else []
        if position_direction:basis.append('position_direction')
        record=case.record_context
        comparable=(current_record is not None and case.trade_phase==current_record['phase']=='regular_season'
            and record is not None and record.season==case.football_season and record.through_week==current_record.get('through_week')
            and _balance(record.wins,record.losses)==_balance(current_record['wins'],current_record['losses']))
        if comparable:basis.extend(('same_season_phase','same_completed_week','same_record_balance'))
        # This is a factual example, not a claim that the owner shares today's
        # strategic objectives, had surplus, or will accept the new offer.
        def compact(assets,labels):
            economic=[a for a in assets if a.kind in ('player','pick')]
            if economic and all(a.kind=='pick'for a in economic):return f'{len(economic)} draft pick'+('s'if len(economic)!=1 else '')
            return ' + '.join(labels[:2])+(f' + {len(labels)-2} more'if len(labels)>2 else '')
        found.append({'case_id':case.case_id,'event_id':case.event_id,'completed_at':case.completed_at.isoformat(),
            'season':case.season,'football_season':case.football_season,'trade_phase':case.trade_phase,'situation':case.situation,
            'record_context':record.model_dump()if record else None,'match_basis':basis,
            'match_type':'contextual'if comparable else 'directional',
            'sent_summary':compact(case.disposed_assets,case.sent),'received_summary':compact(case.acquired_assets,case.received),
            'retained_players':list(case.retained_players)})
    # Categorical relevance, then recency. Frequency is not a preference weight.
    found.sort(key=lambda p:(p['match_type']=='contextual',p['completed_at'],p['event_id']),reverse=True)
    return found[:2]


def precedent_category(features):
    """Ordering within existing economic/search gates, never a value score."""
    if not isinstance(features,(str,tuple,list,set,frozenset)):return 2
    return 0 if 'contextual_precedent'in features else 1 if 'directional_precedent'in features else 2


def current_season_precedents(*, profile, acquired, disposed, as_of):
    """Receipt-backed pick direction only; no fabricated at-trade circumstances.

    Current metadata cannot prove historical positions. Observation clocks are
    strict: first-seen-after-State examples wait for a subsequent State.
    """
    activity=profile.current_season_activity
    if activity is None or activity.cutoff>as_of:return []
    def kinds(items):return frozenset(a.kind for a in items if a.kind in ('player','pick'))
    incoming,outgoing=kinds(acquired),kinds(disposed)
    if 'pick' not in incoming|outgoing:return []
    found=[]
    for m in activity.trade_examples:
        if m.observed_at>as_of or m.completed_at>as_of:continue
        event=m.event
        if event.owner_id!=profile.owner_id or event.league_family_id!=profile.league_family_id:continue
        if kinds(event.acquired)!=incoming or kinds(event.disposed)!=outgoing:continue
        def compact(items):
            players=sum(a.kind=='player' for a in items);picks=sum(a.kind=='pick' for a in items)
            return ' + '.join(f'{n} {word}'+('s' if n!=1 else '') for n,word in ((players,'player'),(picks,'draft pick')) if n)
        found.append({'case_id':event.event_id,'event_id':event.event_id,
            'completed_at':m.completed_at.isoformat(),'season':event.season,'football_season':None,
            'trade_phase':'unknown','situation':None,'record_context':None,
            'match_basis':['draft_pick_direction'],'match_type':'directional',
            'sent_summary':compact(event.disposed),'received_summary':compact(event.acquired),
            'retained_players':[],'evidence_basis':'completed_current_season_action',
            'source_observed_at':m.observed_at.isoformat()})
    return sorted(found,key=lambda p:(p['completed_at'],p['event_id']),reverse=True)[:2]
