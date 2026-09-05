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
    source_version = "cbs-season-projections-html-v1"
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
            url = self._url(season=season, position=position)
            rows.extend(_parse_page(self._http_get_text(url), provider=self.provider_name, position=position))
        if not rows:
            raise ValueError("CBS returned no current projections")
        # CBS current projection pages do not consistently expose an explicit
        # publication/update timestamp. Retrieval time is therefore the earliest
        # demonstrable availability time FSFFL may claim for this live snapshot.
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
        return (
            "https://www.cbssports.com/fantasy/football/stats/"
            f"{position.value}/{season}/season/projections/nonppr/"
        )


def _parse_page(html: str, *, provider: str, position: Position) -> tuple[CurrentProjectionRow, ...]:
    parser = HtmlTableParser()
    parser.feed(html)
    for table in parser.tables:
        header_index = next(
            (index for index, row in enumerate(table) if any(normalize_cell(cell).startswith("Player") for cell in row)),
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
            return tuple(output)
    raise ValueError(f"CBS {position.value} projection table was not found")


def _extract_identity(cell: str, position: Position) -> tuple[str, str]:
    # CBS player cells commonly contain both a short display name and the full
    # identity, e.g. "J. Gibbs RB DET Jahmyr Gibbs RB DET". Capture the full
    # identity between the first and final position/team markers.
    pattern = re.compile(
        rf"^.*?\b{re.escape(position.value)}\s+([A-Z]{{2,3}})\s+(.+?)\s+{re.escape(position.value)}\s+\1$"
    )
    match = pattern.match(cell.strip())
    if match:
        team, name = match.groups()
        return name.strip(), team
    trailing = re.search(rf"(.+?)\s+{re.escape(position.value)}\s+([A-Z]{{2,3}})$", cell.strip())
    if trailing:
        return trailing.group(1).strip(), trailing.group(2)
    raise ValueError("CBS player identity could not be parsed")


def _row_from_cells(*, provider: str, position: Position, cells: list[str]) -> CurrentProjectionRow | None:
    if len(cells) < 8:
        return None
    name, team = _extract_identity(cells[0], position)
    stats: dict[str, float]
    if position == Position.QB:
        # Player, GP, CMP, ATT, YDS, TD, INT, ... rushing ATT/YDS/TD ...
        if len(cells) < 14:
            return None
        stats = {
            "pass_yd": numeric(cells[4]),
            "pass_td": numeric(cells[5]),
            "pass_int": numeric(cells[6]),
            "rush_yd": numeric(cells[9]),
            "rush_td": numeric(cells[11]),
        }
    elif position == Position.RB:
        # Player, GP, rush ATT/YDS/AVG/TD, TGT, REC, rec YDS/YDSG/AVG/TD, ...
        if len(cells) < 13:
            return None
        stats = {
            "rush_yd": numeric(cells[3]),
            "rush_td": numeric(cells[5]),
            "rec": numeric(cells[7]),
            "rec_yd": numeric(cells[8]),
            "rec_td": numeric(cells[11]),
        }
    elif position == Position.WR:
        if len(cells) < 13:
            return None
        stats = {
            "rec": numeric(cells[3]),
            "rec_yd": numeric(cells[4]),
            "rec_td": numeric(cells[7]),
            "rush_yd": numeric(cells[9]),
            "rush_td": numeric(cells[11]),
        }
    elif position == Position.TE:
        if len(cells) < 8:
            return None
        stats = {
            "rec": numeric(cells[3]),
            "rec_yd": numeric(cells[4]),
            "rec_td": numeric(cells[7]),
            "rush_yd": 0.0,
            "rush_td": 0.0,
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
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1 (+private-beta projection research)"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider URL
        return response.read().decode("utf-8", errors="replace")
