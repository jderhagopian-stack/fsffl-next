# Provider-neutral historical ledger replay — 2026-11-07

## Goal and scope

Continue the backend historical-snapshot capability so it can be reused across seasons, leagues, providers, team counts, and rule configurations. A second private league is not required; synthetic profiles exercise structural variation, while the pinned Sleeper archive remains evidence only for its own league. This increment is retrospective and backend-only.

## Implemented in PR #513

- `historical_roster_replay.py` now accepts normalized player transfers, draft-pick transfers, and signed changes to cumulative budget usage.
- Snapshot rows carry pick owners, per-roster budget-usage values (including explicit unknowns), and independent flags for complete pick universe and complete budget usage. Both completeness declarations default to false.
- Same-time player and pick changes are reversed atomically. Duplicate pick movements, conflicting anchors, unknown roster references, unknown budget anchors, and out-of-bounds reversal are explicit issues; the replay does not invent ordering or balances.
- The Sleeper adapter routes player, pick, waiver-budget transfer, and waiver-bid reversal through shared provider-neutral operations while retaining its source-specific parsing and evidence labels.
- Fixed a false duplicate-player check: event participants who remain on end-anchor rosters are valid; duplicate ownership is evaluated among anchor rosters, while event-only player IDs are still included in free-agent snapshots.
- Synthetic tests cover a pick transfer, waiver usage reversal, incomplete pick inventory, complete usage coverage, an unknown usage anchor, and a contradictory pick anchor.

## What this establishes

The shared replay can now reconstruct normalized membership, recorded pick ownership, and cumulative budget usage when the adapter supplies those facts. League rules remain identity metadata; the replay does not interpret roster slots, scoring, acquisition/lineup eligibility, or point-in-time source availability. A list of traded picks is not a complete pick universe. Conditional archive FAAB usage is not automatically a certified balance.

## Next backend step

Build the adapter-neutral bridge from reconstructed, evidenced season snapshots into the canonical whole-roster State materializer. Its input contract must include historical roster placements and slot semantics, a full pick universe with receipts, FAAB balance evidence, season/rule identity, and source availability at the requested cutoff. Where the retained archive lacks one of those facts, the bridge should produce concrete blockers and a coverage report rather than silently promote the replay to canonical State. Use synthetic league profiles for generalization and the pinned Sleeper history for adapter regression; no second private league is a gate.

No database writes, migrations, deployment, or app/UI changes are included.

## Validation

All executable changes passed focused contract validation, pinned archive validation, general CI, PR164 regression, and the Stable full suite on code head `1a0b83e81a7c5df594859284a9c6e7afba694291`. The docs-only checkpoint update is being revalidated by Stable before merge. The exact run IDs are recorded in `docs/operations/CURRENT_OPERATIONS.md`.
