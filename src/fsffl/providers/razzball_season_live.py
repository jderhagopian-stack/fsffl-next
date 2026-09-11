from __future__ import annotations

import re
from datetime import UTC, datetime
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
    source_version = "razzball-season-projections-html-v3:horizon-isolated"
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
        if not re.search(
            rf"\b{season}\s+(?:Fantasy\s+Football\s+)?Projections\b",
            page_text,
            re.IGNORECASE,
        ):
            raise ValueError("Razzball response did not match requested full-season horizon")
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
