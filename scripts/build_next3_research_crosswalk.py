from __future__ import annotations

import argparse
import csv
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_PLAYERIDS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_playerids.csv"
)


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fsffl-next-research/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed research source
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    value = value.strip()
    return "" if value.upper() in {"NA", "NAN", "NULL", "NONE"} else value


def build_crosswalk(csv_text: str) -> tuple[list[dict[str, str]], int, int]:
    """Build a research-only FantasyPros/Sleeper identity bridge.

    The generated asset_id is deliberately namespaced as ``research:sleeper:*``.
    It exists only to let independent market sources join during calibration and
    benchmarking; it is not canonical NEXT player identity and must never be
    persisted into authoritative state.
    """
    reader = csv.DictReader(StringIO(csv_text))
    fields = set(reader.fieldnames or ())
    required = {"fantasypros_id", "sleeper_id"}
    if not required.issubset(fields):
        raise ValueError(
            "DynastyProcess db_playerids schema must contain fantasypros_id and sleeper_id"
        )

    rows: list[dict[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    source_rows = 0
    skipped = 0
    for row in reader:
        source_rows += 1
        fp_id = _clean(row.get("fantasypros_id"))
        sleeper_id = _clean(row.get("sleeper_id"))
        if not fp_id or not sleeper_id:
            skipped += 1
            continue
        pair = (fp_id, sleeper_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        rows.append(
            {
                "asset_id": f"research:sleeper:{sleeper_id}",
                "fp_id": fp_id,
                "sleeper_id": sleeper_id,
            }
        )

    rows.sort(key=lambda item: (item["sleeper_id"], item["fp_id"]))
    return rows, source_rows, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a non-authoritative NEXT-3 research provider crosswalk."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--playerids-url", default=DEFAULT_PLAYERIDS_URL)
    args = parser.parse_args()

    rows, source_rows, skipped = build_crosswalk(_download_text(args.playerids_url))
    if not rows:
        raise RuntimeError("research crosswalk produced no usable provider-id pairs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("asset_id", "fp_id", "sleeper_id"))
        writer.writeheader()
        writer.writerows(rows)

    print(
        "built NEXT-3 research crosswalk: "
        f"source_rows={source_rows} usable_pairs={len(rows)} skipped={skipped}"
    )


if __name__ == "__main__":
    main()
