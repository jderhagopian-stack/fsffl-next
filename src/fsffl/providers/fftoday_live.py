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
_MAX_PAGES = 12
_NFL_TEAMS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
    "HOU", "IND", "JAC", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS", "WSH",
}


class FFTodayLiveProjectionSource:
    provider_name = "fftoday"
    source_version = "fftoday-season-projections-html-v5"
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
            position_rows: list[CurrentProjectionRow] = []
            seen_external_ids: set[str] = set()
            for page in range(_MAX_PAGES):
                html = self._http_get_text(self._url(season=season, pos_id=pos_id, page=page))
                parsed_rows, updated, has_next = _parse_page(
                    html,
                    provider=self.provider_name,
                    position=position,
                )
                for row in parsed_rows:
                    if row.external_id in seen_external_ids:
                        continue
                    seen_external_ids.add(row.external_id)
                    position_rows.append(row)
                effective = updated if effective is None else max(effective, updated)
                if not has_next:
                    break
            rows.extend(position_rows)
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
    def _url(*, season: int, pos_id: str, page: int = 0) -> str:
        if page < 0:
            raise ValueError("FFToday page must be non-negative")
        page_param = "" if page == 0 else f"&cur_page={page}"
        return (
            "https://www.fftoday.com/rankings/playerproj.php"
            f"?LeagueID=&PosID={pos_id}&Season={season}{page_param}&order_by=FFPts&sort_order=DESC"
        )


_UPDATED_RE = re.compile(r"Updated:\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.IGNORECASE)


def _parse_page(
    html: str, *, provider: str, position: Position
) -> tuple[tuple[CurrentProjectionRow, ...], datetime, bool]:
    parser = HtmlTableParser()
    parser.feed(html)
    page_text = " ".join(parser.text_parts)
    match = _UPDATED_RE.search(page_text)
    if match is None:
        raise ValueError("FFToday projection update date was not found")
    month, day, year = (int(value) for value in match.groups())
    effective = datetime(year, month, day, 12, 0, tzinfo=UTC)
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
                row = _row_from_headers(
                    provider=provider,
                    position=position,
                    headers=headers,
                    cells=values,
                )
            except (ValueError, IndexError):
                row = _row_from_relative_cells(provider=provider, position=position, cells=values)
            if row is not None:
                output.append(row)
        if output:
            return tuple(output), effective, has_next

    text_rows = _rows_from_text_parts(parser.text_parts, provider=provider, position=position)
    if text_rows:
        return text_rows, effective, has_next
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


def _identity_from_cells(cells: list[str]) -> tuple[str, str, int] | None:
    for i, cell in enumerate(cells):
        token = cell.upper().strip()
        if token in _NFL_TEAMS and i > 0:
            name = _clean_name(cells[i - 1])
            if name and not re.fullmatch(r"[\d.\-]+", name):
                return name, ("JAX" if token == "JAC" else "WAS" if token == "WSH" else token), i
    return None


def _row_from_relative_cells(*, provider: str, position: Position, cells: list[str]) -> CurrentProjectionRow | None:
    identity = _identity_from_cells(cells)
    if identity is None:
        return None
    name, team, team_i = identity
    tail = cells[team_i + 1 :]
    try:
        if position == Position.QB and len(tail) >= 10:
            stats = {
                "pass_yd": numeric(tail[3]),
                "pass_td": numeric(tail[4]),
                "pass_int": numeric(tail[5]),
                "rush_yd": numeric(tail[7]),
                "rush_td": numeric(tail[8]),
            }
        elif position == Position.RB and len(tail) >= 8:
            stats = {
                "rush_yd": numeric(tail[2]),
                "rush_td": numeric(tail[3]),
                "rec": numeric(tail[4]),
                "rec_yd": numeric(tail[5]),
                "rec_td": numeric(tail[6]),
            }
        elif position == Position.WR and len(tail) >= 8:
            stats = {
                "rec": numeric(tail[1]),
                "rec_yd": numeric(tail[2]),
                "rec_td": numeric(tail[3]),
                "rush_yd": numeric(tail[5]),
                "rush_td": numeric(tail[6]),
            }
        elif position == Position.TE and len(tail) >= 5:
            stats = {
                "rec": numeric(tail[1]),
                "rec_yd": numeric(tail[2]),
                "rec_td": numeric(tail[3]),
                "rush_yd": 0.0,
                "rush_td": 0.0,
            }
        else:
            return None
    except (ValueError, IndexError):
        return None
    return CurrentProjectionRow(
        provider=provider,
        external_id=f"{position.value}:{team}:{name}",
        player_name=name,
        position=position,
        nfl_team=team,
        stats=stats,
    )


def _required_numeric_tail(position: Position) -> int:
    if position == Position.QB:
        return 10
    if position in {Position.RB, Position.WR}:
        return 8
    if position == Position.TE:
        return 5
    raise ValueError(f"unsupported FFToday position: {position.value}")


def _rows_from_text_parts(
    parts: list[str], *, provider: str, position: Position
) -> tuple[CurrentProjectionRow, ...]:
    """Fallback for hosted FFToday responses whose projection grid is not emitted as a normal HTML table.

    FFToday's server-rendered page still emits player name, team, and the documented numeric
    projection columns in sequence. This parser is intentionally provider-local and only accepts
    rows with the exact position-specific numeric shape, so unrelated page text cannot become
    forecast evidence.
    """

    required = _required_numeric_tail(position)
    output: list[CurrentProjectionRow] = []
    for index, raw in enumerate(parts):
        team_token = normalize_cell(raw).upper()
        if team_token not in _NFL_TEAMS or index == 0:
            continue
        name = _clean_name(normalize_cell(parts[index - 1]))
        if not name or re.fullmatch(r"[\d.,\-]+", name):
            continue
        numeric_tail: list[str] = []
        cursor = index + 1
        while cursor < len(parts) and len(numeric_tail) < required:
            token = normalize_cell(parts[cursor])
            try:
                numeric(token)
            except ValueError:
                break
            numeric_tail.append(token)
            cursor += 1
        if len(numeric_tail) != required:
            continue
        row = _row_from_relative_cells(
            provider=provider,
            position=position,
            cells=[name, team_token, *numeric_tail],
        )
        if row is not None:
            output.append(row)
    return tuple(output)


def _row_from_headers(
    *,
    provider: str,
    position: Position,
    headers: list[str],
    cells: list[str],
) -> CurrentProjectionRow | None:
    player_i = _header_index(headers, lambda value: value.startswith("player"))
    team_candidates = [i for i, header in enumerate(headers) if header.strip().lower() == "tm"]
    if not team_candidates:
        return _row_from_relative_cells(provider=provider, position=position, cells=cells)
    team_i = team_candidates[0]
    if player_i >= len(cells) or team_i >= len(cells):
        return None
    name = _clean_name(cells[player_i])
    team = cells[team_i].upper().strip()
    if team == "JAC":
        team = "JAX"
    elif team == "WSH":
        team = "WAS"
    if not name or team not in _NFL_TEAMS:
        return _row_from_relative_cells(provider=provider, position=position, cells=cells)

    yds = _matching_indices(headers, "yds")
    td = _matching_indices(headers, "td")
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
    if "Projections" not in text or "Updated:" not in text:
        raise ValueError("FFToday hosted response did not contain projection content")
    return text
