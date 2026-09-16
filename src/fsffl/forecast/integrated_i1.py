from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

from .canonical_state import CanonicalFootballState

STATES = ("out", "depth", "usable", "starter", "premium", "elite")
POSITIVE_STATES = STATES[1:]


@dataclass(frozen=True)
class I1RegularizationPolicy:
    """Versioned I1 regularization policy; current research selection is C=0.25.

    Component overrides are intentionally a governance seam, not a runtime knob.
    A later separately-authorized calibration may replace the one blanket C with
    multiple evidence-backed C values without changing the Forecast architecture.
    """

    version: str = "i1-regularization-v1"
    default_c: float = 0.25
    component_c: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = (self.default_c, *self.component_c.values())
        if any((not math.isfinite(v) or v <= 0) for v in values):
            raise ValueError("all I1 regularization C values must be finite and positive")

    def c_for(self, component: str) -> float:
        return float(self.component_c.get(component, self.default_c))


FROZEN_I1_REGULARIZATION = I1RegularizationPolicy()


def feature_dict(row: CanonicalFootballState) -> dict[str, float]:
    """Provider-neutral feature semantics frozen by research PR #146."""

    exp = None if row.experience_years is None else float(row.experience_years)
    exp_band = "unknown" if exp is None else "0_1" if exp <= 1 else "2_3" if exp <= 3 else "4_6" if exp <= 6 else "7_plus"
    d: dict[str, float] = {
        f"p={row.position}": 1.0,
        f"a={row.age_band}": 1.0,
        f"s={row.current_state}": 1.0,
        f"h={row.horizon}": 1.0,
        f"e={exp_band}": 1.0,
        "exp": min(15.0, max(0.0, float(exp or 0.0))) / 10.0,
    }

    p = max(0.0, float(row.current_fantasy_points)); q = max(0.0, float(row.prior_fantasy_points or 0.0))
    d.update({"lp": math.log1p(p)/6.0, "lprev": math.log1p(q)/6.0, "dpts": max(-2.0, min(2.0, (p-q)/100.0)), "prev_cov": 1.0 if row.prior_fantasy_points is not None else 0.0})

    if row.usage_evidence_coverage:
        d.update({f"role={row.role_band or 'unknown'}": 1.0, "u_cov": 1.0, "lopg": math.log1p(max(0.0, float(row.opportunity_per_game or 0.0)))/4.0, "lg": math.log1p(max(0.0, float(row.games or 0.0)))/3.0})
    else:
        d.update({"role=unknown": 1.0, "u_cov": 0.0, "lopg": 0.0, "lg": 0.0})

    # The research rich/reduced route was keyed by observed roster weeks. If
    # absent, the feature builder returns here; missing is never read as healthy,
    # retained, released, or non-persistent.
    if not row.has_full_i1_evidence:
        d.update({"r_cov": 0.0, "i_cov": 0.0, "part_cov": 0.0})
        return d

    d.update({
        "r_cov": 1.0,
        "i_cov": 1.0 if float(row.injury_report_weeks or 0.0) > 0.0 else 0.0,
        "part_cov": 1.0 if float(row.participation_weeks or 0.0) > 0.0 else 0.0,
    })
    for name in ("active_share", "released_share", "practice_share", "reserve_share", "last_status_active", "last_status_attached", "last_status_release", "last_status_practice", "last_status_reserve"):
        d[name] = float(getattr(row, name) or 0.0)
    for name in ("status_change_count", "team_change_count", "active_return_count", "release_entry_count", "practice_entry_count", "reserve_entry_count"):
        d["l" + name] = math.log1p(max(0.0, float(getattr(row, name) or 0.0)))/3.0
    d["young_active"] = (1.0 if row.age_band == "young" else 0.0) * float(row.active_share or 0.0)
    d["low_release"] = (1.0 if row.current_state in {"depth", "usable"} else 0.0) * float(row.released_share or 0.0)
    for name in ("injury_limited_weeks", "non_ir_injury_limited_weeks", "inactive_injury_limited_weeks", "reserve_injury_limited_weeks"):
        d["l" + name] = math.log1p(max(0.0, float(getattr(row, name) or 0.0)))/3.0
    d["nonir"] = float(row.non_ir_injury_flag or 0.0); d["inactiveinj"] = float(row.inactive_injury_flag or 0.0); d["inj_attached"] = d["nonir"] * float(row.last_status_attached or 0.0)
    for name in ("participation_weeks", "stats_weeks", "snap_play_weeks"):
        d["l" + name] = math.log1p(max(0.0, float(getattr(row, name) or 0.0)))/3.0
    return d


@dataclass(frozen=True)
class FrozenLogit:
    intercept: float
    coefficients: Mapping[str, float]

    def probability(self, features: Mapping[str, float]) -> float:
        z = self.intercept + sum(float(self.coefficients.get(k, 0.0))*float(v) for k, v in features.items())
        z = max(-40.0, min(40.0, z))
        return 1.0/(1.0 + math.exp(-z))


@dataclass(frozen=True)
class I1ModelArtifact:
    version: str
    regularization_policy: I1RegularizationPolicy
    persistence_full: FrozenLogit | None
    persistence_reduced: FrozenLogit | None
    ordered_full: tuple[FrozenLogit, ...]
    ordered_reduced: tuple[FrozenLogit, ...]

    def predict(self, row: CanonicalFootballState, baseline: Mapping[str, float]) -> tuple[dict[str, float], str]:
        rich = row.has_full_i1_evidence; persistence = self.persistence_full if rich else self.persistence_reduced; ordered = self.ordered_full if rich else self.ordered_reduced
        if persistence is None or len(ordered) != 4: return _normalize(baseline), "b0_fallback"
        x = feature_dict(row); q = persistence.probability(x); cuts=[]; last=1.0
        for model in ordered:
            v=min(last,max(0.0,min(1.0,model.probability(x)))); cuts.append(v); last=v
        a,b,c,d=cuts; conditional={"depth":1-a,"usable":a-b,"starter":b-c,"premium":c-d,"elite":d}
        return _normalize({"out":1-q, **{s:q*conditional[s] for s in POSITIVE_STATES}}), "full" if rich else "red"


def _normalize(probs: Mapping[str, float]) -> dict[str, float]:
    out={s:max(0.0,float(probs.get(s,0.0))) for s in STATES}; total=sum(out.values())
    if total <= 0: raise ValueError("career-state probability vector has no mass")
    return {s:out[s]/total for s in STATES}
