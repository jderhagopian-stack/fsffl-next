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
    """Acquire current public Razzball season projections at the provider boundary.

    The provider is beta/personal-research evidence only until commercial usage
    rights are reviewed. This class performs network acquisition and provider-table
    extraction only; player identity resolution and forecast normalization live
    downstream in NEXT-2.
    """

    provider_name = "razzball"
    source_url = "https://football.razzball.com/projections/"
    source_version = "razzball-season-projections-html-v1"

    def __init__(
        self,
        *,
        http_get_text: HtmlGetter | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self) -> RazzballProjectionSnapshot:
        captured_at = self._clock()
        if captured_at.tzinfo is None:
            raise ValueError("live Razzball clock must return a timezone-aware datetime")
        html = self._http_get_text(self.source_url)
        rows, page_text = _extract_projection_rows(html)
        effective_at = _parse_updated_at(page_text)
        if effective_at > captured_at:
            raise ValueError("Razzball effective timestamp cannot be in the future")
        return RazzballProjectionSnapshot(
            provider_name=self.provider_name,
            source_url=self.source_url,
            captured_at=captured_at.astimezone(UTC),
            effective_at=effective_at.astimezone(UTC),
            rows=rows,
            source_version=self.source_version,
        )


def _normalize_header(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).strip()


def _extract_projection_rows(html: str) -> tuple[tuple[Mapping[str, str], ...], str]:
    parser = _TableParser()
    parser.feed(html)
    required = {"Name", "Pos", "Team", "Pass Yds", "Pass TD", "Int", "Rush Yds", "Run TD", "Rec", "Rec Yds", "Rec TD"}

    for table in parser.tables:
        if not table:
            continue
        headers = [_normalize_header(cell) for cell in table[0]]
        if not required.issubset(set(headers)):
            continue
        output: list[Mapping[str, str]] = []
        for cells in table[1:]:
            normalized = [_normalize_header(cell) for cell in cells]
            if len(normalized) < len(headers):
                normalized.extend([""] * (len(headers) - len(normalized)))
            row = {header: normalized[index] for index, header in enumerate(headers) if header}
            if row.get("Name") and row.get("Pos") and row.get("Team"):
                output.append(row)
        if not output:
            raise ValueError("Razzball projection table was found but contained no rows")
        return tuple(output), " ".join(parser.text_parts)

    raise ValueError("Razzball season projection table was not found")


_UPDATED_RE = re.compile(
    r"Updated:\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+(AM|PM)\s+E[DS]T",
    re.IGNORECASE,
)


def _parse_updated_at(page_text: str) -> datetime:
    match = _UPDATED_RE.search(page_text)
    if match is None:
        raise ValueError("Razzball projection update timestamp was not found")
    date_text, time_text, meridiem = match.groups()
    local = datetime.strptime(
        f"{date_text} {time_text} {meridiem.upper()}",
        "%Y-%m-%d %I:%M:%S %p",
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local


def _default_get_text(url: str) -> str:
    if url != RazzballLiveProjectionSource.source_url:
        raise ValueError("Razzball live source only permits its fixed HTTPS projection URL")
    request = Request(
        url,
        headers={
            "User-Agent": "fsffl-next/0.1 (+private-beta projection research)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
