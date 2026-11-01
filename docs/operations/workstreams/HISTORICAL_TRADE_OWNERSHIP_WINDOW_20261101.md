# Retrospective trade ownership window — 2026-11-01

**Accepted:** merged as PR #500, merge `28c2164d4bec1fd3ca7640ec6fdf5bf24e8af298`, from exact tested head `ba5aa4db8f160fecbecf0b50060d437207be6520`. Scope remains backend-only fact reconstruction for the selected October 1, 2023 completed trade.

## Change

The archived Sleeper replay now returns league-wide player ownership and ownership for pick records present in the retained traded-pick ledger at the reconstructed boundaries immediately before and after the selected trade. It retains conditional archived FAAB-used values only for the two trade participants. Nonparticipant FAAB is excluded from this scoped result.

The result is explicitly `retrospective_ownership_snapshot_only`. The archive does not enumerate the full universe of untraded picks, so those are outside the pick snapshot. Roster slot, starter, taxi, reserve, and IR placement at the trade cutoff remains unknown. The snapshot is not a canonical `LeagueState`, it does not authorize a historical grade, and archived FAAB remains conditional on the retained ledger.

## Why the isolated archive discrepancy does not block this transition

The transferred 2025 third-round pick is present in the retained ledger. The unrelated $3 FAAB usage delta belongs to a nonparticipant roster; this implementation omits nonparticipant FAAB rather than treating that discrepancy as resolved. The Deneric Prince screenshot separately supports the missing later player departure in the season-wide audit. It remains supplemental retrospective evidence, and the original provider audit is unchanged.

## Evidence boundary

The source remains the pinned, retrospectively retained 2023 league archive (legacy Git blob `e18c01bf25f58c5dfe3d0802f53de484ea257ca1`, commit `1179d3104cbe3330cf27e4173d61df95f2494b1a`). Raw bytes and player/manager payloads are not copied into this repository or printed by the workflow.

## Acceptance

Synthetic regressions passed across varied team counts. Pinned-source historical replay run 41347254052, ordinary CI run 41347254086, and Stable full suite run 41347339803 passed on the exact PR head; Stable passed 2,608 tests with 4 skipped. The pinned archive ran ephemerally without raw asset identities in logs. No database writes, migration, Render deployment, or app change.
