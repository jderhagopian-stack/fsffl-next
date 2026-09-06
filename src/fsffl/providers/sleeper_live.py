from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence
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
    schedule_base_url = "https://api.sleeper.app"

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

        league_payload = self._get(f"/league/{league_id}")
        season = int(league_payload.get("season")) if league_payload.get("season") else None
        rosters = self._complete_rosters(league_id, league_payload)
        payload = {
            "league": league_payload,
            "users": self._get(f"/league/{league_id}/users"),
            "rosters": rosters,
            "players": self._get("/players/nfl"),
            "traded_picks": self._get(f"/league/{league_id}/traded_picks"),
            "matchups": self._regular_season_matchups(league_id, league_payload),
            "nfl_schedule": self._nfl_regular_season_schedule(season),
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

    def _complete_rosters(
        self,
        league_id: str,
        league_payload: Mapping[str, Any],
    ) -> Any:
        path = f"/league/{league_id}/rosters"
        rosters = self._get(path)
        settings = league_payload.get("settings") or {}
        raw_expected = settings.get("num_teams")
        try:
            expected = int(raw_expected) if raw_expected not in (None, "", 0) else 0
        except (TypeError, ValueError):
            expected = 0
        if expected <= 0:
            return rosters

        def roster_count(value: Any) -> int:
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                return -1
            return len(value)

        if roster_count(rosters) == expected:
            return rosters
        # A transient/partial provider response must not silently become canonical
        # State. Retry once, then fail closed with an explicit count mismatch.
        rosters = self._get(path)
        actual = roster_count(rosters)
        if actual != expected:
            raise ValueError(
                f"Sleeper roster payload incomplete: expected {expected} teams, received {actual}"
            )
        return rosters

    def _regular_season_matchups(
        self,
        league_id: str,
        league_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        settings = league_payload.get("settings") or {}
        raw_start = settings.get("playoff_week_start")
        if raw_start in (None, "", 0):
            return {}
        try:
            playoff_week_start = int(raw_start)
        except (TypeError, ValueError) as exc:
            raise ValueError("Sleeper playoff_week_start must be an integer") from exc
        if not 2 <= playoff_week_start <= 19:
            raise ValueError("Sleeper playoff_week_start is outside supported NFL week range")
        return {
            str(week): self._get(f"/league/{league_id}/matchups/{week}")
            for week in range(1, playoff_week_start)
        }

    def _nfl_regular_season_schedule(self, season: int | None) -> Any:
        if season is None:
            return []
        return self._http_get_json(
            f"{self.schedule_base_url}/schedule/nfl/regular/{season}"
        )

    def _get(self, path: str) -> Any:
        return self._http_get_json(f"{self.base_url}{path}")


def _default_get_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider base
        return json.loads(response.read().decode("utf-8"))