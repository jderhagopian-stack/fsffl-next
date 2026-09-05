from __future__ import annotations

from datetime import datetime
from typing import Mapping

from pydantic import Field, field_validator, model_validator

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility import (
    CompetitiveStatePolicy,
    FranchiseAssetPortfolio,
    OptimizedTeamLineup,
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamCompetitiveOutcome,
    TeamScoringDistribution,
    TeamUtilityVector,
    assemble_team_utility_vector,
    build_team_scoring_distribution,
    optimize_team_lineup,
    simulate_regular_season,
)


class Next4LeagueSanityInput(FrozenModel):
    """Runtime-only orchestration input for a realistic NEXT-4 league sanity pass.

    This contract owns no model coefficients. It requires callers to supply the
    canonical point-in-time league state, admissible NEXT-2 forecasts, an explicit
    schedule, and an explicit competitive-state policy. Optional NEXT-3 portfolio
    evidence may be supplied by team.
    """

    league_state: LeagueState
    forecasts: tuple[ForecastObservation, ...]
    schedule: tuple[ScheduledMatchup, ...]
    horizon: ForecastHorizon
    playoff_team_count: int = Field(ge=1)
    competitive_state_policy: CompetitiveStatePolicy
    asset_portfolios: Mapping[str, FranchiseAssetPortfolio] = Field(default_factory=dict)
    simulation_count: int = Field(default=50_000, ge=1)
    seed: int = 20260905
    as_of: datetime
    model_version: str = "next4-runtime-sanity-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_request(self) -> "Next4LeagueSanityInput":
        if not self.model_version.strip():
            raise ValueError("model_version cannot be blank")
        if self.league_state.as_of > self.as_of:
            raise ValueError("runtime sanity cannot use league state from the future")
        if self.competitive_state_policy.evidence_through > self.as_of:
            raise ValueError("runtime sanity cannot use future competitive-state policy evidence")
        team_ids = {team.team_id for team in self.league_state.teams}
        if self.playoff_team_count > len(team_ids):
            raise ValueError("playoff_team_count cannot exceed league team count")
        unknown_portfolios = set(self.asset_portfolios) - team_ids
        if unknown_portfolios:
            raise ValueError(f"asset portfolios reference unknown teams: {sorted(unknown_portfolios)}")
        for team_id, portfolio in self.asset_portfolios.items():
            if portfolio.team_id != team_id:
                raise ValueError("asset portfolio mapping key must match portfolio team_id")
        return self


class TeamSanityDiagnostic(FrozenModel):
    team_id: str
    lineup: OptimizedTeamLineup
    scoring: TeamScoringDistribution
    competitive_outcome: TeamCompetitiveOutcome
    utility: TeamUtilityVector

    @model_validator(mode="after")
    def validate_team_alignment(self) -> "TeamSanityDiagnostic":
        for component in (self.lineup, self.scoring, self.competitive_outcome, self.utility):
            if component.team_id != self.team_id:
                raise ValueError("sanity diagnostic components must describe the same team")
        return self


class Next4LeagueSanityResult(FrozenModel):
    league_id: str
    as_of: datetime
    diagnostics: tuple[TeamSanityDiagnostic, ...]
    simulation_count: int = Field(ge=1)
    seed: int
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


def run_next4_league_sanity(request: Next4LeagueSanityInput) -> Next4LeagueSanityResult:
    """Execute a league-wide NEXT-4 sanity pass without adding model authority.

    The runner only sequences authoritative components. It does not fetch data,
    invent forecasts, infer schedules, choose competitive-state thresholds,
    calculate trade desirability, or produce report/presentation output.
    """

    team_ids = tuple(sorted(team.team_id for team in request.league_state.teams))

    lineups: dict[str, OptimizedTeamLineup] = {}
    scoring: list[TeamScoringDistribution] = []
    for team_id in team_ids:
        lineups[team_id] = optimize_team_lineup(
            request.league_state,
            request.forecasts,
            team_id=team_id,
            as_of=request.as_of,
            horizon=request.horizon,
        )
        scoring.append(
            build_team_scoring_distribution(
                request.league_state,
                request.forecasts,
                team_id=team_id,
                as_of=request.as_of,
                horizon=request.horizon,
            )
        )

    simulation = simulate_regular_season(
        RegularSeasonSimulationInput(
            scoring=tuple(scoring),
            schedule=request.schedule,
            playoff_team_count=request.playoff_team_count,
            simulation_count=request.simulation_count,
            seed=request.seed,
            model_version=f"{request.model_version}:simulation",
        )
    )
    outcomes = {outcome.team_id: outcome for outcome in simulation.outcomes}
    scoring_by_team = {item.team_id: item for item in scoring}

    diagnostics: list[TeamSanityDiagnostic] = []
    for team_id in team_ids:
        outcome = outcomes[team_id]
        utility = assemble_team_utility_vector(
            request.league_state,
            request.forecasts,
            team_id=team_id,
            as_of=request.as_of,
            horizon=request.horizon,
            competitive_outcome=outcome,
            competitive_state_policy=request.competitive_state_policy,
            asset_portfolio=request.asset_portfolios.get(team_id),
            model_version=f"{request.model_version}:team-utility",
        )
        diagnostics.append(
            TeamSanityDiagnostic(
                team_id=team_id,
                lineup=lineups[team_id],
                scoring=scoring_by_team[team_id],
                competitive_outcome=outcome,
                utility=utility,
            )
        )

    return Next4LeagueSanityResult(
        league_id=request.league_state.league.league_id,
        as_of=request.as_of,
        diagnostics=tuple(diagnostics),
        simulation_count=simulation.simulation_count,
        seed=simulation.seed,
        model_version=request.model_version,
    )
