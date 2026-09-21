# Forecast / Value authority reconciliation — FINAL CLOSEOUT

Date: 2026-09-20

## Green management checkpoint recovered

- protected `main`: `085bc6c21b3422b579d2d7b826906726d2ad35c2`
- PR #162 branch: `correctness/forecast-value-authority-reconciliation-20260920`
- green directive-complete head recovered: `2edf3b4097e5e3d7be40156f6a83a976a4cb4949`
- PR #162 state at recovery: open, draft, mergeable, not merged
- CI `35542705522`: PASS
- League value-lens real-roster audit `35542705573`: PASS
- Cardinal Value Research `35542705508`: PASS

## Directive status

The substantive Forecast/Value reconciliation directive is **COMPLETE TO THE AUTHORIZED BOUNDARY**.

No incomplete implementation step remains before management review.

### Completed

1. **Numerical Razzball audit**
   - live Razzball values were inspected numerically, not just by source id;
   - the current provider page itself is materially inflated/malformed before FSFFL ingestion;
   - parser -> current snapshot -> normalized Forecast preserves those numbers exactly;
   - no arbitrary divide-by-two, clipping, provider down-weight, or model tuning was introduced;
   - duplicate same-provider player/metric/horizon observations now fail closed;
   - the frozen Sep-10 preseason/P0 baseline was not rewritten because historical individual provider rows are not durably retained.

2. **Cardinal provenance / authority**
   - final classification: **B — market/reference/compatibility coordinate**;
   - Stats Guy-backed FSFFL Cardinal Value remains a governed market-cardinal magnitude/accounting coordinate;
   - it is explicitly not Broad Market, FSFFL Intrinsic, League Market Value, Team Utility, or a universal master value;
   - ambiguous generic `FSFFL Value` / `Franchise value` aliases encountered by the reconciliation were corrected to explicit Cardinal language.

3. **Full live ranking/value authority ledger**
   - requested player, team, League, Market, Trade, Simulation, Home, Owner, and API authorities are mapped;
   - each displayed rank/value/percentile now has an identified coordinate and owner;
   - Total Market Value remains intentionally unavailable because Broad Market percentiles are non-additive.

4. **Broad Market vs FSFFL Intrinsic**
   - real-roster audit passed on the 12-team league;
   - Broad Market and Shapley Intrinsic remain independently available;
   - comparison uses percentile/rank presentation only;
   - no raw-value subtraction;
   - no Cardinal substitution;
   - no team value;
   - no League Market Value;
   - no Team Utility;
   - no recommendation or acceptance-probability authority.

5. **League Atlas input contract**
   - held contract remains:
     `Broad Market | FSFFL Intrinsic (Shapley) | Difference`
   - player/distribution level only;
   - Forecast-backed position strength, Simulation outcomes, and fragility remain separate governed layers;
   - Cardinal may appear only as explicitly named market-cardinal/accounting context if management later chooses.

6. **Legacy Intrinsic reconciliation**
   - legacy `/api/value/intrinsic-v1` and Shapley Intrinsic are economically different coordinates;
   - replacement-adjusted surplus is not semantic/parity-equivalent to Shapley deployment attribution;
   - Franchise endpoint migration is therefore **not safe presentation wiring**.

## Hard stop reached

The only remaining issue is a **management product/economic-semantics decision**, not unfinished implementation.

Management must choose whether to:
1. retire legacy Intrinsic v1 from product presentation and redesign Franchise around Shapley semantics; or
2. retain both Intrinsic coordinates under distinct names/questions.

PR #162 must not choose that semantic policy implicitly.

## Required disposition

STOP.

Do not:
- merge PR #162 without management direction;
- rewrite frozen P0;
- repair upstream Razzball values with an invented transform;
- migrate the Franchise Intrinsic endpoint silently;
- create a new team-value coordinate;
- create League Market Value;
- feed these value lenses into Team Utility;
- resume the full League Atlas rollout.

This closeout records that the reconciliation itself is finished and ready for management review.
