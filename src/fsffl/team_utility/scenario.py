from __future__ import annotations

from datetime import datetime

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel

from .utility import TeamUtilityVector


class CompetitiveOutcomeDelta(FrozenModel):
    expected_wins: float | None = None
    playoff_probability: float | None = None
    first_place_probability: float | None = None


class RosterResilienceDelta(FrozenModel):
    largest_single_player_lineup_drop: float | None = None
    bench_forecasted_count: int | None = None
    unavailable_count: int | None = None
    missing_forecast_count: int | None = None


class AssetPortfolioDelta(FrozenModel):
    mean_value: float | None = None
    stddev_value: float | None = None


class TeamScenarioDelta(FrozenModel):
    """Structured before/after consequence comparison for one team.

    This object does not decide whether a move is good, recommend a trade, or
    combine channels into a scalar score. It only records differences between
    two authoritative NEXT-4 team-utility states.
    """

    team_id: str
    baseline_as_of: datetime
    scenario_as_of: datetime
    competitive: CompetitiveOutcomeDelta | None = None
    resilience: RosterResilienceDelta | None = None
    asset_portfolio: AssetPortfolioDelta | None = None
    calculated_state_before: str
    calculated_state_after: str
    model_version: str

    @field_validator("baseline_as_of", "scenario_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scenario timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identifiers(self) -> "TeamScenarioDelta":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("scenario identifiers cannot be blank")
        return self


def compare_team_utility_vectors(
    baseline: TeamUtilityVector,
    scenario: TeamUtilityVector,
    *,
    model_version: str = "next4-scenario-delta-v1",
) -> TeamScenarioDelta:
    """Compare two team-utility states without collapsing distinct channels."""

    if baseline.team_id != scenario.team_id:
        raise ValueError("scenario comparison requires the same team")
    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    competitive: CompetitiveOutcomeDelta | None = None
    if baseline.competitive_outcome is not None and scenario.competitive_outcome is not None:
        competitive = CompetitiveOutcomeDelta(
            expected_wins=(
                scenario.competitive_outcome.expected_wins
                - baseline.competitive_outcome.expected_wins
            ),
            playoff_probability=(
                scenario.competitive_outcome.playoff_probability
                - baseline.competitive_outcome.playoff_probability
            ),
            first_place_probability=(
                scenario.competitive_outcome.first_place_probability
                - baseline.competitive_outcome.first_place_probability
            ),
        )

    resilience: RosterResilienceDelta | None = None
    if baseline.roster_resilience is not None and scenario.roster_resilience is not None:
        resilience = RosterResilienceDelta(
            largest_single_player_lineup_drop=(
                scenario.roster_resilience.largest_single_player_lineup_drop
                - baseline.roster_resilience.largest_single_player_lineup_drop
            ),
            bench_forecasted_count=(
                scenario.roster_resilience.bench_forecasted_count
                - baseline.roster_resilience.bench_forecasted_count
            ),
            unavailable_count=(
                scenario.roster_resilience.unavailable_count
                - baseline.roster_resilience.unavailable_count
            ),
            missing_forecast_count=(
                scenario.roster_resilience.missing_forecast_count
                - baseline.roster_resilience.missing_forecast_count
            ),
        )

    asset_portfolio: AssetPortfolioDelta | None = None
    if baseline.asset_portfolio is not None and scenario.asset_portfolio is not None:
        if baseline.asset_portfolio.scale != scenario.asset_portfolio.scale:
            raise ValueError("asset portfolio deltas require the same value scale/version")
        if baseline.asset_portfolio.value_concept != scenario.asset_portfolio.value_concept:
            raise ValueError("asset portfolio deltas require the same value concept")
        asset_portfolio = AssetPortfolioDelta(
            mean_value=(
                scenario.asset_portfolio.distribution.mean
                - baseline.asset_portfolio.distribution.mean
            ),
            stddev_value=(
                scenario.asset_portfolio.distribution.stddev
                - baseline.asset_portfolio.distribution.stddev
            ),
        )

    return TeamScenarioDelta(
        team_id=baseline.team_id,
        baseline_as_of=baseline.as_of,
        scenario_as_of=scenario.as_of,
        competitive=competitive,
        resilience=resilience,
        asset_portfolio=asset_portfolio,
        calculated_state_before=baseline.calculated_competitive_state.value,
        calculated_state_after=scenario.calculated_competitive_state.value,
        model_version=model_version,
    )
