from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.providers.sleeper import SleeperNormalizer, SleeperPayloadBundle
from fsffl.state.models import (
    LeagueState,
    NflTeamBye,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    ProviderRef,
)


_TEAM_ALIASES = {
    "JAC": "JAX",
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LAR",
}
_FANTASY_POSITIONS = {
    "QB": Position.QB,
    "RB": Position.RB,
    "WR": Position.WR,
    "TE": Position.TE,
}


class SleeperSnapshotNormalizer:
    """Bridge an acquired Sleeper snapshot into canonical point-in-time State.

    Current live snapshots include the unrostered QB/RB/WR/TE universe by default
    so waiver/free-agent discovery has canonical candidates. Historical callers can
    explicitly disable that enrichment when their snapshot does not carry a valid
    point-in-time player universe.
    """

    provider_name = "sleeper"

    def __init__(self, *, include_unrostered_players: bool = True) -> None:
        self._normalizer = SleeperNormalizer()
        self._include_unrostered_players = include_unrostered_players

    def normalize_snapshot(self, snapshot: ProviderSnapshot, *, as_of) -> LeagueState:
        if snapshot.provider_name != self.provider_name:
            raise ValueError("snapshot provider must be sleeper")
        payload = snapshot.payload
        required = ("league", "users", "rosters", "players")
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"Sleeper snapshot missing required payloads: {', '.join(missing)}")

        bundle = SleeperPayloadBundle(
            league=payload["league"],
            users=payload["users"],
            rosters=payload["rosters"],
            players=payload["players"],
            traded_picks=payload.get("traded_picks", ()),
            matchups=payload.get("matchups", {}),
            retrieved_at=snapshot.captured_at,
        )
        state = self._normalizer.normalize(bundle, as_of=as_of)
        if self._include_unrostered_players:
            state = _attach_current_fantasy_player_universe(
                state,
                payload.get("players"),
                retrieved_at=snapshot.captured_at,
                effective_at=as_of,
            )
        state = _attach_fantasy_regular_season_horizon(state, payload.get("league"))
        byes, schedule_provenance = _normalize_nfl_byes(
            payload.get("nfl_schedule", ()),
            season=state.league.season,
            retrieved_at=snapshot.captured_at,
            effective_at=as_of,
        )
        if not byes:
            return state
        return state.model_copy(
            update={
                "nfl_team_byes": byes,
                "provenance": state.provenance + (schedule_provenance,),
            }
        )


def _age_years(raw_age: Any) -> float | None:
    if isinstance(raw_age, bool) or raw_age is None:
        return None
    try:
        age = float(raw_age)
    except (TypeError, ValueError):
        return None
    return age if age >= 0 else None


def _attach_current_fantasy_player_universe(
    state: LeagueState,
    raw_players: Any,
    *,
    retrieved_at,
    effective_at,
) -> LeagueState:
    """Add current unrostered fantasy-relevant NFL players to live State.

    Ownership remains entirely in TeamState.roster. This only broadens the canonical
    player identity/state universe so Search can truthfully distinguish rostered
    assets from available players. Players without a current NFL team are excluded
    from automatic waiver discovery; no browser-side player catalog is invented.
    """

    if not isinstance(raw_players, Mapping):
        return state
    players_by_id = {player.player_id: player for player in state.players}
    states_by_id = {player_state.player_id: player_state for player_state in state.player_states}
    provenance = Provenance(
        source="sleeper:current_player_universe",
        retrieved_at=retrieved_at,
        effective_at=effective_at,
        provider_ref=ProviderRef(provider="sleeper", external_id="players:nfl"),
    )

    for external_id, raw in raw_players.items():
        if not isinstance(raw, Mapping):
            continue
        position = _FANTASY_POSITIONS.get(str(raw.get("position") or "").upper())
        nfl_team = _normalize_team(raw.get("team"))
        if position is None or nfl_team is None:
            continue
        player_id = f"sleeper:player:{external_id}"
        if player_id in players_by_id:
            continue
        full_name = str(
            raw.get("full_name")
            or " ".join(
                filter(None, [raw.get("first_name"), raw.get("last_name")])
            )
            or external_id
        )
        players_by_id[player_id] = Player(
            player_id=player_id,
            full_name=full_name,
            position=position,
            nfl_team=nfl_team,
            provider_refs=(ProviderRef(provider="sleeper", external_id=str(external_id)),),
        )
        status_raw = str(raw.get("status") or "unknown").lower()
        status = PlayerStatus.ACTIVE if status_raw == "active" else PlayerStatus.UNKNOWN
        states_by_id[player_id] = PlayerState(
            player_id=player_id,
            as_of=effective_at,
            age_years=_age_years(raw.get("age")),
            nfl_team=nfl_team,
            status=status,
            provenance=provenance,
        )

    return state.model_copy(
        update={
            "players": tuple(sorted(players_by_id.values(), key=lambda item: item.player_id)),
            "player_states": tuple(sorted(states_by_id.values(), key=lambda item: item.player_id)),
            "provenance": state.provenance + (provenance,),
        }
    )


def _attach_fantasy_regular_season_horizon(
    state: LeagueState,
    raw_league: Any,
) -> LeagueState:
    """Preserve Sleeper's configured regular-season endpoint as canonical rules.

    Future-week matchup payloads can be absent or incomplete even when the league's
    schedule horizon is already known. Forecast horizon authority must therefore use
    the configured playoff start, not infer the season length from currently
    materialized matchup rows.
    """

    if not isinstance(raw_league, Mapping):
        return state
    settings = raw_league.get("settings")
    if not isinstance(settings, Mapping):
        return state
    raw_start = settings.get("playoff_week_start")
    try:
        playoff_week_start = int(raw_start)
    except (TypeError, ValueError):
        return state
    end_week = playoff_week_start - 1
    if not 1 <= end_week <= 18:
        return state
    rules = state.league.rules.model_copy(
        update={"fantasy_regular_season_end_week": end_week}
    )
    return state.model_copy(
        update={"league": state.league.model_copy(update={"rules": rules})}
    )


def _normalize_team(raw: Any) -> str | None:
    if raw is None:
        return None
    team = str(raw).strip().upper()
    if not team:
        return None
    return _TEAM_ALIASES.get(team, team)


def _normalize_nfl_byes(
    raw_schedule: Any,
    *,
    season: int,
    retrieved_at,
    effective_at,
) -> tuple[tuple[NflTeamBye, ...], Provenance]:
    provenance = Provenance(
        source="sleeper:nfl_schedule",
        retrieved_at=retrieved_at,
        effective_at=effective_at,
        provider_ref=ProviderRef(
            provider="sleeper",
            external_id=f"nfl:regular:{season}",
        ),
    )
    if not isinstance(raw_schedule, Sequence) or isinstance(raw_schedule, (str, bytes)):
        return (), provenance

    teams: set[str] = set()
    teams_by_week: dict[int, set[str]] = {}
    for row in raw_schedule:
        if not isinstance(row, Mapping):
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if not 1 <= week <= 18:
            continue
        home = _normalize_team(row.get("home") or row.get("home_team"))
        away = _normalize_team(row.get("away") or row.get("away_team"))
        if home is None or away is None:
            continue
        teams.update((home, away))
        teams_by_week.setdefault(week, set()).update((home, away))

    # A complete NFL regular-season schedule exposes all 32 teams. Fail closed
    # rather than deriving false byes from a partial provider response.
    if len(teams) != 32 or not teams_by_week:
        return (), provenance

    bye_by_team: dict[str, int] = {}
    for week, playing in sorted(teams_by_week.items()):
        for team in teams - playing:
            if team in bye_by_team:
                return (), provenance
            bye_by_team[team] = week

    if set(bye_by_team) != teams:
        return (), provenance

    return (
        tuple(
            NflTeamBye(
                season=season,
                nfl_team=team,
                week=week,
                provenance=provenance,
            )
            for team, week in sorted(bye_by_team.items())
        ),
        provenance,
    )
