# Historical context reuse: players, picks and FAAB

## Finding and correction

Historical reconstruction is already implemented. The seven candidates in the
[saved-State audit](owner-context-validation-20261117.md) describe only that
snapshot route. They do not measure the broader archived replay route, and
cannot establish that total history is insufficient for owner-preference research.

Preserve both source paths and their distinct provenance. A retrospective
ownership fact can be useful without being a complete contemporaneous
`LeagueState` or eligible for an at-time Decision grade. Conversely, reconstructed
ownership alone does not supply active roster counts or historical forecasts.

## Existing components to reuse

| Component | Accepted behavior | Remaining boundary |
| --- | --- | --- |
| `state/historical_roster_context.py` — PR #504 | Season-specific before/after completed-event batches; player membership, traded-pick membership, conditional waiver usage; settings fingerprints | Not full pick inventory or historical slot placement |
| Same adapter — PRs #507/#509 | Supplemental movement receipts and date uncertainty; explicit league-family identity | Does not silently repair original source or infer owner continuity |
| `state/historical_roster_replay.py` — PRs #511/#513 | Provider-neutral atomic player/pick transfers and signed budget-usage reversal; separate issue scopes | Requires supplied anchors; no pick issuance or consumption event contract |
| `state/historical_roster_state.py` — PRs #510/#514 | One canonical State construction path for evidenced archive or generic replay snapshots | Requires identities, slot placements, direct FAAB balances and complete pick-universe evidence |
| `state/historical_materializer.py` | Applies an evidenced bilateral transaction to a supplied canonical State | A transition builder, not a season-history acquisition/reconstruction engine |
| `behavioral/action_context.py`, `context_dataset.py`, `historical_context_profile.py` | Saved-State event context and accepted eventwise residual research | Current input contract needs facts absent from membership-only archives |

Original authority includes PR #513 merge
`aede8bda785127f9bf492f4132724c412cb4d5ef` and PR #514 merge
`6f27c9443392f91757a5ee4c1ef6b86abfd5b8f1`. These are existing capabilities,
not proposals to create another historical State owner or inference model.

## Existing real-source evidence

The accepted archive tests pin legacy Git blob
`e18c01bf25f58c5dfe3d0802f53de484ea257ca1`, rather than using today's
provider response or inventing history. The archived 2026 portion is partial.

| Season | Completed transactions | Distinct completed trade rows |
| --- | ---: | ---: |
| 2022 | 246 | 14 |
| 2023 | 350 | 48 |
| 2024 | 358 | 26 |
| 2025 | 339 | 34 |
| 2026 | 107 | 22 |
| Total | 1,400 | 144 |

These are source rows, not owner-side training examples. They overlap the newer
319 owner-side records; neither summing the datasets nor treating 144 trades as
144 model-ready observations is valid. No joined/deduplicated research sample or
predictive backtest has been produced in this review.

Accepted [archive workflow 42333621726](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42333621726),
job `128285479362`, ran on executable head
`d46b25b48d3a38c1e86314bb64ad9ff08b98b038`: **92 focused tests passed**, then
**three non-skipped pinned-archive tests passed**. Its decoded logs were inspected
for this review; raw archive inputs were not exported or refetched.

Those tests establish provisionally consistent membership replay for 2022 and
2024–2026, not complete contemporaneous State. Original 2023 has one recorded
missing player departure. Existing supplemental handling preserves the original
audit and separately records the date-only evidence and uncertain boundaries.
Original 2023 source evidence includes **83 pick movements**, **24 FAAB transfers**,
and **82 completed waiver bids**. Conditional usage discrepancies in 2022/2024
do not automatically invalidate otherwise consistent membership.

The current replay/materializer contracts were also exercised locally at the
reviewed main tree: **95 tests passed in 0.80s**. These are controlled regression
tests, not a fresh run of the private archive or new empirical model validation.

## Picks: what is reconstructable and what needs completion

**Already implemented:** retain pick identity and reverse recorded ownership
transfers. The archived identity is `(draft season, round, original roster)`;
current owner is a separate changing fact. A pick's future slot/rank is not
required to establish its ownership.

**Not yet complete:** the archive adapter initializes from `traded_picks` and
labels its scope accordingly. That list does not enumerate untraded rights. The
generic replay can accept a complete inventory anchor, but its completeness flag
is a caller attestation, not a reconstruction algorithm. Its event contract has
transfers, not creation/use/expiry of draft rights.

The live Sleeper adapter in `providers/sleeper.py` generates the next three
seasons from current rules and then overlays ownership. Reusing that convention
at historical dates would not prove when those rights became available. Do not
copy it into historical research as evidence.

The smallest durable extension is an evidence-backed inventory/lifecycle adapter
feeding the existing shared replay:

1. Establish original allotments from that season's draft rules and roster
   identities, including documented extra/removed rights where applicable.
2. Carry explicit availability intervals or unknown date bounds. Do not use a
   platform's current future-year window as historical issuance proof.
3. Apply completed transfers to the same original pick identities; reconcile
   against independent inventory/draft evidence where available.
4. Record selections or other consumption from evidenced draft results. A used
   right must not remain tradable, and an undrafted right must not disappear just
   because the NFL season changed. Startup/auction/draft-type rules need their
   own evidence; do not assume every league uses ordinary rookie rounds.
5. Handle tied/uncertain clocks explicitly and report known ownership separately
   from whether the full inventory is covered. Do not assume archived draft
   metadata contains every selection or its timestamp without inspecting it.

This fills a source-normalization and lifecycle gap. It does not change pick
Intrinsic, reference anchors, market values, discounting or valuation methodology.

## FAAB, roster slots and model input readiness

The replay already reverses signed cumulative usage, including waiver bids and
recorded transfers. A cutoff balance additionally depends on original allocation,
reset dates, rebates/credits and source accounting semantics. Usage is not a
certified balance merely because subtraction produces a plausible number.

Unknown IR/taxi/bench placement must not erase separately supported ownership.
It also must not be silently filled with BENCH/active to satisfy a model schema.
Accepted v2 context uses active position counts, active roster size, league means
and total owned-pick count. Membership and traded-pick-only snapshots cannot
supply those exact inputs without additional evidence. Position/owner mappings
must also be historical, rather than inferred from current names or tenure.

Event clocks differ: the behavioral importer uses provider `created`; archive
replay uses `status_updated`. The earlier supplemental research already records
an actual creation/completion date difference. Joining must preserve both clocks
and source semantics, not attach a completion-boundary roster to a creation-time
decision by silently treating the timestamps as equal.

## Next execution order

1. Reconcile the existing archive and behavioral histories by provider transaction,
   season and roster identity; preserve source revisions, dual clocks, ownership
   scopes and unknown fields. Do not add owner-side counts to source-trade counts.
2. Inspect available draft/inventory source coverage, then implement the bounded
   inventory/lifecycle adapter above. Reuse atomic transfer primitives and the
   existing materializer; do not rewrite replay or relax canonical-State gates.
3. Produce per-field/event research coverage across both routes. Use supported
   ownership facts for factual research while checking the exact requirements of
   the accepted context model. Any alternate feature set needs explicit versioned
   validation, not hidden zeros or a competing universal framework.
4. Validate context-conditioned tendencies chronologically with grouped
   transactions, other-owner training, pooled comparisons and independent later
   observations. Counts alone do not establish persistent preference or effects
   controlled for competitive state.

No stronger owner weights, acceptance odds, production writes, historical NFL
recomputation or deployment are part of this review. Current completed-history
search and manual priorities remain unchanged. The missing rejected-offer data
will not be manufactured as negative examples.
