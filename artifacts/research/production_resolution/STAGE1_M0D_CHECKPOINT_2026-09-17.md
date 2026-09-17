# FSFFL NEXT — Stage 1 / M0-D Historical Compression Decomposition Checkpoint

Checkpoint date: 2026-09-17
Authority: research only
Protocol: Forecast Production-Resolution & Player-State Research Execution — Management Revised 2026-09-17
Status: **STAGE1_M0D_ANALYSIS_COMPLETE — ROW-LEVEL ARTIFACT PERSISTENCE BLOCKED — STOPPED BEFORE M1a/M1b**

## 1. Recovered live state and authority boundary

- Research branch: `research/future-state-resolution-phase34-resume`
- Stage 0 durable checkpoint / Stage 1 parent: `3b2b1dcd9d1c9cae89de3ed24fbd666b110b4880`
- Stage 0 artifact: `artifacts/research/production_resolution/STAGE0_PREFLIGHT_2026-09-17.md`
- Live `main` re-fetched before Stage 1 persistence: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147 re-fetched before Stage 1 persistence: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`
- Fixed routed Forecast preserved unchanged: QB -> `A2+C+D`; RB/WR/TE -> `A2+D`.
- Global governed C=0.25, Intrinsic/Shapley architecture, discount, lineup legality, production authority, main, and PR #147 were not changed.
- No M1a, M1b, M2, M3a, M3b, M4, or M5 fit/test was run.
- No named current player was used.

The research branch was re-fetched immediately before this persistence step and still pointed to the Stage 0 parent above. No branch conflict was present.

## 2. Stage 1 sample and point-in-time execution

The decomposition uses the existing routed baseline only. No challenger was fit.

- Y2 / h2: source seasons 2014–2023; 5,726 rows.
- Y3 / h3: source seasons 2014–2022; 5,168 rows.
- Total: 10,894 historical row-level waterfalls.
- H2 fitting at source season s uses only frozen H1/H2 transition rows whose outcomes satisfy source_season + horizon <= s.
- H3 uses the frozen direct-H3 path and only transitions satisfying source_season + 3 <= s.
- State boundaries, source residuals, production-tier coordinates, within-state coordinates, career-stage coordinates, and trajectory labels are point-in-time.
- No realized test-row error metric, holdout MAE/bias, challenger comparison, or current-player sentinel was run.

Recovered evidence integrity:
- Phase 2 workflow artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`
- `phase2_player_season_panel.csv` SHA-256: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`
- Maximum full-precision waterfall reconciliation error: `2.842170943040401e-14` points.

## 3. Waterfall definition

For each historical player-date-horizon row:

1. conditional-mean compression = current source production minus the generic conditional mean for retaining the current source state at that horizon;
2. state-mix effect = current-state reference mean minus the probability-weighted future positive-state mean;
3. existing residual/carryover effect = explicit governed conditional-mean adjustment already present;
4. persistence discount = conditional-on-active expected points minus final unconditional expected points;
5. interaction flag = positive-compression row where no single component exceeds 50% of the sum of absolute component magnitudes.

Exact identity:
`current_points - final_unconditional_points = conditional_mean_compression + state_mix_effect + residual_carryover_compression + persistence_discount`.

The fixed routed contender contains no B/carryover conditional-mean adjustment because B was deferred in the prior research. The explicit residual/carryover mean effect is therefore 0.0 points on every Stage 1 row. Current/prior production still influences persistence and future-state probabilities through the existing baseline.

## 4. High-end compression result

| Horizon | Cohort | n | Current | Final | Drop | Conditional mean | State mix | Persistence | Interaction |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Y2 | Elite >90 | 569 | 196.59 | 118.76 | 77.83 | 33.42 | 32.07 | 12.34 | 19.5% |
| Y3 | Elite >90 | 514 | 196.33 | 94.21 | 102.12 | 34.34 | 44.59 | 23.20 | 28.8% |
| Y2 | Extreme upper >95 | 285 | 221.93 | 123.30 | 98.63 | 58.95 | 26.99 | 12.69 | 26.0% |
| Y3 | Extreme upper >95 | 256 | 221.83 | 96.66 | 125.18 | 60.27 | 40.79 | 24.11 | 41.4% |

Row-level largest-component frequencies corroborate the mean waterfall:
- Elite Y2: state mix 56.4%; conditional mean 43.2%; persistence 0.4%.
- Elite Y3: state mix 62.1%; conditional mean 34.6%; persistence 3.3%.
- Extreme-upper Y2: conditional mean 72.3%; state mix 27.7%.
- Extreme-upper Y3: conditional mean 59.0%; state mix 38.3%; persistence 2.7%.

### Position-specific high-end waterfall

| H | Pos | Cohort | n | Current | Final | Drop | Cond-mean | State-mix | Persistence | Interaction | Dominant |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2 | QB | elite90 | 71 | 347.23 | 212.08 | 135.14 | 88.36 | 29.64 | 17.14 | 19.7% | conditional mean |
| 2 | QB | >95 | 35 | 372.97 | 216.98 | 155.99 | 113.95 | 24.13 | 17.91 | 2.9% | conditional mean |
| 2 | RB | elite90 | 164 | 212.64 | 125.04 | 87.60 | 29.30 | 45.89 | 12.40 | 14.0% | state mix |
| 2 | RB | >95 | 82 | 245.13 | 129.62 | 115.51 | 61.80 | 40.80 | 12.91 | 25.6% | conditional mean |
| 2 | WR | elite90 | 214 | 175.83 | 108.70 | 67.14 | 26.36 | 27.79 | 12.98 | 22.0% | state mix |
| 2 | WR | >95 | 108 | 198.84 | 114.17 | 84.67 | 49.37 | 22.26 | 13.04 | 34.3% | conditional mean |
| 2 | TE | elite90 | 120 | 122.56 | 72.89 | 49.66 | 19.12 | 22.27 | 8.28 | 22.5% | state mix |
| 2 | TE | >95 | 60 | 143.68 | 76.43 | 67.25 | 40.24 | 18.28 | 8.73 | 25.0% | conditional mean |
| 3 | QB | elite90 | 64 | 347.35 | 182.99 | 164.36 | 89.98 | 40.96 | 33.41 | 43.8% | conditional mean |
| 3 | QB | >95 | 31 | 373.36 | 183.56 | 189.80 | 115.97 | 36.63 | 37.19 | 25.8% | conditional mean |
| 3 | RB | elite90 | 149 | 212.33 | 94.58 | 117.75 | 31.48 | 62.81 | 23.45 | 18.8% | state mix |
| 3 | RB | >95 | 74 | 245.87 | 97.76 | 148.10 | 65.03 | 59.17 | 23.90 | 36.5% | conditional mean |
| 3 | WR | elite90 | 193 | 174.94 | 85.94 | 89.00 | 25.86 | 39.81 | 23.33 | 28.5% | state mix |
| 3 | WR | >95 | 97 | 197.97 | 89.92 | 108.05 | 48.89 | 35.51 | 23.64 | 49.5% | conditional mean |
| 3 | TE | elite90 | 108 | 123.00 | 55.88 | 67.12 | 20.45 | 30.11 | 16.56 | 34.3% | state mix |
| 3 | TE | >95 | 54 | 144.77 | 57.35 | 87.42 | 42.23 | 27.48 | 17.72 | 42.6% | conditional mean |

## 5. Requested cohort decomposition

| H | Dimension | Level | n | Drop | Cond-mean | State-mix | Persistence | Dominant |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 2 | production tier | replacement-adjacent | 2290 | -2.49 | -1.43 | -18.62 | 17.56 | persistence |
| 2 | production tier | starter | 1721 | 11.74 | -5.88 | -0.97 | 18.59 | persistence |
| 2 | production tier | very good | 1146 | 35.34 | -7.91 | 27.57 | 15.68 | state mix |
| 2 | production tier | elite | 569 | 77.83 | 33.42 | 32.07 | 12.34 | conditional mean |
| 2 | production tier | >95 | 285 | 98.63 | 58.95 | 26.99 | 12.69 | conditional mean |
| 3 | production tier | replacement-adjacent | 2066 | -2.91 | -1.47 | -27.71 | 26.28 | persistence |
| 3 | production tier | starter | 1554 | 19.52 | -5.98 | -1.61 | 27.11 | persistence |
| 3 | production tier | very good | 1034 | 52.52 | -7.29 | 32.76 | 27.05 | state mix |
| 3 | production tier | elite | 514 | 102.12 | 34.34 | 44.59 | 23.20 | state mix |
| 3 | production tier | >95 | 256 | 125.18 | 60.27 | 40.79 | 24.11 | conditional mean |
| 2 | within-state | lower | 1904 | 9.41 | -16.68 | 11.63 | 14.46 | persistence |
| 2 | within-state | middle | 2682 | 16.70 | 0.54 | -1.43 | 17.59 | persistence |
| 2 | within-state | extreme-upper | 1140 | 32.08 | 23.57 | -11.22 | 19.73 | conditional mean |
| 3 | within-state | lower | 1719 | 14.74 | -16.53 | 7.23 | 24.04 | persistence |
| 3 | within-state | middle | 2420 | 25.21 | 0.71 | -2.63 | 27.13 | persistence |
| 3 | within-state | extreme-upper | 1029 | 43.51 | 23.79 | -8.77 | 28.49 | persistence |
| 2 | career stage | young/developing | 848 | 8.74 | -0.86 | -7.47 | 17.07 | persistence |
| 2 | career stage | established | 3093 | 12.86 | -0.62 | -1.89 | 15.36 | persistence |
| 2 | career stage | late-career | 1785 | 29.19 | -0.44 | 9.91 | 19.72 | persistence |
| 3 | career stage | young/developing | 771 | 11.37 | -0.65 | -11.90 | 23.91 | persistence |
| 3 | career stage | established | 2795 | 19.40 | -0.47 | -4.14 | 24.01 | persistence |
| 3 | career stage | late-career | 1602 | 42.53 | -0.27 | 11.10 | 31.69 | persistence |
| 2 | trajectory | declining | 1424 | 16.16 | -11.47 | 11.91 | 15.72 | persistence |
| 2 | trajectory | stable | 1412 | 22.46 | -2.63 | 8.86 | 16.23 | persistence |
| 2 | trajectory | ascending | 1421 | 27.05 | 14.01 | -5.61 | 18.65 | persistence |
| 2 | trajectory | unavailable | 1469 | 4.16 | -2.24 | -10.89 | 17.28 | persistence |
| 3 | trajectory | declining | 1291 | 25.85 | -11.26 | 10.74 | 26.37 | persistence |
| 3 | trajectory | stable | 1276 | 33.69 | -2.30 | 9.67 | 26.32 | persistence |
| 3 | trajectory | ascending | 1261 | 37.77 | 14.46 | -4.25 | 27.55 | persistence |
| 3 | trajectory | unavailable | 1340 | 5.32 | -2.24 | -17.77 | 25.32 | persistence |

These are decomposition diagnostics, not causal attributions and not challenger performance results.

## 6. Primitive stop-condition decision

**Different-dominant-primitive stop condition: NOT TRIGGERED.**

Across the full population, persistence is the largest average compression component. That is not the governing defect under study: the protocol targets high-end multi-year compression. In the elite/extreme-upper cohorts, conditional-state mean compression and future-state probability mix are larger than persistence, and the >95th percentile cohort is conditional-mean dominated at both horizons. The M0-D evidence therefore continues to identify the protocol-targeted conditional-production/state-resolution family as the relevant high-end mechanism.

This conclusion does not authorize a challenger. M1a/M1b remain unexecuted.

## 7. Required persistence boundary

A full 10,894-row waterfall was produced in the Python runtime. The compact durable candidate is 229,016 bytes after XZ compression and has SHA-256 `af31afc42d46fe9d64a6f71728203e63b9e5366176a62bf68e93abda6f30561e`. It contains row identity/cohort coordinates and every Section 4 scalar waterfall component. The full-precision local audit archive has SHA-256 `f9aa5491353d45859bd5fdce7d93cef91e487087047e9e56a129c6af97501770`.

The connected GitHub write surface available in this chat can create UTF-8 files/blobs, but it does not expose a direct file-reference-to-repository binary upload handoff from the Python runtime. Serializing and manually sharding a binary result through chat/tool arguments would be an invented workaround, which the governing execution instruction forbids.

Therefore this text checkpoint persists the bounded Stage 1 result, but the required row-level compression-waterfall artifact itself is **not yet durably committed to the branch**. Stage 1 is stopped at that exact persistence boundary for management review.

**STOP:** no M1a, M1b, M2, M3a, M3b, M4, M5, final-holdout scoring, named-player sentinel, implementation, PR #147 change, main change, merge, deploy, promotion, or production-authority change was performed.
