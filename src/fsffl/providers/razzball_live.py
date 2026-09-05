from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Callable, Mapping
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

HtmlGetter = Callable[[str], str]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class RazzballProjectionSnapshot:
    provider_name: str
    source_url: str
    captured_at: datetime
    effective_at: datetime
    rows: tuple[Mapping[str, str], ...]
    source_version: str
    usage_class: str = "beta-personal-research-requires-commercial-review"


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.text_parts: list[str] = []
        self._table_depth = 0
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_table = []
        elif tag == "tr" and self._table_depth == 1:
            self._current_row = []
        elif tag in {"th", "td"} and self._table_depth == 1 and self._current_row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.text_parts.append(text)
        if self._cell_parts is not None:
            self._cell_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell_parts is not None and self._current_row is not None:
            self._current_row.append(" ".join(self._cell_parts).strip())
            self._cell_parts = None
        elif tag == "tr" and self._table_depth == 1 and self._current_row is not None:
            if any(cell for cell in self._current_row):
                assert self._current_table is not None
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "table":
            if self._table_depth == 1 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None
            self._table_depth = max(0, self._table_depth - 1)


class RazzballLiveProjectionSource:
    provider_name = "razzball"
    source_url = "https://football.razzball.com/projections/"
    source_version = "razzball-season-projections-html-v2"
    position_urls = {
        "QB": "https://football.razzball.com/projections-qb-restofseason/",
        "RB": "https://football.razzball.com/projections-rb-restofseason/",
        "WR": "https://football.razzball.com/projections-wr-restofseason/",
        "TE": "https://football.razzball.com/projections-te-restofseason/",
    }

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self) -> RazzballProjectionSnapshot:
        captured_at = self._clock()
        if captured_at.tzinfo is None:
            raise ValueError("live Razzball clock must return a timezone-aware datetime")
        html = self._http_get_text(self.source_url)
        base_rows, page_text = _extract_projection_rows(html)
        effective_at = _parse_updated_at(page_text)

        fumbles: dict[tuple[str, str, str], str] = {}
        for position, url in self.position_urls.items():
            try:
                position_html = self._http_get_text(url)
                position_rows, position_text = _extract_position_fumble_rows(position_html)
                effective_at = max(effective_at, _parse_updated_at(position_text))
                for row in position_rows:
                    key = (position, _identity_name(row.get("Name", "")), (row.get("Team") or "").upper().strip())
                    if key[1] and key[2] and row.get("Fum Lst") not in {None, ""}:
                        fumbles[key] = row["Fum Lst"]
            except ValueError:
                # The all-player table remains a valid provider snapshot even when a
                # position page temporarily changes shape. Fumble coverage then fails
                # the downstream multi-source gate rather than fabricating a value.
                continue

        merged: list[Mapping[str, str]] = []
        for raw in base_rows:
            row = dict(raw)
            key = ((row.get("Pos") or "").upper().strip(), _identity_name(row.get("Name", "")), (row.get("Team") or "").upper().strip())
            if key in fumbles:
                row["Fum Lst"] = fumbles[key]
            merged.append(row)

        if effective_at > captured_at:
            raise ValueError("Razzball effective timestamp cannot be in the future")
        return RazzballProjectionSnapshot(
            provider_name=self.provider_name,
            source_url=self.source_url,
            captured_at=captured_at.astimezone(UTC),
            effective_at=effective_at.astimezone(UTC),
            rows=tuple(merged),
            source_version=self.source_version,
        )


def _identity_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_header(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).strip()


def _table_rows(html: str, required: set[str]) -> tuple[tuple[Mapping[str, str], ...], str]:
    parser = _TableParser()
    parser.feed(html)
    for table in parser.tables:
        if not table:
            continue
        header_index = next((i for i, row in enumerate(table) if required.issubset({_normalize_header(cell) for cell in row})), None)
        if header_index is None:
            continue
        headers = [_normalize_header(cell) for cell in table[header_index]]
        output: list[Mapping[str, str]] = []
        for cells in table[header_index + 1:]:
            normalized = [_normalize_header(cell) for cell in cells]
            if len(normalized) < len(headers):
                normalized.extend([""] * (len(headers) - len(normalized)))
            row = {header: normalized[index] for index, header in enumerate(headers) if header}
            output.append(row)
        if output:
            return tuple(output), " ".join(parser.text_parts)
    raise ValueError("Razzball projection table was not found")


def _extract_projection_rows(html: str) -> tuple[tuple[Mapping[str, str], ...], str]:
    required = {"Name", "Pos", "Team", "Pass Yds", "Pass TD", "Int", "Rush Yds", "Run TD", "Rec", "Rec Yds", "Rec TD"}
    rows, text = _table_rows(html, required)
    filtered = tuple(row for row in rows if row.get("Name") and row.get("Pos") and row.get("Team"))
    if not filtered:
        raise ValueError("Razzball projection table was found but contained no rows")
    return filtered, text


def _extract_position_fumble_rows(html: str) -> tuple[tuple[Mapping[str, str], ...], str]:
    rows, text = _table_rows(html, {"Name", "Team", "Fum Lst"})
    filtered = tuple(row for row in rows if row.get("Name") and row.get("Team"))
    if not filtered:
        raise ValueError("Razzball fumble table contained no rows")
    return filtered, text


_UPDATED_RE = re.compile(r"Updated:\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(AM|PM)\s+E[DS]T", re.IGNORECASE)


def _parse_updated_at(page_text: str) -> datetime:
    match = _UPDATED_RE.search(page_text)
    if match is None:
        raise ValueError("Razzball projection update timestamp was not found")
    date_text, time_text, meridiem = match.groups()
    return datetime.strptime(f"{date_text} {time_text} {meridiem.upper()}", "%Y-%m-%d %I:%M:%S %p").replace(tzinfo=ZoneInfo("America/New_York"))


def _default_get_text(url: str) -> str:
    allowed = {RazzballLiveProjectionSource.source_url, *RazzballLiveProjectionSource.position_urls.values()}
    if url not in allowed:
        raise ValueError("Razzball live source only permits fixed HTTPS projection URLs")
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1 (+private-beta projection research)", "Accept": "text/html,application/xhtml+xml"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
