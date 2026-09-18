# FSFFL NEXT - Multi-Year Production Consistency Experiment Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: one final bounded pre-holdout test  
Status: **EXPERIMENT COMPLETE - MANAGEMENT TRADEOFF - STOPPED BEFORE FINAL HOLDOUT**

## 1. Recovered authority boundary

- Research branch: `research/future-state-resolution-phase34-resume`.
- Durable remaining-information-gap audit checkpoint recovered first.
- Live experiment start head: `00863c9cd968d5f80f96cc5979cb32fc7bdfc411`.
- `main` at experiment start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at experiment start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- No final-holdout row was evaluated.
- No named current player was used.
- M2, M3a, M3b, role/security research, M4/M5, implementation, promotion, merge, and deployment remained out of scope.

## 2. Frozen candidate executed

Baseline: fixed routed Forecast + frozen M1a continuous within-state magnitude.

The one authorized consistency candidate used exactly:

- `prior2_mean_age_state_z = mean(z[t-1], z[t-2])`;
- `prior2_abs_gap_age_state_z = abs(z[t-1] - z[t-2])`;
- explicit `prior2_coverage`;
- missing continuous values fixed at neutral zero;
- regularized global effects plus position deviations only;
- conditional-production adjustment only;
- persistence and future-state probabilities unchanged.

No third prior season, hard tier, repeated-elite threshold, current residual, trajectory term, age/stage interaction, role/security feature, or named-player adjustment was introduced.

Implementation detail: the candidate fit is `BayesianRidge(fit_intercept=False)` on target within-state residual-z minus the already-frozen M1a residual-z prediction. Mean/gap values are standardized from covered training rows at each historical cutoff only. Position sensitivity is represented only through regularized mean/gap interaction deviations for QB/RB/WR/TE.

## 3. Support

| Horizon | QB | RB | WR | TE | Total prior-two coverage |
|---|---:|---:|---:|---:|---:|
| Y2 | 88/153 | 194/344 | 249/461 | 147/251 | 678/1,209 = 56.1% |
| Y3 | 79/145 | 179/330 | 225/442 | 138/248 | 621/1,165 = 53.3% |

Rows without two genuine prior seasons are unchanged from M1a by construction.

## 4. Primary validation result

| Metric | Routed + M1a | Consistency candidate | Delta | 95% paired clustered interval |
|---|---:|---:|---:|---:|
| Y2 overall MAE | 31.021 | 30.849 | -0.172 | [-0.419, +0.038] |
| Y3 overall MAE | 30.652 | 30.512 | -0.140 | [-0.339, +0.033] |
| Y2 active-only MAE | 37.215 | 36.876 | -0.339 | [-0.746, +0.007] |
| Y3 active-only MAE | 41.348 | 41.066 | -0.281 | [-0.678, +0.052] |

All four chronological source-season point estimates improved:

- Y2 source 2020: -0.135 MAE.
- Y2 source 2021: -0.207.
- Y3 source 2019: -0.108.
- Y3 source 2020: -0.171.

However, the primary clustered 95% intervals for aggregate Y2 and Y3 MAE both cross zero.

## 5. Position results

| Horizon | QB delta | RB delta | WR delta | TE delta |
|---|---:|---:|---:|---:|
| Y2 MAE | -0.739 | -0.047 | **-0.142** | -0.052 |
| Y3 MAE | -0.820 | +0.009 | -0.065 | -0.075 |

The Y2 WR interval is clearly beneficial: [-0.257, -0.021]. Other position intervals cross zero. The fitted prior-two mean effect is largest and most stable for QB, but QB forecast-error uncertainty remains wide enough that this experiment does not establish a clean QB-only advancement rule.

## 6. High-end production cohorts

### >90th percentile

- Y2 MAE: 56.447 -> 55.535, delta -0.912, CI [-2.639, +0.632].
- Y2 bias: -11.619 -> -8.937, change **+2.682**, CI **[+1.197, +4.432]**.
- Y3 MAE: 64.735 -> 64.050, delta -0.685, CI [-2.117, +0.526].
- Y3 bias: -21.345 -> -19.832, change **+1.513**, CI **[+0.132, +3.429]**.

### >95th percentile

- Y2 MAE: 62.753 -> 60.087, delta **-2.666**, CI **[-5.405, -0.550]**.
- Y2 bias: -32.690 -> -29.574, change **+3.116**, CI **[+0.990, +5.822]**.
- Y3 MAE: 68.692 -> 67.479, delta -1.213, CI [-3.531, +0.390].
- Y3 bias: -43.063 -> -41.106, change **+1.956**, CI **[+0.533, +4.111]**.

The strongest replicated benefit is reduced high-end underforecast bias. Y2 extreme-upper MAE also improves clearly.

## 7. Lower-tail stress cohorts

- Y2 non-persistence: +0.075 MAE, CI [-0.055, +0.243].
- Y3 non-persistence: +0.001, CI [-0.096, +0.110].
- Y2 realized role-loss: +0.079, CI [-0.700, +1.004].
- Y3 realized role-loss: -0.052, CI [-0.900, +0.717].

No stress interval establishes clear harm or clear benefit. The experiment therefore does not trigger the directive's lower-tail rejection rule.

## 8. Covered versus uncovered rows

- Y2 covered rows: 678; MAE delta -0.306, CI [-0.708, +0.066].
- Y3 covered rows: 621; MAE delta -0.263, CI [-0.620, +0.060].
- Uncovered rows: exactly zero forecast change by construction.

## 9. Fitted-effect interpretation

Across the four official validation cutoffs, effective standardized prior-two **mean-level** slopes were approximately:

- QB: +0.264 to +0.283 residual-z;
- RB: -0.011 to +0.042;
- WR: +0.065 to +0.108;
- TE: +0.072 to +0.098.

The absolute-gap effect was smaller and generally positive rather than negative. Thus the empirical signal is better described as **multi-year production level / track record** than as evidence that lower production volatility itself is beneficial.

This interpretation does not alter the frozen candidate and no feature was dropped after results were seen.

## 10. Era and regularization sensitivity

Development-era active residual-z diagnostic:

- Y2 2016-2019: aggregate delta -0.0034; all 4/4 source seasons improve.
- Y3 2015-2018: aggregate delta -0.0045; 3/4 improve; the lone regression is +0.0005.

Regularization sensitivity using fixed penalties at 0.5x, 1x, 2x and 4x the Bayesian posterior-mean effective penalty:

- Y2 MAE deltas remain between -0.173 and -0.157.
- Y3 remain between -0.147 and -0.112.
- >90th bias correction remains positive at both horizons under every tested penalty.

The qualitative pattern is not a fragile single-penalty artifact.

## 11. Management classification

**MANAGEMENT TRADEOFF - DO NOT AUTOMATICALLY ADVANCE.**

Why:

1. Aggregate accuracy improves numerically at Y2 and Y3 and in every chronological validation source season, but the primary clustered 95% intervals for overall MAE still include zero.
2. High-end underforecast bias improves clearly and repeatedly at >90th and >95th production cohorts.
3. Y2 >95th MAE also improves clearly.
4. No clear non-persistence or realized role-loss harm is established.
5. The directive explicitly maps near-neutral aggregate evidence plus clear high-end bias improvement without lower-tail harm to **MANAGEMENT TRADEOFF**, not automatic advancement.

The experiment therefore provides real evidence that prior multi-year production level contains some incremental information, but it does not independently clear the predeclared bar for automatic promotion to the final exam.

## 12. Persisted evidence and reproducibility

Machine-readable result:

`artifacts/research/production_resolution/MULTI_YEAR_CONSISTENCY_EXPERIMENT_2026-09-18.json`

Local full validation row audit:

- 2,374 rows.
- SHA-256: `04ac0f236784492c4af06ca684edec66a5d318b44110a1ce50c28c083ebfd96e`.
- Not manually sharded through GitHub.

Input hashes:

- directive PDF: `a48bb07d17ba4b501bb21f72f0b36f39924609d99c464d242fc87fbd77fe86b4`;
- corrected Phase 2 Q3 rows: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`;
- clean Stage 3 validation audit: `22ba1638fb7e86146ad228c6d803c9ff1693d19f9dd36744bdefe0de37204767`;
- local deterministic result JSON: `3f08a6d4806dfbc1c3c4947cdf354c14b3b720a17b57e9c928dc63bcb87f51bf`.

Deterministic recomputation:

1. Use only Y2 source 2020-2021 and Y3 source 2019-2020 validation rows.
2. Training transitions must satisfy `source_season + horizon <= evaluation_source_season`, positive current/target state, and finite current/target residual-z.
3. Refit frozen M1a at each historical cutoff exactly as Stage 2: Bayesian ridge of target residual-z on current residual-z.
4. Build t-1/t-2 age/state residual mean and absolute gap from residuals normalized at their own PIT cutoffs.
5. Learn training-only mean/SD transforms on covered rows; missing values remain zero with coverage=0.
6. Fit the frozen global + position-deviation Bayesian ridge to residual target-z after M1a.
7. Apply only to positive-state conditional means using the frozen Stage 2 state-SD fallback hierarchy; probabilities remain untouched.
8. Evaluate paired error with 5,000 two-way source-season/player cluster bootstrap replicates for primary comparisons and 2,000 for stress cohorts.
9. Do not evaluate Y2 sources 2022-2023 or Y3 sources 2021-2022 without new authorization.

## 13. Stop boundary

**STOP.** The authorized experiment is complete and durably checkpointed. Do not consume the final holdout, run current-player sentinels, open role/security research, test another feature family, run M4/M5, implement, promote, merge, or deploy without a new explicit management authorization.
