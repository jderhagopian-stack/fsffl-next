from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fsffl.state.models import LeagueState, Provenance, RosterSlot

from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


PROVISIONAL_POSITION_FLOOR_SOURCE = "fsffl:provisional_position_floor"
PROVISIONAL_POSITION_FLOOR_MODEL_VERSION = "next2-provisional-position-floor-v1"


def attach_provisional_position_floor_forecasts(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    as_of: datetime,
    horizon: ForecastHorizon = ForecastHorizon.SEASON,
) -> tuple[ForecastObservation, ...]:
    """Fill rare active-roster forecast gaps from conservative live position evidence.

    This is a governed provisional fallback, not a second authoritative ensemble.
    For each active roster player missing a fantasy-points forecast, the mean uses
    the lowest currently available same-position FSFFL forecast and uncertainty
    uses the widest same-position calibrated standard deviation. No multiplicative
    haircut or hidden volatility coefficient is introduced.

    Taxi/IR players are intentionally excluded because they cannot fill a current
    legal lineup slot. If no same-position evidence exists, the function fails
    closed instead of fabricating a value.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    latest_by_player: dict[str, ForecastObservation] = {}
    by_position: dict[object, list[ForecastObservation]] = defaultdict(list)
    for observation in forecasts:
        if observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        if observation.horizon != horizon or observation.as_of > as_of:
            continue
        current = latest_by_player.get(observation.player_id)
        if current is None or observation.as_of > current.as_of:
            latest_by_player[observation.player_id] = observation

    for observation in latest_by_player.values():
        by_position[observation.position].append(observation)

    players_by_id = {player.player_id: player for player in league_state.players}
    active_player_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
        if entry.slot not in {RosterSlot.TAXI, RosterSlot.IR}
    }

    fallbacks: list[ForecastObservation] = []
    for player_id in sorted(active_player_ids - set(latest_by_player)):
        player = players_by_id.get(player_id)
        if player is None:
            raise ValueError(f"active roster references unknown player {player_id}")
        peers = by_position.get(player.position, [])
        if not peers:
            raise ValueError(
                f"no same-position forecast evidence for missing active player "
                f"{player.full_name} ({player.position.value})"
            )
        mean_peer = min(peers, key=lambda item: (item.distribution.mean, item.player_id))
        stddev = max(item.distribution.stddev for item in peers)
        fallbacks.append(
            ForecastObservation(
                player_id=player_id,
                position=player.position,
                horizon=horizon,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=mean_peer.period_start,
                period_end=mean_peer.period_end,
                distribution=ForecastDistribution(
                    mean=mean_peer.distribution.mean,
                    stddev=stddev,
                ),
                source=PROVISIONAL_POSITION_FLOOR_SOURCE,
                model_version=PROVISIONAL_POSITION_FLOOR_MODEL_VERSION,
                as_of=as_of,
                provenance=Provenance(
                    source=PROVISIONAL_POSITION_FLOOR_SOURCE,
                    retrieved_at=as_of,
                    effective_at=as_of,
                    source_version=PROVISIONAL_POSITION_FLOOR_MODEL_VERSION,
                ),
            )
        )

    return forecasts + tuple(fallbacks)
