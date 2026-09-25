from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Annotated

from pydantic import Field

from fsffl.state.models import FrozenModel, canonical_nfl_team

from .models import ForecastMetric, NflTeamUnitForecastSubject


class RealizedKickerGame(FrozenModel):
    season: Annotated[int, Field(ge=2000)]
    game_id: str
    player_id: str
    metrics: tuple[tuple[ForecastMetric, float], ...]
    missing_distance_attempts: Annotated[int, Field(ge=0)] = 0

    def value(self, metric: ForecastMetric) -> float:
        return dict(self.metrics).get(metric, 0.0)


class RealizedDstGame(FrozenModel):
    season: Annotated[int, Field(ge=2000)]
    game_id: str
    subject: NflTeamUnitForecastSubject
    metrics: tuple[tuple[ForecastMetric, float], ...]

    def value(self, metric: ForecastMetric) -> float:
        return dict(self.metrics).get(metric, 0.0)


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    try:
        return float(value) != 0.0
    except (TypeError, ValueError):
        return False


def _distance_bin_metric(distance: float, *, made: bool) -> ForecastMetric:
    if distance < 20:
        return ForecastMetric.FG_MADE_0_19 if made else ForecastMetric.FG_MISS_0_19
    if distance < 30:
        return ForecastMetric.FG_MADE_20_29 if made else ForecastMetric.FG_MISS_20_29
    if distance < 40:
        return ForecastMetric.FG_MADE_30_39 if made else ForecastMetric.FG_MISS_30_39
    if distance < 50:
        return ForecastMetric.FG_MADE_40_49 if made else ForecastMetric.FG_MISS_40_49
    if distance < 60:
        return ForecastMetric.FG_MADE_50_59 if made else ForecastMetric.FG_MISS_50_59
    return ForecastMetric.FG_MADE_60_PLUS if made else ForecastMetric.FG_MISS_60_PLUS


def reconstruct_kicker_games_from_nflverse(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[RealizedKickerGame, ...]:
    """Reconstruct direct kicker outcomes from nflverse/nflfastR-style PBP rows.

    The adapter intentionally uses raw kick result and distance evidence. Blocked
    field goals and extra points count as misses, matching the accepted research
    contract. Missing kick distance is retained as an explicit completeness defect
    rather than heuristically assigning a scoring band.
    """

    metrics_by_key: dict[tuple[int, str, str], dict[ForecastMetric, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    missing_distance_by_key: dict[tuple[int, str, str], int] = defaultdict(int)

    for row in rows:
        raw_player_id = row.get("kicker_player_id")
        raw_game_id = row.get("game_id")
        raw_season = row.get("season")
        if raw_player_id in (None, "") or raw_game_id in (None, "") or raw_season in (None, ""):
            continue
        try:
            season = int(raw_season)
        except (TypeError, ValueError):
            continue
        key = (season, str(raw_game_id), str(raw_player_id))
        metrics = metrics_by_key[key]

        fg_result_raw = row.get("field_goal_result")
        fg_result = str(fg_result_raw).strip().lower() if fg_result_raw not in (None, "") else ""
        is_fg = _truthy(row.get("field_goal_attempt")) or bool(fg_result)
        if is_fg:
            metrics[ForecastMetric.FG_ATTEMPT] += 1.0
            made = fg_result in {"made", "good", "success"}
            missed = fg_result in {"missed", "miss", "no good", "no_good", "blocked", "failed"}
            if made:
                metrics[ForecastMetric.FG_MADE] += 1.0
            elif missed:
                metrics[ForecastMetric.FG_MISS] += 1.0

            if made or missed:
                raw_distance = row.get("kick_distance")
                try:
                    distance = float(raw_distance)
                except (TypeError, ValueError):
                    missing_distance_by_key[key] += 1
                else:
                    metrics[_distance_bin_metric(distance, made=made)] += 1.0
                    if made:
                        metrics[ForecastMetric.FG_MADE_YARDS] += distance
                        metrics[ForecastMetric.FG_MADE_YARDS_OVER_30] += max(distance - 30.0, 0.0)

        xp_result_raw = row.get("extra_point_result")
        xp_result = str(xp_result_raw).strip().lower() if xp_result_raw not in (None, "") else ""
        is_xp = _truthy(row.get("extra_point_attempt")) or bool(xp_result)
        if is_xp:
            metrics[ForecastMetric.XP_ATTEMPT] += 1.0
            if xp_result in {"good", "made", "success"}:
                metrics[ForecastMetric.XP_MADE] += 1.0
            elif xp_result in {"failed", "missed", "miss", "no good", "no_good", "blocked"}:
                metrics[ForecastMetric.XP_MISS] += 1.0

    return tuple(
        RealizedKickerGame(
            season=season,
            game_id=game_id,
            player_id=player_id,
            metrics=tuple(sorted(metrics.items(), key=lambda item: item[0].value)),
            missing_distance_attempts=missing_distance_by_key[(season, game_id, player_id)],
        )
        for (season, game_id, player_id), metrics in sorted(metrics_by_key.items())
    )


def reconstruct_dst_games_from_nflverse(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[RealizedDstGame, ...]:
    """Reconstruct directly observable D/ST events from nflverse-style PBP.

    This deliberately does not derive points-allowed/yards-allowed bucket scoring,
    defensive two-point returns, or obscure team-special-teams fumble attribution.
    Those coordinates remain outside production authority until Sleeper truth
    fixtures establish exact platform semantics.
    """

    metrics_by_key: dict[tuple[int, str, str], dict[ForecastMetric, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    def metric_bucket(season: int, game_id: str, team: str) -> dict[ForecastMetric, float]:
        return metrics_by_key[(season, game_id, canonical_nfl_team(team))]

    for row in rows:
        raw_game_id = row.get("game_id")
        raw_season = row.get("season")
        if raw_game_id in (None, "") or raw_season in (None, ""):
            continue
        try:
            season = int(raw_season)
        except (TypeError, ValueError):
            continue
        game_id = str(raw_game_id)

        raw_defteam = row.get("defteam")
        defteam = None
        if raw_defteam not in (None, ""):
            try:
                defteam = canonical_nfl_team(str(raw_defteam))
            except ValueError:
                defteam = None

        if defteam is not None:
            metrics = metric_bucket(season, game_id, defteam)
            if _truthy(row.get("sack")):
                metrics[ForecastMetric.DST_SACK] += 1.0
            if _truthy(row.get("interception")):
                metrics[ForecastMetric.DST_INTERCEPTION] += 1.0
            if _truthy(row.get("fumble_lost")):
                metrics[ForecastMetric.DST_FUMBLE_RECOVERY] += 1.0
            if _truthy(row.get("fumble_forced")) or row.get("fumble_forced_1_player_id") not in (None, ""):
                metrics[ForecastMetric.DST_FORCED_FUMBLE] += 1.0
            if _truthy(row.get("safety")):
                metrics[ForecastMetric.DST_SAFETY] += 1.0
            if _truthy(row.get("punt_blocked")) or str(row.get("field_goal_result") or "").lower() == "blocked":
                metrics[ForecastMetric.DST_BLOCKED_KICK] += 1.0

            raw_td_team = row.get("td_team")
            td_team = None
            if raw_td_team not in (None, ""):
                try:
                    td_team = canonical_nfl_team(str(raw_td_team))
                except ValueError:
                    td_team = None
            turnover_td = (
                _truthy(row.get("touchdown"))
                and td_team == defteam
                and (_truthy(row.get("interception")) or _truthy(row.get("fumble_lost")))
            )
            if turnover_td:
                metrics[ForecastMetric.DST_DEFENSIVE_TD] += 1.0

        raw_td_team = row.get("td_team")
        if (
            _truthy(row.get("return_touchdown"))
            and (_truthy(row.get("kickoff_attempt")) or _truthy(row.get("punt_attempt")))
            and raw_td_team not in (None, "")
        ):
            try:
                td_team = canonical_nfl_team(str(raw_td_team))
            except ValueError:
                td_team = None
            if td_team is not None:
                metric_bucket(season, game_id, td_team)[ForecastMetric.DST_TEAM_ST_TD] += 1.0

    return tuple(
        RealizedDstGame(
            season=season,
            game_id=game_id,
            subject=NflTeamUnitForecastSubject(season=season, nfl_team=team),
            metrics=tuple(sorted(metrics.items(), key=lambda item: item[0].value)),
        )
        for (season, game_id, team), metrics in sorted(metrics_by_key.items())
    )
