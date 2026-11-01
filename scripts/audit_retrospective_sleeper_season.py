"""Read-only sanitized season-wide historical audit; does not publish or persist source.

The caller supplies a local original source with independently pinned Git blob SHA.
It emits counts and public-safe reason codes, never league, roster or player data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha1
import json
from pathlib import Path

from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season


def main() -> int:
    p = argparse.ArgumentParser(description="Audit original historical source ledger (offline only)")
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--git-blob-sha", required=True)
    p.add_argument("--season", type=int, required=True)
    args = p.parse_args()
    raw = args.archive.read_bytes()
    got = sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if got != args.git_blob_sha:
        raise SystemExit("archived source Git object mismatch; stopped")
    matches = [x for x in json.loads(raw) if int(x["league"]["season"]) == args.season]
    if len(matches) != 1:
        raise SystemExit("expected exactly one historical season in archive")
    audit = audit_retrospective_sleeper_season(matches[0], source_revision=f"git-blob:{got}")
    issues = Counter(x.code for x in audit.issues)
    print(json.dumps({
        "season": audit.season, "status": audit.status, "completed_events": audit.completed_events_examined,
        "completed_trades": audit.completed_trades_examined, "team_count": audit.team_count,
        "player_ledger_movements": audit.player_movements_examined,
        "pick_ledger_movements": audit.pick_movements_examined,
        "faab_trade_movements": audit.faab_transfers_examined,
        "waiver_bids": audit.waiver_bids_examined,
        "completion_timestamp_tie_groups": audit.completed_timestamp_tie_groups,
        "issue_counts": dict(sorted(issues.items())),
        "source_provides_contemporaneous_state": audit.source_provides_contemporaneous_state,
        "historically_validated_faab_balances": audit.historically_validated_faab_balances,
        "eligible_for_pit_decision_grade": audit.eligible_for_pit_decision_grade,
    }, sort_keys=True))
    return 0 if audit.status == "retrospective_ledger_consistent" else 2


if __name__ == "__main__":
    raise SystemExit(main())
