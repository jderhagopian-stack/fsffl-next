"""Source → grounded case → existing owner profile. No preference coefficients."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from fsffl.state.historical_roster_context import HistoricalRosterContextHistory,_digest
from fsffl.state.historical_season_lineage import HistoricalSeasonSource
from .historical_circumstances import HistoricalTradeCircumstances
from .historical_case_models import OwnerHistoricalTradeCase
from .models import BehavioralAssetKind,BehavioralEventKind,OwnerBehaviorEvent,OwnerBehaviorProfile
from .sleeper_history import normalize_sleeper_behavior_transaction

MAX_PROFILE_CASES=12  # Compact product window; source events/history are not deleted.


@dataclass(frozen=True)
class HistoricalCaseCompilation:
    case: OwnerHistoricalTradeCase | None
    blockers: tuple[str,...] = ()


def historical_event_fingerprint(event: OwnerBehaviorEvent) -> str:
    payload=event.model_dump(mode='json')
    # Provider-normalized historical position labels can be absent or enriched
    # independently. Case prose uses its own dated production evidence instead.
    for direction in ('acquired','disposed'):
        for asset in payload[direction]:asset.pop('position',None)
    return _digest(payload)



@dataclass(frozen=True)
class HistoricalActivityWitness:
    league_family_id: str
    provider_league_id: str
    through: datetime
    sha256: str


def historical_activity_witness(events,*,league_family_id,provider_league_id,through):
    scoped=sorted((e for e in events if e.league_family_id==league_family_id
        and e.league_external_id==provider_league_id and e.occurred_at<=through),key=lambda e:e.event_id)
    if len({e.event_id for e in scoped})!=len(scoped):raise ValueError('duplicate historical activity event')
    return HistoricalActivityWitness(league_family_id,provider_league_id,through,
        _digest(tuple((e.event_id,historical_event_fingerprint(e))for e in scoped)))


def _asset_labels(assets,names,pick_origins):
    labels=[]
    for asset in assets:
        if asset.kind==BehavioralAssetKind.PLAYER:
            pid=asset.asset_ref.removeprefix('sleeper:player:')
            label=names.get(pid)
            labels.append(str(label).strip() if label and str(label).strip() else 'Player name unavailable')
        elif asset.kind==BehavioralAssetKind.PICK:
            label=f'{asset.pick_season} Round {asset.pick_round}'
            origin=pick_origins.get(asset.asset_ref.rsplit(':',1)[-1])
            labels.append(label+f' · {origin}' if origin else label)
        elif asset.kind==BehavioralAssetKind.FAAB:
            labels.append(f'${asset.faab_amount} FAAB')
    return tuple(labels)


def _join_names(names):
    if len(names)==1:return names[0]
    return ', '.join(names[:-1])+' and '+names[-1]


def compile_historical_owner_case(*,event: OwnerBehaviorEvent,
        circumstances: HistoricalTradeCircumstances, history: HistoricalRosterContextHistory,
        source: HistoricalSeasonSource, season_data: Mapping,
        player_names: Mapping[str,str], evidence_as_of: datetime,
        activity_witness: HistoricalActivityWitness | None = None) -> HistoricalCaseCompilation:
    """Only an initiating-account witness plus admitted season roster binding.

    This says nothing about rejected offers, all counterparties or full tenure.
    Raw-source direction is checked by the same normalizer used for live scans.
    Every narrative is a factual composition; no model interpretation is inserted.
    """
    if (source.source_content_sha256 != history.source_sha256 or _digest(season_data)!=history.source_sha256
            or circumstances.history_id!=history.history_id
            or source.provider_ref.external_id!=event.league_external_id
            or event.league_family_id!=source.season.league_family_id
            or circumstances.season!=source.season
            or event.season!=source.season.season):
        raise ValueError('historical case source/event cohort mismatch')
    snapshots={s.snapshot_id:s for s in history.snapshots}
    snapshot=snapshots.get(circumstances.snapshot_id)
    if (snapshot is None or snapshot.effective_at!=circumstances.completed_at
            or snapshot.boundary!='before_completed_event_batch'
            or circumstances.transaction_id not in snapshot.transaction_ids):
        raise ValueError('historical case snapshot boundary mismatch')
    rows=[t for t in season_data.get('transactions',())if str(t.get('transaction_id'))==circumstances.transaction_id]
    if len(rows)!=1:raise ValueError('historical case requires one source transaction')
    raw=rows[0]
    if event.kind!=BehavioralEventKind.TRADE:return HistoricalCaseCompilation(None,('not_a_trade',))
    owner_map={int(b.provider_roster_id):b.provider_manager_id for b in source.roster_bindings if b.provider_manager_id is not None}
    if str(raw.get('creator')or'')!=event.owner_id:
        return HistoricalCaseCompilation(None,('initiating_account_not_witnessed',))
    if owner_map.get(event.roster_id)!=event.owner_id:
        return HistoricalCaseCompilation(None,('admitted_roster_account_binding_unavailable',))
    normalized=normalize_sleeper_behavior_transaction(raw,family_id=event.league_family_id,
        league_external_id=event.league_external_id,season=event.season,
        owner_by_roster=owner_map,player_positions={})
    witness=next((e for e in normalized if e.roster_id==event.roster_id),None)
    if witness is None or historical_event_fingerprint(witness)!=historical_event_fingerprint(event):
        raise ValueError('historical case differs from normalized source event')
    completion=raw.get('status_updated')
    if (type(completion) not in (int,float) or int(completion)!=int(circumstances.completed_at.timestamp()*1000)
            or circumstances.created_at!=event.occurred_at):
        raise ValueError('historical case trade clocks mismatch')
    if evidence_as_of.tzinfo is None or evidence_as_of.utcoffset() is None or evidence_as_of<circumstances.completed_at:
        raise ValueError('historical case evidence clock invalid')
    if any(r.effective_at>=circumstances.completed_at for r in circumstances.used_receipts):
        raise ValueError('future circumstance cannot become a historical narrative')
    team=next((t for t in circumstances.teams if t.provider_roster_id==str(event.roster_id)),None)
    if team is None:raise ValueError('historical case participant missing from circumstances')
    roster=next((t for t in snapshot.teams if t.provider_roster_id==str(event.roster_id)),None)
    if roster is None:raise ValueError('historical case source roster missing')
    if team.roster_size is not None and (team.roster_size!=len(roster.player_ids)
            or history.membership_issues or snapshot.uncertain_player_ids or snapshot.membership_uncertainty_reasons
            or not {p.player_id for p in team.prior_production}<=set(roster.player_ids)):
        raise ValueError('historical case roster facts differ from source snapshot')
    if team.roster_size is None and team.prior_production:
        raise ValueError('unknown membership cannot support roster retention prose')
    situation=None;sentences=[]
    records=sorted(team.records,key=lambda r:r.season.season,reverse=True)
    for record in records:
        # Do not imply a complete season-to-date record from a gapped week set.
        if not record.weeks or record.weeks!=tuple(range(1,max(record.weeks)+1)):continue
        if record.wins+record.losses+record.ties!=len(record.weeks):continue
        standing=f'{record.wins}–{record.losses}'+(f'–{record.ties}'if record.ties else '')
        prefix=''if record.season.season==event.season else f'{record.season.season}: '
        situation=f'{prefix}{standing} through Week {max(record.weeks)}'
        if record.season.season==event.season:sentences.append(f'They were {standing} through Week {max(record.weeks)}.')
        else:sentences.append(f'In {record.season.season}, they were {standing} through Week {max(record.weeks)}.')
        break
    disposed={a.asset_ref.removeprefix('sleeper:player:')for a in event.disposed if a.kind==BehavioralAssetKind.PLAYER}
    acquired={a.asset_ref.removeprefix('sleeper:player:')for a in event.acquired if a.kind==BehavioralAssetKind.PLAYER}
    # Retention, never an invented starter replacement or a current-strength claim.
    positions={p.position for p in team.prior_production if p.player_id in disposed}
    after=next((s for s in history.snapshots if s.boundary=='after_completed_event_batch'
        and s.effective_at==circumstances.completed_at and circumstances.transaction_id in s.transaction_ids),None)
    after_roster=next((t for t in after.teams if t.provider_roster_id==str(event.roster_id)),None)if after else None
    kept_members=set(after_roster.player_ids)if after_roster is not None and not after.uncertain_player_ids and not after.membership_uncertainty_reasons else set()
    candidates=sorted((p for p in team.prior_production if p.player_id not in disposed|acquired
        and p.player_id in kept_members and p.position in positions),
        key=lambda p:(-p.fantasy_points,p.player_id))
    retained=tuple(str(player_names[p.player_id]).strip() for p in candidates
        if player_names.get(p.player_id) and str(player_names[p.player_id]).strip())[:2]
    if retained:sentences.append(f'They kept {_join_names(retained)} on their roster.')
    activity_through=max(s.effective_at for s in history.snapshots if s.effective_at is not None)
    if activity_witness is None:
        activity_events=[]
        for tx in season_data.get('transactions',()):
            activity_events.extend(normalize_sleeper_behavior_transaction(tx,family_id=event.league_family_id,
                league_external_id=event.league_external_id,season=event.season,
                owner_by_roster=owner_map,player_positions={}))
        activity_witness=historical_activity_witness(activity_events,league_family_id=event.league_family_id,
            provider_league_id=event.league_external_id,through=activity_through)
    if (activity_witness.league_family_id!=event.league_family_id
            or activity_witness.provider_league_id!=event.league_external_id
            or activity_witness.through!=activity_through):raise ValueError('case activity scope mismatch')
    fingerprint=historical_event_fingerprint(event)
    users={str(u.get('user_id')):u for u in season_data.get('users',())}
    origins={}
    for roster in season_data.get('rosters',()):
        user=users.get(str(roster.get('owner_id')),{})
        label=(user.get('metadata')or{}).get('team_name') or user.get('display_name')
        if label:origins[str(roster['roster_id'])]=str(label)
    sent=_asset_labels(event.disposed,player_names,origins);received=_asset_labels(event.acquired,player_names,origins)
    if not sent and not received:return HistoricalCaseCompilation(None,('exchange_unavailable',))
    identity=_digest({'event':fingerprint,'history':history.history_id,'snapshot':snapshot.snapshot_id,
        'circumstance_sources':circumstances.evidence_source_sha256,'evidence_as_of':evidence_as_of.isoformat(),
        'activity':activity_witness.sha256,'activity_through':activity_through.isoformat(),
        'sent':sent,'received':received,'sentences':sentences,'owner_label':users.get(event.owner_id,{}).get('display_name'),'version':'owner-historical-trade-case-v1'})
    return HistoricalCaseCompilation(OwnerHistoricalTradeCase(case_id='hcase_'+identity,event_id=event.event_id,
        event_sha256=fingerprint,league_family_id=event.league_family_id,owner_id=event.owner_id,
        provider_league_id=event.league_external_id,transaction_id=circumstances.transaction_id,
        roster_id=event.roster_id,season=event.season,created_at=event.occurred_at,
        completed_at=circumstances.completed_at,evidence_as_of=evidence_as_of,
        activity_through=activity_through,activity_sha256=activity_witness.sha256,sent=sent,received=received,
        situation=situation,retained_players=retained,context_sentences=tuple(sentences),
        history_id=history.history_id,snapshot_id=snapshot.snapshot_id,source_sha256=history.source_sha256,
        circumstance_evidence_sha256=_digest(circumstances.evidence_source_sha256),
        owner_display_name=users.get(event.owner_id,{}).get('display_name')))


def attach_historical_owner_cases(profiles: Sequence[OwnerBehaviorProfile], *,
        events: Sequence[OwnerBehaviorEvent], cases: Sequence[OwnerHistoricalTradeCase]) -> tuple[OwnerBehaviorProfile,...]:
    """Compact verified cases through the existing profile owner/persistence path."""
    index={e.event_id:e for e in events}
    if len(index)!=len(events):raise ValueError('historical case attachment requires unique events')
    if len({c.event_id for c in cases})!=len(cases):raise ValueError('select one historical case revision per event')
    results=[];activity_digests={}
    for profile in profiles:
        candidates={c.event_id:c for c in profile.historical_trade_cases}
        candidates.update({c.event_id:c for c in cases if c.owner_id==profile.owner_id and c.league_family_id==profile.league_family_id})
        kept=[]
        for case in candidates.values():
            scope=(case.league_family_id,case.provider_league_id,case.activity_through)
            if scope not in activity_digests:
                activity_digests[scope]=historical_activity_witness(events,league_family_id=case.league_family_id,
                    provider_league_id=case.provider_league_id,through=case.activity_through).sha256
            if activity_digests[scope]!=case.activity_sha256:continue
            event=index.get(case.event_id)
            if (event is None or event.kind!=BehavioralEventKind.TRADE or event.owner_id!=profile.owner_id
                    or event.league_family_id!=profile.league_family_id or event.occurred_at!=case.created_at
                    or max(case.completed_at,case.evidence_as_of)>profile.as_of
                    or historical_event_fingerprint(event)!=case.event_sha256):continue
            kept.append(case)
        kept.sort(key=lambda c:(c.completed_at,c.event_id),reverse=True)
        payload=profile.model_dump();payload['historical_trade_cases']=tuple(kept[:MAX_PROFILE_CASES])
        results.append(OwnerBehaviorProfile.model_validate(payload))
    return tuple(results)


def preserve_historical_owner_cases(profiles, *, previous_profiles, events):
    """A refresh must neither discard valid cases nor revive stale/foreign cases."""
    previous={ (p.league_family_id,p.owner_id):p for p in previous_profiles }
    cases=[]
    for profile in profiles:
        old=previous.get((profile.league_family_id,profile.owner_id))
        if old is not None:cases.extend(old.historical_trade_cases)
    return attach_historical_owner_cases(profiles,events=events,cases=cases)
