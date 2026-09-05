from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.providers.razzball_live import RazzballProjectionSnapshot
from fsffl.state.models import LeagueState, Player, Position, Provenance, ProviderRef

from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation


_TEAM_ALIASES = {
    "JAC": "JAX",
    "WSH": "WAS",
    "LA": "LAR",
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
    return re.sub(r"[^a-z0-9]+", "", ascii_text.lower())


def _normalize_team(value: str | None) -> str:
    team = (value or "").upper().strip()
    return _TEAM_ALIASES.get(team, team)


def _player_indexes(league_state: LeagueState) -> tuple[
    dict[tuple[str, Position, str], list[Player]],
    dict[tuple[str, Position], list[Player]],
]:
    exact: dict[tuple[str, Position, str], list[Player]] = {}
    loose: dict[tuple[str, Position], list[Player]] = {}
    for player in league_state.players:
        name = _normalize_name(player.full_name)
        team = _normalize_team(player.nfl_team)
        exact.setdefault((name, player.position, team), []).append(player)
        loose.setdefault((name, player.position), []).append(player)
    return exact, loose


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
    for raw in snapshot.rows:
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

    if evaluation_as_of.tzinfo is None:
        raise ValueError("evaluation_as_of must be timezone-aware")
    evaluation_as_of = evaluation_as_of.astimezone(UTC)
    if snapshot.effective_at > evaluation_as_of:
        raise ValueError("provider snapshot cannot postdate evaluation_as_of")

    period_start, period_end = canonical_season_window(season)
    exact_index, loose_index = _player_indexes(league_state)
    observations: list[ForecastObservation] = []

    for row in snapshot.rows:
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
                    horizon=ForecastHorizon.SEASON,
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
