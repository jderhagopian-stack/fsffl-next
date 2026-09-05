from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Callable
from urllib.request import Request, urlopen

from fsffl.state.models import Position

from .current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from .html_tables import HtmlTableParser, normalize_cell, numeric

HtmlGetter = Callable[[str], str]
Clock = Callable[[], datetime]
_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


class CBSLiveProjectionSource:
    provider_name = "cbs"
    source_version = "cbs-season-projections-html-v3"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> CurrentProjectionSnapshot:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("live CBS clock must be timezone-aware")
        rows: list[CurrentProjectionRow] = []
        for position in _POSITIONS:
            rows.extend(_parse_page(self._http_get_text(self._url(season=season, position=position)), provider=self.provider_name, position=position))
        if not rows:
            raise ValueError("CBS returned no current projections")
        return CurrentProjectionSnapshot(
            provider=self.provider_name,
            captured_at=captured.astimezone(UTC),
            effective_at=captured.astimezone(UTC),
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
        )

    @staticmethod
    def _url(*, season: int, position: Position) -> str:
        return f"https://www.cbssports.com/fantasy/football/stats/{position.value}/{season}/season/projections/nonppr/"


def _parse_page(html: str, *, provider: str, position: Position) -> tuple[CurrentProjectionRow, ...]:
    parser = HtmlTableParser()
    parser.feed(html)
    for table in parser.tables:
        header_index = next((i for i, row in enumerate(table) if any(normalize_cell(cell).lower().startswith("player") for cell in row)), None)
        if header_index is None:
            continue
        headers = [normalize_cell(cell).upper() for cell in table[header_index]]
        output: list[CurrentProjectionRow] = []
        for cells in table[header_index + 1:]:
            values = [normalize_cell(cell) for cell in cells]
            try:
                row = _row_from_cells(provider=provider, position=position, headers=headers, cells=values)
            except (ValueError, IndexError):
                continue
            if row is not None:
                output.append(row)
        if output:
            return tuple(output)
    raise ValueError(f"CBS {position.value} projection table was not found")


def _extract_identity(cell: str, position: Position) -> tuple[str, str]:
    pattern = re.compile(rf"^.*?\b{re.escape(position.value)}\s+([A-Z]{{2,3}})\s+(.+?)\s+{re.escape(position.value)}\s+\1$")
    match = pattern.match(cell.strip())
    if match:
        team, name = match.groups()
        return name.strip(), team
    trailing = re.search(rf"(.+?)\s+{re.escape(position.value)}\s+([A-Z]{{2,3}})$", cell.strip())
    if trailing:
        return trailing.group(1).strip(), trailing.group(2)
    raise ValueError("CBS player identity could not be parsed")


def _indices(headers: list[str], label: str) -> list[int]:
    return [i for i, value in enumerate(headers) if value == label]


def _at(cells: list[str], indexes: list[int], occurrence: int = 0, default: float | None = None) -> float:
    if len(indexes) <= occurrence:
        if default is not None:
            return default
        raise ValueError("required CBS projection column missing")
    return numeric(cells[indexes[occurrence]])


def _row_from_cells(*, provider: str, position: Position, headers: list[str], cells: list[str]) -> CurrentProjectionRow | None:
    if len(cells) < 8:
        return None
    name, team = _extract_identity(cells[0], position)
    yds = _indices(headers, "YDS")
    td = _indices(headers, "TD")
    fl = _indices(headers, "FL")
    rec = _indices(headers, "REC")
    interceptions = _indices(headers, "INT")

    if position == Position.QB:
        stats = {
            "pass_yd": _at(cells, yds, 0),
            "pass_td": _at(cells, td, 0),
            "pass_int": _at(cells, interceptions, 0),
            "rush_yd": _at(cells, yds, 1),
            "rush_td": _at(cells, td, 1),
            "fum_lost": _at(cells, fl, 0, 0.0),
        }
    elif position == Position.RB:
        stats = {
            "rush_yd": _at(cells, yds, 0),
            "rush_td": _at(cells, td, 0),
            "rec": _at(cells, rec, 0),
            "rec_yd": _at(cells, yds, 1),
            "rec_td": _at(cells, td, 1),
            "fum_lost": _at(cells, fl, 0, 0.0),
        }
    elif position == Position.WR:
        stats = {
            "rec": _at(cells, rec, 0),
            "rec_yd": _at(cells, yds, 0),
            "rec_td": _at(cells, td, 0),
            "rush_yd": _at(cells, yds, 1, 0.0),
            "rush_td": _at(cells, td, 1, 0.0),
            "fum_lost": _at(cells, fl, 0, 0.0),
        }
    elif position == Position.TE:
        stats = {
            "rec": _at(cells, rec, 0),
            "rec_yd": _at(cells, yds, 0),
            "rec_td": _at(cells, td, 0),
            "rush_yd": 0.0,
            "rush_td": 0.0,
            "fum_lost": _at(cells, fl, 0, 0.0),
        }
    else:
        return None

    return CurrentProjectionRow(
        provider=provider,
        external_id=f"{position.value}:{team}:{name}",
        player_name=name,
        position=position,
        nfl_team=team,
        stats=stats,
    )


def _default_get_text(url: str) -> str:
    if not url.startswith("https://www.cbssports.com/fantasy/football/stats/"):
        raise ValueError("CBS live source only permits fixed fantasy projection URLs")
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
    if "Projections Fantasy Football" not in text and "projection" not in text.lower():
        raise ValueError("CBS hosted response did not contain projection content")
    return text
