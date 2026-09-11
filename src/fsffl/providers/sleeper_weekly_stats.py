from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence
from urllib.request import Request, urlopen
import json


JsonGetter = Callable[[str], Any]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class SleeperNflState:
    season: int
    week: int
    season_type: str
    captured_at: datetime

    @property
    def completed_through_week(self) -> int:
        if self.season_type.lower() in {"post", "postseason", "off"}:
            return 18
        return max(0, self.week - 1)


@dataclass(frozen=True)
class SleeperWeeklyStatLine:
    player_id: str
    season: int
    week: int
    stats: Mapping[str, float]
    captured_at: datetime
    source_company: str | None = None


class SleeperWeeklyStatsSource:
    """Acquire measured weekly NFL stat lines from Sleeper's stats feed.

    This is Data-layer evidence only. It never applies league scoring or Forecast
    semantics; Forecast converts the retained raw stat keys through LeagueRules.
    """

    provider_name = "sleeper_stats"
    source_version = "sleeper-weekly-nfl-stats-v1"
    base_url = "https://api.sleeper.app/v1/stats/nfl/regular"
    state_url = "https://api.sleeper.app/v1/state/nfl"

    def __init__(self, *, http_get_json: JsonGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_json = http_get_json or _default_get_json
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_nfl_state(self) -> SleeperNflState:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("Sleeper stats clock must be timezone-aware")
        payload = self._http_get_json(self.state_url)
        if not isinstance(payload, Mapping):
            raise ValueError("Sleeper NFL state response must be an object")
        try:
            season = int(payload["season"])
            week = int(payload["week"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Sleeper NFL state lacks season/week identity") from exc
        season_type = str(payload.get("season_type") or "regular")
        if not 0 <= week <= 22:
            raise ValueError("Sleeper NFL state week is outside supported range")
        return SleeperNflState(
            season=season,
            week=week,
            season_type=season_type,
            captured_at=captured.astimezone(UTC),
        )

    def fetch_week(self, *, season: int, week: int) -> tuple[SleeperWeeklyStatLine, ...]:
        if season < 2000:
            raise ValueError("Sleeper stats season is invalid")
        if not 1 <= week <= 18:
            raise ValueError("Sleeper stats week must be between 1 and 18")
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("Sleeper stats clock must be timezone-aware")
        payload = self._http_get_json(f"{self.base_url}/{season}/{week}")
        rows = _rows(payload)
        output: list[SleeperWeeklyStatLine] = []
        for raw in rows:
            raw_season = raw.get("season")
            raw_week = raw.get("week")
            if raw_season not in (None, "") and int(raw_season) != season:
                raise ValueError("Sleeper weekly stats response season mismatch")
            if raw_week not in (None, "") and int(raw_week) != week:
                raise ValueError("Sleeper weekly stats response week mismatch")
            player_id = str(raw.get("player_id") or "").strip()
            if not player_id:
                continue
            stats_raw = raw.get("stats") if isinstance(raw.get("stats"), Mapping) else raw
            stats: dict[str, float] = {}
            for key, value in stats_raw.items():
                if isinstance(value, bool):
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                stats[str(key)] = numeric
            if not stats:
                continue
            output.append(
                SleeperWeeklyStatLine(
                    player_id=f"sleeper:player:{player_id}",
                    season=season,
                    week=week,
                    stats=stats,
                    captured_at=captured.astimezone(UTC),
                    source_company=(str(raw.get("company")) if raw.get("company") else None),
                )
            )
        return tuple(sorted(output, key=lambda item: item.player_id))


def _rows(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(payload, Mapping):
        if all(isinstance(value, Mapping) for value in payload.values()):
            rows: list[Mapping[str, Any]] = []
            for key, value in payload.items():
                row = dict(value)
                row.setdefault("player_id", key)
                rows.append(row)
            return tuple(rows)
        if isinstance(payload.get("data"), Sequence):
            return tuple(item for item in payload["data"] if isinstance(item, Mapping))
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return tuple(item for item in payload if isinstance(item, Mapping))
    raise ValueError("Sleeper weekly stats response shape is unsupported")


def _default_get_json(url: str) -> Any:
    allowed_state = url == SleeperWeeklyStatsSource.state_url
    allowed_stats = url.startswith(f"{SleeperWeeklyStatsSource.base_url}/")
    if not (allowed_state or allowed_stats):
        raise ValueError("Sleeper weekly stats source only permits fixed NFL state/stats URLs")
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider base
        return json.loads(response.read().decode("utf-8"))
