from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.trade_decision.decision_quality_normalization import DecisionQualityNormalizationPolicy
from fsffl.trade_decision.decision_quality_weight_robustness import DecisionQualityWeightFamily

from .historical_trade import GovernedGradePolicy


class HistoricalGradePolicyBundle(FrozenModel):
    """Explicit runtime/config bundle for historical PIT grade envelopes.

    No universal coefficients, normalization knots, or grade bands are embedded
    in NEXT. A deployment/research workflow supplies this versioned bundle and can
    later replace bounded priors with calibrated policies without changing the
    engine API.
    """

    bundle_id: str
    model_version: str
    provenance: str
    normalization_policies: tuple[DecisionQualityNormalizationPolicy, ...]
    weight_family: DecisionQualityWeightFamily
    grade_policy: GovernedGradePolicy

    @model_validator(mode="after")
    def validate_bundle(self) -> "HistoricalGradePolicyBundle":
        if any(not value.strip() for value in (self.bundle_id, self.model_version, self.provenance)):
            raise ValueError("historical grade policy bundle metadata cannot be blank")
        if not self.normalization_policies:
            raise ValueError("historical grade policy bundle requires normalization policies")

        component_ids = [item.component_id for item in self.normalization_policies]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("historical grade policy bundle component ids must be unique")
        authorities = [item.authority_id for item in self.normalization_policies]
        if len(authorities) != len(set(authorities)):
            raise ValueError("historical grade policy bundle cannot count one authority twice")
        overlaps = [item.overlap_group for item in self.normalization_policies]
        if len(overlaps) != len(set(overlaps)):
            raise ValueError("historical grade policy bundle cannot contain overlapping channels")

        weight_ids = {item.component_id for item in self.weight_family.bounds}
        if set(component_ids) != weight_ids:
            raise ValueError("weight family must describe exactly the bundle normalization components")
        return self

    def normalization_policy(self, component_id: str) -> DecisionQualityNormalizationPolicy:
        matches = [item for item in self.normalization_policies if item.component_id == component_id]
        if not matches:
            raise KeyError(component_id)
        return matches[0]
