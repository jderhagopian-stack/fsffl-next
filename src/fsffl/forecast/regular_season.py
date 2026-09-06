from __future__ import annotations

from datetime import timedelta

from fsffl.state.models import LeagueState, Provenance

from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


_NFL_REGULAR_SEASON_GAMES_PER_TEAM = 17
_NFL_REGULAR_SEASON_WEEKS = 18
MODEL_VERSION = "next2-fantasy-regular-season-horizon-v1"
SOURCE = "fsffl:fantasy_regular_season_horizon"


def fantasy_regular_season_weeks(league_state: LeagueState) -> tuple[int, ...]:
    """Return the canonical fantasy regular-season weeks from State authority."""

    weeks = tuple(sorted({matchup.week for matchup in league_state.matchups}))
    if not weeks:
        raise ValueError("canonical fantasy regular-season schedule is required")
    if weeks[0] != 1:
        raise ValueError("fantasy regular-season schedule must begin in week 1")
    expected = tuple(range(1, weeks[-1] + 1))
    if weeks != expected:
        raise ValueError("fantasy regular-season weeks must be contiguous")
    if weeks[-1] > _NFL_REGULAR_SEASON_WEEKS:
        raise ValueError("fantasy regular season cannot exceed NFL regular-season weeks")
    return weeks


def _active_game_fraction(
    league_state: LeagueState,
    *,
    player_id: str,
    fantasy_weeks: tuple[int, ...],
) -> float:
    players = {player.player_id: player for player in league_state.players}
    player = players.get(player_id)
    if player is None:
        raise ValueError(f"forecast references unknown player {player_id}")

    nfl_team = (player.nfl_team or "").upper().strip()
    if nfl_team:
        bye = next(
            (
                item.week
                for item in league_state.nfl_team_byes
                if item.season == league_state.league.season and item.nfl_team == nfl_team
            ),
            None,
        )
        if bye is not None:
            active_games = len(fantasy_weeks) - (1 if bye in fantasy_weeks else 0)
            return active_games / _NFL_REGULAR_SEASON_GAMES_PER_TEAM

    # If canonical bye state is unavailable for a player, use the structural NFL
    # schedule expectation rather than inventing a player-specific bye. Across an
    # 18-week NFL regular season, clubs play 17 games.
    expected_active_games = len(fantasy_weeks) * (
        _NFL_REGULAR_SEASON_GAMES_PER_TEAM / _NFL_REGULAR_SEASON_WEEKS
    )
    return expected_active_games / _NFL_REGULAR_SEASON_GAMES_PER_TEAM


def _scale_optional(value: float | None, factor: float) -> float | None:
    return None if value is None else value * factor


def derive_fantasy_regular_season_forecasts(
    league_state: LeagueState,
    season_forecasts: tuple[ForecastObservation, ...],
) -> tuple[ForecastObservation, ...]:
    """Derive fantasy-regular-season totals from full NFL-season forecasts.

    Current live providers expose season-total means. FSFFL preserves those source
    totals for simulation's per-active-game decomposition, then derives a separate
    league-specific display/analytics horizon using the canonical fantasy schedule
    and NFL bye state. This bridge is structurally derived and explicitly versioned;
    direct multi-source weekly forecast means can replace it without changing the
    product contract.
    """

    fantasy_weeks = fantasy_regular_season_weeks(league_state)
    output: list[ForecastObservation] = []
    for observation in season_forecasts:
        if observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        if observation.horizon != ForecastHorizon.SEASON:
            continue
        factor = _active_game_fraction(
            league_state,
            player_id=observation.player_id,
            fantasy_weeks=fantasy_weeks,
        )
        distribution = observation.distribution
        provenance = Provenance(
            source=f"{SOURCE}[{observation.source}]",
            retrieved_at=observation.provenance.retrieved_at,
            effective_at=observation.provenance.effective_at,
            provider_ref=observation.provenance.provider_ref,
            source_version=MODEL_VERSION,
        )
        output.append(
            ForecastObservation(
                player_id=observation.player_id,
                position=observation.position,
                horizon=ForecastHorizon.FANTASY_REGULAR_SEASON,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=observation.period_start,
                period_end=min(
                    observation.period_end,
                    observation.period_start + timedelta(weeks=len(fantasy_weeks)),
                ),
                distribution=ForecastDistribution(
                    mean=distribution.mean * factor,
                    stddev=distribution.stddev * factor,
                    p10=_scale_optional(distribution.p10, factor),
                    p50=_scale_optional(distribution.p50, factor),
                    p90=_scale_optional(distribution.p90, factor),
                ),
                source=SOURCE,
                model_version=f"{MODEL_VERSION}:weeks_1_{fantasy_weeks[-1]}",
                as_of=observation.as_of,
                provenance=provenance,
            )
        )
    return tuple(sorted(output, key=lambda item: (item.player_id, item.as_of, item.source)))