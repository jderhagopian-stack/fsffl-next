from __future__ import annotations

from html.parser import HTMLParser


class HtmlTableParser(HTMLParser):
    """Minimal dependency-free HTML table extractor for fixed public provider pages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.text_parts: list[str] = []
        self._depth = 0
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._table = []
        elif tag == "tr" and self._depth == 1:
            self._row = []
        elif tag in {"th", "td"} and self._depth == 1 and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.replace("\xa0", " ").split())
        if not text:
            return
        self.text_parts.append(text)
        if self._cell is not None:
            self._cell.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._depth == 1 and self._row is not None:
            if any(self._row):
                assert self._table is not None
                self._table.append(self._row)
            self._row = None
        elif tag == "table":
            if self._depth == 1 and self._table is not None:
                self.tables.append(self._table)
                self._table = None
            self._depth = max(0, self._depth - 1)


def normalize_cell(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split()).strip()


def numeric(value: str) -> float:
    cleaned = value.replace(",", "").strip()
    if cleaned in {"", "-", "—"}:
        return 0.0
    return float(cleaned)
