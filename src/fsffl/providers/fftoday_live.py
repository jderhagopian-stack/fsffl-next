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

_POSITION_IDS = {
    Position.QB: "10",
    Position.RB: "20",
    Position.WR: "30",
    Position.TE: "40",
}


class FFTodayLiveProjectionSource:
    provider_name = "fftoday"
    source_version = "fftoday-season-projections-html-v2"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> CurrentProjectionSnapshot:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("live FFToday clock must be timezone-aware")
        rows: list[CurrentProjectionRow] = []
        effective: datetime | None = None
        for position, pos_id in _POSITION_IDS.items():
            html = self._http_get_text(self._url(season=season, pos_id=pos_id))
            parsed_rows, updated = _parse_page(html, provider=self.provider_name, position=position)
            rows.extend(parsed_rows)
            effective = updated if effective is None else max(effective, updated)
        if not rows or effective is None:
            raise ValueError("FFToday returned no current projections")
        if effective > captured:
            raise ValueError("FFToday effective timestamp cannot be in the future")
        return CurrentProjectionSnapshot(
            provider=self.provider_name,
            captured_at=captured.astimezone(UTC),
            effective_at=effective.astimezone(UTC),
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
        )

    @staticmethod
    def _url(*, season: int, pos_id: str) -> str:
        return (
            "https://www.fftoday.com/rankings/playerproj.php"
            f"?PosID={pos_id}&Season={season}&order_by=FFPts&sort_order=DESC"
        )


_UPDATED_RE = re.compile(r"Updated:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE)


def _parse_page(html: str, *, provider: str, position: Position) -> tuple[tuple[CurrentProjectionRow, ...], datetime]:
    parser = HtmlTableParser()
    parser.feed(html)
    page_text = " ".join(parser.text_parts)
    match = _UPDATED_RE.search(page_text)
    if match is None:
        raise ValueError("FFToday projection update date was not found")
    month, day, year = (int(value) for value in match.groups())
    effective = datetime(year, month, day, 12, 0, tzinfo=UTC)

    for table in parser.tables:
        header_index = next(
            (
                index
                for index, row in enumerate(table)
                if any(normalize_cell(cell).lower().startswith("player") for cell in row)
                and any(normalize_cell(cell).lower() == "tm" for cell in row)
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
                row = _row_from_headers(
                    provider=provider,
                    position=position,
                    headers=headers,
                    cells=values,
                )
            except (ValueError, IndexError):
                continue
            if row is not None:
                output.append(row)
        if output:
            return tuple(output), effective
    raise ValueError(f"FFToday {position.value} projection table was not found")


def _clean_name(value: str) -> str:
    for marker in (" Risk:", " Upside:"):
        if marker in value:
            value = value.split(marker, 1)[0]
    return value.strip()


def _header_index(headers: list[str], predicate) -> int:
    for index, header in enumerate(headers):
        if predicate(header.strip().lower()):
            return index
    raise ValueError("required FFToday header missing")


def _matching_indices(headers: list[str], label: str) -> list[int]:
    label = label.lower()
    return [i for i, header in enumerate(headers) if header.strip().lower() == label]


def _value(cells: list[str], indexes: list[int], occurrence: int = 0, default: float | None = None) -> float:
    if occurrence >= len(indexes) or indexes[occurrence] >= len(cells):
        if default is not None:
            return default
        raise ValueError("required FFToday projection column missing")
    return numeric(cells[indexes[occurrence]])


def _row_from_headers(
    *,
    provider: str,
    position: Position,
    headers: list[str],
    cells: list[str],
) -> CurrentProjectionRow | None:
    player_i = _header_index(headers, lambda value: value.startswith("player"))
    team_i = _header_index(headers, lambda value: value == "tm")
    if player_i >= len(cells) or team_i >= len(cells):
        return None
    name = _clean_name(cells[player_i])
    team = cells[team_i].upper().strip()
    if not name or len(team) not in {2, 3}:
        return None

    yds = _matching_indices(headers, "yds")
    td = _matching_indices(headers, "td")
    att = _matching_indices(headers, "att")
    rec = _matching_indices(headers, "rec")
    ints = _matching_indices(headers, "int")

    if position == Position.QB:
        stats = {
            "pass_yd": _value(cells, yds, 0),
            "pass_td": _value(cells, td, 0),
            "pass_int": _value(cells, ints, 0),
            "rush_yd": _value(cells, yds, 1),
            "rush_td": _value(cells, td, 1),
        }
    elif position == Position.RB:
        stats = {
            "rush_yd": _value(cells, yds, 0),
            "rush_td": _value(cells, td, 0),
            "rec": _value(cells, rec, 0),
            "rec_yd": _value(cells, yds, 1),
            "rec_td": _value(cells, td, 1),
        }
    elif position in {Position.WR, Position.TE}:
        stats = {
            "rec": _value(cells, rec, 0),
            "rec_yd": _value(cells, yds, 0),
            "rec_td": _value(cells, td, 0),
            "rush_yd": _value(cells, yds, 1, 0.0),
            "rush_td": _value(cells, td, 1, 0.0),
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
    if not url.startswith("https://www.fftoday.com/rankings/playerproj.php?"):
        raise ValueError("FFToday live source only permits fixed projection URLs")
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1 (+private-beta projection research)"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
