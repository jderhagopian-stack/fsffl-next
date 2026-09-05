from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from fsffl.value import CalibrationPanel
from fsffl.value.sources import normalize_dynastyprocess_values


DEFAULT_DYNASTYPROCESS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values.csv"
)


def _load_crosswalk(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"fp_id", "asset_id"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError("crosswalk must contain fp_id and asset_id columns")
        result: dict[str, str] = {}
        for row in reader:
            fp_id = (row.get("fp_id") or "").strip()
            asset_id = (row.get("asset_id") or "").strip()
            if not fp_id or not asset_id:
                continue
            prior = result.get(fp_id)
            if prior is not None and prior != asset_id:
                raise ValueError(f"conflicting crosswalk entries for fp_id={fp_id}")
            result[fp_id] = asset_id
    return result


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fsffl-next-research/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit governed source URL
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a normalized NEXT-3 market calibration panel artifact."
    )
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dynastyprocess-url", default=DEFAULT_DYNASTYPROCESS_URL)
    parser.add_argument("--panel-version", default="next3-market-panel-v1")
    args = parser.parse_args()

    crosswalk = _load_crosswalk(args.crosswalk)
    csv_text = _download_text(args.dynastyprocess_url)
    normalized = normalize_dynastyprocess_values(
        csv_text,
        asset_id_by_fp_id=crosswalk,
        provenance_uri=args.dynastyprocess_url,
    )
    if not normalized.observations:
        raise RuntimeError("DynastyProcess import produced no mapped observations")

    as_of = max(row.observed_at for row in normalized.observations)
    panel = CalibrationPanel(
        observations=normalized.observations,
        as_of=as_of,
        panel_version=args.panel_version,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(panel.model_dump_json(indent=2), encoding="utf-8")
    print(
        "built market panel: "
        f"rows_seen={normalized.rows_seen} "
        f"rows_imported={normalized.rows_imported} "
        f"rows_unmapped={normalized.rows_unmapped} "
        f"observations={len(panel.observations)} "
        f"as_of={as_of.astimezone(UTC).isoformat()}"
    )


if __name__ == "__main__":
    main()
