from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Mapping

from fsffl.providers.razzball_live import RazzballProjectionSnapshot
from fsffl.state.models import FrozenModel, LeagueState, Player, Position, Provenance, ProviderRef

from ..models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)


class PlayerMatchMethod(StrEnum):
    EXACT_NAME_POSITION_TEAM = "exact_name_position_team"
    UNIQUE_NAME_POSITION = "unique_name_position"


class ProjectionMatch(FrozenModel):
    provider_name: str
    provider_team: str
    provider_position: str
    player_id: str
    player_name: str
    method: PlayerMatchMethod


class ProjectionCoverageReport(FrozenModel):
    provider: str
    source_version: str
    total_rows: int
    eligible_offensive_rows: int
    matched_rows: int
    exact_matches: int
    fallback_matches: int
    ambiguous_rows: tuple[str, ...]
    unmatched_rows: tuple[str, ...]
    matches: tuple[ProjectionMatch, ...]
    usage_class: str


_POSITION_MAP = {
    "QB": Position.QB,
    "RB": Position.RB,
    "WR": Position.WR,
    "TE": Position.TE,
}

_TEAM_ALIASES = {
    "JAC": "JAX",
    "WSH": "WAS",
    "LA": "LAR",
}

_METRIC_COLUMNS: dict[str, ForecastMetric] = {
    "Pass Yds": ForecastMetric.PASS_YARDS,
    "Pass TD": ForecastMetric.PASS_TD,
    "Int": ForecastMetric.INTERCEPTIONS,
    "Rush Yds": ForecastMetric.RUSH_YARDS,
    "Run TD": ForecastMetric.RUSH_TD,
    "Rec": ForecastMetric.RECEPTIONS,
    "Rec Yds": ForecastMetric.REC_YARDS,
    "Rec TD": ForecastMetric.REC_TD,
}


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


def _float_value(row: Mapping[str, str], column: str) -> float | None:
    raw = (row.get(column) or "").replace(",", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def normalize_razzball_snapshot(
    snapshot: RazzballProjectionSnapshot,
    *,
    league_state: LeagueState,
    period_end: datetime,
) -> tuple[tuple[ForecastObservation, ...], ProjectionCoverageReport]:
    """Resolve Razzball rows against canonical players and emit raw NEXT-2 stats.

    Provider fantasy-point totals are intentionally ignored. FSFFL derives
    fantasy points later from raw stats and canonical league scoring rules.
    """

    if period_end.tzinfo is None:
        raise ValueError("period_end must be timezone-aware")
    if period_end <= snapshot.effective_at:
        raise ValueError("period_end must be after provider effective_at")

    exact_index, loose_index = _player_indexes(league_state)
    observations: list[ForecastObservation] = []
    matches: list[ProjectionMatch] = []
    ambiguous: list[str] = []
    unmatched: list[str] = []
    eligible = 0
    exact_count = 0
    fallback_count = 0

    for row in snapshot.rows:
        provider_position = (row.get("Pos") or "").upper().strip()
        position = _POSITION_MAP.get(provider_position)
        if position is None:
            continue
        eligible += 1
        provider_name = (row.get("Name") or "").strip()
        provider_team = _normalize_team(row.get("Team"))
        normalized_name = _normalize_name(provider_name)
        candidates = exact_index.get((normalized_name, position, provider_team), [])
        method: PlayerMatchMethod | None = None
        if len(candidates) == 1:
            player = candidates[0]
            method = PlayerMatchMethod.EXACT_NAME_POSITION_TEAM
            exact_count += 1
        elif len(candidates) > 1:
            ambiguous.append(f"{provider_name}|{provider_position}|{provider_team}")
            continue
        else:
            loose = loose_index.get((normalized_name, position), [])
            if len(loose) == 1:
                player = loose[0]
                method = PlayerMatchMethod.UNIQUE_NAME_POSITION
                fallback_count += 1
            elif len(loose) > 1:
                ambiguous.append(f"{provider_name}|{provider_position}|{provider_team}")
                continue
            else:
                unmatched.append(f"{provider_name}|{provider_position}|{provider_team}")
                continue

        matches.append(
            ProjectionMatch(
                provider_name=provider_name,
                provider_team=provider_team,
                provider_position=provider_position,
                player_id=player.player_id,
                player_name=player.full_name,
                method=method,
            )
        )
        external_id = f"{_normalize_name(provider_name)}:{provider_position}:{provider_team}"
        provenance = Provenance(
            source=snapshot.provider_name,
            retrieved_at=snapshot.captured_at,
            effective_at=snapshot.effective_at,
            provider_ref=ProviderRef(provider=snapshot.provider_name, external_id=external_id),
            source_version=snapshot.source_version,
        )
        for column, metric in _METRIC_COLUMNS.items():
            value = _float_value(row, column)
            if value is None:
                continue
            observations.append(
                ForecastObservation(
                    player_id=player.player_id,
                    position=player.position,
                    horizon=ForecastHorizon.REST_OF_SEASON,
                    metric=metric,
                    period_start=snapshot.effective_at,
                    period_end=period_end,
                    distribution=ForecastDistribution(mean=value, stddev=0.0),
                    source=snapshot.provider_name,
                    model_version=snapshot.source_version,
                    as_of=snapshot.effective_at,
                    provenance=provenance,
                )
            )

    report = ProjectionCoverageReport(
        provider=snapshot.provider_name,
        source_version=snapshot.source_version,
        total_rows=len(snapshot.rows),
        eligible_offensive_rows=eligible,
        matched_rows=len(matches),
        exact_matches=exact_count,
        fallback_matches=fallback_count,
        ambiguous_rows=tuple(sorted(ambiguous)),
        unmatched_rows=tuple(sorted(unmatched)),
        matches=tuple(sorted(matches, key=lambda item: item.player_id)),
        usage_class=snapshot.usage_class,
    )
    return (
        tuple(
            sorted(
                observations,
                key=lambda item: (item.player_id, item.metric.value),
            )
        ),
        report,
    )
