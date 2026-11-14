"""Immutable seasonal slot economics; probability application is a separate read.

Research-only until the native outcome model is validated. No provider, forecast
fitter, persistence connection, State refresh or scheduler is owned by Value.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.models import DraftPick, FrozenModel
from .models import PickValueEstimate, ValueDistribution, ValueScale
from .native_pick_research import (MODEL_VERSION as NATIVE_MODEL_VERSION,
    NativePickResearchEvidence, ResearchNativePickResult, ResearchPickHorizon,
    native_slot_research_distribution)
from .origin_aware_pick import OriginPickProbabilityEvidence
from .pick import PickOutcome, PickOutcomeSet, estimate_pick_value

CURVE_VERSION='season-stable-native-pick-curve-research-v1'


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class NativePickCurveRelease(FrozenModel):
    economic_scope_id: str  # widest safe source/eligibility/data-rights scope, private when needed
    evaluation_season: Annotated[int, Field(ge=1900, le=2300)]
    draft_season: Annotated[int, Field(ge=1900, le=2300)]
    round: Annotated[int, Field(ge=1)]
    team_count: Annotated[int, Field(ge=1)]
    rules_signature: str
    scoring_signature: str
    native_coordinate_id: str
    stage: Literal['annual_baseline','post_declarations','post_nfl_draft','correction']
    revision: Annotated[int, Field(ge=1)] = 1
    released_at: datetime
    event_evidence_refs: Annotated[tuple[str, ...], Field(min_length=1)]
    supersedes_curve_id: str | None = None
    correction_reason: str | None = None

    @model_validator(mode='after')
    def release_identity(self):
        if self.released_at.tzinfo is None:
            raise ValueError('curve release requires a timezone-aware timestamp')
        identifiers=(self.economic_scope_id,self.rules_signature,self.scoring_signature,
            self.native_coordinate_id,*self.event_evidence_refs)
        if any(not x.strip() for x in identifiers):
            raise ValueError('curve scope, coordinate and event evidence cannot be blank')
        if self.draft_season<self.evaluation_season:
            raise ValueError('draft must not precede the annual evaluation season')
        if self.stage=='annual_baseline' and (self.revision!=1 or self.supersedes_curve_id is not None):
            raise ValueError('annual baseline is first edition; revisions require an explicit correction release')
        if self.stage!='annual_baseline' and not (self.supersedes_curve_id or '').strip():
            raise ValueError('later stages require the exact superseded curve identity')
        if (self.stage=='correction' or self.revision>1) and not (self.correction_reason or '').strip():
            raise ValueError('corrections require a documented reason')
        return self

    @property
    def economic_scope_key(self):
        # Deliberately excludes league State, user/team/owner, refresh time and probabilities.
        return fingerprint({k:getattr(self,k) for k in ('economic_scope_id','evaluation_season',
            'draft_season','round','team_count','rules_signature','scoring_signature','native_coordinate_id')})


class FrozenNativePickSlot(FrozenModel):
    slot_in_round: Annotated[int, Field(ge=1)]
    three_year: ValueDistribution | None
    career: ValueDistribution | None

    @model_validator(mode='after')
    def finite_values(self):
        for value in (self.three_year,self.career):
            if value is not None and any(not isfinite(x) for x in
                (value.mean,value.stddev,*(q for q in (value.p10,value.p50,value.p90) if q is not None))):
                raise ValueError('frozen slot economics must be finite')
        return self


class FrozenNativePickCurve(FrozenModel):
    release: NativePickCurveRelease
    source_as_of: datetime
    forecast_model_version: str
    source_fingerprints: Annotated[tuple[str, ...], Field(min_length=1)]
    native_input_fingerprint: str
    slots: tuple[FrozenNativePickSlot, ...]
    production_eligible: Literal[False] = False
    model_version: Literal[CURVE_VERSION] = CURVE_VERSION

    @model_validator(mode='after')
    def coverage_and_time(self):
        if self.source_as_of.tzinfo is None or self.source_as_of>self.release.released_at:
            raise ValueError('source evidence must be available at curve release')
        if any(not x.strip() for x in (self.forecast_model_version,self.native_input_fingerprint,*self.source_fingerprints)):
            raise ValueError('frozen curve requires source identities')
        if sorted(x.slot_in_round for x in self.slots)!=list(range(1,self.release.team_count+1)):
            raise ValueError('curve must explicitly cover every slot, including missing horizon values')
        return self

    @property
    def curve_id(self):
        return fingerprint(self.model_dump(mode='json'))


def freeze_native_pick_research_curve(evidence: NativePickResearchEvidence, release: NativePickCurveRelease):
    """Explicit annual/staged producer action. Never called by a refresh reader."""
    for name in ('evaluation_season','draft_season','round','team_count','rules_signature',
                 'scoring_signature','native_coordinate_id'):
        if getattr(evidence,name)!=getattr(release,name):
            raise ValueError('source does not match the curve economic scope')
    if evidence.evidence_as_of>release.released_at:
        raise ValueError('curve source cannot postdate release')
    by_slot={s.slot_in_round:s for s in evidence.slot_forecasts}
    slots=tuple(FrozenNativePickSlot(slot_in_round=slot,
        three_year=native_slot_research_distribution(by_slot.get(slot),evidence,'three_year'),
        career=native_slot_research_distribution(by_slot.get(slot),evidence,'career'))
        for slot in range(1,release.team_count+1))
    # Ownership and origin probabilities do not participate in slot economics.
    inputs=evidence.model_dump(mode='json',exclude={'pick_id','owner_team_id','original_team_id','slot_evidence'})
    return FrozenNativePickCurve(release=release,source_as_of=evidence.evidence_as_of,
        forecast_model_version=evidence.forecast_model_version,source_fingerprints=evidence.source_fingerprints,
        native_input_fingerprint=fingerprint(inputs),slots=slots)


def apply_frozen_native_pick_curve(curve: FrozenNativePickCurve, pick: DraftPick, *, owner_team_id: str,
    probabilities: OriginPickProbabilityEvidence, as_of: datetime, economic_scope_id: str,
    rules_signature: str, scoring_signature: str, native_coordinate_id: str,
    evaluation_season: int, team_count: int):
    """Cheap mixture only: no annual trajectories, model calls or source fetching."""
    release=curve.release
    if as_of.tzinfo is None or release.released_at>as_of:
        raise ValueError('curve release must be available at the requested cutoff')
    for key,value in (('economic_scope_id',economic_scope_id),('rules_signature',rules_signature),
                      ('scoring_signature',scoring_signature),('native_coordinate_id',native_coordinate_id),
                      ('evaluation_season',evaluation_season),('team_count',team_count)):
        if getattr(release,key)!=value:
            raise ValueError('pick does not match the curve economic scope')
    if pick.season!=release.draft_season or pick.round!=release.round:
        raise ValueError('pick draft year and round must match the frozen curve')
    if (probabilities.original_team_id!=pick.original_team_id or probabilities.draft_season!=pick.season
        or any(x.slot_in_round>release.team_count for x in probabilities.slot_probabilities)):
        raise ValueError('probabilities must match the pick origin, draft year and legal slots')
    if not owner_team_id.strip():
        raise ValueError('current owner must be explicit')
    by_slot={x.slot_in_round:x for x in curve.slots};results={}
    for horizon in ('three_year','career'):
        missing=tuple(p.slot_in_round for p in probabilities.slot_probabilities
                      if getattr(by_slot[p.slot_in_round],horizon) is None)
        estimate=None
        if not missing:
            try:
                estimate=estimate_pick_value(PickOutcomeSet(outcomes=tuple(PickOutcome(slot=p.slot_in_round,
                    probability=p.probability,value=getattr(by_slot[p.slot_in_round],horizon))
                    for p in probabilities.slot_probabilities)),asset_id=pick.pick_id,
                    scale=ValueScale(scale_id=f'research-native-shapley:{horizon}:{release.native_coordinate_id}',
                        version=NATIVE_MODEL_VERSION,unit_label=f'{horizon} raw Shapley contribution'),
                    as_of=as_of,draft_season=pick.season,round=pick.round,model_version=CURVE_VERSION,
                    class_strength_model_version=curve.forecast_model_version,
                    slot_uncertainty_model_version=probabilities.draft_order_projection_model_version)
            except OverflowError as exc:
                raise ValueError('native pick mixture must remain finite') from exc
            if not isfinite(estimate.distribution.mean) or not isfinite(estimate.distribution.stddev):
                raise ValueError('native pick mixture must remain finite')
        results[horizon]=ResearchPickHorizon(status='unavailable' if missing else 'research_only',estimate=estimate,
            missing_slots=missing,discounting_applied=horizon=='three_year',
            reason='Missing frozen slot economics' if missing else 'Research-only frozen slot release; current origin probabilities applied')
    return ResearchNativePickResult(pick_id=pick.pick_id,original_team_id=pick.original_team_id,owner_team_id=owner_team_id,
        input_fingerprint=fingerprint({'curve_id':curve.curve_id,'pick':pick.model_dump(mode='json'),
            'owner':owner_team_id,'probabilities':probabilities.model_dump(mode='json'),'as_of':as_of.isoformat()}),
        source_fingerprints=(*curve.source_fingerprints,curve.curve_id,probabilities.simulation_input_fingerprint),**results)
