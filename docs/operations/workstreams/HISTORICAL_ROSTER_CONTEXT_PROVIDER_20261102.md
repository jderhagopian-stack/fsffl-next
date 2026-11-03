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
- leaves roster-slot placement unknown, exposes source/completeness issues, and permanently marks the output ineligible for a PIT Decision grade.

The existing `retrospective_sleeper_replay.py` remains useful as the focused acceptance witness for one trade. The exact `historical_materializer.py` remains a separate transformation for a supplied canonical State with complete transition evidence.

## Validation and limitations

- Added `tests/test_historical_roster_context.py` for varying team counts, season/rule changes, event-boundary membership, conditional FAAB, traded-pick scope, and missing event time.
- Local manual checks passed for a synthetic mixed-asset season, 4- and 12-team settings, changed season scoring/rule fingerprint, and missing-time incomplete status. `compileall` and `git diff --check` passed.
- Focused `pytest` could not run in this environment because pytest is not installed; offline package resolution found no cached pytest wheel. Do not report the tests as passed until CI executes them.
- No real archive was run through the new season-wide provider yet. The selected trade replay's prior pinned-source acceptance does not validate this new path.
- Current adapter consumes Sleeper-shaped season archives. The snapshot model is shared, but another provider still needs its own normalization adapter.
- Ownership is membership-only. Player position/age, full pick universe, verified point-in-time FAAB balances, and roster placement are not created by this function.

## Next actions

1. Run the new focused test file in CI and fix any failures on the same branch.
2. Run the pinned 2022–2026 archive through the new provider in the sanitized workflow and report aggregate issue/snapshot counts only.
3. Check the varying season rules and known 2023 event gap across the retained five-year cohort. Synthetic cases vary team count; another verified league source is needed to prove real-world team-count variation.
4. Add provider adapters only where another source is available and its event semantics are understood.
5. Connect the resulting context to a governed historical analysis after available historical Forecast/Value evidence is mapped; keep ex-ante and realized-outcome lenses separate.

No production database write, migration, deployment, or app/UI work is part of this slice.
