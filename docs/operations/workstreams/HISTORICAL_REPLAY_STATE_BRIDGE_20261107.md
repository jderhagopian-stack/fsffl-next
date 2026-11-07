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

Focused historical contract [42333621463](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42333621463), pinned archive [42333621726](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42333621726), general CI [42333621507](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42333621507), and PR164 [42333621455](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42333621455) passed on executable head `d46b25b48d3a38c1e86314bb64ad9ff08b98b038`. Stable full suite [42334001651](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42334001651) passed on exact ready head `d8cb66050aaa5533c0ad10588c8a91efc53ee420`, with before/after head checks. PR #514 merged as `6f27c9443392f91757a5ee4c1ef6b86abfd5b8f1`.
