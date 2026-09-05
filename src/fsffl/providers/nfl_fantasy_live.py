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
    Position.QB: "1",
    Position.RB: "2",
    Position.WR: "3",
    Position.TE: "4",
}
_PAGE_SIZE = 25
_MAX_PAGES = 12


class NFLFantasyLiveProjectionSource:
    provider_name = "nfl_fantasy"
    source_version = "nfl-fantasy-season-projections-html-v2"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> CurrentProjectionSnapshot:
        captured = self._clock()
        if captured.tzinfo is None:
            raise ValueError("NFL Fantasy live clock must be timezone-aware")

        rows: list[CurrentProjectionRow] = []
        for position, position_id in _POSITION_IDS.items():
            position_rows: list[CurrentProjectionRow] = []
            for page in range(_MAX_PAGES):
                offset = 1 if page == 0 else page * _PAGE_SIZE + 1
                html = self._http_get_text(self._url(season=season, position_id=position_id, offset=offset))
                parsed, has_next = _parse_page(html, provider=self.provider_name, position=position)
                if not parsed:
                    break
                position_rows.extend(parsed)
                if not has_next:
                    break
            rows.extend(position_rows)

        if not rows:
            raise ValueError("NFL Fantasy returned no current projections")

        captured_utc = captured.astimezone(UTC)
        return CurrentProjectionSnapshot(
            provider=self.provider_name,
            captured_at=captured_utc,
            effective_at=captured_utc,
            rows=tuple(rows),
            source_version=self.source_version,
            usage_class=self.usage_class,
        )

    @staticmethod
    def _url(*, season: int, position_id: str, offset: int) -> str:
        return (
            "https://fantasy.nfl.com/research/projections"
            f"?offset={offset}&position={position_id}&sort=projectedPts"
            f"&statCategory=projectedStats&statSeason={season}"
            "&statType=seasonProjectedStats"
        )


def _parse_page(html: str, *, provider: str, position: Position) -> tuple[tuple[CurrentProjectionRow, ...], bool]:
    parser = HtmlTableParser()
    parser.feed(html)

    for table in parser.tables:
        header_index = next(
            (index for index, row in enumerate(table) if any(normalize_cell(cell).lower().startswith("player") for cell in row)),
            None,
        )
        if header_index is None:
            continue

        output: list[CurrentProjectionRow] = []
        for raw_cells in table[header_index + 1 :]:
            cells = [normalize_cell(cell) for cell in raw_cells]
            try:
                row = _row_from_cells(provider=provider, position=position, cells=cells)
            except (ValueError, IndexError):
                continue
            if row is not None:
                output.append(row)

        if output:
            text = " ".join(parser.text_parts)
            has_next = bool(re.search(r"\b\d+\s*-\s*\d+\s+of\s+\d+\b", text)) and not _is_last_page(text)
            return tuple(output), has_next

    raise ValueError(f"NFL Fantasy {position.value} projection table was not found")


def _is_last_page(text: str) -> bool:
    match = re.search(r"\b(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\b", text)
    if match is None:
        return True
    _, end, total = (int(value) for value in match.groups())
    return end >= total


def _extract_identity(cell: str, position: Position) -> tuple[str, str]:
    match = re.search(rf"^(.*?)\s+{re.escape(position.value)}\s+-\s+([A-Z]{{2,3}})\b", cell.strip())
    if match is None:
        raise ValueError("NFL Fantasy player identity could not be parsed")
    return match.group(1).strip(), match.group(2)


def _row_from_cells(*, provider: str, position: Position, cells: list[str]) -> CurrentProjectionRow | None:
    if len(cells) < 16:
        return None
    name, team = _extract_identity(cells[0], position)
    stats = {
        "pass_yd": numeric(cells[3]),
        "pass_td": numeric(cells[4]),
        "pass_int": numeric(cells[5]),
        "rush_yd": numeric(cells[6]),
        "rush_td": numeric(cells[7]),
        "rec": numeric(cells[8]),
        "rec_yd": numeric(cells[9]),
        "rec_td": numeric(cells[10]),
        "fum_lost": numeric(cells[14]),
    }
    return CurrentProjectionRow(
        provider=provider,
        external_id=f"{position.value}:{team}:{name}",
        player_name=name,
        position=position,
        nfl_team=team,
        stats=stats,
    )


def _default_get_text(url: str) -> str:
    if not url.startswith("https://fantasy.nfl.com/research/projections?"):
        raise ValueError("NFL Fantasy live source only permits fixed projection URLs")
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
    lowered = text.lower()
    if "projection" not in lowered or "player" not in lowered:
        raise ValueError("NFL Fantasy hosted response did not contain projection content")
    return text
