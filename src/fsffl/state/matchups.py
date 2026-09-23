from __future__ import annotations

from .models import LeagueMatchup, LeagueState


def completed_through_week(state: LeagueState) -> int | None:
    """Return the strongest governed matchup-completion boundary available.

    Canonical provider state may carry an explicit completed-through coordinate.
    Older persisted snapshots predate that field, so they fail closed by deriving
    only the latest week with affirmative scoring evidence. Trailing numeric 0-0
    schedule placeholders therefore never advance the completion boundary.
    """

    if state.completed_through_week is not None:
        return state.completed_through_week

    evidenced_weeks = {
        matchup.week
        for matchup in state.matchups
        if matchup.team_a_points is not None
        and matchup.team_b_points is not None
        and (
            float(matchup.team_a_points) != 0.0
            or float(matchup.team_b_points) != 0.0
        )
    }
    return max(evidenced_weeks, default=None)


def completed_matchups(state: LeagueState) -> tuple[LeagueMatchup, ...]:
    """Return matchups proven complete under the canonical State contract."""

    boundary = completed_through_week(state)
    if boundary is None:
        return ()
    return tuple(
        matchup
        for matchup in state.matchups
        if matchup.week <= boundary
        and matchup.team_a_points is not None
        and matchup.team_b_points is not None
    )
