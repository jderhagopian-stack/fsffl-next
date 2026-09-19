# Routed Forecast Final Resolution — post-Stage-0 final checkpoint

Date: 2026-09-18  
Authority: research only  
Final management outcome: **A — ROUTING SUPPORTED**

## 1. Continuation boundary

Stage 0 recovery/parity was treated as complete and was not rerun.

The post-recovery study began from:
- research branch head: `9f110204229ac2bcef0644cd7591f4e697aaba0c`
- compact recovered coordinate: 4,287 rows
- coordinate SHA-256: `8095788e1b48028c50b65d7fba51ac48a41daceeaa6459ae3a219723ce30b1eb`
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open/unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

No Forecast model was rerun or refit.

## 2. Frozen source-time career state

Frozen before candidate-by-state performance inspection:

- developmental: NFL experience 0–3
- established: experience 4–8
- veteran: experience 9+

This uses only information available at the forecast cutoff. Position remains a separate dimension. The labels do not assume future ascent or decline.

Support floor: at least 20 observations in every required fold for that candidate/horizon.

Chronological folds:
- early: source seasons 2014–2016
- mid: 2017–2018
- validation: 2019–2020

## 3. Frozen routing specification

Default everywhere: **B2a**.

Exceptions:
- QB / established / Y2 -> **R2**
- QB / established / Y3 -> **R2**
- QB / veteran / Y2 -> **R2**

Explicit defaults:
- QB / developmental / Y2 and Y3 -> B2a
- QB / veteran / Y3 -> B2a because mid/validation support is below the frozen 20-row floor (18 / 14)
- RB / WR / TE, every career state and both horizons -> B2a

Machine-readable specification is persisted separately in `FROZEN_ROUTING_SPEC.json`.

## 4. Why these routes survive

### QB established, Y2
R2 MAE gain versus B2a:
- early +6.84 (n=43)
- mid +0.48 (n=30)
- validation +12.09 (n=34)

### QB established, Y3
- early +5.57 (n=33)
- mid +1.62 (n=29)
- validation +4.65 (n=29)

### QB veteran, Y2
- early +22.50 (n=40)
- mid +27.24 (n=23)
- validation +15.41 (n=21)

Positive gain means lower MAE than B2a.

R2 also beats R1 on the combined selected-cell evidence:
- established Y2: +1.162 MAE, paired 95% interval [+0.497, +1.820]
- established Y3: +0.660, [+0.199, +1.133]
- veteran Y2: +1.632, [+0.851, +2.448]

H2 is not selected. Although H2 is useful in some mid/validation cells, its incremental advantage over R2 is not stably separated from zero on the selected states and it lacks an early-fold evaluation by construction. R2 therefore wins the frozen complexity tie-break.

## 5. Why developmental QB stays B2a

R2 versus B2a for developmental QBs:

Y2:
- early -7.93
- mid -6.07
- validation -10.64

Y3:
- early -1.23
- mid -10.49
- validation -15.26

The sign is wrong in every fold. A QB-wide route would hide this damage because gains among established/veteran QBs dominate the position average.

This is the central reason position x broad career-state routing is justified rather than position-only routing.

## 6. Universal B2a versus frozen route

All 4,287 pre-holdout active observations:

| Metric | Universal B2a | Frozen route | Change |
|---|---:|---:|---:|
| MAE | 41.7557 | **41.0709** | **-0.6847** |
| Total absolute error | 179,006.6 | **176,071.2** | **-2,935.4** |
| Mean signed error | -15.4315 | **-13.2574** | 2.1741 closer to zero |
| Underprediction rate | 51.83% | **51.15%** | -0.68 pp |

Overall MAE improves 1.64%.

Paired row-resampling summary for universal B2a -> frozen route:
- mean MAE gain: +0.6847
- 95% interval: [+0.3586, +1.0175]
- 20,000 deterministic resamples

The three routed cells contain 282 / 4,287 observations (6.58% of the population). Within those rows:
- B2a MAE 83.55
- R2 MAE 73.14
- improvement 10.41 MAE
- B2a bias -59.00 -> R2 -25.95

## 7. Y2 / Y3 and chronological stability

Y2:
- B2a MAE 41.0893
- frozen route 40.0077
- improvement 1.0816

Y3:
- B2a 42.5842
- frozen route 42.3929
- improvement 0.1913

Every pre-holdout fold/horizon point estimate improves:

| Fold | Horizon | B2a | Frozen route | Gain |
|---|---:|---:|---:|---:|
| early | Y2 | 40.8601 | 39.6265 | +1.2336 |
| early | Y3 | 42.3612 | 42.1212 | +0.2399 |
| mid | Y2 | 43.8298 | 42.8659 | +0.9639 |
| mid | Y3 | 45.6442 | 45.5605 | +0.0836 |
| validation | Y2 | 38.9351 | 37.9461 | +0.9890 |
| validation | Y3 | 39.9275 | 39.6964 | +0.2311 |

No fold/horizon reversal occurs.

## 8. Complexity challenger

Full-chronology position-only challenger:
- route R2 to every QB at Y2; B2a elsewhere
- overall MAE 41.4020

Frozen position x career route:
- overall MAE 41.0709
- additional MAE gain over position-only: +0.3311
- paired 95% interval: [+0.0507, +0.6188]

The position-only route also worsens developmental-QB Y2 MAE from 75.50 to 83.86, while the frozen career-state route leaves developmental QBs exactly on B2a.

A position-only H2 sensitivity is evaluable only on mid/validation. On those common rows, the frozen state route is directionally better by 0.252 MAE, but the interval crosses zero; H2's missing early chronology and richer treatment prevent it from displacing the full-history state route.

## 9. Upper tail and developmental calibration

Common upper-tail evaluation cohort: B2 source-time percentile >= 90th percentile. This is an evaluation cohort only and is not a routing input.

Top-10% rows (n=479):
- B2a MAE 60.1136 -> frozen route 59.6726
- bias -5.3165 -> -5.2202

Developmental rows (experience 0–3; n=2,877):
- B2a MAE 39.9204
- frozen route 39.9204
- identical by construction

The route therefore preserves the protected young/developmental behavior rather than trading it away for older-QB gains.

## 10. Role-loss / deep-collapse stress

Role-loss rows (n=586):
- B2a MAE 34.7706
- frozen route 36.3230
- deterioration +1.5524
- share of total population AE: 11.38% -> 12.09%

Deep-collapse rows (n=295):
- B2a MAE 50.6173
- frozen route 53.7254
- deterioration +3.1081
- share of total population AE: 8.34% -> 9.00%

This cost is real and is not hidden.

However:
- the frozen route still lowers total population AE by 2,935.4;
- non-role-loss MAE improves 42.8617 -> 41.8227;
- non-deep-collapse MAE improves 41.1008 -> 40.1358;
- upper-tail accuracy improves;
- developmental accuracy is unchanged;
- broad signed bias moves materially toward zero;
- repository-governed role-loss research previously found that most of B's safety advantage over R2 was concentrated in severe realized collapses and could not establish source-time foreseeability;
- the bounded source-time role/security correction previously tested worsened broad replicated calibration and was rejected.

Under the governing rule that future collapse cannot determine route assignment retrospectively and role-loss is a stress test rather than an automatic veto, the collapse penalty does not erase the replicated broad gain or justify a hindsight carve-out.

## 11. Holdout disposition

No holdout was used to discover or select the route.

After the routing specification was frozen, the repository's final-holdout checkpoint was rechecked. It states that the one-time final holdout (target seasons 2024–2025) was already permanently consumed in an earlier frozen-candidate study. It therefore is not untouched evidence available to this routed study.

The 2021–2022 block is also already classified as non-pristine historical evidence and was not used to rescue this selection.

No current-player board was run.

## 12. Final management outcome

**A — ROUTING SUPPORTED.**

The evidence supports one compact exception architecture rather than universal B2a:

- preserve B2a everywhere by default;
- use R2 only for established QBs at Y2/Y3 and veteran QBs at Y2.

This is a research freeze only. It is not implementation or promotion authority.

## 13. Reproducibility / runtime

Reproducible metric evaluation runtime: **1.681452 seconds** on the chat Python runtime.

Local generated audit artifacts:
- candidate-by-position/career-state CSV SHA-256: `910c956323caec6c27f31d6aeb75c0162f314e5d59a86371fca77fd8ccba6060`
- route comparison CSV: `a33a88f7c5d59ef442e1f3520930a222fb5759d207fbc186e427958e9e239277`
- stress/calibration CSV: `8f2ba76a11501e7acb3737433bfb3dd6f01d234339d78070543432ada6f2d39d`
- candidate tie-break uncertainty CSV: `29c6118d6afe80a5782eb63ab02e9c20cdd56391eae21d6ff70b3e7a56733602`
- machine-readable local final result: `547d63d4249f6cd589b7569c0cff79ff8928f56ca574c12344f24adc6672001a`
- local frozen spec serialization: `bd3ecbcc081fd7072d1c70cd458eb13c564afea7076b477a6d42532aaf599999`

Execution accounting:
- Forecast model reruns: 0
- Forecast model refits: 0
- new Forecast candidates: 0
- holdout routing runs: 0
- current-player routing runs: 0
- main changes: 0
- PR #147 changes: 0
- Intrinsic/Shapley/Constitution/C=0.25 changes: 0

STOP after durable Outcome A and management report.
