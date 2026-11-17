# Owner preference research: validation and readiness

The existing context-controlled methods are reusable, but the available history
is not sufficient to promote reliable owner preferences into live trade search.
Continue using the completed-trade observations already live. Do not replace
missing historical context with today's roster or infer acceptance odds.

## What was validated

The audit used repository main `86a3883f4a1a0c23f30b543b03f662a46095f413`
and aggregate, read-only queries over the existing league-family history. The
football/history cutoff was **2026-11-14 22:05:29.887921 UTC**. No production
records, provider rules, scoring, forecasts, values, simulations or plans changed.
No historical NFL calculation was run.

Original authorities remain:

- [PR #37](https://github.com/jderhagopian-stack/fsffl-next/pull/37), merge
  `eefdc266eaedaaee994bc41386505ec542547df5`: full-roster multiclass context
  expectation, excluding the focal owner and same-time/future actions.
- [PR #38](https://github.com/jderhagopian-stack/fsffl-next/pull/38), merge
  `fad1f426a8c6ded78d34620525f08d7dda177d33`: eventwise historical residuals,
  comparing observed/expected acquisitions over the same covered events.
- Existing coverage, shrinkage, stability and Decision evidence contracts remain
  intact. No new coefficient, reference anchor or production policy was selected.

## Actual coverage

These counts describe **owner-side records**, not distinct transactions. Two
owners in one completed trade usually produce two records; some trades have more.

| Season | Owner-side completed trades | With a strictly earlier snapshot |
| --- | ---: | ---: |
| 2022 | 28 | 0 |
| 2023 | 97 | 0 |
| 2024 | 52 | 0 |
| 2025 | 68 | 0 |
| 2026 | 74 | 26 |
| Total | 319 | 26 |

The target league has 425 stored State snapshots, all from the 2026 season,
starting September 10. A second league has 54 snapshots; it is not a substitute
for this league's missing historical rosters or owner mapping.

Additional checks:

- 176 of 319 records include a recorded QB/RB/WR/TE acquisition. The positional
  model cannot train on a pick-only trade as if it acquired a position.
- The 26 covered records use eight prior snapshots. Snapshot ages range from
  about 25 minutes to 6 days 13 hours.
- Nine covered records have intervening recorded activity by the same owner.
- Sixteen have intervening recorded activity somewhere in the league. Other
  owners' changes can also invalidate league-average roster features.
- Two describe a player being disposed who was not on that owner's snapshot
  roster. Both fall within the intervening-activity group. None of the covered
  records have missing team mappings, incoming players already owned in that
  snapshot, or a snapshot persisted after the trade.
- Ten covered records have no known intervening league activity. Seven include
  a positioned acquisition, across seven owners: **one record per owner**.
- Only four of those seven have at least two distinct earlier other owners in
  that restricted sample. This is an upper bound on prediction support, not four
  verified predictions; identity, outcome completeness, neighborhood and policy
  checks can reduce it further.

The seven records are candidates for further validation, not certified complete
pre-trade contexts. Unrecorded IR/taxi moves and other missing evidence remain
possible. Absence of a recorded change is not proof of complete continuity.

## What the model does and does not control

The existing v2 model uses roster counts relative to the league, active roster
counts, mandatory position requirements, FLEX/Superflex capacity, total roster
size and owned-pick counts. Its shared neighborhood captures cross-position
substitution. Strictly earlier other-owner examples and eligible-population
feature scaling protect against important forms of look-ahead leakage.

It does **not** presently consume historical optimized positional strength,
player quality, age mix, playoff outlook, championship probability or competitive
timeline. The context's active count excludes recorded IR/taxi slots; it is not
an independent forecast of NFL availability. Therefore a position residual cannot
be described as an owner preference after controlling for all roster needs and
competitive circumstances.

The generic historical dataset can include waiver/free-agent acquisitions. That
is appropriate for some research questions, but a trade-discovery consumer must
use trade-only outcomes. Other transaction kinds still matter when checking
whether the roster context has become stale.

The inspected production runtime has no validated policy binding for these
context/residual models. Neighbor count, shrinkage and owner-support policy
constructors found in tests are test fixtures, not empirically promoted settings.
An empty artifact-name search alone was not used to infer a missing methodology.

## Durable input safeguard

`behavioral/trade_context_dataset.py` adds an **offline, trade-only adapter** to
existing context and outcome extraction. It preserves native rows for valid
inputs and reports coverage failures for:

- known recorded activity between snapshot and trade;
- disposed players absent from that roster or acquired players already owned;
- unresolved player identities, conflicting historical positions, or missing
  acquisition positions that would otherwise distort a partial outcome;
- absent/non-pre-action snapshots and missing mappings.

It uses one injected-store lookup per trade, indexes known event times, and does
not fetch, write, fit a model or run football calculations. Supply all known
completed transaction kinds, not just trades. Provider aliases require an
explicit identity mapping when they differ from canonical IDs. This adapter does
not certify pick/FAAB ownership or unrecorded roster-slot continuity.

The adapter is not wired into live requests. Existing general research entry
points and all live observed-history behavior remain unchanged.

## Evidence limits

Existing model and new input-guard tests demonstrate structural behavior on
controlled fixtures. Real-history findings above come from aggregate SQL checks;
there was no raw-row production backtest, parameter selection, measured predictive
accuracy or preference promotion. Automatic approval review rejected exporting
raw private snapshots. The audit continued with aggregate-only checks; no raw
snapshots were exported. Aggregate evidence already establishes why promotion
would be premature.

## Efficient next sequence

1. Reconcile known transaction changes from trustworthy snapshots and validate
   ownership continuity. Record exactly which context fields are reconstructed,
   observed or still unknown; do not assume historical IR/taxi placement.
2. Assess older-season coverage using existing historical source records and
   defensible anchors. Completed transactions can support ownership accounting;
   they do not manufacture missing roster-slot history or point-in-time forecasts.
3. Add competitive/quality context only from genuine matching historical model
   outputs where available. Keep counts-only context distinct when it is absent.
4. Validate a versioned policy using chronological tests, other-owner training,
   grouped transactions, pooled baselines, coverage and genuinely new observations
   across time. Multiple cumulative profiles from the same one trade are not
   independent evidence of stability. Preserve format/scoring distinctions.
5. Publish supported preference evidence once through the existing owner/model
   infrastructure; let Decision/Search read it cheaply. Preserve manual goals,
   protections, economic evaluation and unfamiliar package exploration. Do not
   translate relative completed-choice tendencies into rejection or acceptance odds.

No new preference weights or automatic owner-priority changes should be deployed
on the present evidence. This is a data/context readiness finding, not a finding
that the existing Intrinsic economics or live completed-trade history is wrong.
