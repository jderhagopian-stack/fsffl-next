# Provider-neutral replay to canonical roster State — 2026-11-07

## Purpose

Connect the normalized historical replay contract to the existing fail-closed whole-roster State materializer. This closes the gap between reconstructing provider-neutral player/pick ledgers and producing an immutable canonical roster `LeagueState` from independently evidenced facts.

## Implemented in PR #514

- `materialize_historical_roster_state()` accepts either the established Sleeper retrospective context or a provider-neutral `HistoricalRosterReplay` and its `RosterMembershipSnapshot`.
- A small internal view normalizes both input shapes so one validation and State-construction path is used.
- Normalized replay membership issues block materialization. Pick replay conflicts and an incomplete pick-universe declaration also block it.
- The provider-neutral model now retains membership, pick, and budget-usage issue scopes separately, so a valid membership snapshot is not mislabeled because of an unrelated ledger discrepancy.
- Existing evidence requirements remain active: canonical owner/player identities, roster placement receipts at the requested cutoff, settings and roster receipts, direct FAAB balance evidence, and a complete pick-universe receipt. No slot, canonical identity, FAAB balance, or unlisted pick is inferred.
- Synthetic coverage proves a fully evidenced generic replay can produce `LeagueState` and that an incomplete pick universe returns blockers. A second private league is not required.

## Boundary

The output is retrospective roster State only and permanently ineligible for a PIT Decision grade. It does not create scoring/lineup history, projections, Market, Value, Decision, or an operational grade. Sleeper source history remains evidence only for that provider league. Other providers need their own audited normalizers and evidence receipts.

For the retained 2023 archive, this bridge does not itself supply missing placement receipts or complete pick-universe evidence. The State builder will continue to return explicit blockers until those are independently available. Cumulative waiver usage is tracked as a separate ledger fact; a direct, cutoff-specific FAAB balance receipt is still required to materialize State.

## Validation

Focused historical contract, pinned 2022–2026 archive, general CI, and PR164 checks are passing on code head `d46b25b48d3a38c1e86314bb64ad9ff08b98b038`. The checkpoint documentation update and Stable full-suite validation are pending. Results will be added to `docs/operations/CURRENT_OPERATIONS.md`.
