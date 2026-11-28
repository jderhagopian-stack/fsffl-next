"""Read completed Sleeper lineup boxes only on explicit report generation."""
from concurrent.futures import ThreadPoolExecutor
from math import isfinite
from threading import BoundedSemaphore
from time import monotonic

from fsffl.forecast.late_start_snapshot import _schedule_coordinate
from fsffl.providers.sleeper_live import SleeperLiveSource

_admission = BoundedSemaphore(1)


def scored_weeks(state, league, cutoff, source):
    end = min(state.completed_through_week or 0, state.league.rules.fantasy_regular_season_end_week or 0)
    if not end:
        return ()
    dates = {}
    for game in source.fetch_nfl_regular_season_schedule(season=state.league.season):
        week = int(game["week"])
        if 1 <= week <= end:
            dates.setdefault(week, []).append(_schedule_coordinate(game)[1])
    weeks = [w for w in range(1, end+1) if max(dates[w]) < cutoff.date()]
    roster_ids = {int(r.external_id): t.team_id for t in state.teams for r in t.provider_refs if r.provider == "sleeper"}
    scores = {(m.week, team): points for m in state.matchups for team, points in
              ((m.team_a_id, m.team_a_points), (m.team_b_id, m.team_b_points))}
    def read(week):
        rows = source.fetch_league_matchup_week(league, week)
        lineups = {}
        for row in rows:
            rid = int(row["roster_id"])
            score = row.get("custom_points") if row.get("custom_points") is not None else row.get("points")
            expected = scores.get((week, roster_ids[rid]))
            if expected is None or score is None or abs(float(score)-expected) > .011 or rid in lineups:
                raise ValueError("Weekly totals conflict with the saved standings")
            starters, points = row["starters"], row["starters_points"]
            if not starters or len(starters) != len(points):
                raise ValueError("Incomplete weekly starters")
            lineup = {}
            for player, pts in zip(starters, points):
                if str(player) == "0":
                    continue
                if not player or type(pts) not in (int, float) or not isfinite(pts):
                    raise ValueError("Missing starter score")
                ref = f"sleeper:player:{player}"
                if ref in lineup:
                    raise ValueError("Duplicate starter")
                lineup[ref] = pts
            lineups[rid] = lineup
        if lineups.keys() != roster_ids.keys():
            raise ValueError("Missing weekly lineup")
        return min(dates[week]), max(dates[week]), lineups
    with ThreadPoolExecutor(max_workers=3) as executor:
        return tuple(executor.map(read, weeks))


# Keep only the compact scores. State objects and full provider payloads may be large.
_cache = {}


def report_boxes(state, league, cutoff):
    key = (state.state_id, league, cutoff)
    if not _admission.acquire(blocking=False):
        raise BlockingIOError("Another trade report is checking lineups. Try again shortly.")
    try:
        cached = _cache.get(key)
        if cached and cached[0] > monotonic():
            return cached[1]
        result = scored_weeks(state, league, cutoff, SleeperLiveSource(timeout_seconds=4))
        if len(_cache) >= 3 and key not in _cache:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (monotonic()+600, result)
        return result
    except (OSError, KeyError, ValueError, TypeError):
        return ()
    finally:
        _admission.release()
