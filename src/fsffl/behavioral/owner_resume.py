"""Source-bound franchise facts. No historical forecasts or preference inference."""
from datetime import datetime
from math import isfinite
from typing import Literal
from pydantic import Field, model_validator
from fsffl.state.models import FrozenModel
from fsffl.state.historical_roster_context import _digest


class OwnerTenureBinding(FrozenModel):
    provider_league_id: str
    roster_id: int = Field(gt=0)
    owner_id: str
    season: int
    source_sha256: str


class OwnerTenureAttestation(FrozenModel):
    league_family_id: str
    recorded_at: datetime
    reference: str
    bindings: tuple[OwnerTenureBinding, ...]
    basis: Literal['user_confirmed_unchanged_ownership'] = 'user_confirmed_unchanged_ownership'

    @model_validator(mode='after')
    def scoped(self):
        if not self.reference.strip() or not self.league_family_id.strip() or self.recorded_at.tzinfo is None:
            raise ValueError('tenure attestation needs an aware clock and reference')
        keys=[(b.provider_league_id,b.roster_id,b.season) for b in self.bindings]
        if not keys or len(set(keys))!=len(keys):raise ValueError('unique scoped tenure bindings required')
        for b in self.bindings:
            if not b.owner_id.strip() or len(b.source_sha256)!=64 or any(c not in '0123456789abcdef' for c in b.source_sha256):
                raise ValueError('tenure source identity required')
        return self

    def covers(self, source, roster_id, owner_id, as_of):
        return (self.league_family_id==source.season.league_family_id and self.recorded_at<=as_of
            and any(b.provider_league_id==source.provider_ref.external_id and b.season==source.season.season
                and b.roster_id==int(roster_id) and b.owner_id==owner_id
                and b.source_sha256==source.source_content_sha256 for b in self.bindings))


class OwnerSeasonRecord(FrozenModel):
    season: int
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    ties: int = Field(ge=0)
    points_for: float | None = None
    points_against: float | None = None
    season_complete: bool
    source_sha256: str


class OwnerDraftSelection(FrozenModel):
    season: int
    draft_id: str
    draft_kind: Literal['startup','rookie','other']
    round: int = Field(gt=0)
    pick_no: int = Field(gt=0)
    player_id: str
    player_name: str
    position: str | None = None
    source_sha256: str


class OwnerFranchiseResume(FrozenModel):
    league_family_id: str
    owner_id: str
    evidence_as_of: datetime
    tenure_reference: str
    seasons: tuple[OwnerSeasonRecord,...] = ()
    draft_selections: tuple[OwnerDraftSelection,...] = ()
    # Titles/finishes require bracket evidence; regular-season rank is insufficient.
    model_version: Literal['owner-franchise-resume-v1'] = 'owner-franchise-resume-v1'

    @model_validator(mode='after')
    def coherent(self):
        if self.evidence_as_of.tzinfo is None:raise ValueError('resume requires an aware evidence clock')
        if len({s.season for s in self.seasons})!=len(self.seasons):raise ValueError('duplicate season record')
        if len({(d.draft_id,d.pick_no) for d in self.draft_selections})!=len(self.draft_selections):raise ValueError('duplicate draft selection')
        for s in self.seasons:
            if any(x is not None and not isfinite(x) for x in (s.points_for,s.points_against)):
                raise ValueError('finite recorded scores required')
        return self


def compile_owner_resumes(*, seasons, lineage, rookie_drafts, tenure_attestation, evidence_as_of):
    """Explicit admitted bindings plus user tenure attestation; never infer tenure.

    Reads archived provider standings and completed draft selections. Those are
    observed-at facts, not contemporaneous decision inputs or draft grades.
    """
    if tenure_attestation is None:return {}
    records={};picks={}
    rookie_ids={(d.season,d.draft_id) for d in rookie_drafts}
    for source in lineage.sources:
        data=seasons[source.season]
        if _digest(data)!=source.source_content_sha256:raise ValueError('resume source mismatch')
        bindings={int(b.provider_roster_id):b.provider_manager_id for b in source.roster_bindings}
        raw_rosters={int(r['roster_id']):r for r in data.get('rosters',())}
        for rid,owner in bindings.items():
            if not owner or not tenure_attestation.covers(source,rid,owner,evidence_as_of):continue
            raw=raw_rosters.get(rid,{})
            if str(raw.get('owner_id')or'')!=owner:raise ValueError('resume owner binding contradicts source')
            settings=raw.get('settings')or{}
            counts=[settings.get(k) for k in ('wins','losses','ties')]
            if all(type(n) is int and n>=0 for n in counts):
                def score(key):
                    whole=settings.get(key);decimal=settings.get(key+'_decimal',0)
                    if type(whole) not in (int,float) or type(decimal) not in (int,float):return None
                    value=whole+decimal/100
                    return value if isfinite(value) else None
                records.setdefault(owner,[]).append(OwnerSeasonRecord(season=source.season.season,
                    wins=counts[0],losses=counts[1],ties=counts[2],points_for=score('fpts'),points_against=score('fpts_against'),
                    season_complete=data.get('league',{}).get('status')=='complete',source_sha256=source.source_content_sha256))
        for bundle in data.get('drafts',()):
            draft=bundle.get('draft')or{};did=str(draft.get('draft_id')or'')
            completion=draft.get('last_picked')
            if draft.get('status')!='complete' or type(completion) not in (int,float) or completion>evidence_as_of.timestamp()*1000:continue
            # Purpose is explicitly admitted, not inferred from player age/experience.
            kind='rookie' if (source.season,did) in rookie_ids else 'other'
            for pick in bundle.get('picks',()):
                rid=pick.get('roster_id');owner=bindings.get(rid)
                if not owner or not tenure_attestation.covers(source,rid,owner,evidence_as_of):continue
                if pick.get('picked_by') and str(pick['picked_by'])!=owner:continue
                if type(pick.get('round')) is not int or type(pick.get('pick_no')) is not int:continue
                meta=pick.get('metadata')or{};pid=str(pick.get('player_id')or'')
                if not pid:continue
                name=' '.join(str(meta.get(k)or'').strip() for k in ('first_name','last_name')).strip() or 'Player name unavailable'
                picks.setdefault(owner,[]).append(OwnerDraftSelection(season=source.season.season,draft_id=did,
                    draft_kind=kind,round=pick['round'],pick_no=pick['pick_no'],player_id=pid,player_name=name,
                    position=meta.get('position'),source_sha256=source.source_content_sha256))
    return {owner:OwnerFranchiseResume(league_family_id=tenure_attestation.league_family_id,owner_id=owner,
        evidence_as_of=evidence_as_of,tenure_reference=tenure_attestation.reference,
        seasons=tuple(sorted(records.get(owner,()),key=lambda s:s.season)),
        draft_selections=tuple(sorted(picks.get(owner,()),key=lambda p:(p.season,p.draft_id,p.pick_no))))
        for owner in records.keys()|picks.keys()}
