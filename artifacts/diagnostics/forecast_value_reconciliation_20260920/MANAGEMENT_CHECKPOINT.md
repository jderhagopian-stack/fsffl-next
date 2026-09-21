# Forecast / Value authority reconciliation — management checkpoint

Date: 2026-09-20

## Exact repository state before this checkpoint commit

- protected `main`: `085bc6c21b3422b579d2d7b826906726d2ad35c2` (merged PR #161)
- PR #162 branch: `correctness/forecast-value-authority-reconciliation-20260920`
- validated implementation/audit head before final documentation: `7b16506e03234e8cfc6aa49272b88b6316940aad`
- PR #162: open, draft, mergeable, not merged
- CI run `35542514502`: PASS — 1,294 tests, 2 warnings
- League real-roster value-lens audit `35542514540`: PASS
- Cardinal Value Research `35542514495`: PASS

## Private beta

The private beta is still LIVE at `511977b05a76229739946e56adf209ef6ca174ac` (PR #159 deploy `dep-dao1nclg1s2s739440e0`).

Therefore neither merged PR #161 nor draft PR #162 is deployed to the private beta. Do not claim the live app is corrected.

## Directive completion status

### A. Razzball numerical source sanity — COMPLETE

The actual live Razzball page is malformed/inflated before FSFFL ingestion. Representative examples:
- Josh Allen: 7,682 pass yards / 47.9 pass TD / 1,134 rush yards / 21.9 rush TD;
- Puka Nacua: 223 receptions / 2,926 receiving yards / 17 receiving TD;
- Jahmyr Gibbs: 2,665 rush yards / 119 receptions.

FSFFL parser -> current snapshot -> normalized Forecast preserves those values exactly. The current display inherits the inflation because the hosted run had only FFToday + Razzball available.

No arbitrary divisor, clipping, provider down-weight, or model tuning was applied.

One deterministic robustness defect was fixed: duplicate same-provider player/metric/horizon observations now fail closed before the equal-weight ensemble can grant extra weight.

Frozen Sep-10 preseason/P0 authority was not rewritten because the retained artifacts do not preserve the individual historical Razzball rows needed to prove the current Sep-20 provider corruption existed at capture time.

### B. Cardinal / Broad Market / Intrinsic provenance — COMPLETE

Cardinal classification: **B — market/reference/compatibility coordinate.**

FSFFL Cardinal Value is:
- Stats Guy-backed market-cardinal magnitude;
- additive as Cardinal accounting within one coherent context;
- not Broad Market;
- not FSFFL Intrinsic;
- not League Market Value;
- not Team Utility;
- not a universal master value.

Current Cardinal research was re-run successfully. The latest empirical workflow remained consistent with the durable classification.

### C. Full live ranking/value authority ledger — COMPLETE

Every requested live surface/API has been mapped. Generic `FSFFL Value` / `Franchise value` aliases encountered for Cardinal were corrected to explicit Cardinal language.

### D. Player comparison contract — COMPLETE

The merged `/api/league/value-lenses` contract was tested on the real 12-team Sleeper league:
- 244 rostered player rows;
- 220 comparable Market + Shapley rows;
- HTTP 200;
- independent unavailability verified both directions;
- no Cardinal substitution;
- no team value;
- no League Market Value;
- no Team Utility;
- no recommendation/acceptance authority.

Non-Atlas surface placement is now explicitly defined in `VALUE_LENS_SURFACE_PLACEMENT.md`.

### E. Team/franchise semantics — COMPLETE, with management semantics decision remaining

The additive Cardinal franchise portfolio is canonically legitimate **only as explicitly named Cardinal market-cardinal accounting**. It is not competitive strength or universal franchise worth.

No summed Broad Market percentile, summed Intrinsic percentile, League Market Value, replacement universal team-value coordinate, or new Team Utility score was created.

### F. Corrective implementation — COMPLETE to authorized boundary

Implemented:
- numerical Razzball regression/sanity coverage;
- duplicate same-provider observation fail-closed protection;
- explicit Cardinal/Market labels across touched beta surfaces;
- stale generic value aliases corrected;
- legacy Intrinsic presentation explicitly disambiguated;
- regression coverage for authority labels/contracts.

Not implemented:
- provider-value correction for upstream Razzball corruption;
- frozen P0 rewrite;
- Shapley math changes;
- a silent Franchise migration from legacy Intrinsic v1 to Shapley.

### Legacy Intrinsic hard stop

The legacy Franchise `intrinsic-v1` coordinate is replacement-adjusted weighted surplus above lineup replacement.

Current Shapley Intrinsic is a permutation/deployment-attribution coordinate with different horizon economics.

Migration is **not semantic/parity-safe wiring**.

Per management's hard-stop rule, PR #162 does not migrate the Franchise endpoint. Management must choose whether to:
1. retire legacy Intrinsic presentation and redesign Franchise around Shapley semantics; or
2. retain both coordinates under distinct names/questions.

### G. League Atlas hold / future contract — COMPLETE and HELD

The reconciled Atlas contract is:
`Broad Market | FSFFL Intrinsic (Shapley) | Difference`

at player/distribution level.

Forecast-backed position strength, Simulation outcomes, and fragility remain separate governed layers. Cardinal is optional only as explicitly named market-cardinal/accounting context.

The full League Atlas must remain on hold until management reviews this checkpoint.

## Required stop

A directive hard-stop condition was reached: Shapley migration changes economic meaning rather than presentation wiring.

Stop for management.

Do not merge PR #162, rewrite frozen P0, migrate the Franchise Intrinsic endpoint, create a new team-value coordinate, or resume full League Atlas implementation without management direction.
