# 2023 supplemental ownership evidence — Deneric Prince (November 1, 2026)

**Scope:** backend historical research only. The user's screenshot corrects the interpretation of one archived ownership anomaly. It does not change the pinned source, establish an exact transaction timestamp, authorize a point-in-time grade, or involve the separate October 1 trade.

## Evidence

A user-provided player-history screenshot received November 1, 2026 displays:

- Deneric Prince: added from waivers for $3, dated July 20, 2023.
- Deneric Prince: dropped to waivers, dated August 23, 2023.

The screenshot is a retrospective UI record. Its displayed dates have day-level precision only; it provides no event time or proof the screenshot/source was available in 2023. The image is not copied into this repository. Its SHA-256 evidence fingerprint is `0613107bc386ccc01c877962a1d5be1232812a24f7db17ad7706ca0c2dc80c05`.

## Reconciliation boundary

The pinned legacy archive's completed waiver row has `created` on July 20 and `status_updated` on July 27. The UI displays July 20 for the addition. Those fields have not been shown to share date semantics, so do not rewrite either timestamp or claim exact-time agreement.

The August 23 drop supports the missing later ownership departure in the supplemental replay. The pinned archive-only season audit must continue to report its original `post_event_player_missing` issue unchanged. A supplemental-evidence replay may separately report the observation; it must not silently patch the archive or mark the original provider ledger complete.

Deneric Prince was **not part of the October 1, 2023 trade**. The August waiver drop and the October trade are separate events. The screenshot does not establish any trade relationship.

## Backend contract added on this branch

`src/fsffl/state/historical_supplemental_evidence.py` defines immutable provider-neutral receipts and player-movement facts. It carries evidence source, fingerprint, received/source-availability times, date precision, and a fixed retrospective-only scope. Date-only facts cannot carry an exact event time. The contract does not store raw screenshots, mutate provider history, perform replay, or authorize PIT Decision grades.

The first implementation now includes a fail-closed reconciliation function. It matches provider, season, source player ID, source roster ID, and event ordering; nonmatching evidence remains unresolved, while same-day or multiple distinct later drops are marked ambiguous. The result embeds the original provider audit unchanged and is always ineligible for a PIT grade. It does not yet create canonical State or write to persistence.

## Supplement-aware roster replay implementation candidate (November 3, 2026)

`reconstruct_sleeper_roster_context()` now accepts optional supplemental movements. It first audits the original provider archive, reconciles the movements, and applies only a unique, supported, date-only drop after reversing all provider transactions on that UTC date. Source events touching the same player on that date make the finding ambiguous; the adapter fails closed. Snapshots on the movement's date carry `uncertain_player_ids`, and snapshots earlier than the drop carry the evidence IDs that support the corrected membership. Exact-time supplemental replay remains explicitly unsupported by this date-boundary adapter and is reported ambiguous rather than rounded or reordered.

The output is model version `historical-roster-context-v2`. It separately exposes the original `provider_audit` and unchanged `provider_audit_status`, the `supplemental_reconciliation`, replay status, and applied evidence IDs. The archive hash/source revision are unchanged. The raw source audit can remain incomplete while a separate retrospective membership replay is repaired; the result remains ineligible for a PIT Decision grade. This does not create canonical `LeagueState`, player Value, historical Forecast/Market inputs, or historical availability proof.

**Local validation:** 22 focused roster/supplement tests passed; all 3 pinned 2022–2026 archive tests passed. An additional sanitized integration check against the pinned legacy archive verified the 2023 source hash, preserved incomplete provider audit, supported supplemental reconciliation, corrected before/after membership around the archived addition, and PIT ineligibility. No player/manager identifiers or source payload were logged or added to NEXT. Exact-head CI and Stable full-suite acceptance are pending on the implementation PR. No database write, migration, deployment, or app/UI change occurred.

## Next backend gate

After exact-head CI and Stable full-suite acceptance, identify a second real league/source with distinct settings and defensible source semantics. Keep acquisition read-only until identity, timestamps, and rights are understood. Then proceed to bounded canonical State materialization only when taxi/reserve/IR, initial FAAB, source completeness, and historical rules can be represented without inference. No app/UI work, production database writes, migration, deployment, or new service is in scope.
