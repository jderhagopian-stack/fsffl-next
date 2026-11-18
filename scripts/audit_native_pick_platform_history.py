"""Read-only normalized draft-context evidence from a supplied platform export.

Exported historical records improve source qualification; they are not immutable
at-draft snapshots, forecast labels or production model admission.
"""
from collections import Counter
import hashlib
import json


def audit(history, *, source_ref, expected_sha256, payload_sha256):
    if not source_ref.strip() or expected_sha256!=payload_sha256:
        raise ValueError('historical platform export needs exact source identity')
    drafts=[];seen=set()
    for entry in history:
        league=entry['league'];year=int(league['season'])
        for item in entry.get('drafts',()):
            draft=item['draft'];settings=draft['settings'];picks=item.get('picks',())
            if str(draft['season'])!=str(year) or draft.get('league_id')!=league.get('league_id'):
                raise ValueError('draft and historical league scope differ')
            did=draft['draft_id']
            if did in seen:raise ValueError('duplicate historical draft')
            seen.add(did)
            teams=int(settings['teams']);rounds=int(settings['rounds'])
            if teams<1 or rounds<1:raise ValueError('invalid draft capacity')
            ranks=[int(p['pick_no']) for p in picks]
            if len(set(ranks))!=len(ranks):raise ValueError('duplicate selection rank')
            if any(p.get('draft_id')!=did or int(p['round'])!=(int(p['pick_no'])-1)//teams+1
                   or not 1<=int(p['pick_no'])<=teams*rounds for p in picks):
                raise ValueError('selection coordinates differ from draft')
            lineage={'roster_positions':league.get('roster_positions',[]),'scoring_settings':league.get('scoring_settings',{}),'draft_settings':settings}
            fp=hashlib.sha256(json.dumps(lineage,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            # Restrict this workstream to completed three-round supplemental drafts.
            # Twenty-round startup remains excluded, not reinterpreted as a rookie class.
            eligible=draft.get('status')=='complete' and rounds==3
            counts=Counter(p.get('metadata',{}).get('position','unknown') for p in picks)
            drafts.append(dict(season=year,draft_id=did,team_count=teams,rounds=rounds,
                status=draft.get('status'),selection_count=len(picks),expected_selections=teams*rounds,
                missing_ranks=sorted(set(range(1,teams*rounds+1))-set(ranks)),
                supplemental_three_round_candidate=eligible,
                eligibility_code=settings.get('player_type'),
                selection_positions=dict(counts),lineup_slots={k:v for k,v in settings.items() if k.startswith('slots_')},
                roster_positions=league.get('roster_positions',[]),scoring_settings=league.get('scoring_settings',{}),
                context_fingerprint=fp,source_ref=source_ref,source_sha256=payload_sha256,
                qualification='retrospectively_exported_historical_context_not_immutable_draft_time_snapshot'))
    return dict(status='platform_history_context_evidence_not_model_admission',production_eligible=False,
                source_sha256=payload_sha256,drafts=sorted(drafts,key=lambda x:x['season']))
