# FSFFL NEXT — Stage 2 M1a / M1b Production-Magnitude Resolution Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: Stage 2 — Production-Magnitude Resolution, management-approved bounded execution  
Status: **STAGE2_COMPLETE — STOPPED FOR MANAGEMENT REVIEW; NO M2/M3/M4/M5/SENTINELS/HOLDOUT**

## 1. Recovered authority boundary and parent state

- Research branch: `research/future-state-resolution-phase34-resume`.
- Durable Stage 1 checkpoint recovered from `artifacts/research/production_resolution/STAGE1_M0D_CHECKPOINT_2026-09-17.md`.
- Live Stage 2 start head: `075c40b540fc28a11fdb66d5719002749b4adae4`.
- `main` at Stage 2 start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at Stage 2 start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- No production Forecast/Intrinsic authority, Intrinsic Constitution, Shapley rule, global C, discount, lineup legality, `main`, or PR #147 was modified.
- No named current player was used. No final holdout row was scored.

## 2. Frozen Stage 2 design executed

### M1a — continuous magnitude

For each validation source season and horizon, fit a shared-by-horizon `BayesianRidge(fit_intercept=False)` using only historical rows whose target was already observable by that source cutoff. Response: target within-state residual z. Predictor: current within-state residual z.

The fitted residual-z adjustment changes only positive future-state conditional means:

`adjusted_mean(state) = max(0, baseline_mean(state) + predicted_resid_z * training_fold_state_SD(state))`

Baseline persistence and future-state probabilities are unchanged.

Fitted M1a residual-z coefficients:
- Y2 source 2020: n=4,533, training 2005–2018, coefficient 0.07348.
- Y2 source 2021: n=4,900, training 2005–2019, coefficient 0.07698.
- Y3 source 2019: n=3,058, training 2005–2016, coefficient 0.09226.
- Y3 source 2020: n=3,318, training 2005–2017, coefficient 0.07773.

### M1b — limited hard production resolution

Only current `premium` and `elite` states are eligible. Position/current-state q33 and q80 cut points are learned from prior source rows only. Low/middle/upper buckets are retained only when each retained bucket has at least 75 active training rows; otherwise the predeclared merge rule applies or the cell reverts to M1a. States below premium remain M0.

All six official-validation top-state buckets cleared the 75-row support rule at every cutoff; no official-validation bucket required merge/fallback. The strongest stable hard-tier signal is elite/upper: approximately 0.595–0.599 residual-z at Y2 and 0.377–0.382 at Y3. Premium hard-tier effects are generally near zero or slightly negative.

### Validation and uncertainty

- Y2 validation: source seasons 2020–2021 only.
- Y3 validation: source seasons 2019–2020 only.
- Final holdout was not evaluated: no Y2 2022–2023 and no Y3 2021–2022 scoring.
- Paired uncertainty: 5,000-replicate two-way cluster bootstrap over source season and player identity.
- Development-era stability: Y2 2016–2019 and Y3 2015–2018, diagnostic only.
- Sample-size sensitivity: candidate refit using the recent half of eligible training source seasons, diagnostic only.

## 3. Required direct comparison

| Metric / cohort | Baseline M0 | M1a | M1b | M1a Δ vs M0 | M1b Δ vs M0 |
|---|---:|---:|---:|---:|---:|
| Y2 MAE — overall | 31.175 | 31.021 | 30.930 | -0.154 | -0.245 |
| Y3 MAE — overall | 30.758 | 30.652 | 30.520 | -0.106 | -0.238 |
| Y2 MAE — QB | 65.118 | 64.774 | 64.736 | -0.344 | -0.382 |
| Y2 MAE — RB | 31.844 | 31.716 | 31.722 | -0.128 | -0.122 |
| Y2 MAE — WR | 26.764 | 26.622 | 26.362 | -0.143 | -0.402 |
| Y2 MAE — TE | 17.670 | 17.574 | 17.627 | -0.097 | -0.043 |
| Y3 MAE — QB | 59.123 | 59.025 | 58.900 | -0.097 | -0.223 |
| Y3 MAE — RB | 32.495 | 32.322 | 32.187 | -0.173 | -0.308 |
| Y3 MAE — WR | 27.103 | 27.025 | 26.878 | -0.078 | -0.225 |
| Y3 MAE — TE | 18.376 | 18.306 | 18.199 | -0.070 | -0.177 |
| >90th bias Y2 | -14.012 | -11.619 | -2.248 | +2.393 | +11.765 |
| >95th bias Y2 | -36.605 | -32.690 | -20.575 | +3.916 | +16.031 |
| >90th bias Y3 | -23.405 | -21.345 | -17.490 | +2.060 | +5.915 |
| >95th bias Y3 | -46.360 | -43.063 | -37.973 | +3.297 | +8.387 |
| Conditional-active MAE Y2 | 37.476 | 37.215 | 36.882 | -0.261 | -0.595 |
| Conditional-active MAE Y3 | 41.538 | 41.348 | 41.023 | -0.191 | -0.515 |
| State/persistence calibration | frozen M0 | unchanged | unchanged | identical | identical |

Negative MAE deltas are improvements.

## 4. Paired clustered uncertainty and chronological replication

- **Y2 overall:** M1a−M0 = -0.154, 95% CI [-0.282, -0.039]. M1b−M0 = -0.245, CI [-0.605, +0.114]. M1b−M1a = -0.091, CI [-0.384, +0.202].
- **Y3 overall:** M1a−M0 = -0.106, 95% CI [-0.212, -0.001]. M1b−M0 = -0.238, CI [-0.438, -0.042]. M1b−M1a = -0.132, CI [-0.263, -0.007].

Every official validation source season improved numerically:
- Y2_2020: M1a−M0 -0.193; M1b−M0 -0.286; M1b−M1a -0.092.
- Y2_2021: M1a−M0 -0.117; M1b−M0 -0.207; M1b−M1a -0.090.
- Y3_2019: M1a−M0 -0.084; M1b−M0 -0.213; M1b−M1a -0.129.
- Y3_2020: M1a−M0 -0.126; M1b−M0 -0.262; M1b−M1a -0.136.

## 5. High-end compression

- **Y2 >90th:** bias -14.01 → -11.62 → -2.25; MAE 57.49 → 56.45 → 54.88.
- **Y2 >95th:** bias -36.61 → -32.69 → -20.57; MAE 64.64 → 62.75 → 58.75.
- **Y3 >90th:** bias -23.40 → -21.34 → -17.49; MAE 65.41 → 64.74 → 63.63.
- **Y3 >95th:** bias -46.36 → -43.06 → -37.97; MAE 70.37 → 68.69 → 66.19.

M1a improves >95th MAE with beneficial clustered intervals at both horizons. M1b produces the larger >95th point correction; direct M1b-vs-M1a >95th improvement is statistically clear at Y3, but not Y2.

## 6. Stability and stress

- M1a coefficient is small, positive, and stable, preserving only a modest fraction of current within-state magnitude.
- Development-era diagnostics: M1a and M1b both lower aggregate MAE versus M0 in every reported development source season at both horizons.
- Sample-size sensitivity: M1a full-vs-recent-half MAE change = -0.007 Y2 / +0.029 Y3; M1b = -0.034 Y2 / +0.063 Y3.
- M1a clearly improves declining-cohort MAE at both horizons and is statistically near-neutral on non-persistence and realized role-loss.
- M1b does not clearly harm declining cohorts, but **clearly worsens Y2 non-persistence** (Δ +0.271, 95% CI [+0.080, +0.499]) and **Y2 realized role-loss** (Δ +0.876, CI [+0.240, +1.931]).

## 7. Management-matrix interpretation

**M1a = CLEAR_REPLICATED_VALIDATION_IMPROVEMENT.** Overall MAE improves with clustered 95% intervals excluding zero in the beneficial direction for both Y2 and Y3. High-end underforecast bias also improves. Because state/persistence probabilities are unchanged, the gain is isolated to conditional production. Continuous within-state magnitude is the leading general production-resolution mechanism from Stage 2.

**M1b = HORIZON_SPECIFIC_CLEAR_Y3__Y2_MANAGEMENT_TRADEOFF.** Direct M1b-vs-M1a aggregate improvement is statistically clear at Y3 but not Y2. Y2 high-end bias improves materially while aggregate uncertainty remains ambiguous, placing Y2 in the directive's MANAGEMENT TRADEOFF category. The clear Y2 lower-tail harm is a further caution. Limited hard resolution is therefore not established as a general replacement for M1a; it is a bounded Y3/extreme-upper signal for management consideration.

No later candidate or hybrid is authorized by this result.

## 8. Reproducibility, artifacts, and persistence limitation

Persisted standalone summaries:
- `artifacts/research/production_resolution/STAGE2_M1A_VALIDATION_2026-09-18.json`
- `artifacts/research/production_resolution/STAGE2_M1B_VALIDATION_2026-09-18.json`
- `artifacts/research/production_resolution/STAGE2_M1A_M1B_COMPARISON_SUMMARY_2026-09-18.json`

Local Stage 2 execution produced a 2,374-row validation audit with baseline probabilities/conditional means, M1a/M1b residual adjustments, adjusted per-state means, final forecasts, and realized outcomes.

Invariants:
- maximum baseline reconstruction error: `8.45e-08`;
- probability-sum max absolute error: `2.00e-10`;
- state/persistence probabilities unchanged;
- zero adjusted-mean floor events;
- zero state-order inversions;
- final holdout rows absent;
- named current players absent.

Hashes:
- Phase 2 input rows: `ce0f1369487a09f39057dce9eb4dfc804a8c06f041df5e2531880d1e1381534e`
- Stage 1 input waterfall: `eb6ffd6c2ad71aa7c4459e432cf78153432dcaa59a4d5b49bbec1b496ff560a3`
- Stage 2 runner: `9e5a836b2093af7e42c85d275618242e78ff24926d85d47a1d2d0572f6397178`
- Local full M1a result: `61e54d3e50bb4a63921f8ca346e72f3ad3a2407825b53e5763cf43fd78b9f551`
- Local full M1b result: `abdc9357d0752e488cd01893764030840b54e77b9081c72c193dc58c9300e5ea`
- Local full comparison: `9edba2bea8e1baf284246de3cff9151def828965d5351651523809ce6a73c243`
- Local row audit: `1c61b310eccba1ec2c62e34f31f021607bafbadb4806f4dcdc5762ed3f71455a`

The connected GitHub write interface does not expose a safe file-reference-to-repository handoff for the ~1.1 MB row audit. Per the Stage 2 directive, it was **not** manually sharded or serialized through chat arguments. The deterministic summaries above preserve methodology, metrics, coefficients/support, uncertainty, hashes, and recomputation coordinates.

Exact recomputation:
1. Load the Stage 1 waterfall and Phase 2 empirical rows matching the input hashes.
2. Map target states outside the governed six-state set to `out`; `y_persist = y_state != out`.
3. For each official validation source/horizon, train only on rows satisfying `source_season + horizon <= evaluation_source_season`, `y_persist=1`, and finite source/target residual-z.
4. Reconstruct training-fold state SDs using the frozen Phase 3/4 fallback order: position+horizon+state (n>=10), position+state (n>=10), horizon+state (n>=10), state (n>=5).
5. M1a adjusts only positive-state conditional means with the shared horizon residual-z coefficient; probabilities remain fixed.
6. M1b learns prior-only q33/q80 current-residual cutpoints by position/current-state; applies only to premium/elite; enforces n>=75 bucket support; unsupported cells merge or revert to M1a; probabilities remain fixed.
7. Evaluate only Y2 2020–2021 and Y3 2019–2020 with paired absolute-error differences and 5,000-replicate two-way source-season/player cluster bootstrap.

## 9. Stop boundary

**STOP.** M1a and M1b are complete and durably checkpointed. Do not begin M2 career stage, M3a production trajectory, M3b opportunity trajectory, M4/M5 hybrids, final-holdout evaluation, or current-player sentinels without explicit management authorization.
