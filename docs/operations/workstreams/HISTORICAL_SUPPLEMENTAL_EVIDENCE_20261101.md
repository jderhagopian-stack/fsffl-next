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

## Supplement-aware roster replay merged (November 3, 2026)

PR [#507](https://github.com/jderhagopian-stack/fsffl-next/pull/507) merged to `main` as squash `eec049c2498e68da6d159a6f31dbc237531bcc58`, from exact tested head `8dac87c1cd9293e51923113dbdf35dacbb046adf`.

`reconstruct_sleeper_roster_context()` accepts optional supplemental movements. It audits the original provider archive, reconciles the movement, and applies only a unique, supported, date-only drop after reversing provider events through the earliest plausible UTC date. With no timezone on the screenshot, snapshots on the stated date and either adjacent UTC date carry `uncertain_player_ids`; untimed or in-window same-player source events make the finding ambiguous. Exact-time supplemental replay is unsupported by this boundary model and is not rounded or reordered.

Output model `historical-roster-context-v3` separately exposes the original `provider_audit` and unchanged status, supplemental reconciliation, replay status, and applied evidence IDs. Each replay has a deterministic `history_id` bound to its source revision/hash, season-specific rule fingerprint, and model version. Each event-boundary snapshot has a deterministic `snapshot_id` bound to that history plus its boundary, roster/pick membership, uncertainty, and applied evidence that changed that snapshot. The replay also records a digest of all supplemental evidence inputs; unresolved or unrelated evidence therefore remains auditable without changing snapshot identity. Identical source facts produce repeatable keys; changes to source, rules, or reconstructed snapshot facts change the corresponding identity. These are identity keys only: no persistence or canonical PIT State is created. PIT Decision grade eligibility remains false. This is retrospective roster membership, not canonical `LeagueState`, historical Forecast/Market evidence, player Value, or proof of historical availability.

**Validation:** focused roster/supplement tests **24 passed**; pinned 2022–2026 archive tests **3 passed**; sanitized pinned-archive integration passed. Exact PR head `8dac87c1cd9293e51923113dbdf35dacbb046adf`: CI [41574190856](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41574190856), historical source ledger [41574190952](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41574190952), supplemental focused [41574190883](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41574190883), PR164 regression [41574190927](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41574190927), and Stable full suite [41574497863](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41574497863) all passed. Merged squash: `eec049c2498e68da6d159a6f31dbc237531bcc58`. No database write, migration, deployment, or app/UI change occurred.

## Next backend gate: no second private league required

Management has no second private historical league to provide. This is not a blocker and is no longer a prerequisite. Keep factual 2023 replay bounded to the one pinned league archive; do not make claims about a second real source or league.

Validate league/rule generality with deterministic parameterized synthetic profiles that vary team count, roster size, scoring, lineup slots, taxi/reserve/IR, and season-specific rules. Also reuse the two distinct 2026 rule signatures already observed in the current system for compatibility and fingerprinting checks only. Those current configurations do not supply 2023 history or point-in-time evidence.

Next, build bounded canonical-State construction around the available historical source and make every unsupported field an explicit blocker or unknown. Only materialize a historical cutoff when source completeness, event identity/order, roster placement, FAAB semantics, and required rules are evidenced. Do not infer missing values; preserve PIT-grade ineligibility until valid at-time Forecast/Market evidence is independently established. No app/UI work, production database writes, migration, deployment, second private league, or new service is in scope.
