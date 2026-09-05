from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fsffl.value import build_market_calibration_panel_batch
from fsffl.value.sources import (
    normalize_dynastydealer_values,
    normalize_dynastyprocess_values,
    normalize_fantasycalc_values,
    normalize_statsguy_rankings,
)


DEFAULT_DYNASTYPROCESS_URL = (
    "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values.csv"
)
DEFAULT_DYNASTYDEALER_URL = "https://www.dynastydealer.com/api/player-values"
DEFAULT_FANTASYCALC_URL = "https://api.fantasycalc.com/values/current"
DEFAULT_STATSGUY_URL = "https://api.statsguyfantasy.com/api/v1/rankings"


def _load_crosswalk(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"asset_id"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError("crosswalk must contain asset_id and provider-id columns")
        fp: dict[str, str] = {}
        sleeper: dict[str, str] = {}
        for row in reader:
            asset_id = (row.get("asset_id") or "").strip()
            if not asset_id:
                continue
            for key, target in (("fp_id", fp), ("sleeper_id", sleeper)):
                provider_id = (row.get(key) or "").strip()
                if not provider_id:
                    continue
                prior = target.get(provider_id)
                if prior is not None and prior != asset_id:
                    raise ValueError(f"conflicting crosswalk entries for {key}={provider_id}")
                target[provider_id] = asset_id
    return fp, sleeper


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fsffl-next-research/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed source URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a concurrent multi-source NEXT-3 market calibration panel artifact."
    )
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format-context-id", required=True)
    parser.add_argument("--num-qbs", type=int, choices=(1, 2), default=2)
    parser.add_argument("--num-teams", type=int, default=12)
    parser.add_argument("--ppr", type=float, choices=(0.0, 0.5, 1.0), default=0.5)
    parser.add_argument("--dynastyprocess-url", default=DEFAULT_DYNASTYPROCESS_URL)
    parser.add_argument("--dynastydealer-url", default=DEFAULT_DYNASTYDEALER_URL)
    parser.add_argument("--fantasycalc-url", default=DEFAULT_FANTASYCALC_URL)
    parser.add_argument("--statsguy-url", default=DEFAULT_STATSGUY_URL)
    parser.add_argument("--panel-version", default="next3-market-panel-v3")
    args = parser.parse_args()

    fp_crosswalk, sleeper_crosswalk = _load_crosswalk(args.crosswalk)
    acquisition_time = datetime.now(UTC)

    fantasycalc_url = f"{args.fantasycalc_url}?{urlencode({'isDynasty': 'true', 'numQbs': args.num_qbs, 'numTeams': args.num_teams, 'ppr': args.ppr})}"
    statsguy_format = "sf_dynasty" if args.num_qbs == 2 else "non_sf_dynasty"
    statsguy_context = "dynasty:sf" if args.num_qbs == 2 else "dynasty:1qb"
    statsguy_url = f"{args.statsguy_url}?{urlencode({'format': statsguy_format, 'limit': 1000})}"

    def load_dynastyprocess():
        return normalize_dynastyprocess_values(
            _download_text(args.dynastyprocess_url),
            asset_id_by_fp_id=fp_crosswalk,
            provenance_uri=args.dynastyprocess_url,
        ).observations

    def load_dynastydealer():
        return normalize_dynastydealer_values(
            _download_text(args.dynastydealer_url),
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=args.format_context_id,
            provenance_uri=args.dynastydealer_url,
        ).observations

    def load_fantasycalc():
        return normalize_fantasycalc_values(
            _download_text(fantasycalc_url),
            observed_at=acquisition_time,
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=args.format_context_id,
            provenance_uri=fantasycalc_url,
        ).observations

    def load_statsguy():
        return normalize_statsguy_rankings(
            _download_text(statsguy_url),
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=statsguy_context,
            provenance_uri=statsguy_url,
        ).observations

    batch = build_market_calibration_panel_batch(
        {
            "dynastyprocess_market_values": load_dynastyprocess,
            "dynastydealer_market_values": load_dynastydealer,
            "fantasycalc_market_values": load_fantasycalc,
            "statsguy_market_values": load_statsguy,
        },
        as_of=acquisition_time,
        panel_version=args.panel_version,
        max_workers=4,
    )
    if not batch.panel.observations:
        raise RuntimeError("multi-source market import produced no observations")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(batch.panel.model_dump_json(indent=2), encoding="utf-8")
    print(
        "built multi-source market panel: "
        f"completed={batch.completed_source_ids} "
        f"failed={batch.failed_source_ids} "
        f"counts={batch.observation_count_by_source_id} "
        f"observations={len(batch.panel.observations)} "
        f"as_of={batch.panel.as_of.astimezone(UTC).isoformat()}"
    )
    if batch.errors_by_source_id:
        print(f"source_errors={batch.errors_by_source_id}")


if __name__ == "__main__":
    main()
