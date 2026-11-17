# Cross-season pick lineage and trade-context coverage

This offline integration composes accepted season lineage, pick inventory and
roster replay. It does not change valuations, fit a preference model or construct
a competing historical State.

## Identity and joins

`state/historical_pick_lineage.py` consumes registered `HistoricalSeasonSource`
objects and normalized season inventories. An explicit native roster binding
maps each local roster to a canonical franchise. Different yearly roster numbers
can join when those bindings agree; equal raw numbers or manager names alone do
not create continuity. Franchise identity is separate from manager tenure.

Each original right is identified by family, draft year, round and canonical
original franchise. Allotments and use bounds are reconciled; conflicting complete
allotments, owners or disjoint lifecycle dates fail rather than overwrite evidence.
An explicit event namespace distinguishes global provider IDs from season-local
IDs. Matching duplicate event receipts merge once; contradictory receipts fail.

Joining partial source scans does not certify a complete transfer ledger. Different
observation cutoffs do not extrapolate complete ownership from an older source.
Supported terminal use for every enumerated one-use right can establish use
coverage independently of incomplete ownership or issuance history. The admitted
source objects and their contents remain part of the inventory identity.

## Source integration

`providers/sleeper_historical_context.py` accepts already collected archive records,
admitted lineage/crosswalks and explicitly identified rookie drafts. It validates
provider identity, recorded season owners and source hashes. It builds each native
roster history once, projects evidenced allotments through the explicit crosswalk,
normalizes completed transfers and draft uses with existing adapters, then joins.

Existing supplemental player-movement receipts can be supplied to the native
roster replay. The original provider audit remains separate and unchanged. The
adapter does not invent a supplemental receipt from a source discrepancy.

No API acquisition, database operation, cache family, worker, forecast computation
or web-request work is introduced. Tests require one native history construction
per input season. Coverage processing retains only the last queried pick snapshot
while scanning sorted cutoffs, rather than one full inventory per trade date.

## Per-trade coverage

`state/historical_trade_context_coverage.py` indexes native pre-completion snapshots
and reads joined pick facts. It deduplicates exact repeated transaction requests
by season/transaction, rejecting conflicting repeats. Each row preserves both
creation and completion times; a completion snapshot is never silently relabeled
as creation-time decision context. Wrong source fingerprints, family or crosswalk
bindings cannot populate a row from unrelated evidence.

Rows distinguish snapshot availability, source-content matching, provisionally
consistent player membership, recorded season owner mapping, complete pick-count
coverage, known used rights and conditional outstanding rights. The current
archive contract has no historical position catalog or active slot placement;
those gaps remain explicit. No zero-valued feature vectors or missing forecasts
are manufactured. The output is not an admitted full v2 model dataset or a PIT
Decision grade.

Pick-count coverage also requires an explicit manifest of required draft seasons.
Completeness for the known 2023–2026 cohorts cannot stand in for every future
right available to a franchise at an arbitrary date.

## Actual pinned-source measurement

On source Git blob `e18c01bf25f58c5dfe3d0802f53de484ea257ca1`,
[run 44021685016](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/44021685016)
at initial executable head `32279ee9acdf11a1605c7d6c65ba9f865937a018` passed
125 focused contracts and five non-skipped archive cases. The integration uses
an **explicitly declared retrospective fixture franchise crosswalk**, not an
independently certified at-time identity map or a generic matching algorithm.

| Season | Distinct trades | Pre-completion snapshots | Archive-only consistent membership |
| --- | ---: | ---: | ---: |
| 2022 | 14 | 14 | 14 |
| 2023 | 48 | 48 | 0 |
| 2024 | 26 | 26 | 26 |
| 2025 | 34 | 34 | 34 |
| 2026 | 22 | 22 | 22 |
| Total | 144 | 144 | 96 |

The join contains 144 original rookie rights, 200 pick movements across 98
transactions, and 144 terminal selections; its end-of-replay pick issue list is
empty. Source fingerprints and recorded season owner mappings are present for
all 144 trade rows. Creation and completion clocks differ on all 144; none of
these trade boundaries shares its completion batch with another retained event.

The 2023 membership gap is the original known missing departure. Existing
supplement-aware replay remains supported, but no supplemental receipt was
silently supplied to this archive-only baseline. It is not evidence that 2023
is irrecoverable or that accepted supplemental handling is absent.

Complete pick counts and full archived v2 model inputs are currently available
for zero of these rows: original issuance/required-year coverage, complete
ownership admission and active/position evidence are separate requirements.
That is **not a zero count for all project evidence**. The saved-State route and
its earlier seven candidates remain separate, and overlap must be reconciled
before reporting a combined sample. Neither the 144 selections nor the 144
trade rows should be added to the newer owner-side counts.

## Next integration boundary

Carry the existing supported supplemental receipt into the 2023 replay with its
original provenance. Inventory historical position/slot and dated pick-allotment
evidence, distinguish supported features from unknowns, and reconcile the separate
saved-State/Behavioral route with both clocks preserved. Then validate the accepted
context method's input policy and chronological, grouped-transaction performance
before enabling stronger owner preferences. No missing rejected offers or
acceptance probabilities are inferred from completed-trade history.
