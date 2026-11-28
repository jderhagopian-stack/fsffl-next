"""Optional private, dated editorial notes attached to exact completed receipts."""
from datetime import date
import json
import os
from pathlib import Path

SCALE = ("DISASTER", "DUMPSTER", "OOF", "FAIR", "NICE", "ON FIRE", "NUCLEAR")
MARKS = {*SCALE, "TOO SOON", "LINKED"}


def read_editorial(league, season, as_of):
    if not league.isdecimal():
        return {}
    directory = Path(os.getenv("FSFFL_REPORT_EDITION_DIR", "/etc/secrets"))
    path = directory / f"trade-annual-{league}-{season}.json"
    try:
        if path.stat().st_size > 2_000_000:
            return {}
        issue = json.loads(path.read_text())
        if (issue["league"] == league and issue["season"] == season
                and date.fromisoformat(issue["published"]) <= as_of.date()
                and isinstance(issue["teams"], dict) and isinstance(issue["trades"], dict)):
            return issue
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return {}


def reviewed_trade(issue, moves):
    entry = issue.get("trades", {}).get(moves[0].source_sha256)
    if not isinstance(entry, dict) or not isinstance(entry.get("argument"), str):
        return None
    grades = entry.get("grades")
    if not isinstance(grades, dict) or set(grades) != {str(m.event.roster_id) for m in moves}:
        return None
    if not all(isinstance(pair, list) and len(pair) == 2 and all(
            isinstance(mark, str) and mark in MARKS for mark in pair) for pair in grades.values()):
        return None
    return entry
