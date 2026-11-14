"""Research-only bridge from prospective native trajectories to pick horizons.

No forecasts are fitted here. Inputs must be joint annual Shapley scenarios from
an upstream model, on an explicitly matched rules/scoring coordinate. Historical
realized outcomes are training labels, not admissible prospective scenarios.
Nothing in the production runtime imports this module.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from math import fsum, isfinite, sqrt
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel
from .models import PickValueEstimate, ValueDistribution, ValueScale
from .origin_aware_pick import OriginPickProbabilityEvidence
from .pick import PickOutcome, PickOutcomeSet, estimate_pick_value
from .shapley_intrinsic import FROZEN_INTRINSIC_DISCOUNT, SHAPLEY_INTRINSIC_MODEL_VERSION

MODEL_VERSION = 'native-pick-horizon-research-v1'
Year = Annotated[int, Field(ge=1900, le=2300)]


class NativePickAnnualOutcome(FrozenModel):
    season: Year
    raw_shapley: float | None  # None remains missing, never a verified zero.

    @model_validator(mode='after')
    def finite_value(self):
        if self.raw_shapley is not None and not isfinite(self.raw_shapley):
            raise ValueError('native annual contribution must be finite or missing')
        return self


class NativePickJointScenario(FrozenModel):
    probability: Annotated[float, Field(gt=0, le=1)]
    annual: Annotated[tuple[NativePickAnnualOutcome, ...], Field(max_length=100)]
    terminal_start_season: Year | None = None
    terminal_raw_shapley: float | None = None

    @model_validator(mode='after')
    def unique_years(self):
        years=[x.season for x in self.annual]
        if len(years)!=len(set(years)):
            raise ValueError('annual scenario seasons must be unique')
        if self.terminal_raw_shapley is not None and not isfinite(self.terminal_raw_shapley):
            raise ValueError('native terminal contribution must be finite or missing')
        if self.terminal_start_season is not None and any(y>=self.terminal_start_season for y in years):
            raise ValueError('annual and terminal contributions cannot overlap')
        return self


class NativePickSlotForecast(FrozenModel):
    slot_in_round: Annotated[int, Field(ge=1)]
    scenarios: Annotated[tuple[NativePickJointScenario, ...], Field(min_length=1, max_length=4096)]

    @model_validator(mode='after')
    def probability_mass(self):
        if abs(fsum(s.probability for s in self.scenarios)-1)>1e-9:
            raise ValueError('joint scenario probabilities must sum to one')
        return self


class NativePickResearchEvidence(FrozenModel):
    pick_id: str
    original_team_id: str
    owner_team_id: str
    evaluation_season: Year
    draft_season: Year
    round: Annotated[int, Field(ge=1)]
    team_count: Annotated[int, Field(ge=1)]
    evidence_as_of: datetime
    rules_signature: str
    scoring_signature: str
    native_coordinate_id: str
    forecast_model_version: str
    source_fingerprints: Annotated[tuple[str, ...], Field(min_length=1)]
    evidence_kind: Literal['prospective_native_joint_scenarios'] = 'prospective_native_joint_scenarios'
    market_inputs_used: Literal[False] = False
    shapley_model_version: Literal[SHAPLEY_INTRINSIC_MODEL_VERSION] = SHAPLEY_INTRINSIC_MODEL_VERSION
    slot_evidence: OriginPickProbabilityEvidence
    slot_forecasts: tuple[NativePickSlotForecast, ...]

    @model_validator(mode='after')
    def coordinates(self):
        identifiers=(self.pick_id,self.original_team_id,self.owner_team_id,self.rules_signature,
            self.scoring_signature,self.native_coordinate_id,self.forecast_model_version,
            *self.source_fingerprints)
        if any(not x.strip() for x in identifiers):
            raise ValueError('native pick evidence identifiers cannot be blank')
        if self.evidence_as_of.tzinfo is None:
            raise ValueError('native pick evidence requires a timezone')
        if self.draft_season<self.evaluation_season:
            raise ValueError('unresolved pick cannot predate the evaluation season')
        if (self.slot_evidence.original_team_id!=self.original_team_id
            or self.slot_evidence.draft_season!=self.draft_season):
            raise ValueError('slot probability evidence must match pick origin and draft season')
        slots=[s.slot_in_round for s in self.slot_evidence.slot_probabilities]
        if not slots or len(slots)!=len(set(slots)) or max(slots)>self.team_count:
            raise ValueError('origin slot probabilities require unique legal slots')
        if abs(fsum(s.probability for s in self.slot_evidence.slot_probabilities)-1)>1e-9:
            raise ValueError('origin slot probabilities must sum to one')
        forecasts=[s.slot_in_round for s in self.slot_forecasts]
        if len(forecasts)!=len(set(forecasts)) or any(s>self.team_count for s in forecasts):
            raise ValueError('slot forecasts require unique legal slots')
        for slot in self.slot_forecasts:
            for scenario in slot.scenarios:
                if any(x.season<self.draft_season for x in scenario.annual):
                    raise ValueError('unresolved picks cannot earn pre-draft production')
                start=scenario.terminal_start_season
                if start is not None and (start<self.draft_season or start-self.draft_season>100):
                    raise ValueError('terminal season must follow draft within the bounded input span')
        return self


class ResearchPickHorizon(FrozenModel):
    status: Literal['research_only', 'unavailable']
    estimate: PickValueEstimate | None
    missing_slots: tuple[int, ...] = ()
    reason: str
    discounting_applied: bool


class ResearchNativePickResult(FrozenModel):
    pick_id: str
    original_team_id: str
    owner_team_id: str
    three_year: ResearchPickHorizon
    career: ResearchPickHorizon
    input_fingerprint: str
    source_fingerprints: tuple[str, ...]
    production_eligible: Literal[False] = False
    model_version: str = MODEL_VERSION


def _scenario_total(scenario, evidence, horizon):
    annual={x.season:x.raw_shapley for x in scenario.annual}
    if horizon=='three_year':
        end=evidence.evaluation_season+3
        needed=range(evidence.draft_season,end)
        if any(annual.get(y) is None for y in needed):
            return None
        return fsum(annual[y]*FROZEN_INTRINSIC_DISCOUNT**(y-evidence.evaluation_season) for y in needed)
    start=scenario.terminal_start_season
    if start is None or scenario.terminal_raw_shapley is None:
        return None
    needed=range(evidence.draft_season,start)
    if any(annual.get(y) is None for y in needed):
        return None
    # Career follows the accepted undiscounted annual-plus-terminal coordinate.
    return fsum([*(annual[y] for y in needed),scenario.terminal_raw_shapley])


def estimate_native_pick_research(evidence: NativePickResearchEvidence, *, as_of: datetime,
    expected_rules_signature: str, expected_scoring_signature: str,
    expected_native_coordinate_id: str) -> ResearchNativePickResult:
    """Calendar-align joint native paths, then reuse existing exact slot mixture.

    Missing slot mass is never discarded/renormalized. Career requires an explicit
    terminal value (including a verified/model-supported zero), never an assumed
    retirement. Joint-path variance preserves cross-year dependence; horizon
    standard deviations are not added and horizons are not combined.
    """
    if as_of.tzinfo is None or evidence.evidence_as_of>as_of:
        raise ValueError('prospective evidence must be available by the timezone-aware cutoff')
    if (evidence.rules_signature!=expected_rules_signature or evidence.scoring_signature!=expected_scoring_signature
        or evidence.native_coordinate_id!=expected_native_coordinate_id):
        raise ValueError('native pick evidence does not match the requested economic coordinate')
    by_slot={s.slot_in_round:s for s in evidence.slot_forecasts}
    results={}
    for horizon in ('three_year','career'):
        missing=[];outcomes=[]
        for probability in evidence.slot_evidence.slot_probabilities:
            slot=probability.slot_in_round
            if horizon=='three_year' and evidence.draft_season>evidence.evaluation_season+2:
                distribution=ValueDistribution(mean=0,stddev=0)  # calendar proof, not missing-data fill
            else:
                forecast=by_slot.get(slot)
                try:
                    totals=[_scenario_total(s,evidence,horizon) for s in forecast.scenarios] if forecast else []
                except OverflowError as exc:
                    raise ValueError('native trajectory aggregation must remain finite') from exc
                if not totals or any(v is None for v in totals):
                    missing.append(slot);continue
                try:
                    mean=fsum(s.probability*v for s,v in zip(forecast.scenarios,totals))
                    variance=fsum(s.probability*(v-mean)**2 for s,v in zip(forecast.scenarios,totals))
                except OverflowError as exc:
                    raise ValueError('native trajectory aggregation must remain finite') from exc
                if not isfinite(mean) or not isfinite(variance):
                    raise ValueError('native trajectory aggregation must remain finite')
                distribution=ValueDistribution(mean=mean,stddev=sqrt(variance))
            outcomes.append(PickOutcome(slot=slot,probability=probability.probability,value=distribution))
        estimate=None
        if not missing:
            try:
                estimate=estimate_pick_value(PickOutcomeSet(outcomes=tuple(outcomes)),asset_id=evidence.pick_id,
                    scale=ValueScale(scale_id=f'research-native-shapley:{horizon}:{evidence.native_coordinate_id}',
                        version=MODEL_VERSION,unit_label=f'{horizon} raw Shapley contribution'),
                    as_of=as_of,draft_season=evidence.draft_season,round=evidence.round,model_version=MODEL_VERSION,
                    class_strength_model_version=evidence.forecast_model_version,
                    slot_uncertainty_model_version=evidence.slot_evidence.draft_order_projection_model_version)
            except OverflowError as exc:
                raise ValueError('native trajectory aggregation must remain finite') from exc
            if not isfinite(estimate.distribution.mean) or not isfinite(estimate.distribution.stddev):
                raise ValueError('native trajectory aggregation must remain finite')
        results[horizon]=ResearchPickHorizon(status='unavailable' if missing else 'research_only',estimate=estimate,
            missing_slots=tuple(missing),discounting_applied=horizon=='three_year',
            reason='Incomplete native slot/annual/terminal evidence' if missing else 'Research-only prospective native scenario mixture; not a production valuation')
    return ResearchNativePickResult(pick_id=evidence.pick_id,original_team_id=evidence.original_team_id,
        owner_team_id=evidence.owner_team_id,
        input_fingerprint=hashlib.sha256(json.dumps({'evidence':evidence.model_dump(mode='json'),
            'as_of':as_of.isoformat()},sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        source_fingerprints=(*evidence.source_fingerprints,evidence.slot_evidence.simulation_input_fingerprint),**results)
