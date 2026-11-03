# Provider-neutral historical roster replay — 2026-11-03

## Management direction

Build the historical snapshot backend for repeated use across future seasons, providers, and leagues. A second private league is unavailable and is not a prerequisite. Validate variable structures with deterministic synthetic configurations and keep the pinned 2022–2026 source as factual evidence for its own league only.

## Implemented in this slice

- Added `src/fsffl/state/historical_roster_replay.py`, a provider-neutral immutable contract for normalized completed player transfers, a retained end-roster anchor, deterministic history/snapshot identities, atomic reverse batches, `state_at()`, and unambiguous `pre_transaction_state()`.
- Same-time events are one atomic boundary. If they touch the same player or contradict the retained anchor, the batch is not partially reversed and the issue is returned. The replay does not invent event ordering.
- The Sleeper history adapter now maps provider adds/drops to the shared transfer primitive. It continues to use the provider completion clock, and its pick/FAAB accounting, source audit, and supplemental-evidence handling remain explicitly scoped to the Sleeper archive.
- Added synthetic 2/4/8/12/16/18-team coverage, alternate rule-fingerprint identity, free-agent movement, same-time ambiguity, and conflicting-anchor regressions.
- Added the shared contract to focused CI and the pinned 2023 archive workflow. That archive workflow also exercises the Sleeper adapter across all retained 2022–2026 seasons without committing source payloads.

## Authority and limitations

This is a retrospective player-membership replay primitive. It is not canonical point-in-time `LeagueState`, and is permanently ineligible for a PIT Decision grade. It does not infer positions, lineup/bench/taxi/IR placement, scoring semantics, historical source availability, complete pick universes, FAAB balances, Forecast, Market, Value, or Decision evidence. A rules fingerprint is carried for stable identity; it does not mean every league rule is interpreted by this membership engine.

The Sleeper adapter is the only provider adapter exercised against a real archived source. Another provider can use the normalized contract without requiring another real league fixture, but it still needs a separately governed normalizer and source provenance. No database writes, migrations, deployment, or app/UI work are included.

## Validation gate

The exact PR head must pass the focused historical contract workflow and pinned-archive workflow. After review is complete, mark that stable head ready and require the exact-head Stable full suite before merge. Record the exact SHA and all results in `CURRENT_OPERATIONS.md` after the gate.
