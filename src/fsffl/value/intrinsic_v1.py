from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt
from typing import Mapping

from pydantic import field_validator, model_validator

from fsffl.forecast.intrinsic_v1 import (
    ForecastEvidenceStrength,
    IntrinsicV1PlayerForecastPath,
)
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import FrozenModel, LeagueRules, Position, RosterSlot


INTRINSIC_VALUE_V1_VERSION = "intrinsic-value-v1"
INTRINSIC_VALUE_V1_WEIGHTS: tuple[float, float, float] = (1.0, 0.85, 0.70)
REPLACEMENT_CONTEXT_VERSION = "marginal-lineup-opportunity-v1"


class IntrinsicV1Confidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class IntrinsicV1HorizonContribution(FrozenModel):
    horizon_year: int
    player_mean: float
    replacement_mean: float
    surplus: float
    weight: float
    weighted_surplus: float
    forecast_evidence_strength: ForecastEvidenceStrength


class IntrinsicValueV1Estimate(FrozenModel):
    player_id: str
    league_id: str
    evaluation_as_of: datetime
    value: float
    standard_deviation: float
    confidence: IntrinsicV1Confidence
    model_version: str = INTRINSIC_VALUE_V1_VERSION
    forecast_policy_version: str
    base_forecast_model_version: str
    replacement_context_version: str = REPLACEMENT_CONTEXT_VERSION
    horizons: tuple[IntrinsicV1HorizonContribution, ...]

    @field_validator("evaluation_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("evaluation_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_three_horizons(self) -> "IntrinsicValueV1Estimate":
        if tuple(point.horizon_year for point in self.horizons) != (1, 2, 3):
            raise ValueError("Intrinsic v1 requires exactly three horizon contributions")
        return self


class ThreeValueCoordinates(FrozenModel):
    """Product boundary: three value coordinates remain independent."""

    broad_market_value: float | None = None
    intrinsic_value: IntrinsicValueV1Estimate | None = None
    league_market_value: float | None = None


def _required_counts(rules: LeagueRules) -> dict[RosterSlot, int]:
    counts: dict[RosterSlot, int] = {}
    for requirement in rules.lineup:
        counts[requirement.slot] = counts.get(requirement.slot, 0) + requirement.count * rules.team_count
    return counts


def _replacement_for_horizon(
    *,
    paths: Mapping[str, IntrinsicV1PlayerForecastPath],
    horizon_index: int,
    rules: LeagueRules,
) -> dict[Position, ForecastDistribution]:
    """Return the weakest selected league starter at each skill position.

    This is the transparent marginal-lineup-opportunity replacement context used
    by Model A: fixed starters are filled first, then FLEX, then SUPERFLEX from
    the best remaining eligible players. Scarcity therefore comes from league
    structure rather than a positional bonus.
    """

    counts = _required_counts(rules)
    eligible = {Position.QB, Position.RB, Position.WR, Position.TE}
    records: list[tuple[str, Position, ForecastDistribution]] = []
    for player_id, path in paths.items():
        if path.position not in eligible:
            continue
        records.append((player_id, path.position, path.horizons[horizon_index].distribution))

    selected: list[tuple[str, Position, ForecastDistribution]] = []
    used: set[str] = set()

    for position, slot in (
        (Position.QB, RosterSlot.QB),
        (Position.RB, RosterSlot.RB),
        (Position.WR, RosterSlot.WR),
        (Position.TE, RosterSlot.TE),
    ):
        need = counts.get(slot, 0)
        pool = sorted(
            (row for row in records if row[1] == position),
            key=lambda row: row[2].mean,
            reverse=True,
        )
        if need and len(pool) < need:
            raise ValueError(f"insufficient {position.value} forecasts for replacement context")
        for row in pool[:need]:
            selected.append(row)
            used.add(row[0])

    flex_need = counts.get(RosterSlot.FLEX, 0)
    flex_pool = sorted(
        (row for row in records if row[0] not in used and row[1] in {Position.RB, Position.WR, Position.TE}),
        key=lambda row: row[2].mean,
        reverse=True,
    )
    if flex_need and len(flex_pool) < flex_need:
        raise ValueError("insufficient forecasts for FLEX replacement context")
    for row in flex_pool[:flex_need]:
        selected.append(row)
        used.add(row[0])

    superflex_need = counts.get(RosterSlot.SUPERFLEX, 0)
    sf_pool = sorted(
        (row for row in records if row[0] not in used),
        key=lambda row: row[2].mean,
        reverse=True,
    )
    if superflex_need and len(sf_pool) < superflex_need:
        raise ValueError("insufficient forecasts for SUPERFLEX replacement context")
    selected.extend(sf_pool[:superflex_need])

    output: dict[Position, ForecastDistribution] = {}
    for position in eligible:
        position_selected = [row[2] for row in selected if row[1] == position]
        if not position_selected:
            raise ValueError(f"no selected {position.value} starter defines replacement")
        output[position] = min(position_selected, key=lambda dist: dist.mean)
    return output


def build_marginal_lineup_replacement_paths(
    *,
    paths: Mapping[str, IntrinsicV1PlayerForecastPath],
    rules: LeagueRules,
) -> tuple[dict[Position, ForecastDistribution], ...]:
    return tuple(
        _replacement_for_horizon(paths=paths, horizon_index=index, rules=rules)
        for index in range(3)
    )


def _confidence(path: IntrinsicV1PlayerForecastPath) -> IntrinsicV1Confidence:
    strengths = [point.evidence_strength for point in path.horizons[1:]]
    if ForecastEvidenceStrength.LOW in strengths:
        return IntrinsicV1Confidence.LOW
    if all(strength == ForecastEvidenceStrength.MODERATE for strength in strengths):
        return IntrinsicV1Confidence.MODERATE
    return IntrinsicV1Confidence.HIGH


def estimate_intrinsic_value_v1(
    *,
    player_path: IntrinsicV1PlayerForecastPath,
    all_player_paths: Mapping[str, IntrinsicV1PlayerForecastPath],
    league_id: str,
    rules: LeagueRules,
) -> IntrinsicValueV1Estimate:
    if player_path.player_id not in all_player_paths:
        raise ValueError("player path must be present in all_player_paths")

    replacement_paths = build_marginal_lineup_replacement_paths(paths=all_player_paths, rules=rules)
    contributions: list[IntrinsicV1HorizonContribution] = []
    variance = 0.0

    for index, weight in enumerate(INTRINSIC_VALUE_V1_WEIGHTS):
        horizon = player_path.horizons[index]
        replacement = replacement_paths[index][player_path.position]
        surplus = max(0.0, horizon.distribution.mean - replacement.mean)
        weighted = weight * surplus
        contributions.append(
            IntrinsicV1HorizonContribution(
                horizon_year=index + 1,
                player_mean=horizon.distribution.mean,
                replacement_mean=replacement.mean,
                surplus=surplus,
                weight=weight,
                weighted_surplus=weighted,
                forecast_evidence_strength=horizon.evidence_strength,
            )
        )
        # Transparent local linearization: uncertainty only contributes while the
        # expected player output is above replacement. No survival/scarcity term
        # is multiplied again here; both already live in Forecast/replacement.
        if surplus > 0:
            variance += weight**2 * (
                horizon.distribution.stddev**2 + replacement.stddev**2
            )

    return IntrinsicValueV1Estimate(
        player_id=player_path.player_id,
        league_id=league_id,
        evaluation_as_of=player_path.evaluation_as_of,
        value=sum(point.weighted_surplus for point in contributions),
        standard_deviation=sqrt(variance),
        confidence=_confidence(player_path),
        forecast_policy_version=player_path.policy_version,
        base_forecast_model_version=player_path.base_forecast_model_version,
        horizons=tuple(contributions),
    )
