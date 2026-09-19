# FSFFL NEXT — Stage 3 M2 / M3a / M3b Research Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: Stage 3 — Career Stage & Trajectory Research  
Status: **STAGE3_ANALYSIS_COMPLETE_WITH_PROCEDURAL_SEQUENCE_DEVIATION — STOPPED FOR MANAGEMENT REVIEW**

## 1. Recovered authority boundary

- Research branch: `research/future-state-resolution-phase34-resume`.
- Durable Stage 2 checkpoint recovered at `artifacts/research/production_resolution/STAGE2_M1A_M1B_CHECKPOINT_2026-09-18.md`.
- Stage 3 start head re-fetched as `c2b09eb01993f01bd2643414847ba8b99ee24831`.
- `main` at Stage 3 start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at Stage 3 start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- M1a remained the frozen Stage 2 production-magnitude baseline.
- No final-holdout source season was evaluated.
- No named current player was used.
- No production Forecast/Intrinsic authority, Intrinsic Constitution, Shapley rule, global C, discount, lineup legality, `main`, or PR #147 was modified.

Stage 0 Preflight B had already approved M3b with exactly one governed opportunity family:

`opportunity_delta_log = log1p(opportunity_per_game_t) - log1p(opportunity_per_game_t-1)`

plus explicit coverage/missingness. No new opportunity feature was introduced in Stage 3.

## 2. Frozen execution design

### M2 — career stage

M2 preserved frozen M1a and fit an incremental regularized conditional-production adjustment.

- Model: `BayesianRidge(fit_intercept=False)`.
- Response: active target residual-z minus frozen M1a residual-z prediction.
- Features: four shared low-complexity piecewise-linear career features:
  - age below the position-specific training median;
  - age above the position-specific training median;
  - experience below the position-specific training median;
  - experience above the position-specific training median.
- Position-specific medians and IQR scales were learned from pre-cutoff training rows only.
- No trajectory feature was included.

### M3a — production trajectory

M3a was fit incrementally beyond M1a + M2.

- Continuous prior-to-current change in within-state residual-z.
- Two-year residual-z slope only where two genuine prior source seasons existed.
- Explicit coverage flags for both trajectory signals.
- Continuous values standardized from pre-cutoff training rows only.
- No hard ascending/declining label entered the model.

### M3b — opportunity trajectory

M3b was fit incrementally beyond M1a + M2 + M3a.

- Only the Stage-0-frozen `opportunity_delta_log` signal plus explicit coverage.
- No snaps, routes, route participation, target share, red-zone work, or retrospective substitute was introduced.
- Opportunity coverage in official validation was 74.4% at Y2 and 72.7% at Y3.

For all three challengers, persistence and future-state probabilities remained unchanged. Only positive future-state conditional production means were adjusted. There were zero adjusted-mean floor events and zero state-order inversions.

## 3. M2 standalone result — career stage

Correct comparator: frozen M1a.

| Horizon | M1a MAE | M2 MAE | M2 − M1a | 95% clustered interval |
|---|---:|---:|---:|---|
| Y2 | 31.021 | 31.025 | +0.004 | [-0.010, +0.025] |
| Y3 | 30.652 | 30.646 | -0.006 | [-0.018, +0.000] |

Position MAE:

| Horizon | QB | RB | WR | TE |
|---|---:|---:|---:|---:|
| Y2 M1a | 64.774 | 31.716 | 26.622 | 17.574 |
| Y2 M2 | 64.758 | 31.738 | 26.618 | 17.576 |
| Y3 M1a | 59.025 | 32.322 | 27.025 | 18.306 |
| Y3 M2 | 59.023 | 32.314 | 27.019 | 18.299 |

High-end:
- Y2 >95th: MAE 62.753 -> 62.732; bias -32.690 -> -32.532.
- Y3 >95th: MAE 68.692 -> 68.681; bias -43.063 -> -43.101.

Chronological replication:
- Y2 2020 worsened by +0.009 MAE.
- Y2 2021 improved by -0.002.
- Y3 2019 improved by -0.011.
- Y3 2020 improved by -0.002.

Development-era aggregate:
- Y2: 32.931 M1a -> 32.933 M2.
- Y3: 32.178 M1a -> 32.172 M2.

**M2 interpretation: DOES NOT ADD CLEAR REPLICATED SIGNAL.** The effect is near zero and statistically ambiguous after M1a. A separate career-stage conditional-production dimension is not justified merely because it is intuitive.

Persisted before the intentional M3a review:
`artifacts/research/production_resolution/STAGE3_M2_VALIDATION_2026-09-18.json`
Commit: `1775a94702eabe984a1d2db66c6a0961992529cc`.

## 4. M3a standalone result — production trajectory

Correct comparator: M1a + M2 representation.

| Horizon | M2 MAE | M3a MAE | M3a − M2 | 95% clustered interval |
|---|---:|---:|---:|---|
| Y2 | 31.025 | 31.060 | +0.035 | [-0.018, +0.083] |
| Y3 | 30.646 | 30.659 | +0.013 | [-0.017, +0.041] |

Every official validation source season worsened numerically:
- Y2 2020: +0.047.
- Y2 2021: +0.023.
- Y3 2019: +0.006.
- Y3 2020: +0.020.

The main fitted one-year production-trajectory coefficient was consistently negative:
- Y2 cutoffs: approximately -0.030 and -0.035 standardized residual-z units.
- Y3 cutoffs: approximately -0.029 and -0.030.

This is mean-reversion behavior rather than evidence that recent production ascent should be carried forward.

High-end:
- Y2 >95th MAE improved slightly 62.732 -> 62.587, but CI for the delta crossed zero.
- Y3 >95th worsened 68.681 -> 68.866.

Stress cohorts:
- Y2 non-persistence worsened by +0.101 MAE, 95% CI [+0.051, +0.144].
- Y2 realized role-loss worsened by +0.316, CI [+0.110, +0.548].
- Y3 non-persistence worsened by +0.055, CI [+0.036, +0.077].
- Ascending-cohort changes were small and statistically ambiguous.

Development-era aggregate also worsened:
- Y2: 32.933 M2 -> 32.985 M3a.
- Y3: 32.172 M2 -> 32.199 M3a.
- All four reported development source seasons worsened at each horizon.

Validation coverage:
- one-year production-residual delta: 74.4% Y2 / 72.7% Y3;
- two-year slope: 54.7% Y2 / 52.1% Y3;
- missingness was retained explicitly.

**M3a interpretation: DO NOT ADVANCE.** It does not add replicated aggregate signal and clearly harms non-persistence at both horizons, with clear Y2 role-loss harm.

Persisted before the intentional M3b review:
`artifacts/research/production_resolution/STAGE3_M3A_VALIDATION_2026-09-18.json`
Commit: `0d5b68fdb94b804a76b6d719c36d776071470484`.

## 5. M3b standalone result — opportunity trajectory

Correct comparator: M1a + M2 + M3a representation.

| Horizon | M3a MAE | M3b MAE | M3b − M3a | 95% clustered interval |
|---|---:|---:|---:|---|
| Y2 | 31.060 | 31.069 | +0.009 | [-0.001, +0.021] |
| Y3 | 30.65905 | 30.65872 | -0.00033 | [-0.00064, -0.00003] |

Chronological:
- Y2 2020 worsened +0.010.
- Y2 2021 worsened +0.008.
- Y3 2019 improved -0.00029.
- Y3 2020 improved -0.00037.

Fitted opportunity effects:
- Y2 standardized opportunity-delta coefficient: about +0.019 and +0.016.
- Y3 coefficient: about +0.00057 and +0.00053 — effectively near zero.

Stress:
- Y2 realized role-loss worsened by +0.070 MAE, 95% CI [+0.019, +0.135].
- Y2 ascending, non-persistence, stable-prime and aging/declining effects were statistically ambiguous.
- Y3 changes across all stress cohorts were numerically tiny; ascending and non-persistence had statistically negative deltas measured in thousandths of a point.

Development-era aggregate:
- Y2: 32.98506 M3a -> 32.98805 M3b.
- Y3: 32.19939 M3a -> 32.19942 M3b.

**M3b interpretation: DOES NOT EARN GENERAL ADVANCEMENT.** Governed PIT opportunity coverage is adequate, but Y2 worsens in both validation seasons and clearly worsens realized role-loss. Y3 has a statistically detectable but practically near-zero gain with near-zero coefficients and no supporting development-era improvement. Horizon-specific M3b was not predeclared, so this trace is not treated as an independent candidate signal for M4/M5.

Persisted:
`artifacts/research/production_resolution/STAGE3_M3B_VALIDATION_2026-09-18.json`
Commit: `6a7fa7151117107b692ca74e9021876294012668`.

## 6. Stage 3 management interpretation

Stage 3 does **not** produce an additional independently supported dimension beyond Stage 2 M1a:

- M2 career stage: no clear replicated incremental signal.
- M3a production trajectory: fails and produces clear lower-tail harm.
- M3b opportunity trajectory: no general advancement; only a near-zero Y3 statistical trace.

Therefore the protocol's "two or more standalone dimensions show clear independent evidence" condition is **not met**. No M4/M5 hybrid is justified by this Stage 3 evidence.

M1a remains the leading general production-resolution mechanism.

No final holdout has been opened, so the protected final evaluation remains unspent.

## 7. Procedural sequence deviation — management review required

A runner-control defect was discovered during the Stage 3 execution review.

The local runner accepted a `--stage` argument, but its first implementation computed the later-stage M3a/M3b adjustment objects inside the common source-season function even during the initial M2 run. The later-stage metrics were **not inspected, interpreted, or used to alter any feature family, coefficient family, threshold, transform, or candidate form before the required M2 and M3a repository checkpoints were written**. All candidate feature families were frozen from the directive/Stage 0, and no final-holdout or named-player result was available.

This means:
- there is **no outcome leakage into model design** identified;
- the persisted GitHub commits were made in the required M2 -> M3a -> M3b order;
- but the literal directive language "persist M2 before beginning M3a" was not perfectly satisfied because later-stage calculations were precomputed internally.

This is a procedural sequencing deviation, not a hidden modeling adjustment. It is documented here rather than silently treated as compliant. Management should decide whether the Stage 3 evidence may be accepted as-is or whether a fresh management-approved rerun boundary is desired before any later stage.

A reporting-only runner patch made after M2 changed the local runner hash from:
- M2 execution runner: `935db9913a4409a46b5ad0d281a3cff9895c7ea4f0b6acf32ab53cd6d5184dec`
to
- M3a/M3b runner: `4886662ba146bccb89a6fdda29f956ed0a2cd77786c3b1864bbba820ae545944`.

That patch added missingness-report population; it did not change the fitted formulas or candidate predictions.

## 8. Reproducibility and hashes

Inputs:
- Stage 1 routed waterfall: `eb6ffd6c2ad71aa7c4459e432cf78153432dcaa59a4d5b49bbec1b496ff560a3`.
- Phase 2 empirical rows: `ce0f1369487a09f39057dce9eb4dfc804a8c06f041df5e2531880d1e1381534e`.
- Phase 2 player-season panel: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`.

Local standalone result hashes:
- M2 JSON: `536fca987e5719ee5e132ac892c0bbcc2d713f693b29b94ff96cf33e8d9b10d1`.
- M3a JSON: `975e061738d068aa22f0347e455993f21abe47c72b3e3667300176d85edfb5f0`.
- M3b JSON: `2d66274cdbc0b016734f13a3e1499b674c9af47f094c6591a66544459ce962ba`.
- Local 2,374-row audit: `22ba1638fb7e86146ad228c6d803c9ff1693d19f9dd36744bdefe0de37204767`.

Audit invariants:
- validation rows: 2,374;
- Y2 2020: 595; Y2 2021: 614; Y3 2019: 570; Y3 2020: 595;
- M1a parity against Stage 2: maximum error `2.84e-14`;
- baseline reconstruction error: maximum `8.45e-08`;
- probability sum error: maximum `2.00e-10`;
- state probabilities changed: false;
- final-holdout rows present: false;
- named current players used: false.

The full local row audit is not manually sharded through GitHub. Per the directive, deterministic text/JSON summaries and exact hashes are persisted instead.

Deterministic recomputation:
1. Load the Stage 1 routed waterfall, Phase 2 empirical rows and panel matching the hashes above.
2. Preserve Stage 2 M1a exactly at each cutoff.
3. Use only training rows whose target is observable at the historical cutoff.
4. M2: learn position-specific training medians/IQRs for age and experience; fit the four shared hinge features to residual target-z after M1a.
5. M3a: compute PIT current-minus-prior residual-z and two-year residual slope with coverage flags; standardize covered continuous values on training rows; fit incrementally after M1a+M2.
6. M3b: compute only the Stage-0-frozen log opportunity-per-game delta with coverage; standardize on training rows; fit incrementally after M1a+M2+M3a.
7. Apply each residual-z adjustment only to positive-state conditional means using the frozen training-fold state SD fallback hierarchy. Never alter state probabilities.
8. Evaluate only Y2 source 2020–2021 and Y3 source 2019–2020.
9. Compute paired absolute-error differences; bootstrap primary/position/high-end comparisons with 5,000 two-way source-season/player replicates and stress cohorts with 2,000 replicates.
10. Do not evaluate Y2 source 2022–2023 or Y3 source 2021–2022 without a later explicit authorization.

## 9. Stop boundary

**STOP.** Stage 3 research is complete at the management-review boundary. Do not begin M4/M5 hybrid testing, final-holdout evaluation, current-player sentinels, implementation, merge, deployment, promotion, or production-authority changes.
