from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Callable
from urllib.request import Request, urlopen

from fsffl.forecast.models import ForecastMetric
from fsffl.state.models import Position, canonical_nfl_team

from .html_tables import HtmlTableParser, normalize_cell, numeric
from .ros_projection_rows import (
    ProjectionRightsStatus,
    RosProjectionRow,
    RosProjectionSnapshot,
)


HtmlGetter = Callable[[str], str]
Clock = Callable[[], datetime]


class CBSRosKDstProjectionSource:
    """2026 ROS K/DST acquisition contract for bounded evidence/testing.

    This source is deliberately not registered in the production provider set.
    CBS public-content rights are not production-cleared; callers must not treat
    a technically healthy response as deployed Forecast authority.
    """

    provider_name = "cbs"
    independence_group = "cbs"
    source_version = "cbs-2026-ros-kdst-html-v1"
    usage_class = "research-contract-only:public-cbs-content:no-production-rights"
    rights_status = ProjectionRightsStatus.RESEARCH_ONLY

    def __init__(
        self,
        *,
        http_get_text: HtmlGetter | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> RosProjectionSnapshot:
        if season != 2026:
            raise ValueError("CBS late-start K/DST source is authorized only for 2026")
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("CBS ROS clock must be timezone-aware")
        captured = captured.astimezone(UTC)

        pages: list[tuple[Position, str, str]] = []
        rows: list[RosProjectionRow] = []
        for position in (Position.K, Position.DST):
            url = self._url(season=season, position=position)
            html = self._http_get_text(url)
            _assert_ros_page(html, season=season, position=position)
            parsed = _parse_ros_page(
                html,
                provider=self.provider_name,
                position=position,
            )
            if not parsed:
                raise ValueError(f"CBS ROS {position.value} projection table returned no rows")
            pages.append((position, url, html))
            rows.extend(parsed)

        digest = hashlib.sha256()
        for position, url, html in sorted(pages, key=lambda item: item[0].value):
            digest.update(position.value.encode("utf-8"))
            digest.update(b"\0")
            digest.update(url.encode("utf-8"))
            digest.update(b"\0")
            digest.update(html.encode("utf-8"))
            digest.update(b"\0")

        return RosProjectionSnapshot(
            provider=self.provider_name,
            independence_group=self.independence_group,
            endpoint=";".join(url for _position, url, _html in pages),
            season=season,
            captured_at=captured,
            provider_effective_at=None,
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
            rights_status=self.rights_status,
            content_sha256=digest.hexdigest(),
        )

    @staticmethod
    def _url(*, season: int, position: Position) -> str:
        return (
            "https://www.cbssports.com/fantasy/football/stats/"
            f"{position.value}/{season}/restofseason/projections/ppr/"
        )


def _assert_ros_page(html: str, *, season: int, position: Position) -> None:
    parser = HtmlTableParser()
    parser.feed(html)
    text = " ".join(parser.text_parts)
    if str(season) not in text:
        raise ValueError(f"CBS ROS {position.value} response does not prove season {season}")
    if not re.search(r"\brest\s+of\s+season\b|\bROS\b", text, re.IGNORECASE):
        raise ValueError(f"CBS {position.value} response does not prove ROS horizon")


def _indexes(headers: list[str], *labels: str) -> list[int]:
    wanted = {label.upper() for label in labels}
    return [index for index, value in enumerate(headers) if value.upper() in wanted]


def _optional(
    cells: list[str],
    headers: list[str],
    *labels: str,
    occurrence: int = 0,
) -> float | None:
    indexes = _indexes(headers, *labels)
    if len(indexes) <= occurrence:
        return None
    try:
        return numeric(cells[indexes[occurrence]])
    except (ValueError, IndexError):
        return None


def _identity(cell: str, *, position: Position) -> tuple[str, str]:
    text = normalize_cell(cell)
    team_match = re.search(r"\b([A-Z]{2,3})\s*$", text)
    if team_match is None:
        raise ValueError("CBS ROS subject team could not be parsed")
    team = canonical_nfl_team(team_match.group(1))
    prefix = text[: team_match.start()].strip()

    if position == Position.K:
        prefix = re.sub(r"\s+K\s*$", "", prefix, flags=re.IGNORECASE).strip()
        prefix = re.sub(r"^.*?\bK\s+[A-Z]{2,3}\s+", "", prefix).strip()
        if not prefix:
            raise ValueError("CBS ROS kicker name could not be parsed")
        return prefix, team

    prefix = re.sub(r"\s+(?:DST|DEF)\s*$", "", prefix, flags=re.IGNORECASE).strip()
    if not prefix:
        prefix = f"{team} D/ST"
    return prefix, team


def _k_row(
    *,
    provider: str,
    headers: list[str],
    cells: list[str],
) -> RosProjectionRow | None:
    if len(cells) < 4:
        return None
    name, team = _identity(cells[0], position=Position.K)
    gp = _optional(cells, headers, "GP", "G")
    stats: dict[str, float] = {}

    mapping = (
        (ForecastMetric.FG_MADE, ("FGM",)),
        (ForecastMetric.FG_ATTEMPT, ("FGA",)),
        (ForecastMetric.FG_MADE_0_19, ("0-19", "1-19")),
        (ForecastMetric.FG_MADE_20_29, ("20-29",)),
        (ForecastMetric.FG_MADE_30_39, ("30-39",)),
        (ForecastMetric.FG_MADE_40_49, ("40-49",)),
        (ForecastMetric.FG_MADE_50_PLUS, ("50+", "50P")),
        (ForecastMetric.XP_MADE, ("XPM", "PATM")),
        (ForecastMetric.XP_ATTEMPT, ("XPA", "PATA")),
    )
    for metric, labels in mapping:
        value = _optional(cells, headers, *labels)
        if value is not None:
            stats[metric.value] = value

    if not stats:
        return None
    return RosProjectionRow(
        provider=provider,
        external_id=f"K:{team}:{name}",
        subject_name=name,
        position=Position.K,
        nfl_team=team,
        projected_games=int(gp) if gp is not None else None,
        stats=tuple(sorted(stats.items())),
    )


def _dst_row(
    *,
    provider: str,
    headers: list[str],
    cells: list[str],
) -> RosProjectionRow | None:
    if len(cells) < 4:
        return None
    name, team = _identity(cells[0], position=Position.DST)
    gp = _optional(cells, headers, "GP", "G")
    stats: dict[str, float] = {}

    mapping = (
        (ForecastMetric.DST_INTERCEPTION, ("INT", "INTS")),
        (ForecastMetric.DST_SAFETY, ("SAF", "SFTY", "SAFETY")),
        (ForecastMetric.DST_SACK, ("SACK", "SACKS")),
        (ForecastMetric.DST_FUMBLE_RECOVERY, ("FR", "FUM REC")),
        (ForecastMetric.DST_FORCED_FUMBLE, ("FF", "FUM FORCED")),
        (ForecastMetric.DST_DEFENSIVE_TD, ("TD", "DEF TD")),
    )
    for metric, labels in mapping:
        value = _optional(cells, headers, *labels)
        if value is not None:
            stats[metric.value] = value

    # Retain aggregate PA/YA for diagnostics only. These names are intentionally
    # not ForecastMetric values and therefore can never satisfy bucket authority.
    pa = _optional(cells, headers, "PA", "PTS ALLOW", "POINTS ALLOWED")
    if pa is not None:
        stats["diagnostic_points_allowed"] = pa
    ya = _optional(cells, headers, "YDS", "YA", "YARDS ALLOWED")
    if ya is not None:
        stats["diagnostic_yards_allowed"] = ya

    if not stats:
        return None
    return RosProjectionRow(
        provider=provider,
        external_id=f"DST:{team}",
        subject_name=name,
        position=Position.DST,
        nfl_team=team,
        projected_games=int(gp) if gp is not None else None,
        stats=tuple(sorted(stats.items())),
    )


def _parse_ros_page(
    html: str,
    *,
    provider: str,
    position: Position,
) -> tuple[RosProjectionRow, ...]:
    parser = HtmlTableParser()
    parser.feed(html)
    for table in parser.tables:
        header_index = next(
            (
                index
                for index, row in enumerate(table)
                if any(
                    normalize_cell(cell).upper().startswith(("PLAYER", "TEAM"))
                    for cell in row
                )
            ),
            None,
        )
        if header_index is None:
            continue
        headers = [normalize_cell(cell).upper() for cell in table[header_index]]
        output: list[RosProjectionRow] = []
        for raw_cells in table[header_index + 1 :]:
            cells = [normalize_cell(cell) for cell in raw_cells]
            try:
                row = (
                    _k_row(provider=provider, headers=headers, cells=cells)
                    if position == Position.K
                    else _dst_row(provider=provider, headers=headers, cells=cells)
                )
            except (ValueError, IndexError):
                continue
            if row is not None:
                output.append(row)
        if output:
            return tuple(output)
    raise ValueError(f"CBS ROS {position.value} projection table was not found")


def _default_get_text(url: str) -> str:
    if not url.startswith("https://www.cbssports.com/fantasy/football/stats/"):
        raise ValueError("CBS ROS source only permits fixed fantasy projection URLs")
    request = Request(
        url,
        headers={
            "User-Agent": "fsffl-next/0.1",
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
