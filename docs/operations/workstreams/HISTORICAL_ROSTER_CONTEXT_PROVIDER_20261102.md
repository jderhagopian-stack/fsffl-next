# Historical roster-context provider

## Goal

Build shared backend history infrastructure that reconstructs roster membership at completed event-time boundaries from retained later rosters and completed event ledgers. The October 1, 2023 transaction is a mixed-asset validation fixture, not the model target.

The provider must work from each season's original league identity and settings. Team count, scoring, roster slots, waiver rules, and event clocks are inputs, never FSFFL constants. Provider-specific adapters map source records into one stable historical roster-context contract so other leagues and future season years can use the same reconstruction semantics.

This output is retrospective roster context. It does not claim that a retained final roster was available at the historical cutoff. Exact lineup, taxi, reserve, and IR placements stay unknown if the source does not establish them. Missing chronology or contradictions remain visible; supported membership facts are not silently discarded because an unrelated slot detail is absent. The provider is not canonical point-in-time `LeagueState`, Forecast, Value, Decision, or a grade.

## Current implementation

`src/fsffl/state/historical_roster_context.py` adds `reconstruct_sleeper_roster_context()`:

- consumes one archived Sleeper season record, its immutable source revision, season rules, end rosters, completed transactions, and retained traded-pick rows;
- walks backward from the end-roster anchor and emits before/after snapshots for each completion-time batch, treating equal timestamps as one boundary;
- fingerprints each season's scoring, roster settings, slots, and observed team count;
- returns player membership, traded-pick membership only where the archive has ledger rows, and conditionally reconstructed waiver usage;
- leaves roster-slot placement unknown and permanently marks the output ineligible for a PIT Decision grade;
- reports `membership_status` separately from pick-ledger and FAAB issue codes, so uncertain FAAB does not erase otherwise supported roster-membership context.

The existing `retrospective_sleeper_replay.py` remains useful as the focused acceptance witness for one trade. The exact `historical_materializer.py` remains a separate transformation for a supplied canonical State with complete transition evidence.

## Validation and limitations

- Added `tests/test_historical_roster_context.py` for varying team counts, season/rule changes, event-boundary membership, conditional FAAB, traded-pick scope, and missing event time.
- Local manual checks passed for a synthetic mixed-asset season, 4- and 12-team settings, changed season scoring/rule fingerprint, and missing-time incomplete status. `compileall` and `git diff --check` passed.
- Focused `pytest` could not run in this environment because pytest is not installed; offline package resolution found no cached pytest wheel. Do not report the tests as passed until CI executes them.
- The pinned 2022–2026 archive run exercised the new provider. It found the known 2023 player-ownership history gap and conditional FAAB usage underflow in 2022 and 2024; those FAAB amounts remain unknown at affected boundaries, while membership context stays usable where its own chronology is consistent.
- The selected trade replay's prior pinned-source acceptance did not validate this new path; the new season-wide workflow is the required evidence for it.
- Current adapter consumes Sleeper-shaped season archives. The snapshot model is shared, but another provider still needs its own normalization adapter.
- Ownership is membership-only. Player position/age, full pick universe, verified point-in-time FAAB balances, and roster placement are not created by this function.

## Next actions

1. Discover a second real league/source with a different configuration and documented source semantics; keep acquisition read-only until provenance and rights are clear.
2. Map exact cutoff availability for canonical State, Forecast, and Market evidence. A retained later archive is retrospective and cannot stand in for historical availability.
3. Use existing State, evidence-receipt, and materializer owners to construct one bounded historical cutoff only after required facts and roster crosswalks are proven.
4. Connect supported history to backend analysis while keeping ex-ante decision evidence and realized outcomes separate.

No production database write, migration, deployment, or app/UI work is part of this slice.

## 2026-11-03 — merged and source discovery checkpoint

PR [#504](https://github.com/jderhagopian-stack/fsffl-next/pull/504) merged to `main` as `3a2497e994deb1ef1bcb194da4903240670d85e2` from exact tested head `52c2ec72391d3cda495a36fa8f59d1bf2718cd0a`.

Exact-head regular CI [41568385233](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41568385233), pinned archive workflow [41568385277](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41568385277), PR164 focused regression [41568385235](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41568385235), and Stable full suite [41568504932](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/41568504932) passed. The full suite reported **2,618 passed, 5 skipped**, and verified the PR head before and after.

The pinned legacy archive covers five linked seasons, 2022–2026, from one 12-team league family. It contains season-specific settings and retrospective transaction/end-roster evidence. The long-range provider tests show membership context provisionally consistent in 2022, 2024–2026 and incomplete in 2023 due to the known missing post-event player movement; FAAB remains uncertain at affected 2022 and 2024 boundaries. This is not a contemporaneous State archive and does not establish historical Forecast/Market availability. No raw league payload was added to NEXT.

The next program action is to identify a second real source/league setup and map admissible point-in-time evidence before any canonical State materialization. No historical Decision grade, persistence integration, production write, or app work has been accepted from this merge.
