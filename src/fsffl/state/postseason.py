"""Official championship path and its agreement with completed weekly scores."""
from pydantic import BaseModel, ConfigDict


class BracketGame(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)
    game: int
    week: int
    left: str | None
    right: str | None
    left_from: int | None
    right_from: int | None
    winner: str | None
    loser: str | None
    left_points: float | None
    right_points: float | None


def verified_path(state, rules):
    games = state.winners_bracket
    if not games or not rules or rules.simulation_unavailability_reason():
        return ()
    return verified_championship_tree(state, rules.round_weeks, rules.playoff_team_count, rules.bye_count)


def verified_championship_tree(state, weeks, field_size, bye_count):
    games = state.winners_bracket
    if not games or not weeks:
        return ()
    seeds = set()
    byes = set()
    routed = set()
    known = {t.team_id for t in state.teams}
    prior = {}
    for g in games:
        if g.week not in weeks or g.game in prior:
            return ()
        for team, parent in ((g.left, g.left_from), (g.right, g.right_from)):
            if parent is None:
                if team not in known or team in seeds or weeks.index(g.week) > 1:
                    return ()
                seeds.add(team)
                if g.week != weeks[0]:
                    byes.add(team)
            else:
                previous = prior.get(parent)
                if (previous is None or weeks.index(g.week) != weeks.index(previous.week) + 1
                        or parent in routed or team != previous.winner):
                    return ()
                routed.add(parent)
        if g.week <= (state.completed_through_week or 0):
            if (not g.left or not g.right or g.left == g.right
                    or g.left_points is None or g.right_points is None or g.left_points == g.right_points):
                return ()
            winner, loser = (g.left, g.right) if g.left_points > g.right_points else (g.right, g.left)
            if (g.winner, g.loser) != (winner, loser):
                return ()
        elif any(x is not None for x in (g.winner, g.loser, g.left_points, g.right_points)):
            return ()
        prior[g.game] = g
    if (len(seeds) != field_size or len(byes) != bye_count
            or len(games) != len(seeds)-1 or games[-1].week != weeks[-1]
            or set(prior)-routed != {games[-1].game}):
        return ()
    return games
