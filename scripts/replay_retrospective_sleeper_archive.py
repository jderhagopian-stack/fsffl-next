"""Offline-only, sanitized archival replay probe. Never publishes or stores inputs.

Usage: python scripts/replay_retrospective_sleeper_archive.py --archive <path> \
  --git-blob-sha <pinned blob sha1> --season <year> --transaction <id>

Input archive must be obtained separately under source rights/security controls;
public CI must never commit, cache or upload private historical source payloads.
"""
from __future__ import annotations

import argparse
from hashlib import sha1
import json
from pathlib import Path

from fsffl.state.retrospective_sleeper_replay import replay_archived_sleeper_trade


def main() -> int:
    p = argparse.ArgumentParser(description="Offline factual historical replay (sanitized stdout)")
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--git-blob-sha", required=True)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--transaction", required=True)
    args = p.parse_args()
    content = args.archive.read_bytes()
    git_digest = sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    if git_digest != args.git_blob_sha:
        raise SystemExit("source bytes do not match pinned Git blob; no replay attempted")
    records = json.loads(content)
    season_records = [item for item in records if int(item["league"]["season"]) == args.season]
    if len(season_records) != 1:
        raise SystemExit("archive must identify exactly one matching historical season")
    result = replay_archived_sleeper_trade(
        season_records[0], transaction_id=args.transaction,
        source_revision=f"git-blob:{git_digest}",
    )
    # Never log team, roster, owner, transaction, player, pick identities, raw
    # season payload, source contents, or manager behavior to public CI output.
    print(json.dumps({
        "status": result.status,
        "season": result.season,
        "observed_team_count": result.observed_team_count,
        "later_completed_events_reversed": result.future_completed_events_reversed,
        "player_transfers": sum(t.asset_kind == "player" for t in result.transfers),
        "pick_transfers": sum(t.asset_kind == "pick" for t in result.transfers),
        "faab_budget_rows": len(result.faab),
        "issue_codes": result.issues,
        "historical_anchor_independently_verified": result.historical_anchor_independently_verified,
        "eligible_for_pit_decision_grade": result.eligible_for_pit_decision_grade,
    }, sort_keys=True))
    return 0 if result.status == "provisionally_consistent" else 2


if __name__ == "__main__":
    raise SystemExit(main())
