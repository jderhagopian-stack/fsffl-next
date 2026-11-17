"""Offline source-coverage probe; prints counts only, never private draft rows."""
from __future__ import annotations

import argparse
from hashlib import sha1
import json
from pathlib import Path

from fsffl.providers.sleeper_historical_pick_inventory import inspect_sleeper_draft_pick_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--git-blob-sha", required=True)
    args = parser.parse_args()
    raw = args.archive.read_bytes()
    digest = sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if digest != args.git_blob_sha:
        raise SystemExit("source bytes do not match pinned Git blob; no audit attempted")
    summaries = []
    for season in json.loads(raw):
        summaries.append({"season": int(season["league"]["season"]),
                          **inspect_sleeper_draft_pick_coverage(season)})
    print(json.dumps({"draft_pick_source_coverage": sorted(summaries, key=lambda s: s["season"]),
                      "scope": "source_counts_only_not_reconstructed_inventory"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
