from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fsffl.value import CalibrationPanel
from fsffl.value.sources import normalize_statsguy_rankings

DEFAULT_BASE_URL = "https://api.statsguyfantasy.com/api/v1/rankings"


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fsffl-next-research/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed public API
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def _load_sleeper_crosswalk(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"sleeper_id", "asset_id"}.issubset(reader.fieldnames):
            raise ValueError("crosswalk must contain sleeper_id and asset_id")
        return {
            (row.get("sleeper_id") or "").strip(): (row.get("asset_id") or "").strip()
            for row in reader
            if (row.get("sleeper_id") or "").strip() and (row.get("asset_id") or "").strip()
        }


def _dates(start: date, end: date, step_days: int):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=step_days)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build point-in-time Stats Guy market history.")
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", default="2025-09-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--step-days", type=int, default=7)
    parser.add_argument("--format", default="sf_dynasty")
    parser.add_argument("--format-context-id", default="dynasty:sf")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--panel-version", default="next3-statsguy-history-v1")
    args = parser.parse_args()

    if args.step_days < 1:
        raise ValueError("step-days must be positive")
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date) if args.end_date else datetime.now(UTC).date()
    if end < start:
        raise ValueError("end-date cannot precede start-date")

    crosswalk = _load_sleeper_crosswalk(args.crosswalk)
    observations = []
    snapshots = 0
    skipped_empty = 0
    served_dates: set[str] = set()

    for requested_date in _dates(start, end, args.step_days):
        query = urlencode({"format": args.format, "date": requested_date.isoformat(), "limit": 1000})
        url = f"{args.base_url}?{query}"
        payload_text = _download_text(url)
        payload = json.loads(payload_text)
        if not payload.get("rankings"):
            skipped_empty += 1
            continue
        served = str(payload.get("asOf") or "")
        if served in served_dates:
            continue
        served_dates.add(served)
        normalized = normalize_statsguy_rankings(
            payload_text,
            asset_id_by_sleeper_id=crosswalk,
            format_context_id=args.format_context_id,
            source_version=served,
            provenance_uri=url,
        )
        observations.extend(normalized.observations)
        snapshots += 1

    if not observations:
        raise RuntimeError("Stats Guy history import produced no observations")

    panel = CalibrationPanel(
        observations=tuple(sorted(observations, key=lambda row: (row.observed_at, row.asset_id or ""))),
        as_of=max(row.observed_at for row in observations),
        panel_version=args.panel_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(panel.model_dump_json(indent=2), encoding="utf-8")
    print(
        "built Stats Guy history panel: "
        f"snapshots={snapshots} observations={len(panel.observations)} "
        f"skipped_empty={skipped_empty} first={min(row.observed_at for row in panel.observations).date()} "
        f"last={max(row.observed_at for row in panel.observations).date()}"
    )


if __name__ == "__main__":
    main()
