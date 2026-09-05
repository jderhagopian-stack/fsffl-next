from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable
from urllib.request import Request, urlopen

from .acquisition import ProviderSnapshot


JsonGetter = Callable[[str], Any]
Clock = Callable[[], datetime]


class SleeperLiveSource:
    """Live Sleeper acquisition at the Data/provider boundary.

    This class acquires provider-shaped payloads only. It contains no lineup,
    forecast, value, team-utility, or recommendation logic. Historical requests
    deliberately return None because a live endpoint cannot prove point-in-time
    historical availability.
    """

    provider_name = "sleeper"
    base_url = "https://api.sleeper.app/v1"

    def __init__(
        self,
        *,
        http_get_json: JsonGetter | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._http_get_json = http_get_json or _default_get_json
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, league_external_id: str) -> ProviderSnapshot:
        league_id = league_external_id.strip()
        if not league_id:
            raise ValueError("league_external_id cannot be blank")

        captured_at = self._clock()
        if captured_at.tzinfo is None:
            raise ValueError("live Sleeper clock must return a timezone-aware datetime")

        payload = {
            "league": self._get(f"/league/{league_id}"),
            "users": self._get(f"/league/{league_id}/users"),
            "rosters": self._get(f"/league/{league_id}/rosters"),
            "players": self._get("/players/nfl"),
            "traded_picks": self._get(f"/league/{league_id}/traded_picks"),
        }
        return ProviderSnapshot(
            provider_name=self.provider_name,
            league_external_id=league_id,
            captured_at=captured_at,
            payload=payload,
        )

    def fetch_at_or_before(
        self,
        *,
        league_external_id: str,
        as_of: datetime,
    ) -> ProviderSnapshot | None:
        if not league_external_id.strip():
            raise ValueError("league_external_id cannot be blank")
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return None

    def _get(self, path: str) -> Any:
        return self._http_get_json(f"{self.base_url}{path}")


def _default_get_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider base
        return json.loads(response.read().decode("utf-8"))
