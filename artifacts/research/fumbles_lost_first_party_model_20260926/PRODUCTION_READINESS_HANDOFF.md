# FSFFL NEXT — First-Party FUMBLES_LOST Production-Readiness Handoff

Updated: 2026-09-26 UTC  
Research terminal state: **DIRECTIVE COMPLETE — RESEARCH / FIRST-PARTY FUMBLES_LOST MODEL READY FOR IMPLEMENTATION**

## Executive result

The smallest defensible first-party exact `FUMBLES_LOST` model clears the governed Research evidence bar.

Selected model:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`

It uses:
- governed prior-season exact lost-fumble outcomes;
- simple position opportunity rates;
- point-in-time Weeks 1–2 current role evidence;
- one global train-only calibration scalar;
- non-zero OOT residual/count uncertainty.

It does **not** use:
- external projection vendors;
- total fumbles as a substitute for lost fumbles;
- named-player tuning;
- future data;
- random train/test splits;
- player-specific fumble-history coefficients;
- unvalidated current provider Forecast coordinates;
- changes to any unrelated offensive Forecast coordinate.

## Evidence bar

Predeclared gates all pass for the selected model.

Combined chronological OOT primary population: **1,599** player-seasons.

Selected:
- RMSE: **0.8105**;
- MAE: **0.4868**;
- bias: **+0.0509**;
- Spearman: **0.4451**;
- zero-calibration gap: **0.0347**;
- tail RMSE: **1.3696**.

Zero/omission:
- RMSE: **1.0425**;
- MAE: **0.4118**;
- tail RMSE: **2.2033**.

Position game-rate:
- RMSE: **1.0475**;
- MAE: **0.7013**.

The selected model lowers RMSE by about 22% relative to both explicit baselines and sharply improves tail error versus omission.

Chronological held-out RMSE improves monotonically:
- 2023: **0.9103**;
- 2024: **0.7819**;
- 2025: **0.7332**.

## Why sparse-event MAE does not select omission

Zero has lower aggregate MAE because most player-seasons have no future lost fumble, but zero fails the purpose of a Forecast coordinate:
- no player ordering;
- no non-zero expectation;
- zero-calibration gap **0.2239**;
- tail RMSE **2.2033**.

The accepted model improves RMSE, rank information, zero calibration and tail behavior while keeping absolute bias small. The gate deliberately required RMSE improvement against omission and MAE non-regression against the meaningful position-rate predictor, not MAE superiority to a degenerate all-zero forecast.

## Model contract

Full formula and exact constants:
- `MODEL_SPEC.md`.

Current 2026 calibration scalar:
- **0.6158756078393594**, fit only from pseudo-current 2022–2025 evidence.

No coefficient may be retuned from 2026 named-player outputs.

## Uncertainty

The model cannot emit zero uncertainty.

Position OOT residual floors:
- QB: **1.7266**;
- RB: **0.7375**;
- WR: **0.4425**;
- TE: **0.4524** lost fumbles.

Cold-start stress floor:
- **0.7899**.

Runtime stddev:
`max(sqrt(mean), position_residual_floor[, cold_start_floor])`.

QB evidence is explicitly the weakest subgroup and therefore carries the largest uncertainty.

## Current shadows / coverage

Current board:
- 335 players;
- 327 exact/deterministic identities;
- **97.61%** identity coverage;
- 8 identity-light rows.

Evidence tiers:
- 258 history + current;
- 40 history only;
- 28 current only;
- 1 cold start;
- 8 identity-light.

The eight identity-light current FSFFL rows are BENCH/TAXI at the current State. They still require degraded-evidence treatment because lineup status can change.

Implementation must not interpret an absent identity/history row as zero fumbles.

## Existing current Forecast inputs

The retained 1,675-observation season Forecast bundle was audited.

It does not provide the exact opportunity features this model uses, and there is no equivalent multi-season Week-2 PIT provider archive with which to validate those fields out of time.

Therefore existing pass/rush/receive Forecasts remain **shadow-only/non-feature evidence for this model v1**.

See:
- `CURRENT_INPUT_ASSESSMENT.md`.

## Implementation boundary

Existing PR #253/#255 current supplemental-coordinate infrastructure is the correct seam.

Implementation should:
1. add the first-party model behind a provider-neutral/Forecast-owned `FUMBLES_LOST` current supplement contract;
2. acquire current Data-layer opportunity inputs for the exact canonical completed-week cutoff;
3. fit/apply only the frozen global scalar and historical position rates defined in the model contract;
4. preserve evidence tier per player;
5. apply non-zero uncertainty;
6. overlay `FUMBLES_LOST` into current league scoring only;
7. leave all retained ordinary Forecast observations unchanged;
8. never write this output into the annual/preseason baseline;
9. invalidate/rebuild the supplement when canonical completed-week State advances;
10. keep affected player scoring partial if required current inputs/identity/evidence are unavailable under the implementation acceptance contract.

## Historical/PIT guard

A production model output is current intelligence.

It must carry:
- real build/evaluation timestamp;
- canonical State ID/hash;
- completed-through week;
- training-season hashes;
- current-input provenance;
- model version;
- calibration scalar;
- uncertainty version.

It is ineligible for:
- 2026 preseason comparison;
- annual preseason snapshots;
- any PIT query before its actual authority timestamp;
- historical backfill.

The historical OOT study validates the **method**, not a fabricated historical existence of the 2026 artifact.

## Required implementation tests

At minimum:
1. exact lost-fumble components only; total fumbles rejected as substitute;
2. strict prior-season training cutoff;
3. no Weeks 3+ target data can enter Week-2 features;
4. calibration scalar for each fold can use only earlier pseudo-current seasons;
5. current 2026 scalar exactly reproduces `0.6158756078393594`;
6. QB opportunity uses `sacks_suffered`, not defensive sacks;
7. deterministic identity recovery accepts only unique normalized name+position;
8. ambiguous mapping remains identity-light/fail-closed;
9. position and cold-start uncertainty floors are non-zero;
10. current artifact is invisible to earlier PIT cutoffs;
11. preseason baseline hash/content remains unchanged;
12. pass/rush/receive raw observations are unchanged before/after supplement;
13. current State completed-week mismatch invalidates the supplement;
14. player lacking required model evidence cannot silently receive zero;
15. 335-player current shadow fixture reproduces the accepted coverage tiers;
16. existing FSFFL rebuild can promote full current player scoring only if the model supplement satisfies downstream current-authority requirements.

## Retained evidence

Directory:
`artifacts/research/fumbles_lost_first_party_model_20260926/`

Key files:
- `MODEL_SPEC.md`;
- `CURRENT_INPUT_ASSESSMENT.md`;
- `VALIDATION_RESULTS.json`;
- `OOT_METRICS.csv`;
- `CALIBRATION.csv`;
- `COLD_START_STRESS.csv`;
- `CURRENT_SHADOWS.csv`;
- `DATA_LINEAGE.json`;
- `REPORT.md`.

Reproducible study:
- `scripts/run_fumbles_lost_first_party_research.py`;
- `.github/workflows/fumbles-lost-first-party-research.yml`.

The final evidence workflow passed. No external provider permission is required by this first-party model path.

## Research closure

Question: **Is there another authorized Research action available now that materially advances this directive before Forecast Implementation begins?**

Answer: **No.**

The target, inputs, leakage controls, baselines, OOT accuracy, stability, calibration, uncertainty, current coverage, cold-start behavior, PIT boundary, and implementation contract are all persisted.

**DIRECTIVE COMPLETE — RESEARCH / FIRST-PARTY FUMBLES_LOST MODEL READY FOR IMPLEMENTATION**
