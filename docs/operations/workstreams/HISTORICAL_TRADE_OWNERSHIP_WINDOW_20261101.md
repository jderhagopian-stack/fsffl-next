# Retrospective trade ownership window — 2026-11-01

**Scope:** backend-only fact reconstruction for the selected October 1, 2023 completed trade. This checkpoint is for branch `historical-trade-ownership-window-20261101`, based on main `fbb2ad5e789ad76b4b2fdaa5d4554f03d76ab8af`.

## Change

The archived Sleeper replay now returns complete league-wide player/pick ownership sets at the reconstructed boundaries immediately before and after the selected trade. It retains conditional archived FAAB-used values only for the two trade participants. Nonparticipant FAAB is excluded from this scoped result.

The result is explicitly `retrospective_ownership_snapshot_only`. Roster slot, starter, taxi, reserve, and IR placement at the trade cutoff remains unknown. The snapshot is not a canonical `LeagueState`, it does not authorize a historical grade, and archived FAAB remains conditional on the retained ledger.

## Why the isolated archive discrepancy does not block this transition

The selected trade is between provider rosters 2 and 7. The unrelated $3 FAAB usage delta belongs to a nonparticipant roster; this implementation omits nonparticipant FAAB rather than treating that discrepancy as resolved. The Deneric Prince screenshot separately supports the missing later player departure in the season-wide audit. It remains supplemental retrospective evidence, and the original provider audit is unchanged.

## Evidence boundary

The source remains the pinned, retrospectively retained 2023 league archive (legacy Git blob `e18c01bf25f58c5dfe3d0802f53de484ea257ca1`, commit `1179d3104cbe3330cf27e4173d61df95f2494b1a`). Raw bytes and player/manager payloads are not copied into this repository or printed by the workflow.

## Acceptance

Synthetic tests assert deterministic pre/post ownership, pick transfer, participant-only FAAB, and explicit unknown roster-slot coverage across varied team counts. The exact pinned-source workflow verifies the same ownership window without logging private asset identities. Focused CI and the stable full suite remain pending for this draft candidate. No database writes, migration, Render deployment, or app change.
