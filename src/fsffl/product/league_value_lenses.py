from __future__ import annotations

from collections import defaultdict

from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)

from .runtime import UserRuntimeContext
from .value_lens_evidence import build_governed_value_lens_evidence


LEAGUE_VALUE_LENS_CONTRACT_VERSION = "phase3-league-value-lenses-v2:value-index"
BROAD_MARKET_SCALE_ID = "dynasty-market-percentile"
INTRINSIC_PRESENTATION_COORDINATE = "percentile_rank_presentation_only"


def _ownership(runtime: UserRuntimeContext) -> dict[str, str]:
    state = runtime.league_state
    if state is None:
        return {}
    result: dict[str, str] = {}
    for team_state in state.team_states:
        for entry in team_state.roster:
            prior = result.get(entry.player_id)
            if prior is not None and prior != team_state.team_id:
                raise ValueError(
                    f"canonical State assigns player {entry.player_id} to multiple teams"
                )
            result[entry.player_id] = team_state.team_id
    return result


def _latest_season_forecasts(runtime: UserRuntimeContext) -> dict[str, object]:
    """Return attached governed full-season fantasy-point evidence by player."""

    state = runtime.league_state
    evidence = runtime.forecast_evidence
    if state is None or evidence is None:
        return {}
    latest: dict[str, object] = {}
    for observation in evidence.league_scored_forecasts:
        if (
            observation.metric != ForecastMetric.FANTASY_POINTS
            or observation.horizon != ForecastHorizon.SEASON
            or observation.as_of > state.as_of
        ):
            continue
        current = latest.get(observation.player_id)
        if current is None or observation.as_of > current.as_of:
            latest[observation.player_id] = observation
    return latest


def build_league_value_lenses(
    runtime: UserRuntimeContext,
    intrinsic: ShapleyIntrinsicContract | None,
    *,
    intrinsic_error: str | None = None,
    include_unrostered: bool = False,
) -> dict[str, object]:
    """Expose separate Broad Market and Intrinsic player lenses for League Atlas.

    This contract deliberately stops before a team-level value authority. Broad
    Market percentiles are non-additive. Intrinsic raw values live in a different
    coordinate. The Atlas may place the two player-level percentile lenses beside
    each other, but this builder never sums them, substitutes one for the other,
    creates League Market Value, or feeds Team Utility.
    """

    state = runtime.league_state
    if state is None:
        raise ValueError("League value lenses require canonical LeagueState")

    lens_evidence = build_governed_value_lens_evidence(runtime, intrinsic)
    market = lens_evidence.market_percentiles
    intrinsic_ranks = lens_evidence.intrinsic_percentiles
    value_coordinate = lens_evidence.value_coordinate
    value_coordinate_error = lens_evidence.value_coordinate_error

    owner_by_player = _ownership(runtime)
    team_names = {team.team_id: team.display_name for team in state.teams}
    players = {player.player_id: player for player in state.players}
    player_states = {row.player_id: row for row in state.player_states}
    season_forecasts = _latest_season_forecasts(runtime)

    player_ids = (
        sorted(players)
        if include_unrostered
        else sorted(set(owner_by_player) & set(players))
    )
    rows: list[dict[str, object]] = []
    for player_id in player_ids:
        player = players[player_id]
        market_percentile = market.get(player_id)
        intrinsic_percentile = intrinsic_ranks.get(player_id)
        gap = (
            intrinsic_percentile - market_percentile
            if market_percentile is not None and intrinsic_percentile is not None
            else None
        )
        market_index = (
            value_coordinate.index_for_percentile(market_percentile)
            if value_coordinate is not None
            else None
        )
        intrinsic_index = (
            value_coordinate.index_for_percentile(intrinsic_percentile)
            if value_coordinate is not None
            else None
        )
        display_gap = (
            intrinsic_index - market_index
            if market_index is not None and intrinsic_index is not None
            else None
        )
        player_state = player_states.get(player_id)
        season_forecast = season_forecasts.get(player_id)
        rows.append(
            {
                "player_id": player_id,
                "asset_ref": f"player:{player_id}",
                "full_name": player.full_name,
                "position": player.position.value,
                "age_years": (
                    player_state.age_years if player_state is not None else None
                ),
                "owner_team_id": owner_by_player.get(player_id),
                "owner_team_name": (
                    team_names.get(owner_by_player[player_id], owner_by_player[player_id])
                    if player_id in owner_by_player
                    else None
                ),
                "nfl_team": player.nfl_team,
                "roster_status": "rostered" if player_id in owner_by_player else "available",
                "player_status": (
                    player_state.status.value if player_state is not None else "unknown"
                ),
                "broad_market_percentile": market_percentile,
                "intrinsic_percentile": intrinsic_percentile,
                "broad_market_value_index": market_index,
                "intrinsic_value_index": intrinsic_index,
                "value_index_gap": display_gap,
                "percentile_gap": gap,
                "comparison_available": gap is not None,
                "season_forecast_status": (
                    "ready" if season_forecast is not None else "unavailable"
                ),
                "season_fantasy_points_projection": (
                    season_forecast.distribution.mean
                    if season_forecast is not None
                    else None
                ),
                "season_ppg_17": (
                    season_forecast.distribution.mean / 17.0
                    if season_forecast is not None
                    else None
                ),
                "season_forecast_stddev": (
                    season_forecast.distribution.stddev
                    if season_forecast is not None
                    else None
                ),
                "season_forecast_as_of": (
                    season_forecast.as_of.isoformat()
                    if season_forecast is not None
                    else None
                ),
                "season_forecast_model_version": (
                    season_forecast.model_version
                    if season_forecast is not None
                    else None
                ),
                "season_forecast_reason": (
                    None
                    if season_forecast is not None
                    else (
                        "No governed attached full-season fantasy-points Forecast "
                        "covers this player at the current State."
                    )
                ),
            }
        )

    by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_team[str(row["owner_team_id"])].append(row)

    teams = []
    for team in sorted(state.teams, key=lambda item: item.team_id):
        team_rows = by_team.get(team.team_id, [])
        teams.append(
            {
                "team_id": team.team_id,
                "team_name": team.display_name,
                "rostered_player_count": len(team_rows),
                "broad_market_covered_players": sum(
                    row["broad_market_percentile"] is not None for row in team_rows
                ),
                "intrinsic_covered_players": sum(
                    row["intrinsic_percentile"] is not None for row in team_rows
                ),
                "comparable_players": sum(
                    row["comparison_available"] is True for row in team_rows
                ),
                "player_ids": [str(row["player_id"]) for row in team_rows],
            }
        )

    market_ready = bool(market)
    intrinsic_status = (
        intrinsic.status.value if intrinsic is not None else "unavailable"
    )
    if market_ready and intrinsic_ranks and value_coordinate is not None:
        status = "ready"
    elif market_ready or intrinsic_ranks:
        status = "degraded"
    else:
        status = "unavailable"

    return {
        "status": status,
        "contract_version": LEAGUE_VALUE_LENS_CONTRACT_VERSION,
        "league_state_id": state.state_id,
        "broad_market": {
            "status": "ready" if market_ready else "unavailable",
            "scale_id": BROAD_MARKET_SCALE_ID,
            "player_count": len(market),
            "universe": "all_players" if include_unrostered else "rostered_players",
            "team_total_authority": False,
            "reason": (
                None
                if market_ready
                else "Governed Broad Market percentile evidence is unavailable."
            ),
        },
        "fsffl_intrinsic": {
            "authority_family": "canonical_shapley_intrinsic",
            "status": intrinsic_status,
            "contract_version": (
                intrinsic.contract_version if intrinsic is not None else None
            ),
            "quantity_semantics": (
                intrinsic.quantity_semantics if intrinsic is not None else None
            ),
            "display_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
            "player_count": len(intrinsic_ranks),
            "team_total_authority": False,
            "reason": (
                intrinsic.status_reason
                if intrinsic is not None
                and intrinsic.status == ShapleyIntrinsicAvailability.UNAVAILABLE
                else intrinsic_error
            ),
        },
        "value_presentation": (
            {
                "status": "ready",
                **value_coordinate.summary_payload(),
            }
            if value_coordinate is not None
            else {
                "status": "unavailable",
                "reason": value_coordinate_error
                or lens_evidence.reason
                or "Governed native market magnitude evidence is unavailable.",
                "presentation_only": True,
            }
        ),
        "players": rows,
        "all_player_forecast": {
            "status": (
                "ready"
                if season_forecasts and all(
                    row["season_forecast_status"] == "ready" for row in rows
                )
                else ("degraded" if season_forecasts else "unavailable")
            ),
            "horizon": ForecastHorizon.SEASON.value,
            "metric": ForecastMetric.FANTASY_POINTS.value,
            "covered_players": sum(
                row["season_forecast_status"] == "ready" for row in rows
            ),
            "requested_players": len(rows),
            "evidence_basis": (
                runtime.forecast_evidence.evidence_basis
                if runtime.forecast_evidence is not None
                else None
            ),
            "reason": (
                None
                if season_forecasts
                else "No governed attached full-season Forecast evidence is available."
            ),
        },
        "player_universe": "all_players" if include_unrostered else "rostered_players",
        "teams": teams,
        "authority": {
            "canonical_fsffl_intrinsic_authority": "shapley_intrinsic",
            "broad_market_and_intrinsic_are_distinct_lenses": True,
            "comparison_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
            "shared_value_index_presentation_only": value_coordinate is not None,
            "raw_value_subtraction_used": False,
            "display_value_index_subtraction_allowed": (
                value_coordinate.display_gap_subtraction_allowed
                if value_coordinate is not None
                else False
            ),
            "team_value_total_created": False,
            "team_value_rank_created": False,
            "league_market_value_available": False,
            "team_utility_included": False,
            "fsffl_cardinal_value_included": False,
            "recommendation_authority": False,
            "acceptance_probability": None,
        },
    }
