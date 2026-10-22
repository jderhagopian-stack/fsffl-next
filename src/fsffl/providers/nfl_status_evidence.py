"""Recorded official NFL facts, acquired independently of product requests.

Season-unavailability receipts establish whole-season absence; separate current
role receipts only fence active-role eligibility. Neither supplies a player
projection, injury multiplier, signing probability or inferred return date.
Capture time deliberately fences historical replay.
"""
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json


@dataclass(frozen=True)
class SeasonUnavailabilityReceipt:
    player_id: str
    player_name: str
    position: str
    season: int
    source_url: str
    captured_at: datetime

    @property
    def fingerprint(self) -> str:
        # Hash the normalized recorded fact, not a claimed HTML byte capture.
        payload = {**asdict(self), "captured_at": self.captured_at.isoformat(),
                   "fact": "officially_reported_out_for_entire_season"}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# Official pages re-read through the connected web tool at this capture time.
# Publication dates are not substituted for the time evidence was acquired.
_CAPTURED_AT = datetime(2026, 10, 16, 0, 19, 13, tzinfo=UTC)
SEASON_UNAVAILABILITY_RECEIPTS = (
    SeasonUnavailabilityReceipt(
        "sleeper:player:11638", "Ricky Pearsall", "WR", 2026,
        "https://www.nfl.com/news/niners-wr-ricky-pearsall-knee-surgery-will-miss-2026-season",
        _CAPTURED_AT,
    ),
    SeasonUnavailabilityReceipt(
        "sleeper:player:12484", "Jayden Higgins", "WR", 2026,
        "https://www.nfl.com/news/texans-wr-jayden-higgins-torn-acl-out-2026-season",
        _CAPTURED_AT,
    ),
    SeasonUnavailabilityReceipt(
        "sleeper:player:13353", "Chris Brazzell", "WR", 2026,
        "https://www.panthers.com/news/rookie-wide-receiver-chris-brazzell-to-miss-the-entire-2026-season",
        _CAPTURED_AT,
    ),
)


@dataclass(frozen=True)
class NflRoleReceipt:
    """A captured current roster fact, never a season projection or return date."""

    player_id: str
    position: str
    season: int
    status: str
    source_url: str
    captured_at: datetime

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=str).encode()).hexdigest()


# Independently re-read official pages at this instant. These are current-role
# facts, not proof of an entire-season absence or provider projections.
_ROLE_CAPTURE = datetime(2026, 10, 18, 13, 33, 0, tzinfo=UTC)
NFL_ROLE_RECEIPTS = (
    # Retain the prior receipt: published historical States keep their exact
    # dependency identity when a newer current-role capture is appended.
    NflRoleReceipt("sleeper:player:6803", "WR", 2026, "reserve_left_squad",
        "https://www.nfl.com/teams/san-francisco-49ers/roster",
        datetime(2026, 10, 17, 21, 10, 38, tzinfo=UTC)),
    NflRoleReceipt("sleeper:player:6803", "WR", 2026, "reserve_left_squad",
        "https://www.nfl.com/teams/san-francisco-49ers/roster", _ROLE_CAPTURE),
    NflRoleReceipt("sleeper:player:3321", "WR", 2026, "unsigned",
        "https://www.nfl.com/players/tyreek-hill/", _ROLE_CAPTURE),
    NflRoleReceipt("sleeper:player:13268", "WR", 2026, "developmental_depth",
        "https://www.baltimoreravens.com/team/depth-chart", _ROLE_CAPTURE),
    # Rechecked against the official pages on 2026-10-20. Append rather than
    # replace so already-published State fingerprints remain reproducible.
    NflRoleReceipt("sleeper:player:3321", "WR", 2026, "unsigned",
        "https://www.nfl.com/players/tyreek-hill/",
        datetime(2026, 10, 20, 13, 29, 37, tzinfo=UTC)),
    NflRoleReceipt("sleeper:player:6803", "WR", 2026, "reserve_left_squad",
        "https://www.nfl.com/teams/san-francisco-49ers/roster",
        datetime(2026, 10, 20, 13, 29, 37, tzinfo=UTC)),
    NflRoleReceipt("sleeper:player:13268", "WR", 2026, "developmental_depth",
        "https://www.baltimoreravens.com/team/depth-chart",
        datetime(2026, 10, 20, 13, 29, 37, tzinfo=UTC)),
    # Rechecked against official pages on 2026-10-20 at 15:55 ET. The prior
    # six-hour receipt expired shortly before the owned Career build began.
    # Append to preserve every previously published State's input identity.
    NflRoleReceipt("sleeper:player:3321", "WR", 2026, "unsigned",
        "https://www.nfl.com/players/tyreek-hill/",
        datetime(2026, 10, 20, 19, 55, 28, tzinfo=UTC)),
    NflRoleReceipt("sleeper:player:6803", "WR", 2026, "reserve_left_squad",
        "https://www.nfl.com/teams/san-francisco-49ers/roster",
        datetime(2026, 10, 20, 19, 55, 28, tzinfo=UTC)),
    NflRoleReceipt("sleeper:player:13268", "WR", 2026, "developmental_depth",
        "https://www.baltimoreravens.com/team/depth-chart",
        datetime(2026, 10, 20, 19, 55, 28, tzinfo=UTC)),
)

# Management explicitly approved this input assumption in the Career #405
# continuation on 2026-10-18. Scope is these three verified identities/roles;
# another player needs an explicit policy admission, not an inferred zero.
YTD_ONLY_POLICY_VERSION = "career-ytd-only-v1:management-approved-20261018"
YTD_ONLY_POLICY_APPROVED_AT = datetime(2026, 10, 18, 13, 32, 35, tzinfo=UTC)
YTD_ONLY_APPROVED_ROLES = {
    "sleeper:player:3321": "unsigned",
    "sleeper:player:6803": "reserve_left_squad",
    "sleeper:player:13268": "developmental_depth",
}



def recorded_nfl_role_receipts(league_state, *, as_of: datetime) -> dict[str, NflRoleReceipt]:
    """Admit only bounded, roster/position/season/cutoff-matching role facts.

    Unlike a confirmed whole-season absence, a current roster role can change.
    Its six-hour validity is only an eligibility fence: expiration never becomes
    a zero projection, and no request performs a hidden source refresh.
    """
    if as_of.tzinfo is None:
        raise ValueError("NFL role cutoff must be timezone-aware")
    rostered = {entry.player_id for team in league_state.team_states for entry in team.roster}
    players = {player.player_id: player for player in league_state.players}
    return {row.player_id: row for row in sorted(NFL_ROLE_RECEIPTS, key=lambda row: row.captured_at)
            if row.player_id in rostered and row.player_id in players
            and players[row.player_id].position.value == row.position
            and league_state.league.season == row.season
            and row.captured_at <= as_of < row.captured_at + timedelta(hours=6)}


def corroborated_current_role_receipts(
    league_state, *, as_of: datetime, captured_at: datetime,
    catalog: dict | object,
) -> dict[str, NflRoleReceipt]:
    """Renew *verified* roles only when a fresh independent player feed agrees.

    A historical official receipt is not made fresh by fiat: this emits a
    separately sourced, timestamped corroboration from the current Sleeper
    player universe. Ambiguous and changed statuses fail closed. The caller
    must be a producer-owned acquisition, never a GET/chart reader.
    """
    from collections.abc import Mapping
    if as_of.tzinfo is None or captured_at.tzinfo is None:
        raise ValueError("current role times must be timezone-aware")
    if captured_at > as_of or as_of >= captured_at + timedelta(hours=6):
        return {}
    if not isinstance(catalog, Mapping):
        return {}
    rostered = {e.player_id for t in league_state.team_states for e in t.roster}
    players = {p.player_id: p for p in league_state.players}
    latest_verified: dict[str, NflRoleReceipt] = {}
    for row in sorted(NFL_ROLE_RECEIPTS, key=lambda item: item.captured_at):
        if row.captured_at <= as_of:
            latest_verified[row.player_id] = row
    renewed = {}
    for player_id in rostered & latest_verified.keys():
        old = latest_verified[player_id]
        player = players.get(player_id)
        if player is None or player.position.value != old.position or league_state.league.season != old.season:
            continue
        item = catalog.get(player_id.rsplit(":", 1)[-1])
        if not isinstance(item, Mapping):
            continue
        status = str(item.get("status") or "").strip().lower().replace("-", "_").replace(" ", "_")
        team = str(item.get("team") or "").strip()
        try:
            depth = int(item.get("depth_chart_order"))
        except (ValueError, TypeError):
            depth = None
        corroborated = (
            (old.status == "unsigned" and not team and status not in {"active", "practice_squad"})
            or (old.status == "reserve_left_squad" and status in {"rls", "reserve_left_squad", "reserve/left_squad"})
            or (old.status == "developmental_depth" and bool(team) and depth is not None and depth >= 3)
        )
        if corroborated:
            renewed[player_id] = NflRoleReceipt(
                player_id, old.position, old.season, old.status,
                "https://api.sleeper.app/v1/players/nfl", captured_at,
            )
    return renewed


def acquire_official_reserve_role_receipts(
    league_state, *, evaluation_cutoff: datetime,
    fetcher=None, allow_current_capture: bool = False,
) -> dict[str, NflRoleReceipt]:
    """Bounded live verification of the NFL's reserve/left-squad roster status.

    Called only by producer-owned acquisition. Unlike the Sleeper player feed,
    the official roster distinguishes RLS from an ordinary active registration.
    A failed/ambiguous parse produces no receipt, never a fabricated fact.
    A supplied fetcher is for deterministic tests and must return
    (html, actual_capture_time). The default fetcher cannot backdate time.
    """
    import re
    from html.parser import HTMLParser
    from urllib.request import Request, urlopen

    class RosterRows(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows = []
            self.current = None
        def handle_starttag(self, tag, attrs):
            if tag == "tr":
                self.current = []
        def handle_data(self, data):
            if self.current is not None:
                self.current.append(data)
        def handle_endtag(self, tag):
            if tag == "tr" and self.current is not None:
                self.rows.append(" ".join(self.current))
                self.current = None

    def fetch(url):
        request = Request(url, headers={"User-Agent": "FSFFL-NEXT/1.0"})
        with urlopen(request, timeout=5) as response:
            html = response.read(1_500_000).decode("utf-8", errors="replace")
        return html, datetime.now(UTC)

    fetcher = fetcher or fetch
    rostered = {e.player_id for t in league_state.team_states for e in t.roster}
    players = {p.player_id: p for p in league_state.players}
    verified = {}
    for row in sorted(NFL_ROLE_RECEIPTS, key=lambda r: r.captured_at):
        if row.captured_at <= evaluation_cutoff:
            verified[row.player_id] = row
    candidates = {
        row.source_url: [] for pid, row in verified.items()
        if pid in rostered and row.status == "reserve_left_squad"
        and league_state.league.season == row.season
        and players.get(pid) is not None
        and players[pid].position.value == row.position
        and row.source_url.startswith("https://www.nfl.com/teams/")
        and row.source_url.endswith("/roster")
    }
    for pid, row in verified.items():
        if row.source_url in candidates and pid in rostered and row.status == "reserve_left_squad":
            candidates[row.source_url].append(row)
    output = {}
    for url, rows in list(candidates.items())[:4]:
        try:
            html, captured = fetcher(url)
            if captured.tzinfo is None:
                continue
            effective_cutoff = max(evaluation_cutoff, captured) if allow_current_capture else evaluation_cutoff
            if captured > effective_cutoff or effective_cutoff >= captured + timedelta(hours=6):
                continue
            parser = RosterRows()
            parser.feed(html)
            for row in rows:
                player = players[row.player_id]
                matched = [
                    line for line in parser.rows
                    if re.search(r"\\b" + re.escape(player.full_name) + r"\\b", line, flags=re.I)
                ]
                if len(matched) != 1:
                    continue
                if not re.search(r"\\bRLS\\b", matched[0], flags=re.I):
                    continue
                output[row.player_id] = NflRoleReceipt(
                    row.player_id, row.position, row.season, row.status, url, captured,
                )
        except (OSError, ValueError, UnicodeError):
            continue
    return output
