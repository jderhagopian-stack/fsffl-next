"""Owner dossier evidence boundaries, attribution, and persistence."""
from datetime import timedelta
import pytest
from fsffl.behavioral.owner_resume import OwnerTenureAttestation,OwnerTenureBinding,compile_owner_resumes
from fsffl.behavioral.historical_cases import compile_historical_owner_case,preserve_historical_owner_cases
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.state.historical_roster_context import _digest
from tests.test_contextual_owner_delivery import inputs,OBS


def attestation(source):
    return OwnerTenureAttestation(league_family_id=source.season.league_family_id,recorded_at=OBS,
        reference='synthetic:user-confirmed-tenure',bindings=tuple(OwnerTenureBinding(
            provider_league_id=source.provider_ref.external_id,season=source.season.season,
            roster_id=int(b.provider_roster_id),owner_id=b.provider_manager_id,source_sha256=source.source_content_sha256)
            for b in source.roster_bindings if b.provider_manager_id))


def test_counterparty_requires_scoped_tenure_and_keeps_its_basis():
    kwargs,events=inputs();kwargs['event']=events[1];source=kwargs['source'];witness=attestation(source)
    case=compile_historical_owner_case(**kwargs,tenure_attestation=witness).case
    assert case is not None and case.owner_id==events[1].owner_id
    assert case.attribution_basis=='user_attested_tenure_and_admitted_roster_binding'
    assert case.tenure_reference==witness.reference
    for changed in (witness.model_copy(update={'league_family_id':'foreign'}),
        witness.model_copy(update={'recorded_at':OBS+timedelta(days=1)}),
        witness.model_copy(update={'bindings':()}),
        witness.model_copy(update={'bindings':tuple(b.model_copy(update={'source_sha256':'0'*64}) for b in witness.bindings)})):
        assert compile_historical_owner_case(**kwargs,tenure_attestation=changed).case is None


def test_resume_observed_records_drafts_and_refresh(tmp_path):
    from types import SimpleNamespace
    from fsffl.behavioral.store import BehavioralIntelligenceStore
    kwargs,events=inputs();source=kwargs['source'];data=kwargs['season_data']
    binding=next(b for b in source.roster_bindings if b.provider_manager_id==events[0].owner_id)
    rid=int(binding.provider_roster_id)
    data['league']['status']='complete'
    data['league']['metadata']={'latest_league_winner_roster_id':str(rid)}
    raw=next(r for r in data['rosters'] if r['roster_id']==rid)
    raw.update(owner_id=events[0].owner_id,settings={'wins':8,'losses':6,'ties':0,'fpts':1234,'fpts_decimal':56})
    data['drafts']=[{'draft':{'draft_id':'draft-a','status':'complete','last_picked':int(OBS.timestamp()*1000)-1},
        'picks':[{'roster_id':rid,'picked_by':events[0].owner_id,'round':1,'pick_no':3,'player_id':'p',
            'metadata':{'first_name':'Drafted','last_name':'Player','position':'WR'}}]}]
    source=source.model_copy(update={'source_content_sha256':_digest(data)})
    args=dict(seasons={source.season:data},lineage=SimpleNamespace(sources=(source,)),rookie_drafts=(),
        evidence_as_of=OBS,tenure_attestation=attestation(source))
    resume=compile_owner_resumes(**args)[events[0].owner_id]
    assert resume.seasons[0].points_for==1234.56 and resume.seasons[0].points_against is None
    assert resume.seasons[0].season_complete and resume.seasons[0].champion is True
    assert resume.draft_selections[0].player_name=='Drafted Player'
    assert resume.draft_selections[0].draft_kind=='other'
    profile=next(p for p in build_owner_behavior_profiles(events,as_of=OBS) if p.owner_id==resume.owner_id)
    enriched=OwnerBehaviorProfile.model_validate({**profile.model_dump(),'franchise_resume':resume})
    store=BehavioralIntelligenceStore(tmp_path/'owners.sqlite3');store.put_profiles((enriched,))
    restored=store.load_profiles(profile.league_family_id)
    refreshed=preserve_historical_owner_cases((profile,),previous_profiles=restored,events=events)
    assert refreshed[0].franchise_resume==resume
    with pytest.raises(ValueError,match='resume'):
        OwnerBehaviorProfile.model_validate({**profile.model_dump(),'franchise_resume':resume.model_copy(update={'owner_id':'foreign'})})
    assert compile_owner_resumes(**{**args,'tenure_attestation':None})=={}
    data['rosters'][0]['settings']={'wins':1}
    with pytest.raises(ValueError,match='source mismatch'):compile_owner_resumes(**args)


def test_pinned_dossier_all_participant_sides_records_and_drafts():
    import os,json
    from pathlib import Path
    from fsffl.product.historical_owner_delivery import build_historical_owner_delivery
    from tests.historical_circumstances_fixture import pinned_delivery_inputs
    root=os.getenv('FSFFL_RESEARCH_CIRCUMSTANCE_SOURCE')
    if not root:pytest.skip('optional disposable source cohort not mounted')
    args=pinned_delivery_inputs(root)
    scope=OwnerTenureAttestation(league_family_id=args['lineage'].sources[0].season.league_family_id,
        recorded_at=args['source_observed_at'],reference='pinned-fixture:explicit-unchanged-tenure-declaration',
        bindings=tuple(OwnerTenureBinding(provider_league_id=s.provider_ref.external_id,season=s.season.season,
            roster_id=int(b.provider_roster_id),owner_id=b.provider_manager_id,source_sha256=s.source_content_sha256)
            for s in args['lineage'].sources for b in s.roster_bindings if b.provider_manager_id))
    delivery=build_historical_owner_delivery(**args,tenure_attestation=scope)
    assert len(delivery.cases)==291
    assert delivery.coverage['case_blocker_counts']=={}
    assert delivery.coverage['profiles_with_resume']==12
    assert delivery.coverage['recorded_season_rows']==60
    assert delivery.coverage['recorded_draft_selections']==384
    assert all(len(p.franchise_resume.seasons)==5 for p in delivery.profiles)
    assert all(sum(s.season_complete for s in p.franchise_resume.seasons)==4 for p in delivery.profiles)
    # Independently reconcile archived season records against recorded weekly scores.
    for source in args['lineage'].sources:
        by_team={b.canonical_team_id:[0,0,0] for b in source.roster_bindings}
        for week in args['results']:
            if week.receipt.season!=source.season:continue
            for game in week.matchups:
                index=0 if game.points_for>game.points_against else 1 if game.points_for<game.points_against else 2
                by_team[game.team_id][index]+=1
        profiles={p.owner_id:p for p in delivery.profiles}
        for binding in source.roster_bindings:
            record=next(s for s in profiles[binding.provider_manager_id].franchise_resume.seasons if s.season==source.season.season)
            assert [record.wins,record.losses,record.ties]==by_team[binding.canonical_team_id]
            if record.champion:
                # This pinned fixture has a one-week final in Week 17. A final
                # win corroborates the explicit winner field; it cannot replace it.
                finals=json.loads((Path(root)/f'matchups-{record.season}.json').read_text())['17']
                team=next(t for t in finals if str(t['roster_id'])==binding.provider_roster_id)
                opponent=next(t for t in finals if t.get('matchup_id') is not None
                    and t['matchup_id']==team['matchup_id'] and t['roster_id']!=team['roster_id'])
                def points(t):return t['custom_points'] if t.get('custom_points') is not None else t['points']
                assert points(team)>points(opponent)
    assert sum(s.champion is True for p in delivery.profiles for s in p.franchise_resume.seasons)==4
    assert all(s.champion is None for p in delivery.profiles for s in p.franchise_resume.seasons if not s.season_complete)
    assert not delivery.model_policy_promoted
    total=sum(len(p.model_dump_json().encode()) for p in delivery.profiles)
    assert total<500_000
    print({'cases':len(delivery.cases),'season_records':delivery.coverage['recorded_season_rows'],
        'draft_selections':delivery.coverage['recorded_draft_selections'],'profile_bytes':total})
