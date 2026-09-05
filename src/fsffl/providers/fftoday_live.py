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
    source_version = "fftoday-season-projections-html-v1"
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
            url = self._url(season=season, pos_id=pos_id)
            html = self._http_get_text(url)
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
            (index for index, row in enumerate(table) if any(normalize_cell(cell) == "Player" for cell in row)),
            None,
        )
        if header_index is None:
            continue
        output: list[CurrentProjectionRow] = []
        for cells in table[header_index + 1 :]:
            values = [normalize_cell(cell) for cell in cells]
            try:
                row = _row_from_cells(provider=provider, position=position, cells=values)
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


def _row_from_cells(*, provider: str, position: Position, cells: list[str]) -> CurrentProjectionRow | None:
    # FFToday tables expose player, team and bye first, followed by position-specific raw stats.
    if len(cells) < 7:
        return None
    name = _clean_name(cells[0])
    team = cells[1].upper()
    if not name or len(team) not in {2, 3}:
        return None
    stats: dict[str, float]
    if position == Position.QB:
        if len(cells) < 12:
            return None
        stats = {
            "pass_yd": numeric(cells[5]),
            "pass_td": numeric(cells[6]),
            "pass_int": numeric(cells[7]),
            "rush_yd": numeric(cells[9]),
            "rush_td": numeric(cells[10]),
        }
    elif position == Position.RB:
        if len(cells) < 10:
            return None
        stats = {
            "rush_yd": numeric(cells[4]),
            "rush_td": numeric(cells[5]),
            "rec": numeric(cells[6]),
            "rec_yd": numeric(cells[7]),
            "rec_td": numeric(cells[8]),
        }
    elif position in {Position.WR, Position.TE}:
        if len(cells) < 10:
            return None
        stats = {
            "rec": numeric(cells[3]),
            "rec_yd": numeric(cells[4]),
            "rec_td": numeric(cells[5]),
            "rush_yd": numeric(cells[7]),
            "rush_td": numeric(cells[8]),
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
