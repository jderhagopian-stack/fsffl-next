from __future__ import annotations

import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Callable

from .razzball_live import (
    RazzballLiveProjectionSource,
    RazzballProjectionSnapshot,
    _default_get_text,
    _extract_projection_rows,
    _parse_updated_at,
)


HtmlGetter = Callable[[str], str]
Clock = Callable[[], datetime]


class _HorizonHeadings(HTMLParser):
    """Read horizon assertions, excluding unrelated navigation links and scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self._parts: list[str] | None = None
        self._tag: str | None = None

    def handle_starttag(self, tag, attrs) -> None:
        if tag in {"title", "h1", "h2", "caption"} and self._tag is None:
            self._tag, self._parts = tag, []

    def handle_data(self, data) -> None:
        if self._parts is not None:
            self._parts.append(data)

    def handle_endtag(self, tag) -> None:
        if tag == self._tag:
            self.headings.append(" ".join(self._parts or ()))
            self._tag, self._parts = None, None


def _assert_season_horizon(html: str, page_text: str, season: int) -> None:
    headings = _HorizonHeadings()
    headings.feed(html)
    conflicting = re.compile(
        r"\brest[\s-]+of[\s-]+season\b|\bROS\b|\bweek\s*\d+\b",
        re.IGNORECASE,
    )
    # Generic year/title wording is shared by in-season pages. Explicit horizon
    # assertions in the page's headings/captions override that generic wording.
    # Do not scan all links: a valid season page can link to ROS/weekly products.
    if any(conflicting.search(heading) for heading in headings.headings):
        raise ValueError("Razzball response identifies a non-full-season horizon")
    if not re.search(
        rf"\b{season}\s+(?:Fantasy\s+Football\s+)?Projections\b",
        page_text,
        re.IGNORECASE,
    ):
        raise ValueError("Razzball response did not match requested full-season horizon")


class RazzballSeasonProjectionSource:
    """Full-season Razzball source that never reads rest-of-season pages.

    The legacy live source supplemented season rows with fumbles from ROS position
    pages. Fumbles lacked a second full-season source and therefore never acquired
    authoritative ensemble coverage, but the cross-horizon read was still an
    evidence-boundary smell. This source keeps SEASON acquisition horizon-pure and
    verifies the page still identifies itself as the requested season projection.
    """

    provider_name = "razzball"
    source_url = RazzballLiveProjectionSource.source_url
    source_version = "razzball-season-projections-html-v4:horizon-isolated-validated"
    usage_class = "beta-personal-research-requires-commercial-review"

    def __init__(self, *, http_get_text: HtmlGetter | None = None, clock: Clock | None = None) -> None:
        self._http_get_text = http_get_text or _default_get_text
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_latest(self, *, season: int) -> RazzballProjectionSnapshot:
        captured_at = self._clock()
        if captured_at.tzinfo is None:
            raise ValueError("live Razzball clock must return a timezone-aware datetime")
        html = self._http_get_text(self.source_url)
        rows, page_text = _extract_projection_rows(html)
        _assert_season_horizon(html, page_text, season)
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
            usage_class=self.usage_class,
        )
