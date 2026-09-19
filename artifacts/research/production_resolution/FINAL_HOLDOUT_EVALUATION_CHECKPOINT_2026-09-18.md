# FSFFL NEXT - Final Holdout Evaluation Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: one-time evaluation of the frozen Forecast candidate  
Status: **FINAL HOLDOUT CONSUMED ONCE - FROZEN CANDIDATE SURVIVED FINAL EXAM - STOPPED FOR MANAGEMENT REVIEW**

## 1. Authority and frozen candidate

- Research branch start head: `c337df306c5c6f5f4c484e633dd73455923b27d0`.
- Durable multi-year consistency checkpoint recovered before evaluation.
- `main` at task start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at task start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- Frozen baseline: fixed routed Forecast + M1a.
- Frozen selected candidate: fixed routed Forecast + M1a + the exact two-prior-season consistency adjustment.
- Routing remained QB -> A2+C+D; RB/WR/TE -> A2+D.
- M1b, M2, M3a, M3b, role/security, third-prior-season, hard-tier, new-interaction and named-player mechanisms remained excluded.
- Persistence and future-state probabilities were frozen.
- No post-holdout tuning or candidate switching occurred.
- No current-player sentinel was run.

## 2. Pre-holdout reconstruction lock

Before holdout outcomes were evaluated, the execution path was reconstructed against the already-persisted validation outputs.

Maximum validation reconstruction differences:
- probability: `5.05e-09`;
- state mean: `4.31e-06` points;
- M1a adjustment z: `5.01e-09`;
- consistency adjustment z: `4.99e-13`;
- M1a anticipated points: `4.97e-06`;
- selected-candidate anticipated points: `4.98e-06`.

The newly required source-2023 H2 source-state reconstruction code path was parity-checked against persisted source-2022 data:
- 596 matched rows;
- max current residual-z difference `8.88e-16`;
- zero source-state mismatches;
- zero target-state mismatches;
- source points, prior points, state percentile and target points matched exactly.

The candidate/code path was therefore locked before the final holdout was opened.

## 3. Final holdout consumed

| Horizon | Source seasons | Target seasons | Rows |
|---|---|---|---:|
| Y2 | 2022, 2023 | 2024, 2025 | 1,154 |
| Y3 | 2021, 2022 | 2024, 2025 | 1,210 |
| **Total** | | | **2,364** |

The final holdout is now permanently consumed and must not be treated as pristine development evidence in future work.

## 4. Overall final-holdout result

| Metric | Routed + M1a | Selected candidate | Delta MAE | Paired clustered 95% interval |
|---|---:|---:|---:|---:|
| Y2 overall MAE | 32.342 | **32.054** | **-0.288** | [-0.603, +0.013] |
| Y3 overall MAE | 29.419 | **29.262** | **-0.157** | [-0.416, +0.062] |
| Y2 active-only MAE | 39.483 | **38.992** | **-0.491** | [-1.040, +0.011] |
| Y3 active-only MAE | 41.141 | **40.784** | **-0.357** | [-0.908, +0.109] |

Negative MAE deltas favor the selected candidate.

Overall intervals cross zero, so the final holdout is not described as a broad statistical victory. However, all point estimates improve and the chronological replication remains directionally stable.

## 5. Chronological replication

All four final-holdout source seasons improved:

- Y2 source 2022: 32.109 -> 31.757, delta **-0.352**.
- Y2 source 2023: 32.590 -> 32.371, delta **-0.219**.
- Y3 source 2021: 28.977 -> 28.844, delta **-0.132**.
- Y3 source 2022: 29.874 -> 29.691, delta **-0.182**.

No chronological reversal occurred.

## 6. Position results

| H | Position | Baseline MAE | Candidate MAE | Delta | 95% interval |
|---:|---|---:|---:|---:|---:|
| Y2 | QB | 62.509 | **60.950** | -1.559 | [-3.815, +0.449] |
| Y2 | RB | 37.750 | 37.749 | -0.001 | [-0.093, +0.093] |
| Y2 | WR | 25.871 | **25.746** | -0.125 | [-0.302, +0.043] |
| Y2 | TE | 17.431 | **17.277** | -0.155 | [-0.479, +0.126] |
| Y3 | QB | 61.710 | **60.741** | -0.969 | [-3.005, +0.803] |
| Y3 | RB | 32.070 | 32.100 | +0.030 | [-0.004, +0.060] |
| Y3 | WR | 23.504 | **23.440** | -0.064 | [-0.146, +0.010] |
| Y3 | TE | 16.917 | **16.828** | -0.089 | [-0.214, +0.021] |

There is no material position-specific failure. Y3 RB is slightly worse by 0.03 MAE and remains statistically near zero.

## 7. High-end result

### >90th percentile production cohort

- Y2 MAE: 60.012 -> **57.658**, delta **-2.354**, CI **[-4.684, -0.491]**.
- Y2 bias: -20.976 -> **-18.075**, improvement **+2.901**, CI **[+1.130, +5.181]**.
- Y3 MAE: 59.101 -> 57.936, delta -1.165, CI [-3.315, +0.406].
- Y3 bias: -26.001 -> **-24.170**, improvement **+1.831**, CI **[+0.273, +3.870]**.

### >95th percentile production cohort

- Y2 MAE: 66.752 -> **62.950**, delta **-3.802**, CI **[-8.221, -0.598]**.
- Y2 bias: -27.007 -> **-22.121**, improvement **+4.886**, CI **[+1.596, +9.158]**.
- Y3 MAE: 62.952 -> **60.120**, delta **-2.831**, CI **[-6.980, -0.201]**.
- Y3 bias: -32.032 -> **-28.796**, improvement **+3.236**, CI **[+0.591, +7.222]**.

The preselected high-end correction clearly survives the final holdout. Extreme-upper MAE and underforecast bias improve at both horizons.

## 8. Lower-tail and role-loss stress

- Y2 non-persistence: +0.045 MAE, CI [-0.096, +0.240].
- Y3 non-persistence: +0.026, CI [-0.076, +0.125].
- Y2 realized role-loss: +0.080, CI [-0.554, +0.898].
- Y3 realized role-loss: -0.047, CI [-0.598, +0.298].

No stress cohort shows a material new failure. The intervals all span zero.

## 9. Prior-two coverage

- Y2: 693/1,154 = **60.1%** covered; covered-row MAE delta -0.479, CI [-1.027, +0.026].
- Y3: 712/1,210 = **58.8%** covered; covered-row delta -0.267, CI [-0.723, +0.111].
- Missing prior-two rows are exactly unchanged from M1a by construction.

## 10. Calibration and systematic bias

The consistency candidate changes conditional production means only. Persistence and six-state probabilities are identical to routed + M1a.

Routed probability calibration on the final holdout:
- Y2 persistence Brier 0.17494; persistence log loss 0.52081; state Brier 0.64653; state log loss 1.35265.
- Y3 persistence Brier 0.17993; persistence log loss 0.53574; state Brier 0.56114; state log loss 1.19997.

Overall point bias becomes modestly more positive:
- Y2: +0.283 -> +0.790;
- Y3: +0.919 -> +1.279.

That small broad shift is accompanied by a materially reduced high-end underforecast and does not create a meaningful broad error increase.

## 11. Interpretation

**FINAL-HOLDOUT CLASSIFICATION: SURVIVED FINAL EXAM.**

The selected candidate is directionally stable overall, improves every final-holdout source-season point estimate, preserves and strengthens the preselected high-end correction, and introduces no material new lower-tail, position or calibration failure.

Because the overall clustered intervals still cross zero, this should not be presented as a universal statistical victory. The stronger conclusion is the one predeclared by management: the frozen historical candidate survived the final exam.

The only next research action permitted by the directive is a separately management-authorized current-player sentinel. No sentinel was run here.

## 12. Persistence / hashes

Machine-readable repository result:
`artifacts/research/production_resolution/FINAL_HOLDOUT_EVALUATION_2026-09-18.json`

Local full row audit:
- rows: 2,364;
- CSV SHA-256: `2df09a5388c363fe913da9eeae6eb46bad84931157a9e13f34ceede284ae9a89`;
- deterministic gzip SHA-256: `f0ae43de2b304f6d35e8296d01ef1387715ffe88579b801f81086cae19fd6992`;
- local JSON SHA-256: `4263807553eacf0a48b5aa1f0032f6c84bd845411ab920e16a8a9719688f1553`.

Key inputs:
- directive PDF: `528d7d8e809c911eebe0c4c9fee20f0f6c741fd68fcecee996f4408052325789`;
- Phase 2 corrected Q3 rows: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`;
- Phase 2 player-season panel: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`;
- frozen consistency experiment result: `3f08a6d4806dfbc1c3c4947cdf354c14b3b720a17b57e9c928dc63bcb87f51bf`;
- frozen validation row audit: `04ac0f236784492c4af06ca684edec66a5d318b44110a1ce50c28c083ebfd96e`.

The approximately 973 KB row audit was not manually sharded through GitHub. Deterministic hashes, full metrics, fitting metadata and recomputation instructions are persisted instead.

## 13. Stop boundary

**STOP.** The one-time final holdout has been consumed and checkpointed. Do not tune from it. Do not run current-player sentinels, implementation, promotion, merge or deployment in this task.
