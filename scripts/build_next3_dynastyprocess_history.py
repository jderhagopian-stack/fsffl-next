from __future__ import annotations

import argparse
import csv
import subprocess
from datetime import datetime
from pathlib import Path

from fsffl.value import CalibrationPanel
from fsffl.value.sources import normalize_dynastyprocess_values


VALUES_PATH = "files/values.csv"


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _load_crosswalk(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"fp_id", "asset_id"}.issubset(reader.fieldnames):
            raise ValueError("crosswalk must contain fp_id and asset_id columns")
        return {
            (row.get("fp_id") or "").strip(): (row.get("asset_id") or "").strip()
            for row in reader
            if (row.get("fp_id") or "").strip() and (row.get("asset_id") or "").strip()
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build point-in-time DynastyProcess market history from its Git history."
    )
    parser.add_argument("--dynastyprocess-repo", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument("--panel-version", default="next3-dynastyprocess-history-v1")
    args = parser.parse_args()

    start = datetime.fromisoformat(args.start_date).date() if args.start_date else None
    end = datetime.fromisoformat(args.end_date).date() if args.end_date else None
    crosswalk = _load_crosswalk(args.crosswalk)

    commits = [
        line.strip()
        for line in _run_git(args.dynastyprocess_repo, "log", "--format=%H", "--", VALUES_PATH).splitlines()
        if line.strip()
    ]
    if not commits:
        raise RuntimeError("no DynastyProcess values.csv history found")

    by_snapshot_date = {}
    skipped_schema_commits = 0
    for commit in commits:
        csv_text = _run_git(args.dynastyprocess_repo, "show", f"{commit}:{VALUES_PATH}")
        try:
            normalized = normalize_dynastyprocess_values(
                csv_text,
                asset_id_by_fp_id=crosswalk,
                source_version=commit,
                provenance_uri=f"git:dynastyprocess/data@{commit}:{VALUES_PATH}",
            )
        except ValueError as exc:
            # Older DynastyProcess snapshots predate the provider-id fields needed
            # for a defensible canonical crosswalk. They are unusable evidence for
            # NEXT-3 and must be skipped rather than guessed or name-matched.
            if "schema missing required columns" not in str(exc):
                raise
            skipped_schema_commits += 1
            continue
        if not normalized.observations:
            continue
        snapshot_date = max(row.observed_at for row in normalized.observations).date()
        if start is not None and snapshot_date < start:
            continue
        if end is not None and snapshot_date > end:
            continue
        # Git history can contain multiple commits for the same scrape_date. Keep
        # the newest commit encountered by git log for one point-in-time snapshot.
        if snapshot_date not in by_snapshot_date:
            by_snapshot_date[snapshot_date] = normalized.observations

    if not by_snapshot_date:
        raise RuntimeError("no DynastyProcess snapshots matched requested history window")

    observations = tuple(
        row
        for snapshot_date in sorted(by_snapshot_date)
        for row in by_snapshot_date[snapshot_date]
    )
    panel = CalibrationPanel(
        observations=observations,
        as_of=max(row.observed_at for row in observations),
        panel_version=args.panel_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(panel.model_dump_json(indent=2), encoding="utf-8")
    print(
        "built DynastyProcess history panel: "
        f"snapshots={len(by_snapshot_date)} observations={len(observations)} "
        f"skipped_schema_commits={skipped_schema_commits} "
        f"first={min(by_snapshot_date)} last={max(by_snapshot_date)}"
    )


if __name__ == "__main__":
    main()
