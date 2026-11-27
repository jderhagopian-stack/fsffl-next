"""Normalize Sleeper's title game and winner links. Ignore consolation and placement paths."""
from math import isfinite

from fsffl.state.postseason import BracketGame


def championship_path(state, rows, score_weeks, start):
    if not isinstance(rows, list) or not rows or not start:
        return ()
    # Scores are looked up by the roster named by the official bracket. A
    # matchup_id also appears on byes and placement games and is not an edge.
    boundary = state.completed_through_week or 0
    teams = {
        ref.external_id: t.team_id for t in state.teams for ref in t.provider_refs if ref.provider == "sleeper"
    }
    def team(value):
        return teams[str(value)] if value is not None else None

    def score(week, roster):
        matches = [r for r in score_weeks.get(str(week), ()) if r.get("roster_id") == roster]
        if len(matches) != 1:
            return None
        row = matches[0]
        value = row.get("custom_points")
        if value is None:
            value = row.get("points")
        return value if type(value) in (int, float) and isfinite(value) else None

    try:
        finals = [r for r in rows if r.get("p") == 1]
        if len(finals) != 1:
            return ()
        indexed = {r["m"]: r for r in rows}
        if len(indexed) != len(rows):
            return ()
        path = {}
        pending = [finals[0]]
        while pending:
            r = pending.pop()
            mid = r["m"]
            if mid in path:
                return ()
            week = start + r["r"] - 1
            completed = week <= boundary
            sides = []
            for side in ("t1", "t2"):
                source = r.get(side + "_from")
                parent = None
                feeder = None
                if source is not None:
                    if set(source) != {"w"}:
                        return ()
                    parent = source["w"]
                    feeder = indexed.get(parent)
                    if feeder is not None:
                        pending.append(feeder)
                roster = r.get(side)
                # A later archive can contain a descendant's eventual participants.
                # Hide those identities until their feeder week is complete.
                if parent is not None and (feeder is None or start + feeder["r"] - 1 > boundary):
                    roster = None
                elif parent is not None and roster is None:
                    roster = feeder.get("w")
                sides.append((team(roster), parent, score(week, roster) if completed else None))
            left, right = sides
            path[mid] = BracketGame(game=mid, week=week, left=left[0], right=right[0],
                left_from=left[1], right_from=right[1], left_points=left[2], right_points=right[2],
                winner=team(r.get("w")) if completed else None, loser=team(r.get("l")) if completed else None)
        return tuple(sorted(path.values(), key=lambda g: (g.week, g.game)))
    except (KeyError, TypeError, ValueError, AttributeError):
        return ()
