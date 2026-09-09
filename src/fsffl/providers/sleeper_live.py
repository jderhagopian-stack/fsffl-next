from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
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
        max_workers: int = 8,
    ) -> None:
        if max_workers < 1:
            raise ValueError("Sleeper max_workers must be positive")
        self._http_get_json = http_get_json or _default_get_json
        self._clock = clock or (lambda: datetime.now(UTC))
        self._max_workers = max_workers

    def fetch_latest(self, *, league_external_id: str) -> ProviderSnapshot:
        league_id = league_external_id.strip()
        if not league_id:
            raise ValueError("league_external_id cannot be blank")

        captured_at = self._clock()
        if captured_at.tzinfo is None:
            raise ValueError("live Sleeper clock must return a timezone-aware datetime")

        # League metadata must be acquired first because it defines season and
        # regular-season schedule shape. Every remaining payload is independent
        # provider evidence and can be fetched concurrently without changing State
        # semantics or source authority.
        league_payload = self._get(f"/league/{league_id}")
        season = int(league_payload.get("season")) if league_payload.get("season") else None
        matchup_weeks = self._regular_season_weeks(league_payload)

        # Keep roster validation first in logical resolution order. Its requests run
        # concurrently with the rest, but a persistently incomplete roster payload
        # remains the primary canonical-State failure rather than being masked by a
        # later independent endpoint error.
        tasks: dict[str, Callable[[], Any]] = {
            "rosters": lambda: self._complete_rosters(league_id, league_payload),
            "users": lambda: self._get(f"/league/{league_id}/users"),
            "players": lambda: self._get("/players/nfl"),
            "traded_picks": lambda: self._get(f"/league/{league_id}/traded_picks"),
            "nfl_schedule": lambda: self._nfl_regular_season_schedule(season),
        }
        for week in matchup_weeks:
            tasks[f"matchup:{week}"] = lambda week=week: self._get(
                f"/league/{league_id}/matchups/{week}"
            )

        worker_count = min(self._max_workers, len(tasks))
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="fsffl-sleeper",
        ) as executor:
            futures = {key: executor.submit(loader) for key, loader in tasks.items()}
            # Resolve in deterministic logical order even though acquisition runs
            # concurrently. Exceptions still fail closed rather than degrading State.
            results = {key: futures[key].result() for key in tasks}

        payload = {
            "league": league_payload,
            "users": results["users"],
            "rosters": results["rosters"],
            "players": results["players"],
            "traded_picks": results["traded_picks"],
            "matchups": {
                str(week): results[f"matchup:{week}"]
                for week in matchup_weeks
            },
            "nfl_schedule": results["nfl_schedule"],
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

    def _regular_season_weeks(self, league_payload: Mapping[str, Any]) -> tuple[int, ...]:
        settings = league_payload.get("settings") or {}
        raw_start = settings.get("playoff_week_start")
        if raw_start in (None, "", 0):
            return ()
        try:
            playoff_week_start = int(raw_start)
        except (TypeError, ValueError) as exc:
            raise ValueError("Sleeper playoff_week_start must be an integer") from exc
        if not 2 <= playoff_week_start <= 19:
            raise ValueError("Sleeper playoff_week_start is outside supported NFL week range")
        return tuple(range(1, playoff_week_start))

    def _regular_season_matchups(
        self,
        league_id: str,
        league_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Legacy helper retained for direct callers/tests; fetch_latest parallelizes it."""

        return {
            str(week): self._get(f"/league/{league_id}/matchups/{week}")
            for week in self._regular_season_weeks(league_payload)
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