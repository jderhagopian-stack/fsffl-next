from __future__ import annotations

from fsffl.state.models import FrozenModel, Position

from .models import OptimizedTeamLineup


class PositionLineupStrength(FrozenModel):
    position: Position
    starter_count: int
    expected_points: float


class LeagueRelativePositionStrength(FrozenModel):
    """Transparent league-relative positional strength from optimized production.

    The index is descriptive only: 100 equals the league-average optimized starter
    production at that position, 120 is 20% above average, and 80 is 20% below.
    It does not create a composite Team Utility score or introduce fitted weights.
    """

    team_id: str
    position: Position
    starter_count: int
    expected_points: float
    league_average_expected_points: float
    strength_index: float | None
    league_rank: int
    team_count: int
    model_version: str = "next4-league-relative-position-strength-v1"


class PositionStrengthDelta(FrozenModel):
    position: Position
    before_starter_count: int
    after_starter_count: int
    before_expected_points: float
    after_expected_points: float
    expected_points_delta: float


class TeamPositionStrengthComparison(FrozenModel):
    team_id: str
    positions: tuple[PositionStrengthDelta, ...]
    model_version: str = "next4-position-strength-comparison-v1"


def summarize_lineup_by_position(lineup: OptimizedTeamLineup) -> tuple[PositionLineupStrength, ...]:
    """Summarize authoritative optimized-lineup evidence without rescoring players."""

    totals: dict[Position, tuple[int, float]] = {}
    for assignment in lineup.assignments:
        count, points = totals.get(assignment.position, (0, 0.0))
        totals[assignment.position] = (count + 1, points + assignment.expected_points)
    return tuple(
        PositionLineupStrength(position=position, starter_count=count, expected_points=points)
        for position, (count, points) in sorted(totals.items(), key=lambda item: item[0].value)
    )


def build_league_relative_position_strengths(
    lineups: tuple[OptimizedTeamLineup, ...],
    *,
    positions: tuple[Position, ...] = (Position.QB, Position.RB, Position.WR, Position.TE),
    model_version: str = "next4-league-relative-position-strength-v1",
) -> tuple[LeagueRelativePositionStrength, ...]:
    """Compare each team's optimized positional production with the league average.

    Every team is included for every requested position. FLEX and SUPERFLEX remain
    attributed to the player's actual position through the optimized lineup itself.
    This is a named descriptive diagnostic for comparison and before/after views;
    it does not alter Forecast, Simulation, Value, or Decision authority.
    """

    if not model_version.strip():
        raise ValueError("position strength model_version cannot be blank")
    team_ids = [lineup.team_id for lineup in lineups]
    if len(team_ids) != len(set(team_ids)):
        raise ValueError("league-relative position strength requires unique team lineups")
    if not lineups:
        return ()

    summaries = {
        lineup.team_id: {row.position: row for row in summarize_lineup_by_position(lineup)}
        for lineup in lineups
    }
    result: list[LeagueRelativePositionStrength] = []
    team_count = len(lineups)
    for position in positions:
        rows: list[tuple[str, int, float]] = []
        for lineup in lineups:
            row = summaries[lineup.team_id].get(position)
            rows.append(
                (
                    lineup.team_id,
                    row.starter_count if row is not None else 0,
                    row.expected_points if row is not None else 0.0,
                )
            )
        league_average = sum(points for _, _, points in rows) / team_count
        ordered = sorted(rows, key=lambda item: (-item[2], item[0]))
        rank_by_team = {team_id: rank for rank, (team_id, _, _) in enumerate(ordered, start=1)}
        for team_id, starter_count, expected_points in rows:
            strength_index = (
                100.0 * expected_points / league_average
                if league_average > 0
                else None
            )
            result.append(
                LeagueRelativePositionStrength(
                    team_id=team_id,
                    position=position,
                    starter_count=starter_count,
                    expected_points=expected_points,
                    league_average_expected_points=league_average,
                    strength_index=strength_index,
                    league_rank=rank_by_team[team_id],
                    team_count=team_count,
                    model_version=model_version,
                )
            )
    return tuple(
        sorted(result, key=lambda row: (row.team_id, row.position.value))
    )


def compare_position_strengths(
    before: OptimizedTeamLineup,
    after: OptimizedTeamLineup,
    *,
    model_version: str = "next4-position-strength-comparison-v1",
) -> TeamPositionStrengthComparison:
    """Compare before/after optimized starter production by actual player position.

    This is a named Team Utility diagnostic, not a composite roster grade. FLEX and
    SUPERFLEX assignments remain attributed to the player's actual position so the
    output answers which positional strengths changed without inventing weights.
    """

    if before.team_id != after.team_id:
        raise ValueError("position strength comparison requires the same team")
    before_rows = {row.position: row for row in summarize_lineup_by_position(before)}
    after_rows = {row.position: row for row in summarize_lineup_by_position(after)}
    positions = sorted(set(before_rows) | set(after_rows), key=lambda item: item.value)
    rows = []
    for position in positions:
        b = before_rows.get(position)
        a = after_rows.get(position)
        before_count = b.starter_count if b else 0
        after_count = a.starter_count if a else 0
        before_points = b.expected_points if b else 0.0
        after_points = a.expected_points if a else 0.0
        rows.append(
            PositionStrengthDelta(
                position=position,
                before_starter_count=before_count,
                after_starter_count=after_count,
                before_expected_points=before_points,
                after_expected_points=after_points,
                expected_points_delta=after_points - before_points,
            )
        )
    return TeamPositionStrengthComparison(
        team_id=before.team_id,
        positions=tuple(rows),
        model_version=model_version,
    )
