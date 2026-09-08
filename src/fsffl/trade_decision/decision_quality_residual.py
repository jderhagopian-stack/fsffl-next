from __future__ import annotations

from datetime import datetime

from .decision_quality import DecisionQualityComponent


def unresolved_decision_quality_component(
    *,
    component_id: str,
    authority_id: str,
    overlap_group: str,
    as_of: datetime,
    evidence_through: datetime,
    model_version: str,
    provenance: str,
) -> DecisionQualityComponent:
    """Represent a real-but-unresolved channel without assuming it is zero.

    The maximally broad 0..100 range is intentional: an unavailable residual
    channel remains in coefficient robustness rather than having its weight
    redistributed to better-measured channels. Confidence is zero because no
    directional/cardinal evidence is being asserted.
    """

    if as_of.tzinfo is None or evidence_through.tzinfo is None:
        raise ValueError("residual component timestamps must be timezone-aware")
    if evidence_through > as_of:
        raise ValueError("residual component cannot use future evidence")
    if any(not value.strip() for value in (component_id, authority_id, overlap_group, model_version, provenance)):
        raise ValueError("residual component metadata cannot be blank")

    return DecisionQualityComponent(
        component_id=component_id,
        authority_id=authority_id,
        overlap_group=overlap_group,
        score_lower=0,
        score_center=50,
        score_upper=100,
        confidence=0,
        evidence_through=evidence_through,
        model_version=model_version,
        provenance=provenance,
    )
