"""Recorded official NFL facts, acquired independently of product requests.

These receipts establish season-long unavailability only. They are not player
projections, a general injury multiplier, or evidence that unsigned players
will remain unsigned. Capture time deliberately fences historical replay.
"""
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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
