"""Released provisional pick economics, independent of ownership and refresh.

Only compact sufficient statistics are served. Fitting and historical replay are
offline release work. Career references are not predictive distributions.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
import json
from math import fsum, isfinite
from typing import Literal

from pydantic import model_validator

from fsffl.state.models import FrozenModel, LeagueRules
from .career_tail import lineup_capacity_signature
from .career_forward_intrinsic import CareerForwardModelAuthority
from .origin_aware_pick import OriginPickProbabilityEvidence
from .shapley_intrinsic import FROZEN_INTRINSIC_DISCOUNT

MODEL_VERSION = "native-pick-empirical-prefix-conditional-career-provisional-v1"


def fingerprint(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def scoring_signature(rules: LeagueRules) -> str:
    return fingerprint(sorted((row.model_dump(mode="json") for row in rules.scoring), key=fingerprint))


class NativePickPriorSlot(FrozenModel):
    rank: int
    annual_native_means: tuple[float, float, float]
    career_authority: CareerForwardModelAuthority
    prefix_backoff_mass: float
    long_term_backoff_mass: float

    @model_validator(mode="after")
    def finite(self):
        if self.rank < 1 or not all(isfinite(v) for v in (*self.annual_native_means, *self.career_authority.model_dump().values())):
            raise ValueError("released native means and references must be finite")
        if not all(isfinite(v) and 0 <= v <= 1 for v in (self.prefix_backoff_mass, self.long_term_backoff_mass)):
            raise ValueError("backoff mass must be explicit")
        return self


class NativePickPriorRelease(FrozenModel):
    model_version: Literal[MODEL_VERSION] = MODEL_VERSION
    stage: Literal["annual_baseline"] = "annual_baseline"
    status: Literal["bounded_provisional"] = "bounded_provisional"
    evaluation_season: int
    draft_season: int
    team_count: int
    round_count: int
    released_at: datetime
    source_as_of: datetime
    rules_signature: str
    scoring_signature: str
    source_fingerprints: tuple[str, ...]
    source_classes: tuple[int, ...]
    source_drafts: int
    source_limitations: tuple[str, ...]
    slots: tuple[NativePickPriorSlot, ...]
    comparison_policy: Literal["frozen_native_prior_reference_append_v1"] = "frozen_native_prior_reference_append_v1"
    selection_policy: Literal["observed_draft_selection_mixture_not_optimal_exercise"] = "observed_draft_selection_mixture_not_optimal_exercise"

    @model_validator(mode="after")
    def identity(self):
        if (self.released_at.tzinfo is None or self.source_as_of.tzinfo is None
            or self.source_as_of > self.released_at):
            raise ValueError("annual release requires aware, ordered evidence times")
        if (self.team_count < 1 or self.round_count < 1 or self.draft_season != self.evaluation_season + 1
            or [s.rank for s in self.slots] != list(range(1, self.team_count * self.round_count + 1))):
            raise ValueError("complete next-draft release coordinates required")
        if (not self.source_fingerprints or not self.source_classes or self.source_drafts < 1
            or any(not v.strip() for v in (self.rules_signature, self.scoring_signature, *self.source_fingerprints))):
            raise ValueError("annual release requires source and economic identities")
        return self

    @property
    def release_id(self) -> str:
        return fingerprint(self.model_dump(mode="json"))

    @property
    def economic_scope_key(self) -> str:
        return fingerprint({k: getattr(self, k) for k in (
            "evaluation_season", "draft_season", "team_count", "round_count",
            "rules_signature", "scoring_signature", "selection_policy", "model_version")})

    def supports(self, rules: LeagueRules, *, season: int, as_of: datetime) -> bool:
        return (as_of.tzinfo is not None and as_of >= self.released_at
                and season == self.evaluation_season and rules.team_count == self.team_count
                and lineup_capacity_signature(rules) == self.rules_signature
                and scoring_signature(rules) == self.scoring_signature)

    def value(self, *, round_number: int, probabilities: OriginPickProbabilityEvidence,
              horizon: Literal["three_year", "career"]) -> float:
        if (horizon not in ("three_year", "career") or not 1 <= round_number <= self.round_count
            or probabilities.draft_season != self.draft_season
            or any(p.slot_in_round > self.team_count for p in probabilities.slot_probabilities)):
            raise ValueError("pick probability/release coordinates differ")
        def point(slot):
            row = self.slots[(round_number - 1) * self.team_count + slot - 1]
            if horizon == "career":
                return row.career_authority.reference_center
            # Next year's pick has no contribution in the evaluation season.
            return fsum(v * FROZEN_INTRINSIC_DISCOUNT ** (self.draft_season + i - self.evaluation_season)
                        for i, v in enumerate(row.annual_native_means)
                        if self.draft_season + i <= self.evaluation_season + 2)
        return fsum(p.probability * point(p.slot_in_round) for p in probabilities.slot_probabilities)


@lru_cache(maxsize=1)
def packaged_native_pick_release() -> NativePickPriorRelease:
    return NativePickPriorRelease.model_validate_json(
        files("fsffl.value").joinpath("native_pick_prior_2026.json").read_text())
