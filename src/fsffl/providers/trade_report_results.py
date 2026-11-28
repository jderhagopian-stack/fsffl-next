"""Compact public NFL results for retrospective reporting (nflverse player stats and schedule)."""
import csv
import io
import re
from collections import defaultdict
from datetime import date
from threading import Lock
from time import monotonic
from urllib.request import urlopen

SCHEDULE = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
WEEKLY = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{}.csv"
_lock = Lock()
_cache = {}


def player_key(name, position):
    return re.sub("[^a-z0-9]", "", name.casefold()), position


def read_results(season, games, rows):
    dates = {r["game_id"]: date.fromisoformat(r["gameday"]) for r in games
             if r["season"] == str(season) and r["game_type"] == "REG" and r["home_score"] != "" and r["away_score"] != ""}
    lines = defaultdict(dict)
    ambiguous = set()
    identities = {}
    for r in rows:
        if r["season"] != str(season) or r["season_type"] != "REG" or r["game_id"] not in dates:
            continue
        pos = r["position"]
        if pos not in {"QB", "WR", "RB", "TE"}:
            continue
        key = player_key(r["player_display_name"], pos)
        if not r["player_id"] or identities.setdefault(key, r["player_id"]) != r["player_id"]:
            ambiguous.add(key)
        day = dates[r["game_id"]]
        fields = ("passing_yards", "passing_tds") if pos == "QB" else ("rushing_yards","receiving_yards","rushing_tds","receiving_tds")
        if any(r.get(f) in (None, "") for f in fields):
            continue
        totals = tuple(int(r[f]) for f in fields)
        yards, td = totals if pos == "QB" else (sum(totals[:2]),sum(totals[2:]))
        row = (day,int(r["week"]),yards,td)
        if day in lines[key] and lines[key][day] != row:
            ambiguous.add(key)
        lines[key][day] = row
    return {key:tuple(sorted(games.values())) for key,games in lines.items() if key not in ambiguous}


def _rows(url):
    with urlopen(url,timeout=5) as response:
        data = response.read(12_000_001)
    if len(data)>12_000_000:
        raise ValueError("Report source exceeds the season file limit")
    return csv.DictReader(io.StringIO(data.decode("utf-8-sig")))


def published_results(season):
    """One public season at a time; a failed update preserves the previous release."""
    if not 2000 <= season <= date.today().year+1:
        return {}
    with _lock:
        expires, previous = _cache.get(season,(0,{}))
        if monotonic()<expires:
            return previous
        try:
            current = read_results(season,_rows(SCHEDULE),_rows(WEEKLY.format(season)))
            if not current:
                raise ValueError("Empty weekly release")
            ttl=3600
        except (OSError,ValueError,KeyError,csv.Error):
            current,ttl=previous,120
        if len(_cache)>=2 and season not in _cache:
            _cache.pop(next(iter(_cache)))
        _cache[season]=monotonic()+ttl,current
        return current
