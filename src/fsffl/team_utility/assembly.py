from __future__ import annotations

from datetime import datetime

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import LeagueState

from .competitive_state import CompetitiveStatePolicy, classify_calculated_competitive_state
from .resilience import build_roster_resilience
from .simulation import TeamCompetitiveOutcome
from .utility import FranchiseAssetPortfolio, TeamUtilityVector


def assemble_team_utility_vector(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    competitive_outcome: TeamCompetitiveOutcome | None = None,
    competitive_state_policy: CompetitiveStatePolicy | None = None,
    asset_portfolio: FranchiseAssetPortfolio | None = None,
    model_version: str = "next4-team-utility-v1",
) -> TeamUtilityVector:
    """Assemble authoritative NEXT-4 team consequence channels.

    This is orchestration only. It consumes upstream forecasts and NEXT-3 value
    evidence, derives roster resilience, and may attach an already-simulated
    competitive outcome. Calculated competitive-state classification is optional
    and occurs only when an explicit governed policy is supplied; simulation
    outcomes do not require classification. The function does not rerun Value,
    invent owner posture, collapse channels into a scalar utility score, or
    recommend actions.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not team_id.strip() or not model_version.strip():
        raise ValueError("team utility identifiers cannot be blank")
    if league_state.as_of > as_of:
        raise ValueError("team utility cannot use league state from the future")
    if competitive_outcome is not None and competitive_outcome.team_id != team_id:
        raise ValueError("competitive outcome must describe the requested team")
    if asset_portfolio is not None and asset_portfolio.team_id != team_id:
        raise ValueError("asset portfolio must describe the requested team")
    if competitive_state_policy is not None and competitive_outcome is None:
        raise ValueError(
            "competitive-state policy requires a supplied competitive outcome"
        )

    resilience = build_roster_resilience(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
    )

    calculated_state = (
        classify_calculated_competitive_state(
            competitive_outcome,
            competitive_state_policy,
            as_of=as_of,
        )
        if competitive_outcome is not None and competitive_state_policy is not None
        else None
    )

    kwargs = {}
    if calculated_state is not None:
        kwargs["calculated_competitive_state"] = calculated_state

    return TeamUtilityVector(
        team_id=team_id,
        as_of=as_of,
        competitive_outcome=competitive_outcome,
        asset_portfolio=asset_portfolio,
        roster_resilience=resilience,
        model_version=model_version,
        **kwargs,
    )
