from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel


class OpportunitySource(StrEnum):
    AUTOMATIC_FOR_YOU = "automatic_for_you"
    EXPLICIT_TRADE_FINDER_INTENT = "explicit_trade_finder_intent"


class AttentionStatus(StrEnum):
    WORTH_ATTENTION = "worth_attention"
    EXPLORABLE = "explorable"
    MARKET_MATCH_ONLY = "market_match_only"
    SUPPRESSED = "suppressed"


class PreliminaryEconomicBand(StrEnum):
    ROBUST_OR_ORDINARY = "robust_or_ordinary"
    BOUNDED_UNCERTAINTY = "bounded_uncertainty"
    FOCAL_ECONOMIC_STRAIN = "focal_economic_strain"
    COUNTERPARTY_ECONOMIC_STRAIN = "counterparty_economic_strain"
    INCOMPLETE = "incomplete"


class BilateralPlausibility(StrEnum):
    BILATERAL_SUPPORTED = "bilateral_supported"
    BILATERAL_FRICTION = "bilateral_friction"
    COUNTERPARTY_DOMINATED = "counterparty_dominated"
    FOCAL_DOMINATED = "focal_dominated"
    INCOMPLETE = "incomplete"


class DeepEvaluationStatus(StrEnum):
    PRELIM_SCREENED = "prelim_screened"
    NEEDS_DEEP_EVALUATION = "needs_deep_evaluation"
    DEEP_EVALUATED = "deep_evaluated"
    NOT_WARRANTED = "not_warranted"


class MarketSurfaceStatus(StrEnum):
    READY = "ready"
    DEGRADED = "degraded"
    BUILDING_OPTIONAL = "building_optional"
    BLOCKED = "blocked"


class OpportunityHypothesis(FrozenModel):
    hypothesis_id: str
    league_state_id: str
    focal_team_id: str
    as_of: datetime
    objective_family: str
    need_dimension: str
    target_archetype: str
    calculated_competitive_state: str
    requested_owner_posture: str
    strategic_evidence: tuple[str, ...] = ()
    source: OpportunitySource
    evidence_status: str
    model_versions: tuple[str, ...] = ()
    model_version: str = "market-opportunity-hypothesis-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("opportunity hypothesis as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identifiers(self) -> "OpportunityHypothesis":
        required = (
            self.hypothesis_id,
            self.league_state_id,
            self.focal_team_id,
            self.objective_family,
            self.need_dimension,
            self.target_archetype,
            self.evidence_status,
            self.model_version,
        )
        if any(not str(value).strip() for value in required):
            raise ValueError("opportunity hypothesis identifiers cannot be blank")
        return self


class CandidatePath(FrozenModel):
    path_id: str
    opportunity_id: str
    counterparty_team_id: str
    receive_asset_refs: tuple[str, ...]
    package_family_key: str
    representative_package: dict[str, Any]
    alternate_packages: tuple[dict[str, Any], ...] = ()
    structural_status: str
    economic_screen: PreliminaryEconomicBand
    roster_legality_status: str
    bilateral_plausibility: BilateralPlausibility
    negotiation_feasibility_shape: str | None = None
    owner_context_status: str = "unavailable"
    owner_context: dict[str, Any] | None = None
    deep_evaluation_status: DeepEvaluationStatus
    evidence_completeness: str
    missing_evidence: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    authority: dict[str, Any] = {}
    model_version: str = "market-candidate-path-v1"

    @model_validator(mode="after")
    def validate_path(self) -> "CandidatePath":
        required = (
            self.path_id,
            self.opportunity_id,
            self.counterparty_team_id,
            self.package_family_key,
            self.structural_status,
            self.roster_legality_status,
            self.evidence_completeness,
            self.model_version,
        )
        if any(not str(value).strip() for value in required):
            raise ValueError("candidate path identifiers cannot be blank")
        if not self.receive_asset_refs:
            raise ValueError("candidate path requires at least one received asset")
        return self


class MarketOpportunity(FrozenModel):
    opportunity_id: str
    hypothesis_id: str
    league_state_id: str
    focal_team_id: str
    objective_family: str
    need_dimension: str
    target_family: str
    why_now: tuple[str, ...]
    strategic_relevance: str
    preliminary_economic_band: PreliminaryEconomicBand
    bilateral_plausibility: BilateralPlausibility
    evidence_completeness: str
    attention_status: AttentionStatus
    opportunity_family_key: str
    representative_path_ids: tuple[str, ...]
    alternate_path_count: int = 0
    top_risks: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    authority: dict[str, Any] = {}
    freshness: dict[str, Any] = {}
    model_version: str = "market-opportunity-v1"

    @model_validator(mode="after")
    def validate_opportunity(self) -> "MarketOpportunity":
        required = (
            self.opportunity_id,
            self.hypothesis_id,
            self.league_state_id,
            self.focal_team_id,
            self.objective_family,
            self.need_dimension,
            self.target_family,
            self.strategic_relevance,
            self.evidence_completeness,
            self.opportunity_family_key,
            self.model_version,
        )
        if any(not str(value).strip() for value in required):
            raise ValueError("market opportunity identifiers cannot be blank")
        if self.attention_status == AttentionStatus.WORTH_ATTENTION and not self.representative_path_ids:
            raise ValueError("worth-attention opportunity requires a representative path")
        return self


class MarketSurfaceReadiness(FrozenModel):
    surface: str
    status: MarketSurfaceStatus
    required_dependencies: tuple[str, ...]
    optional_dependencies: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    missing_optional: tuple[str, ...] = ()
    league_state_id: str | None = None
    evidence_coordinates: dict[str, Any] = {}
    retry_after_ms: int | None = None
    model_version: str = "market-surface-readiness-v1"

    @model_validator(mode="after")
    def validate_surface(self) -> "MarketSurfaceReadiness":
        if not self.surface.strip() or not self.model_version.strip():
            raise ValueError("market surface readiness identifiers cannot be blank")
        if self.status == MarketSurfaceStatus.BLOCKED and not self.blockers:
            raise ValueError("blocked market surface requires blockers")
        return self


def canonical_package_family_key(
    *,
    opportunity_id: str,
    counterparty_team_id: str,
    receive_asset_refs: tuple[str, ...],
) -> str:
    receive = ",".join(sorted(receive_asset_refs))
    return f"{opportunity_id}|{counterparty_team_id}|{receive}"


def canonical_opportunity_family_key(
    *,
    focal_team_id: str,
    objective_family: str,
    need_dimension: str,
    target_family: str,
) -> str:
    return "|".join((focal_team_id, objective_family, need_dimension, target_family))


def canonical_path_id(
    *,
    package_family_key: str,
    send_asset_refs: tuple[str, ...],
) -> str:
    return f"{package_family_key}|send:{','.join(sorted(send_asset_refs))}"
