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


NFL_ROLE_RECEIPTS = (
    NflRoleReceipt(
        "sleeper:player:6803", "WR", 2026, "reserve_left_squad",
        "https://www.nfl.com/teams/san-francisco-49ers/roster",
        datetime(2026, 10, 17, 21, 10, 38, tzinfo=UTC),
    ),
)


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
    return {row.player_id: row for row in NFL_ROLE_RECEIPTS
            if row.player_id in rostered and row.player_id in players
            and players[row.player_id].position.value == row.position
            and league_state.league.season == row.season
            and row.captured_at <= as_of < row.captured_at + timedelta(hours=6)}
