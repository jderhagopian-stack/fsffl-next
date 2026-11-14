"""Read-only research projection of frozen pick priors beside published players.

No runtime imports this module. Metadata here is supplied evidence, not an
approval authority. Every result stays research-only, including shared-game cases.
There is no fitting, source acquisition, persistence, cache or publication owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from types import MappingProxyType
from typing import Annotated, Literal, Mapping
from weakref import ReferenceType, ref

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueState, PickAsset, PlayerAsset
from fsffl.value.career_tail import lineup_capacity_signature
from fsffl.value.models import AssetValueProfile, IntrinsicDynastyValueEstimate, ValueDistribution, ValueScale
from fsffl.value.native_pick_curve_releases import FrozenNativePickCurve, apply_frozen_native_pick_curve, fingerprint
from fsffl.value.origin_aware_pick import OriginPickProbabilityEvidence
from fsffl.value.shapley_intrinsic import FROZEN_INTRINSIC_DISCOUNT
from fsffl.value.native_pick_reference_research import FrozenNativePickReferenceCurve, apply_frozen_native_pick_reference_curve
from .economics import summarize_bilateral_trade_economics
from .economic_net import calculate_bilateral_economic_net
from .intrinsic_roster_economics import adjust_bilateral_intrinsic_net_for_mandatory_cuts
from .models import BilateralTradeProposal
from .roster_legality import TeamRosterLegalityResolution
from .scenario import _validate_leg_ownership

VERSION = 'research-native-pick-player-binding-v1'
Horizon = Literal['three_year', 'career']
BASIS = {'three_year':f'evaluation_calendar_y1_y3_discount_{FROZEN_INTRINSIC_DISCOUNT}',
         'career':'undiscounted_y1_y7_plus_y8_terminal'}


def scoring_signature(state: LeagueState) -> str:
    """Research metadata convention over canonical scoring rows, not a scorer."""
    rows = [r.model_dump(mode='json') for r in state.league.rules.scoring]
    return fingerprint(sorted(rows, key=fingerprint))


def _freeze(value):
    if isinstance(value,dict):return MappingProxyType({k:_freeze(v) for k,v in value.items()})
    if isinstance(value,(list,tuple)):return tuple(_freeze(v) for v in value)
    return value


def _thaw(value):
    if isinstance(value,Mapping):return {k:_thaw(v) for k,v in value.items()}
    if isinstance(value,tuple):return [_thaw(v) for v in value]
    return value


class ResearchEconomicContext(FrozenModel):
    horizon: Horizon
    evaluation_season: int
    team_count: int
    rules_signature: str
    scoring_signature: str
    economic_scope_id: str
    native_coordinate_id: str
    horizon_basis: str
    current_season_basis: Literal['governed_full_season','remaining_from_cutoff']
    point_basis: Literal['expected_mean','model_reference']
    allocation_basis: Literal['joint_game','frozen_reference_append','estimated_prior']
    eligibility_policy_id: str
    population_policy_id: str
    model_policy_id: str
    game_fingerprint: str | None = None
    metric: Literal['raw_shapley'] = 'raw_shapley'

    @model_validator(mode='after')
    def semantics(self):
        if self.horizon_basis != BASIS[self.horizon]:
            raise ValueError('research binding requires the accepted horizon semantics')
        if any(isinstance(v,str) and not v.strip() for v in self.model_dump().values()):
            raise ValueError('economic context identifiers cannot be blank')
        return self

    @property
    def policy_key(self):
        # Changes in live forecasts do not refit a frozen prior or mint a new policy.
        return fingerprint(self.model_dump(mode='json', exclude={'game_fingerprint'}))

    @property
    def semantics_key(self):
        return fingerprint(self.model_dump(mode='json', exclude={
            'game_fingerprint','population_policy_id','model_policy_id','allocation_basis'}))


class ResearchPlayerPublication(FrozenModel):
    user_id: str
    league_id: str
    state_id: str
    generation_id: str
    as_of: datetime
    context: ResearchEconomicContext
    source_fingerprint: str
    source_scale: ValueScale
    values: tuple[tuple[str, float | None], ...]
    input_assumptions: tuple[tuple[str,str], ...] = ()
    source_limitations: tuple[str,...] = ()

    @model_validator(mode='after')
    def valid_source(self):
        if self.as_of.tzinfo is None:
            raise ValueError('player publication requires an aware cutoff')
        if not self.source_scale.scale_id.startswith('raw-shapley:'):
            raise ValueError('player source must retain the native raw publication scale')
        if len({pid for pid,_ in self.values}) != len(self.values):
            raise ValueError('duplicate player value identity')
        if len({pid for pid,_ in self.input_assumptions}) != len(self.input_assumptions):
            raise ValueError('duplicate player assumption identity')
        if any(not pid.strip() or not assumption.strip() for pid,assumption in self.input_assumptions):
            raise ValueError('player assumption identifiers and descriptions cannot be blank')
        if any(v is not None and not isfinite(v) for _,v in self.values):
            raise ValueError('player means must be finite or missing')
        if any(not x.strip() for x in (self.user_id,self.league_id,self.state_id,
                                      self.generation_id,self.source_fingerprint,*(pid for pid,_ in self.values))):
            raise ValueError('publication source identifiers cannot be blank')
        return self


class ResearchPickAttachment(FrozenModel):
    pick_id: str
    state_id: str
    as_of: datetime
    availability: Literal['available','exercised','expired','unknown']
    inventory_evidence_ref: str
    selected_player_id: str | None = None
    source_qualifications: tuple[str,...] = ()
    curve: FrozenNativePickCurve | FrozenNativePickReferenceCurve | None = None
    prior_context: ResearchEconomicContext | None = None
    probabilities: OriginPickProbabilityEvidence | None = None
    probability_source_state_id: str | None = None
    probability_as_of: datetime | None = None
    probability_round: int | None = None

    @model_validator(mode='after')
    def valid_inventory(self):
        if self.as_of.tzinfo is None or (self.probability_as_of is not None and self.probability_as_of.tzinfo is None):
            raise ValueError('pick evidence requires aware cutoffs')
        if self.availability=='available' and self.selected_player_id is not None:
            raise ValueError('an exercised selection cannot remain an available pick')
        if any(not x.strip() for x in (self.pick_id,self.state_id,self.inventory_evidence_ref)):
            raise ValueError('pick inventory evidence must identify its source')
        return self


class ResearchCompatibilityAssessment(FrozenModel):
    curve_id: str
    prior_context_fingerprint: str
    live_policy_key: str
    horizon: Horizon
    mode: Literal['shared_game','frozen_prior_approximation']
    reviewed_at: datetime
    evidence_refs: Annotated[tuple[str, ...], Field(min_length=1)]
    production_eligible: Literal[False] = False

    @model_validator(mode='after')
    def referenced_assessment(self):
        if self.reviewed_at.tzinfo is None or any(not x.strip() for x in (
            self.curve_id,self.prior_context_fingerprint,self.live_policy_key,*self.evidence_refs)):
            raise ValueError('compatibility research needs an aware, referenced assessment')
        return self


@dataclass(frozen=True)
class ResearchMixedRead:
    user_id: str
    league_id: str
    generation_id: str
    as_of: datetime
    state_ref: ReferenceType[LeagueState]
    horizon: Horizon
    scale: ValueScale
    profiles: Mapping[str, AssetValueProfile]
    cut_values: Mapping[str, float]
    provenance: Mapping[str, object]
    pick_qualifications: tuple[Mapping[str, object], ...]


def prepare_research_mixed_read(state: LeagueState, *, user_id: str, generation_id: str,
    players: ResearchPlayerPublication, picks: tuple[ResearchPickAttachment, ...],
    assessments: tuple[ResearchCompatibilityAssessment, ...] = ()) -> ResearchMixedRead:
    """Project once per research read; package binding below performs no mixtures.

    Callers supply already-owned evidence. This consistency checker is not an
    authentication or publication-proof service and is not a live admission path.
    """
    context=players.context;rules=state.league.rules;state_id=state.state_id
    live_policy_key=context.policy_key;semantic_key=context.semantics_key
    curve_ids={}
    def curve_id_of(curve):
        if id(curve) not in curve_ids:curve_ids[id(curve)]=curve.curve_id
        return curve_ids[id(curve)]
    if ((players.user_id,players.league_id,players.state_id,players.generation_id,players.as_of) !=
        (user_id,state.league.league_id,state_id,generation_id,state.as_of)):
        raise ValueError('player publication does not match the current request')
    if (context.metric!='raw_shapley' or context.horizon_basis!=BASIS[context.horizon]
        or context.evaluation_season!=state.league.season or context.team_count!=rules.team_count
        or context.rules_signature!=lineup_capacity_signature(rules) or context.scoring_signature!=scoring_signature(state)):
        raise ValueError('player economic context does not match canonical rules/season')
    if len({p.pick_id for p in picks})!=len(picks):
        raise ValueError('duplicate pick attachment')
    player_ids={p.player_id for p in state.players};pick_map={p.pick_id:p for p in state.draft_picks}
    if any(pid not in player_ids for pid,_ in players.values):
        raise ValueError('player projection contains a noncanonical identity')
    if player_ids.intersection(pick_map):
        raise ValueError('player and pick identifiers cannot alias in the economic adapter')
    values={pid:value for pid,value in players.values if value is not None};pick_values={};qualifications=[]
    for attachment in picks:
        pick=pick_map.get(attachment.pick_id);reason=None;mode=None;value=None;source_authority=None
        if (pick is None or attachment.state_id!=state_id or attachment.as_of!=state.as_of):
            raise ValueError('pick attachment does not match canonical State')
        if pick.league_id!=state.league.league_id or pick.season<state.league.season:
            reason='pick_outside_current_selection_right'
        elif attachment.availability!='available':reason='selection_right_'+attachment.availability
        elif rules.rookie_draft_rounds and pick.round>rules.rookie_draft_rounds:
            reason='pick_round_not_supported_by_canonical_rules'
        elif context.horizon=='three_year' and pick.season>state.league.season+2:
            value=0.;mode='calendar_structural_zero'  # No model, probability or Career zero inferred.
        elif attachment.curve is None or attachment.prior_context is None:reason='curve_context_unavailable'
        else:
            curve=attachment.curve;prior=attachment.prior_context;release=curve.release
            reference_curve=isinstance(curve,FrozenNativePickReferenceCurve)
            expected_basis='model_reference' if reference_curve else 'expected_mean'
            if prior.point_basis!=expected_basis:reason='curve_point_authority_mismatch'
            elif reference_curve and context.horizon!='career':reason='curve_horizon_mismatch'
            elif (prior.semantics_key!=semantic_key or prior.horizon!=context.horizon
                or any(getattr(prior,k)!=getattr(release,k) for k in ('evaluation_season','team_count',
                    'rules_signature','scoring_signature','economic_scope_id','native_coordinate_id'))):
                reason='economic_semantics_mismatch'
            elif attachment.probabilities is None:reason='slot_probabilities_unavailable'
            elif (attachment.probability_source_state_id!=state_id or attachment.probability_as_of is None
                  or attachment.probability_as_of>state.as_of or attachment.probability_round!=pick.round):reason='slot_probability_context_mismatch'
            else:
                matches=[r for r in assessments if r.curve_id==curve_id_of(curve) and r.horizon==context.horizon
                    and r.prior_context_fingerprint==fingerprint(prior.model_dump(mode='json'))
                    and r.live_policy_key==live_policy_key and r.reviewed_at<=state.as_of]
                if len(matches)!=1:reason='compatibility_assessment_missing_or_ambiguous'
                else:
                    assessment=matches[0]
                    if assessment.mode=='shared_game' and (prior.allocation_basis!='joint_game' or context.allocation_basis!='joint_game'
                        or not prior.game_fingerprint or prior.game_fingerprint!=context.game_fingerprint):
                        reason='shared_game_not_established'
                    else:
                        owner=next((o.owner_team_id for o in state.pick_ownership if o.pick_id==pick.pick_id),None)
                        if owner is None:reason='pick_owner_unavailable'
                        else:
                            try:
                                apply_curve=apply_frozen_native_pick_reference_curve if reference_curve else apply_frozen_native_pick_curve
                                result=apply_curve(curve,pick,owner_team_id=owner,
                                    probabilities=attachment.probabilities,as_of=state.as_of,
                                    economic_scope_id=context.economic_scope_id,rules_signature=context.rules_signature,
                                    scoring_signature=context.scoring_signature,native_coordinate_id=context.native_coordinate_id,
                                    evaluation_season=context.evaluation_season,team_count=context.team_count)
                            except ValueError:
                                reason='curve_application_rejected'
                            else:
                                if reference_curve:
                                    if result.authority is None:reason='horizon_slot_economics_unavailable'
                                    else:
                                        value=result.authority.reference_center;mode=assessment.mode
                                        source_authority=result.authority.model_dump(mode='json')
                                else:
                                    estimate=getattr(result,context.horizon).estimate
                                    if estimate is None:reason='horizon_slot_economics_unavailable'
                                    else:value=estimate.distribution.mean;mode=assessment.mode
        if value is not None:pick_values[pick.pick_id]=value
        qualifications.append(dict(pick_id=pick.pick_id,status='shadow_available' if value is not None else 'unavailable',
            mode=mode,reason=reason,inventory_evidence_ref=attachment.inventory_evidence_ref,
            source_authority=source_authority,point_basis=context.point_basis))
    # A deliberately separate research coordinate; original source scales are preserved below.
    source=dict(state_id=state_id,league_id=state.league.league_id,as_of=state.as_of.isoformat(),
        player_source=players.source_fingerprint,projected_values_fingerprint=fingerprint(players.values),player_scale=players.source_scale.model_dump(mode='json'),
        context=context.model_dump(mode='json'),generation_id=generation_id,
        input_assumptions=dict(players.input_assumptions),source_limitations=list(players.source_limitations),
        picks=[dict(pick_id=p.pick_id,curve_id=curve_id_of(p.curve) if p.curve else None,
            prior_context=p.prior_context.model_dump(mode='json') if p.prior_context else None,
            probabilities=p.probabilities.model_dump(mode='json') if p.probabilities else None,
            probability_source_state_id=p.probability_source_state_id,probability_round=p.probability_round,
            probability_as_of=p.probability_as_of.isoformat() if p.probability_as_of else None,
            state_id=p.state_id,as_of=p.as_of.isoformat(),availability=p.availability,
            inventory_evidence_ref=p.inventory_evidence_ref,selected_player_id=p.selected_player_id,
            source_qualifications=list(p.source_qualifications)) for p in picks],
        assessments=[r.model_dump(mode='json') for r in assessments])
    scale=ValueScale(scale_id='research-mixed-native:'+fingerprint(source),version=VERSION,
        unit_label=context.horizon+' raw Shapley research comparison')
    profiles={}
    for kind,entries in (('player',values),('pick',pick_values)):
        for asset_id,value in entries.items():
            profiles[asset_id]=AssetValueProfile(asset_id=asset_id,asset_kind=kind,
                intrinsic_value=IntrinsicDynastyValueEstimate(asset_id=asset_id,asset_kind=kind,
                    distribution=ValueDistribution(mean=value),scale=scale,as_of=state.as_of,
                    model_version=VERSION,conversion_model_version='explicit-research-bridge-no-rescaling'))
    # Only compact means/provenance survive; do not retain curve graphs or State strongly.
    compact={**source,'input_fingerprint':fingerprint(source),'picks':[
        {**{k:v for k,v in p.items() if k not in ('prior_context','probabilities')},
         'prior_context_fingerprint':fingerprint(p['prior_context']) if p['prior_context'] else None,
         'slot_input_fingerprint':p['probabilities']['simulation_input_fingerprint'] if p['probabilities'] else None,
         'slot_evidence_fingerprint':fingerprint(p['probabilities']) if p['probabilities'] else None}
        for p in source['picks']]}
    return ResearchMixedRead(user_id,state.league.league_id,generation_id,state.as_of,ref(state),context.horizon,
        scale,MappingProxyType(profiles),MappingProxyType(values),_freeze(compact),
        tuple(_freeze(q) for q in qualifications))


def bind_research_trade(state: LeagueState, proposal: BilateralTradeProposal, read: ResearchMixedRead, *,
    user_id: str, generation_id: str, roster_resolutions: tuple[TeamRosterLegalityResolution,...] | None = None):
    """Existing NEXT-5 mean arithmetic, never a live classification or utility score."""
    if (read.state_ref() is not state or read.user_id!=user_id or read.league_id!=state.league.league_id
        or read.generation_id!=generation_id or read.as_of!=state.as_of or proposal.as_of!=state.as_of):
        raise ValueError('research read does not match the current request')
    _validate_leg_ownership(state,proposal.side_a);_validate_leg_ownership(state,proposal.side_b)
    economics=summarize_bilateral_trade_economics(proposal,read.profiles)
    net=calculate_bilateral_economic_net(economics)
    adjusted=None
    if roster_resolutions is not None:
        adjusted=adjust_bilateral_intrinsic_net_for_mandatory_cuts(net,roster_resolutions,
            cut_values=read.cut_values,scale=read.scale).model_dump(mode='json')
    selected_picks={a.pick_id for leg in (proposal.side_a,proposal.side_b) for a in leg.sends if isinstance(a,PickAsset)}
    selected_players={a.player_id for leg in (proposal.side_a,proposal.side_b) for a in leg.sends if isinstance(a,PlayerAsset)}
    if roster_resolutions is not None:
        selected_players.update(c.player_id for r in roster_resolutions for c in r.cuts)
    selected_sources=[p for p in read.provenance['picks'] if p['pick_id'] in selected_picks]
    curve_ids={p['curve_id'] for p in selected_sources}
    source={**{k:_thaw(v) for k,v in read.provenance.items() if k not in ('picks','assessments','input_assumptions')},
        'input_assumptions':{pid:value for pid,value in read.provenance['input_assumptions'].items() if pid in selected_players},
        'picks':[_thaw(p) for p in selected_sources],
        'assessments':[_thaw(r) for r in read.provenance['assessments'] if r['curve_id'] in curve_ids]}
    return dict(production_eligible=False,live_ledger_eligible=False,decision_effect='research_only_no_recommendation',
        horizon=read.horizon,net=net.model_dump(mode='json'),economics=economics.model_dump(mode='json'),
        roster_adjusted=adjusted,package_uncertainty=None,pick_qualifications=[_thaw(q) for q in read.pick_qualifications if q['pick_id'] in selected_picks],
        source=source,model_version=VERSION)
