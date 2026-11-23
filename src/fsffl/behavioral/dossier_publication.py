"""Guarded attachment of admitted historical facts to current owner profiles.

Administrative/background publication only. No provider acquisition, schema,
profile-count replacement, learned policy or request-time history computation.
"""
from dataclasses import dataclass
from typing import Literal
from fsffl.state.models import FrozenModel
from fsffl.state.historical_roster_context import _digest
from .models import OwnerBehaviorProfile
from .historical_case_models import OwnerHistoricalTradeCase
from .owner_resume import OwnerFranchiseResume
from .historical_cases import attach_historical_owner_cases


class PreparedOwnerDossier(FrozenModel):
    league_family_id: str
    current_provider_league_id: str
    cases: tuple[OwnerHistoricalTradeCase,...] = ()
    resumes: tuple[OwnerFranchiseResume,...] = ()
    version: Literal['prepared-owner-dossier-v1'] = 'prepared-owner-dossier-v1'


def prepare_owner_dossier(delivery, *, current_provider_league_id):
    families={p.league_family_id for p in delivery.profiles}
    if len(families)!=1:raise ValueError('one owner dossier family required')
    return PreparedOwnerDossier(league_family_id=next(iter(families)),
        current_provider_league_id=current_provider_league_id,cases=delivery.cases,
        resumes=tuple(p.franchise_resume for p in delivery.profiles if p.franchise_resume is not None))


class DossierPublicationConflict(RuntimeError):
    """A refresh changed the inputs; never overwrite it with a stale attachment."""


def profile_snapshot(profiles):
    return _digest(sorted((p.owner_id,p.model_dump(mode='json')) for p in profiles))


def event_snapshot(events):
    return _digest(sorted((e.event_id,e.model_dump(mode='json')) for e in events))


def validate_enrichment(expected, profiles):
    """Attachment cannot change owners, clocks, counts or existing model fields."""
    if not expected:raise ValueError('existing production owner profiles required')
    old={(p.league_family_id,p.owner_id):p for p in expected}
    new={(p.league_family_id,p.owner_id):p for p in profiles}
    if len(old)!=len(expected) or len(new)!=len(profiles) or set(old)!=set(new):
        raise ValueError('dossier publication must preserve profile membership')
    if len({family for family,_ in old})!=1:raise ValueError('one publication family required')
    for key,previous in old.items():
        before=previous.model_dump();after=new[key].model_dump()
        for name in ('historical_trade_cases','franchise_resume'):
            before.pop(name);after.pop(name)
        if before!=after:raise ValueError('dossier publication cannot replace current profile truth')
    return next(iter(old))[0]


@dataclass(frozen=True)
class DossierPublicationResult:
    profiles: tuple[OwnerBehaviorProfile,...]
    changed_profiles: int
    attached_cases: int
    attached_resumes: int
    skipped_future_resumes: int
    published: bool


def publish_owner_dossier(*, store, user_id, prepared, publish=False):
    """Read current durable truth; attach only historical fields with an atomic lease.

    Default is a dry run. A private, already admitted prepared bundle is not an
    alternative source of current events/profiles. No web API accepts this bundle.
    """
    context=store.load_runtime_context(user_id)
    if (context is None or context['league_family_id']!=prepared.league_family_id
            or context['sleeper_league_external_id']!=prepared.current_provider_league_id):
        raise ValueError('dossier publication requires matching durable user/league context')
    previous=store.load_profiles(prepared.league_family_id)
    events=store.load_events(prepared.league_family_id)
    if not previous:raise ValueError('current owner history must be built before dossier publication')
    if any(c.league_family_id!=prepared.league_family_id for c in prepared.cases):
        raise ValueError('foreign-family historical case')
    if any(r.league_family_id!=prepared.league_family_id for r in prepared.resumes):
        raise ValueError('foreign-family franchise resume')
    resumes={r.owner_id:r for r in prepared.resumes}
    if len(resumes)!=len(prepared.resumes):raise ValueError('duplicate owner resume')
    future=sum(r.evidence_as_of>p.as_of for p in previous for r in prepared.resumes if r.owner_id==p.owner_id)
    updated=enrich_current_profiles(previous,events=events,prepared=prepared)
    changed=sum(a!=b for a,b in zip(previous,updated))
    if publish and changed:
        store.put_profile_enrichment_if_unchanged(expected_profiles=previous,profiles=updated,expected_events=events)
    return DossierPublicationResult(updated,changed,
        sum(len(p.historical_trade_cases) for p in updated),
        sum(p.franchise_resume is not None for p in updated),future,publish and bool(changed))


DOSSIER_ARTIFACT_KIND='admitted_owner_dossier'


def dossier_artifact(prepared, *, computed_at):
    """One immutable admitted revision in the existing artifact store."""
    from fsffl.persistence.contracts import ArtifactKey,ReusableArtifactRecord
    payload=prepared.model_dump(mode='json')
    if len(prepared.model_dump_json().encode())>2_000_000:raise ValueError('compact dossier exceeds publication budget')
    return ReusableArtifactRecord(key=ArtifactKey(artifact_kind=DOSSIER_ARTIFACT_KIND,
        scope_kind='league_family',scope_id=prepared.league_family_id,
        input_fingerprint=_digest(payload),model_version=prepared.version),payload=payload,computed_at=computed_at)


def load_admitted_dossier(artifact_store, *, family_id, current_provider_league_id):
    """Called only during the existing owned Behavioral refresh, never a GET."""
    record=artifact_store.get_latest_reusable_artifact(artifact_kind=DOSSIER_ARTIFACT_KIND,
        scope_kind='league_family',scope_id=family_id,model_version='prepared-owner-dossier-v1')
    if record is None:return None
    prepared=PreparedOwnerDossier.model_validate(record.payload)
    if (prepared.league_family_id!=family_id or prepared.current_provider_league_id!=current_provider_league_id
            or record.key.input_fingerprint!=_digest(record.payload)):
        raise ValueError('admitted dossier artifact identity mismatch')
    return prepared


def enrich_current_profiles(profiles, *, events, prepared):
    """Share the same event-prefix and cutoff gates as administrative publication."""
    if any(p.league_family_id!=prepared.league_family_id for p in profiles):
        raise ValueError('foreign-family dossier publication')
    if any(c.league_family_id!=prepared.league_family_id for c in prepared.cases):
        raise ValueError('foreign-family historical case')
    resumes={r.owner_id:r for r in prepared.resumes}
    if len(resumes)!=len(prepared.resumes) or any(r.league_family_id!=prepared.league_family_id for r in resumes.values()):
        raise ValueError('invalid dossier resume scope')
    enriched=attach_historical_owner_cases(profiles,events=events,cases=prepared.cases)
    result=[]
    for profile in enriched:
        resume=resumes.get(profile.owner_id)
        if resume is not None and resume.evidence_as_of<=profile.as_of and (
                profile.franchise_resume is None or profile.franchise_resume.evidence_as_of<=resume.evidence_as_of):
            profile=OwnerBehaviorProfile.model_validate({**profile.model_dump(),'franchise_resume':resume})
        result.append(profile)
    validate_enrichment(profiles,result)
    return tuple(result)
