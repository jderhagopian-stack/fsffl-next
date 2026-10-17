from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

from fsffl.execution_cooperation import cooperative_cpu_yield
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.providers.razzball_live import RazzballProjectionSnapshot
from fsffl.state.models import LeagueState, Player, Position, Provenance, ProviderRef

from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation


_TEAM_ALIASES = {
    "JAC": "JAX",
    "WSH": "WAS",
    "LA": "LAR",
}
_NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# NFL's canonical profile uses the formal URL and the shortened display name:
# https://www.nfl.com/players/chigoziem-okonkwo/ (verified 2026-10-17).
# Bind spelling equivalence to the asserted player identity and position; this
# is not fuzzy matching or permission to merge unrelated players by nickname.
_VERIFIED_PLAYER_NAMES = {
    ("sleeper:player:8210", Position.TE): frozenset({"chigokonkwo", "chigoziemokonkwo"}),
}

_STAT_METRICS: dict[str, ForecastMetric] = {
    "pass_yd": ForecastMetric.PASS_YARDS,
    "pass_td": ForecastMetric.PASS_TD,
    "pass_int": ForecastMetric.INTERCEPTIONS,
    "rush_yd": ForecastMetric.RUSH_YARDS,
    "rush_td": ForecastMetric.RUSH_TD,
    "rec": ForecastMetric.RECEPTIONS,
    "rec_yd": ForecastMetric.REC_YARDS,
    "rec_td": ForecastMetric.REC_TD,
    "fum_lost": ForecastMetric.FUMBLES_LOST,
}

_RAZZBALL_COLUMNS: dict[str, str] = {
    "Pass Yds": "pass_yd",
    "Pass TD": "pass_td",
    "Int": "pass_int",
    "Rush Yds": "rush_yd",
    "Run TD": "rush_td",
    "Rec": "rec",
    "Rec Yds": "rec_yd",
    "Rec TD": "rec_td",
    "Fum Lst": "fum_lost",
}


def canonical_season_window(season: int) -> tuple[datetime, datetime]:
    """Return one shared comparison window for full-season provider projections."""

    return (
        datetime(season, 9, 1, tzinfo=UTC),
        datetime(season + 1, 3, 1, tzinfo=UTC),
    )


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    parts = re.findall(r"[a-z0-9]+", ascii_text.lower())
    while parts and parts[-1] in _NAME_SUFFIXES:
        parts.pop()
    return "".join(parts)


def _normalize_team(value: str | None) -> str:
    team = (value or "").upper().strip()
    return _TEAM_ALIASES.get(team, team)


def _player_indexes(players: tuple[Player, ...]) -> tuple[
    dict[tuple[str, Position, str], list[Player]],
    dict[tuple[str, Position], list[Player]],
]:
    exact: dict[tuple[str, Position, str], list[Player]] = {}
    loose: dict[tuple[str, Position], list[Player]] = {}
    for index, player in enumerate(players):
        cooperative_cpu_yield(index)
        name = _normalize_name(player.full_name)
        team = _normalize_team(player.nfl_team)
        names = {name}
        verified = _VERIFIED_PLAYER_NAMES.get((player.player_id, player.position), frozenset())
        if name in verified:
            names.update(verified)
        for indexed_name in names:
            exact.setdefault((indexed_name, player.position, team), []).append(player)
            loose.setdefault((indexed_name, player.position), []).append(player)
    return exact, loose


def _provider_identity_index(players: tuple[Player, ...]) -> dict[tuple[str, str], list[Player]]:
    """Index only provider identities already asserted by canonical State."""

    result: dict[tuple[str, str], list[Player]] = {}
    for player in players:
        for reference in player.provider_refs:
            key = (reference.provider.strip().lower(), reference.external_id.strip())
            if key[0] and key[1]:
                result.setdefault(key, []).append(player)
    return result


def map_projection_rows(
    snapshot: CurrentProjectionSnapshot,
    *,
    players: tuple[Player, ...],
) -> tuple[tuple[CurrentProjectionRow, Player], ...]:
    """Map provider rows to any supplied canonical player universe.

    This is shared by normal forecast ingestion and bounded acquisition packets.
    The frozen Career reference cohort is deliberately not consulted here.
    Explicit canonical provider references win; otherwise only unique exact
    name/position/team or unique name/position matches (including verified
    canonical identity spellings) are accepted.
    """
    exact_index, loose_index = _player_indexes(players)
    provider_index = _provider_identity_index(players)
    mapped: list[tuple[CurrentProjectionRow, Player]] = []
    for index, row in enumerate(snapshot.rows):
        cooperative_cpu_yield(index)
        provider_matches = provider_index.get(
            (snapshot.provider.strip().lower(), row.external_id.strip()), []
        )
        if provider_matches:
            if len(provider_matches) != 1 or provider_matches[0].position != row.position:
                continue
            player = provider_matches[0]
        else:
            name = _normalize_name(row.player_name)
            team = _normalize_team(row.nfl_team)
            exact = exact_index.get((name, row.position, team), [])
            if len(exact) == 1:
                player = exact[0]
            elif len(exact) > 1:
                continue
            else:
                loose = loose_index.get((name, row.position), [])
                if len(loose) != 1:
                    continue
                player = loose[0]
        mapped.append((row, player))
    return tuple(mapped)


def _float_or_none(value: str | None) -> float | None:
    raw = (value or "").replace(",", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def current_snapshot_from_razzball(snapshot: RazzballProjectionSnapshot) -> CurrentProjectionSnapshot:
    """Convert the Razzball acquisition shape into the shared current-row contract."""

    position_map = {"QB": Position.QB, "RB": Position.RB, "WR": Position.WR, "TE": Position.TE}
    rows: list[CurrentProjectionRow] = []
    for index, raw in enumerate(snapshot.rows):
        cooperative_cpu_yield(index)
        position_text = (raw.get("Pos") or "").upper().strip()
        position = position_map.get(position_text)
        name = (raw.get("Name") or "").strip()
        team = (raw.get("Team") or "").upper().strip()
        if position is None or not name or not team:
            continue
        stats: dict[str, float] = {}
        for column, canonical_stat in _RAZZBALL_COLUMNS.items():
            value = _float_or_none(raw.get(column))
            if value is not None:
                stats[canonical_stat] = value
        if not stats:
            continue
        rows.append(
            CurrentProjectionRow(
                provider=snapshot.provider_name,
                external_id=f"{position.value}:{team}:{_normalize_name(name)}",
                player_name=name,
                position=position,
                nfl_team=team,
                stats=stats,
            )
        )
    return CurrentProjectionSnapshot(
        provider=snapshot.provider_name,
        captured_at=snapshot.captured_at,
        effective_at=snapshot.effective_at,
        rows=tuple(rows),
        source_version=snapshot.source_version,
        usage_class=snapshot.usage_class,
    )


def normalize_projection_snapshot(
    snapshot: CurrentProjectionSnapshot,
    *,
    league_state: LeagueState | None = None,
    players: tuple[Player, ...] | None = None,
    horizon: ForecastHorizon,
    period_start: datetime,
    period_end: datetime,
    evaluation_as_of: datetime,
) -> tuple[ForecastObservation, ...]:
    """Resolve one provider snapshot into canonical observations for one explicit horizon.

    The caller owns the canonical period identity. This function never guesses whether
    a provider row is season, ROS, or weekly evidence; that semantic choice must be made
    by the horizon-specific acquisition path before normalization.
    """

    for name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
        ("evaluation_as_of", evaluation_as_of),
    ):
        if value.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware")
    period_start = period_start.astimezone(UTC)
    period_end = period_end.astimezone(UTC)
    evaluation_as_of = evaluation_as_of.astimezone(UTC)
    if period_end <= period_start:
        raise ValueError("projection period_end must be after period_start")
    if snapshot.effective_at > evaluation_as_of:
        raise ValueError("provider snapshot cannot postdate evaluation_as_of")

    if (league_state is None) == (players is None):
        raise ValueError("provide exactly one canonical player universe: league_state or players")
    player_universe = league_state.players if league_state is not None else players
    if player_universe is None:
        raise ValueError("canonical player universe is unavailable")
    observations: list[ForecastObservation] = []

    mapped_rows = map_projection_rows(snapshot, players=tuple(player_universe))
    for row, player in mapped_rows:
        provenance = Provenance(
            source=snapshot.provider,
            retrieved_at=snapshot.captured_at,
            effective_at=snapshot.effective_at,
            provider_ref=ProviderRef(provider=snapshot.provider, external_id=row.external_id),
            source_version=snapshot.source_version,
        )
        for stat, value in row.stats.items():
            metric = _STAT_METRICS.get(stat)
            if metric is None:
                continue
            observations.append(
                ForecastObservation(
                    player_id=player.player_id,
                    position=player.position,
                    horizon=horizon,
                    metric=metric,
                    period_start=period_start,
                    period_end=period_end,
                    distribution=ForecastDistribution(mean=float(value), stddev=0.0),
                    source=snapshot.provider,
                    model_version=snapshot.source_version,
                    as_of=evaluation_as_of,
                    provenance=provenance,
                )
            )

    return tuple(
        sorted(
            observations,
            key=lambda item: (item.player_id, item.metric.value, item.source),
        )
    )


def normalize_current_projection_snapshot(
    snapshot: CurrentProjectionSnapshot,
    *,
    league_state: LeagueState,
    season: int,
    evaluation_as_of: datetime,
) -> tuple[ForecastObservation, ...]:
    """Resolve one current provider snapshot into canonical full-season observations.

    The provider's own effective timestamp remains in provenance. `evaluation_as_of`
    is the common FSFFL cutoff used to compare multiple current providers that were
    published on different dates. This keeps like-for-like ensemble grouping intact
    without pretending their source publication times were identical.
    """

    period_start, period_end = canonical_season_window(season)
    return normalize_projection_snapshot(
        snapshot,
        league_state=league_state,
        horizon=ForecastHorizon.SEASON,
        period_start=period_start,
        period_end=period_end,
        evaluation_as_of=evaluation_as_of,
    )
