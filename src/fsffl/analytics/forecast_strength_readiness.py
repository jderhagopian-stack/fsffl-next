"""Research-only readiness audit for fantasy team-strength evidence.

This module is NOT a substitute for Forecast or weekly lineup simulation. It
prevents comparisons across incompatible forecast regimes and identifies
starter participation gaps without inventing injury absences or zero points.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from statistics import mean
from typing import Sequence


MODEL_VERSION = "research-strength-evidence-readiness-v1"
_RISKY_STATUSES = frozenset({"injured", "inactive", "pup", "suspended"})


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True)
class CompletedForecastReceipt:
    """One genuinely pregame, subsequently completed full-league prediction."""

    artifact_id: str
    week: int
    model_regime: str
    lineup_horizon: str
    forecast_computed_at: datetime
    first_game_kickoff_at: datetime
    week_completed_at: datetime
    league_projected_mean: float
    league_actual_mean: float

    def __post_init__(self) -> None:
        if not self.artifact_id.strip() or not self.model_regime.strip():
            raise ValueError("forecast identity and model regime required")
        if self.week < 1 or not self.lineup_horizon.strip():
            raise ValueError("forecast week and lineup horizon required")
        for key in ("forecast_computed_at", "first_game_kickoff_at", "week_completed_at"):
            _aware(getattr(self, key), key)
        if not self.forecast_computed_at < self.first_game_kickoff_at < self.week_completed_at:
            raise ValueError("forecast must predate first kickoff and completed result")
        if not all(isfinite(x) and x >= 0 for x in
                   (self.league_projected_mean, self.league_actual_mean)):
            raise ValueError("forecast and actual scoring means must be nonnegative finite")


@dataclass(frozen=True)
class OptimizedStarterStatus:
    team_id: str
    player_id: str
    status: str

    def __post_init__(self) -> None:
        if not self.team_id.strip() or not self.player_id.strip():
            raise ValueError("team and player identities are required")
        if not self.status.strip():
            raise ValueError("source status required")


@dataclass(frozen=True)
class ExplicitWeekAvailability:
    week: int
    player_id: str
    status: str

    def __post_init__(self) -> None:
        if self.week < 1 or not self.player_id.strip():
            raise ValueError("week and player identity required")
        if self.status not in {"available", "unavailable"}:
            raise ValueError("weekly participation must be explicit available/unavailable")


@dataclass(frozen=True)
class ForecastReadinessResult:
    compatible_completed_weeks: tuple[int, ...]
    incompatible_model_artifact_ids: tuple[str, ...]
    unverified_starter_player_ids: tuple[str, ...]
    confirmed_unavailable_starter_player_ids: tuple[str, ...]
    confirmed_available_starter_player_ids: tuple[str, ...]
    compatible_mean_projection_error: float | None
    validation_eligible: bool
    publication_ready: bool
    reasons: tuple[str, ...]
    model_version: str = MODEL_VERSION


def audit_forecast_readiness(
    *,
    target_week: int,
    as_of: datetime,
    current_model_regime: str,
    current_lineup_horizon: str,
    receipts: Sequence[CompletedForecastReceipt],
    optimized_starters: Sequence[OptimizedStarterStatus],
    week_availability: Sequence[ExplicitWeekAvailability],
) -> ForecastReadinessResult:
    """Review comparable history and exact-week availability; fail closed.

    The returned validation_eligible flag means at least one compatible
    *completed* week is available. It does not establish a calibrated model,
    and publication_ready remains false until separately governed review.
    """
    _aware(as_of, "as_of")
    if target_week < 2 or not current_model_regime.strip() or not current_lineup_horizon.strip():
        raise ValueError("target week, current model regime and horizon required")
    ids = [r.artifact_id for r in receipts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate archived forecast receipts")
    starter_ids = [s.player_id for s in optimized_starters]
    if len(set(starter_ids)) != len(starter_ids):
        raise ValueError("duplicate optimized player IDs")
    facts = {}
    for fact in week_availability:
        key = (fact.week, fact.player_id)
        if key in facts:
            raise ValueError("duplicate weekly participation fact")
        facts[key] = fact.status
    comparable: list[CompletedForecastReceipt] = []
    incompatible: list[str] = []
    for receipt in receipts:
        if receipt.week >= target_week or receipt.week_completed_at > as_of:
            raise ValueError("future or incomplete outcomes cannot calibrate this target")
        if receipt.model_regime != current_model_regime or receipt.lineup_horizon != current_lineup_horizon:
            incompatible.append(receipt.artifact_id)
        else:
            comparable.append(receipt)
    unresolved = []
    unavailable = []
    available = []
    for starter in optimized_starters:
        fact = facts.get((target_week, starter.player_id))
        if fact == "unavailable":
            unavailable.append(starter.player_id)
        elif fact == "available":
            available.append(starter.player_id)
        elif starter.status.lower() in _RISKY_STATUSES:
            unresolved.append(starter.player_id)

    reasons = []
    if not comparable:
        reasons.append("no_compatible_completed_forecast_regime")
    if incompatible:
        reasons.append("historical_model_regime_mismatch")
    if unresolved:
        reasons.append("injury_or_status_without_exact_week_participation")
    if unavailable:
        # Baseline optimized starters can legitimately contain absent players:
        # the week-specific lineup reoptimizer must remove them before usage.
        reasons.append("baseline_optimized_starter_explicitly_unavailable")
    return ForecastReadinessResult(
        compatible_completed_weeks=tuple(sorted(r.week for r in comparable)),
        incompatible_model_artifact_ids=tuple(sorted(incompatible)),
        unverified_starter_player_ids=tuple(sorted(unresolved)),
        confirmed_unavailable_starter_player_ids=tuple(sorted(unavailable)),
        confirmed_available_starter_player_ids=tuple(sorted(available)),
        compatible_mean_projection_error=(
            mean(r.league_actual_mean-r.league_projected_mean for r in comparable)
            if comparable else None
        ),
        validation_eligible=bool(comparable),
        publication_ready=False,
        reasons=tuple(reasons),
    )
