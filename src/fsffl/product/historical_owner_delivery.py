"""Explicit offline composition of admitted sources into owner-profile evidence.

No acquisition, DB adapter, web request job or new calculation authority. The
caller owns admitted inputs and publication through the existing profile store.
"""
from collections import Counter
from dataclasses import dataclass
from fsffl.behavioral.historical_cases import compile_historical_owner_case,attach_historical_owner_cases,historical_activity_witness
from fsffl.behavioral.historical_circumstances import build_historical_trade_circumstances
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.owner_resume import compile_owner_resumes
from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.sleeper_history import normalize_sleeper_behavior_transaction
from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context


@dataclass(frozen=True)
class HistoricalOwnerDelivery:
    profiles: tuple
    events: tuple
    cases: tuple
    coverage: dict
    model_policy_promoted: bool = False


def build_historical_owner_delivery(*,seasons,lineage,rookie_drafts,source_revision,source_observed_at,
        production_by_previous_season,results,player_names,supplemental_movements=None,
        observed_events=None,profiles=None,tenure_attestation=None):
    """One bounded path from sources through cases to the existing profile model.

    Research callers may create descriptive profiles from the supplied archive.
    Publishing into a live store requires its existing events/profiles instead;
    no archive cohort is represented as complete current production history.
    """
    integration=build_sleeper_historical_context(seasons=seasons,lineage=lineage,rookie_drafts=rookie_drafts,
        source_revision=source_revision,source_observed_at=source_observed_at,
        supplemental_movements=supplemental_movements)
    sources={s.season:s for s in lineage.sources}
    histories={ (h.league_family_id,h.provider_league_id,h.season):h for h in integration.roster_histories }
    normalized=[]
    for identity,data in seasons.items():
        source=sources[identity]
        mapping={int(b.provider_roster_id):b.provider_manager_id for b in source.roster_bindings if b.provider_manager_id is not None}
        seen=set()
        for raw in data.get('transactions',()):
            tid=str(raw.get('transaction_id')or'')
            if tid in seen:raise ValueError('duplicate source transaction requires reconciliation')
            seen.add(tid)
            normalized.extend(normalize_sleeper_behavior_transaction(raw,family_id=identity.league_family_id,
                league_external_id=source.provider_ref.external_id,season=identity.season,
                owner_by_roster=mapping,player_positions={}))
    events=tuple(normalized)if observed_events is None else tuple(observed_events)
    events_by_id={e.event_id:e for e in events}
    if len(events_by_id)!=len(events):raise ValueError('duplicate owner event identity')
    family_ids={identity.league_family_id for identity in seasons}
    if len(family_ids)!=1:raise ValueError('one isolated family per owner delivery')
    if any(e.league_family_id not in family_ids for e in events):raise ValueError('foreign-family event in delivery')
    cases=[];blockers=Counter();seen_trade_groups=set();activity_witnesses={}
    for row in integration.trades.rows:
        request=row.request;identity=request.season;source=sources[identity]
        group=(identity.league_family_id,request.transaction_id)
        if group in seen_trade_groups:raise ValueError('cross-season trade overlap requires explicit reconciliation')
        seen_trade_groups.add(group)
        history=histories[(identity.league_family_id,source.provider_ref.external_id,identity.season)]
        if identity not in activity_witnesses:
            through=max(s.effective_at for s in history.snapshots if s.effective_at is not None)
            activity_witnesses[identity]=historical_activity_witness(normalized,league_family_id=identity.league_family_id,
                provider_league_id=source.provider_ref.external_id,through=through)
        circumstances=build_historical_trade_circumstances(coverage=row,history=history,lineage=lineage,
            prior_production=production_by_previous_season.get(identity.season-1),results=tuple(results))
        for rid in request.participant_roster_ids:
            eid=f'sleeper:{source.provider_ref.external_id}:{request.transaction_id}:roster:{rid}'
            event=events_by_id.get(eid)
            if event is None:blockers['observed_event_unavailable']+=1;continue
            compiled=compile_historical_owner_case(event=event,circumstances=circumstances,history=history,
                source=source,season_data=seasons[identity],player_names=player_names,evidence_as_of=source_observed_at,
                activity_witness=activity_witnesses[identity],tenure_attestation=tenure_attestation)
            if compiled.case is not None:cases.append(compiled.case)
            blockers.update(compiled.blockers)
    base_profiles=tuple(profiles)if profiles is not None else build_owner_behavior_profiles(events,as_of=source_observed_at)
    if any(p.league_family_id not in family_ids for p in base_profiles):raise ValueError('foreign profile family in delivery')
    enriched=attach_historical_owner_cases(base_profiles,events=events,cases=cases)
    resumes=compile_owner_resumes(seasons=seasons,lineage=lineage,rookie_drafts=rookie_drafts,
        tenure_attestation=tenure_attestation,evidence_as_of=source_observed_at)
    enriched=tuple(OwnerBehaviorProfile.model_validate({**p.model_dump(),'franchise_resume':resumes.get(p.owner_id,p.franchise_resume)}) for p in enriched)
    coverage={**integration.trades.summary(),'compiled_initiator_cases':sum(c.attribution_basis=='initiating_account_and_admitted_roster_binding' for c in cases),
        'compiled_attested_cases':sum(c.attribution_basis=='user_attested_tenure_and_admitted_roster_binding' for c in cases),
        'compiled_cases':len(cases),'profiles_with_resume':sum(p.franchise_resume is not None for p in enriched),
        'recorded_season_rows':sum(len(r.seasons) for r in resumes.values()),
        'recorded_draft_selections':sum(len(r.draft_selections) for r in resumes.values()),
        'profile_cases':sum(len(p.historical_trade_cases)for p in enriched),
        'profiles_with_cases':sum(bool(p.historical_trade_cases)for p in enriched),
        'case_blocker_counts':dict(sorted(blockers.items())),
        'grounded_statements':sum(len(c.context_sentences)for c in cases),
        'predictive_policy_promoted':False,'owner_model_training_rows_admitted':0}
    return HistoricalOwnerDelivery(enriched,events,tuple(cases),coverage)
