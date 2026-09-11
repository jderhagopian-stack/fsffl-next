from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Callable, Mapping
from urllib.request import Request, urlopen

from fsffl.state.models import Position

from .cbs_live import _POSITIONS as CBS_POSITIONS
from .cbs_live import _default_get_text as cbs_get_text
from .cbs_live import _parse_page as parse_cbs_page
from .current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from .fftoday_live import (
    _MAX_PAGES,
    _POSITION_IDS,
    _row_from_headers as fftoday_row_from_headers,
    _row_from_relative_cells as fftoday_row_from_relative_cells,
    _rows_from_text_parts as fftoday_rows_from_text_parts,
)
from .html_tables import HtmlTableParser, normalize_cell
from .razzball_live import (
    RazzballProjectionSnapshot,
    RazzballLiveProjectionSource,
    _parse_updated_at as parse_razzball_updated_at,
    _table_rows as razzball_table_rows,
)


HtmlGetter = Callable[[str], str]
Clock = Callable[[], datetime]


class CBSInSeasonProjectionSource:
    """Explicit CBS ROS/weekly acquisition; never reinterprets the season URL."""

    provider_name = "cbs"
    ros_source_version = "cbs-rest-of-season-projections-html-v1"
    weekly_source_version = "cbs-week-projections-html-v1"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or cbs_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_rest_of_season(self, *, season: int) -> CurrentProjectionSnapshot:
        return self._fetch(
            season=season,
            path="restofseason",
            heading=r"Rest\s+of\s+Season\s+Proj",
            source_version=self.ros_source_version,
        )

    def fetch_week(self, *, season: int, week: int) -> CurrentProjectionSnapshot:
        if not 1 <= week <= 18:
            raise ValueError("CBS projection week must be between 1 and 18")
        return self._fetch(
            season=season,
            path=str(week),
            heading=rf"Week\s+{week}\s+Proj",
            source_version=self.weekly_source_version,
        )

    def _fetch(
        self,
        *,
        season: int,
        path: str,
        heading: str,
        source_version: str,
    ) -> CurrentProjectionSnapshot:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("live CBS clock must be timezone-aware")
        rows: list[CurrentProjectionRow] = []
        for position in CBS_POSITIONS:
            url = (
                "https://www.cbssports.com/fantasy/football/stats/"
                f"{position.value}/{season}/{path}/projections/nonppr/"
            )
            html = self._http_get_text(url)
            _assert_cbs_heading(html, heading=heading, position=position)
            rows.extend(parse_cbs_page(html, provider=self.provider_name, position=position))
        if not rows:
            raise ValueError("CBS returned no in-season projections")
        captured = captured.astimezone(UTC)
        return CurrentProjectionSnapshot(
            provider=self.provider_name,
            captured_at=captured,
            effective_at=captured,
            rows=tuple(rows),
            source_version=source_version,
            usage_class=self.usage_class,
        )


def _assert_cbs_heading(html: str, *, heading: str, position: Position) -> None:
    parser = HtmlTableParser()
    parser.feed(html)
    text = " ".join(parser.text_parts)
    if not re.search(rf"{heading}.*?Fantasy\s+Football", text, re.IGNORECASE):
        raise ValueError(f"CBS {position.value} response did not match requested projection horizon")


class FFTodayWeeklyProjectionSource:
    provider_name = "fftoday"
    source_version = "fftoday-week-projections-html-v1"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _fftoday_week_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_week(self, *, season: int, week: int) -> CurrentProjectionSnapshot:
        if not 1 <= week <= 18:
            raise ValueError("FFToday projection week must be between 1 and 18")
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("live FFToday clock must be timezone-aware")
        rows: list[CurrentProjectionRow] = []
        for position, pos_id in _POSITION_IDS.items():
            seen_external_ids: set[str] = set()
            for page in range(_MAX_PAGES):
                html = self._http_get_text(
                    self._url(season=season, week=week, pos_id=pos_id, page=page)
                )
                parsed_rows, has_next = _parse_fftoday_week_page(
                    html,
                    provider=self.provider_name,
                    position=position,
                    season=season,
                    week=week,
                )
                for row in parsed_rows:
                    if row.external_id in seen_external_ids:
                        continue
                    seen_external_ids.add(row.external_id)
                    rows.append(row)
                if not has_next:
                    break
        if not rows:
            raise ValueError("FFToday returned no weekly projections")
        captured = captured.astimezone(UTC)
        return CurrentProjectionSnapshot(
            provider=self.provider_name,
            captured_at=captured,
            effective_at=captured,
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
        )

    @staticmethod
    def _url(*, season: int, week: int, pos_id: str, page: int = 0) -> str:
        if page < 0:
            raise ValueError("FFToday page must be non-negative")
        page_param = "" if page == 0 else f"&cur_page={page}"
        return (
            "https://www.fftoday.com/rankings/playerwkproj.php"
            f"?GameWeek={week}&LeagueID=&PosID={pos_id}&Season={season}"
            f"{page_param}&order_by=FFPts&sort_order=DESC"
        )


def _parse_fftoday_week_page(
    html: str,
    *,
    provider: str,
    position: Position,
    season: int,
    week: int,
) -> tuple[tuple[CurrentProjectionRow, ...], bool]:
    parser = HtmlTableParser()
    parser.feed(html)
    page_text = " ".join(parser.text_parts)
    if not re.search(rf"\b{season}\s+Week\s+{week}\b", page_text, re.IGNORECASE):
        raise ValueError("FFToday response did not match requested projection week")
    has_next = bool(re.search(r"\bNext\s+Page\b", page_text, re.IGNORECASE))

    for table in parser.tables:
        header_index = next(
            (
                index
                for index, row in enumerate(table)
                if any(normalize_cell(cell).lower().startswith("player") for cell in row)
            ),
            None,
        )
        if header_index is None:
            continue
        headers = [normalize_cell(cell) for cell in table[header_index]]
        output: list[CurrentProjectionRow] = []
        for cells in table[header_index + 1 :]:
            values = [normalize_cell(cell) for cell in cells]
            try:
                row = fftoday_row_from_headers(
                    provider=provider,
                    position=position,
                    headers=headers,
                    cells=values,
                )
            except (ValueError, IndexError):
                row = fftoday_row_from_relative_cells(
                    provider=provider,
                    position=position,
                    cells=values,
                )
            if row is not None:
                output.append(row)
        if output:
            return tuple(output), has_next

    text_rows = fftoday_rows_from_text_parts(
        parser.text_parts,
        provider=provider,
        position=position,
    )
    if text_rows:
        return text_rows, has_next
    raise ValueError(f"FFToday {position.value} weekly projection table was not found")


def _fftoday_week_get_text(url: str) -> str:
    if not url.startswith("https://www.fftoday.com/rankings/playerwkproj.php?"):
        raise ValueError("FFToday weekly source only permits fixed projection URLs")
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        text = response.read().decode("utf-8", errors="replace")
    if "Projections" not in text or "Week" not in text:
        raise ValueError("FFToday hosted response did not contain weekly projection content")
    return text


_RAZZBALL_CANONICAL_COLUMNS = {
    "Pass Yds",
    "Pass TD",
    "Int",
    "Rush Yds",
    "Run TD",
    "Rec",
    "Rec Yds",
    "Rec TD",
    "Fum Lst",
}
_RAZZBALL_REQUIRED_BY_POSITION = {
    "QB": {"Name", "Team", "Pass Yds", "Pass TD", "Int", "Rush Yds", "Run TD"},
    "RB": {"Name", "Team", "Rush Yds", "Run TD", "Rec", "Rec Yds", "Rec TD"},
    "WR": {"Name", "Team", "Rec", "Rec Yds", "Rec TD"},
    "TE": {"Name", "Team", "Rec", "Rec Yds", "Rec TD"},
}


class RazzballRestOfSeasonProjectionSource:
    provider_name = "razzball"
    source_version = "razzball-rest-of-season-projections-html-v2:season-verified"
    usage_class = "beta-personal-research-requires-commercial-review"
    position_urls = RazzballLiveProjectionSource.position_urls

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _razzball_ros_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> RazzballProjectionSnapshot:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("live Razzball clock must be timezone-aware")
        rows: list[Mapping[str, str]] = []
        effective: datetime | None = None
        for position, url in self.position_urls.items():
            html = self._http_get_text(url)
            parsed, page_text = razzball_table_rows(
                html,
                _RAZZBALL_REQUIRED_BY_POSITION[position],
            )
            if not re.search(r"Rest\s+of\s+Season", page_text, re.IGNORECASE):
                raise ValueError(f"Razzball {position} response did not identify rest-of-season projections")
            if not re.search(rf"\b{season}\b", page_text):
                raise ValueError(
                    f"Razzball {position} response did not identify requested {season} season"
                )
            updated = parse_razzball_updated_at(page_text)
            effective = updated if effective is None else max(effective, updated)
            for raw in parsed:
                if not raw.get("Name") or not raw.get("Team"):
                    continue
                row = {
                    key: value
                    for key, value in raw.items()
                    if key in _RAZZBALL_CANONICAL_COLUMNS or key in {"Name", "Team"}
                }
                row["Pos"] = position
                rows.append(row)
        if not rows or effective is None:
            raise ValueError("Razzball returned no rest-of-season projections")
        if effective > captured:
            raise ValueError("Razzball effective timestamp cannot be in the future")
        return RazzballProjectionSnapshot(
            provider_name=self.provider_name,
            source_url=f"razzball:{season}:rest-of-season",
            captured_at=captured.astimezone(UTC),
            effective_at=effective.astimezone(UTC),
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
        )


def _razzball_ros_get_text(url: str) -> str:
    if url not in set(RazzballRestOfSeasonProjectionSource.position_urls.values()):
        raise ValueError("Razzball ROS source only permits fixed HTTPS projection URLs")
    request = Request(
        url,
        headers={
            "User-Agent": "fsffl-next/0.1 (+private-beta projection research)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
