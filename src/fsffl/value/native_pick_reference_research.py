"""Frozen Career reference authority, distinct from a probability distribution.

Consumes complete prospective slot authorities supplied by existing Value owners.
Does not fit a model, create a Career tail or invent probabilistic uncertainty.
"""
from datetime import datetime
from math import fsum, isfinite
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.models import DraftPick, FrozenModel
from .career_forward_intrinsic import CareerForwardModelAuthority
from .native_pick_curve_releases import NativePickCurveRelease, fingerprint, validate_native_pick_curve_attachment
from .origin_aware_pick import OriginPickProbabilityEvidence

REFERENCE_VERSION = 'season-stable-native-pick-career-reference-research-v1'


class FrozenCareerReferenceSlot(FrozenModel):
    slot_in_round: Annotated[int, Field(ge=1)]
    authority: CareerForwardModelAuthority | None

    @model_validator(mode='after')
    def finite_authority(self):
        if self.authority is not None and any(not isfinite(v) for v in self.authority.model_dump().values()):
            raise ValueError('Career reference authority must remain finite')
        return self


class FrozenNativePickReferenceCurve(FrozenModel):
    release: NativePickCurveRelease
    source_as_of: datetime
    source_fingerprints: Annotated[tuple[str,...], Field(min_length=1)]
    forecast_model_version: str
    authority_basis_model_versions: Annotated[tuple[str,...], Field(min_length=1)]
    slots: tuple[FrozenCareerReferenceSlot,...]
    horizon: Literal['career'] = 'career'
    point_basis: Literal['model_reference'] = 'model_reference'
    authority_kind: Literal['model_authority_envelope_not_predictive_interval'] = 'model_authority_envelope_not_predictive_interval'
    evidence_kind: Literal['prospective_governed_career_slot_authorities'] = 'prospective_governed_career_slot_authorities'
    production_eligible: Literal[False] = False
    model_version: Literal[REFERENCE_VERSION] = REFERENCE_VERSION

    @model_validator(mode='after')
    def complete_slot_coordinate(self):
        if self.source_as_of.tzinfo is None or self.source_as_of>self.release.released_at:
            raise ValueError('reference evidence must be available at release')
        if sorted(s.slot_in_round for s in self.slots)!=list(range(1,self.release.team_count+1)):
            raise ValueError('reference curve must explicitly retain every slot')
        if any(not x.strip() for x in (self.forecast_model_version,*self.source_fingerprints,*self.authority_basis_model_versions)):
            raise ValueError('reference curve requires source provenance')
        return self

    @property
    def curve_id(self):
        return fingerprint(self.model_dump(mode='json'))


class ResearchPickReference(FrozenModel):
    pick_id: str
    original_team_id: str
    owner_team_id: str
    curve_id: str
    authority: CareerForwardModelAuthority | None
    missing_slots: tuple[int,...]
    input_fingerprint: str
    source_fingerprints: tuple[str,...]
    point_basis: Literal['model_reference'] = 'model_reference'
    authority_kind: Literal['weighted_outer_model_authority_not_predictive_interval'] = 'weighted_outer_model_authority_not_predictive_interval'
    production_eligible: Literal[False] = False


def apply_frozen_native_pick_reference_curve(curve: FrozenNativePickReferenceCurve, pick: DraftPick, *,
    owner_team_id: str, probabilities: OriginPickProbabilityEvidence, as_of: datetime,
    economic_scope_id: str, rules_signature: str, scoring_signature: str, native_coordinate_id: str,
    evaluation_season: int, team_count: int) -> ResearchPickReference:
    validate_native_pick_curve_attachment(curve.release,pick,owner_team_id=owner_team_id,
        probabilities=probabilities,as_of=as_of,economic_scope_id=economic_scope_id,
        rules_signature=rules_signature,scoring_signature=scoring_signature,native_coordinate_id=native_coordinate_id,
        evaluation_season=evaluation_season,team_count=team_count)
    by_slot={s.slot_in_round:s.authority for s in curve.slots}
    missing=tuple(p.slot_in_round for p in probabilities.slot_probabilities if by_slot[p.slot_in_round] is None)
    authority=None
    if not missing:
        # Weighted bounds are model-authority bounds, never mixture quantiles/stddev.
        totals={key:fsum(p.probability*getattr(by_slot[p.slot_in_round],key) for p in probabilities.slot_probabilities)
            for key in ('low','reference_center','high')}
        if any(not isfinite(v) for v in totals.values()):raise ValueError('reference mixture must remain finite')
        authority=CareerForwardModelAuthority(**totals,width=totals['high']-totals['low'])
    return ResearchPickReference(pick_id=pick.pick_id,original_team_id=pick.original_team_id,
        owner_team_id=owner_team_id,curve_id=curve.curve_id,authority=authority,missing_slots=missing,
        input_fingerprint=fingerprint(dict(curve_id=curve.curve_id,pick=pick.model_dump(mode='json'),
            owner=owner_team_id,probabilities=probabilities.model_dump(mode='json'),as_of=as_of.isoformat())),
        source_fingerprints=(*curve.source_fingerprints,probabilities.simulation_input_fingerprint))
