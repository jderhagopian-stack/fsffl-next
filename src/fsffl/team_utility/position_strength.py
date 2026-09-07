from __future__ import annotations

from fsffl.state.models import FrozenModel, Position

from .models import OptimizedTeamLineup


class PositionLineupStrength(FrozenModel):
    position: Position
    starter_count: int
    expected_points: float


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
