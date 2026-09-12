# PR #131 — Model A Chronological Benchmark Results

**Status:** research-only. These findings do not change production behavior, production coefficients, authority boundaries, or the current intrinsic-value implementation. Model B was not fitted.

## Executive conclusion

Model A is a materially better historical predictor of three-year replacement-adjusted football surplus than the existing affine intrinsic-value control, but the evidence does **not** justify production promotion yet.

Across 17 true chronological holdout seasons and 9,430 evaluated player-season observations, the best Model A replacement specification reduced mean absolute error by **24.2%** versus the affine control. The `starter_threshold` replacement definition had the lowest aggregate Model A MAE and won the replacement-policy comparison in **17 of 17 holdout folds**.

That result is important: the transparent multi-year surplus construction is carrying real out-of-time signal beyond a one-year affine mapping. It is not merely reproducing market consensus. However, three unresolved problems block promotion:

1. Model A's nominal 80% uncertainty interval covered **91.2%** of realized outcomes, just outside the predeclared +/-10 percentage-point calibration tolerance. The uncertainty distribution is too wide/conservative.
2. Only **4 of 6** predefined economic-usefulness scenarios passed. The aging-RB, elite-QB, developing-WR, and developing-TE checks passed; the position-scarcity shift and expected appreciation/decline checks failed.
3. The best raw-error replacement candidate, `starter_threshold`, is structurally insensitive to superflex/flex allocation in its current definition. Its failure on the position-scarcity scenario therefore points first to replacement/context specification, not to a need for a richer intrinsic-value functional form.

The aggregate residual probe found an elite-tail residual gap large enough to make a bounded nonlinear surplus transformation worth **investigating later**, but this benchmark did not establish that the residual is chronologically persistent after the replacement/context and uncertainty issues are corrected. Therefore this result does **not** yet justify fitting Model B.

## 1. Historical evidence and fold construction

The benchmark rebuilt the historical Forecast state separately inside every fold rather than applying a through-2025 calibration backward.

Historical transition extraction produced:

- **14,876** QB/RB/WR/TE career-transition rows;
- seasons **1999 through 2024**;
- known age on all 14,876 rows;
- explicit player-entry season on all 14,876 rows;
- observed next-season survival rate of **74.66%**.

A target preseason season `T` was eligible only if all of the following held:

- at least **5 completed prehistory seasons** were available;
- every position parent had at least **100 transition rows**;
- every position parent had at least **50 survivor rows**;
- calibration used only transition rows with source season `<= T-2`, so their next-season outcomes were already knowable by the preseason-T cutoff;
- the three realized seasons required to score the Model A horizon were fully observed.

This produced supported target seasons:

`2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022`.

The first supported season seeded the affine training history. The affine control was then re-fit only on earlier supported folds and frozen before each subsequent holdout, producing **17 chronological affine-vs-Model-A holdouts**.

### Historical Forecast reconstruction

Within each fold, Forecast owns the football trajectory:

- next-season continuation/survival;
- conditional production change;
- age/career-state effects through the empirical-Bayes transition cells;
- recursive multi-season development/decline;
- football uncertainty.

No post-cutoff transition evidence is used to calibrate that fold. Survival is incorporated once in Forecast and is not re-applied by Value.

Incoming rookies without a prior NFL season are not hindsight-filled into the historical preseason Forecast universe. This is point-in-time safe but remains an important limitation for replacement-pool and young-player coverage.

## 2. Model A construction

Model A is the transparent three-year replacement-adjusted surplus model defined by PR #131.

For each player and each horizon season:

`surplus = max(0, player Forecast - replacement Forecast)`

The benchmark aggregates three seasons with fixed research weights:

- Year 1: `1.00`
- Year 2: `0.85`
- Year 3: `0.70`

These are transparent benchmark weights, **not an empirically identified time-preference curve**. Time preference remains underidentified and was not fitted.

The primary league context was a 12-team superflex structure with QB / 2 RB / 3 WR / TE / FLEX / SUPERFLEX. A 12-team 1QB context was used for the scarcity sensitivity check.

## 3. Replacement-definition comparison

Four candidate replacement policies were tested as a model-selection problem rather than assuming a correct baseline in advance.

| Candidate | Chronological holdouts | N | Model A MAE | Affine MAE | MAE improvement | Model A nominal-80% coverage |
|---|---:|---:|---:|---:|---:|---:|
| `starter_threshold` | 17 | 9,430 | **14.018** | 18.485 | **24.2%** | 91.2% |
| `marginal_lineup_opportunity` | 17 | 9,430 | 20.307 | 26.968 | 24.7% | 90.0% |
| `first_rostered_replacement` | 17 | 9,430 | 21.545 | 28.501 | 24.4% | 89.8% |
| `replacement_pool_quantile` | 17 | 9,430 | 45.492 | 52.293 | 13.0% | **81.0%** |

### Best raw-error candidate

`starter_threshold` produced the lowest absolute Model A MAE and won the candidate comparison in **17/17 chronological holdout folds (100%)**.

That stability is much stronger than the predeclared 60% stability gate.

### Important interpretation

The replacement comparison is not a simple “starter threshold is solved” conclusion.

The `replacement_pool_quantile` specification had much worse prediction error but materially better uncertainty coverage. Conversely, `starter_threshold` dominated raw-error performance but failed the explicit league-context/scarcity scenario because its current structural threshold is based on required positional starters and does not move with superflex/flex allocation.

Therefore the evidence supports `starter_threshold` as the best **current prediction-error baseline**, while still requiring a context-aware replacement refinement before production consideration. That refinement belongs inside replacement/model selection, not Model B.

## 4. Model A versus affine control

The predeclared material-outperformance threshold was a **5% reduction in chronological holdout MAE**.

Best-candidate result:

- Model A MAE: **14.018**
- affine-control MAE: **18.485**
- relative MAE improvement: **24.2%**
- material-outperformance threshold: **passed decisively**

This is the central positive result of the study. The transparent multi-year replacement-adjusted construction produces substantially more useful out-of-time football-economic predictions than the one-year affine control on the historical evidence available here.

All four replacement candidates also beat their corresponding affine control by more than the predeclared 5% threshold, ranging from 13.0% to 24.7% MAE improvement. Model A's advantage is therefore not confined to a single replacement definition.

## 5. Uncertainty calibration

For the winning `starter_threshold` candidate, nominal 80% Model A intervals covered **91.2%** of realized outcomes.

The promotion rule required coverage within +/-10 percentage points of 80%; acceptable coverage was therefore 70%-90%.

**Result: FAIL by 1.2 percentage points.**

Interpretation: the current propagated Forecast/replacement uncertainty is somewhat too wide. This should be treated as an uncertainty-calibration problem first. It is not evidence that the economic mean function needs Model B complexity.

For comparison:

- marginal-lineup-opportunity coverage: 90.0%;
- first-rostered-replacement coverage: 89.8%;
- replacement-pool-quantile coverage: 81.0%.

The interaction between replacement definition and uncertainty calibration is therefore material and should remain part of replacement-policy selection.

## 6. Predefined economic-usefulness scenarios

The winning Model A specification passed **4 of 6** scenarios (**66.7%**). The predeclared promotion gate required at least 5 of 6.

### Passed

**Aging RB vs young RB**

- comparable-production age-separated pair comparisons: 66,683;
- directional accuracy: **75.28%**;
- result: **PASS**.

Model A generally distinguishes the longer-horizon economics of younger versus older RBs even when near-term production is similar.

**Elite QB longevity**

- N: 241;
- Model-A-vs-realized rank signal: **0.3025**;
- result: **PASS**.

**Developing WR**

- N: 1,429;
- rank signal: **0.4854**;
- result: **PASS**.

**Developing TE**

- N: 819;
- rank signal: **0.3981**;
- result: **PASS**.

These three career-stage results are encouraging because they are exactly the kinds of multi-year distinctions the affine one-year mapping cannot express as naturally.

### Failed

**Position-scarcity shift**

- QB relative value change, SF versus 1QB: **0.0**;
- non-QB relative value change: **0.0**;
- result: **FAIL**.

This failure is structurally interpretable. The raw-error-winning `starter_threshold` candidate currently uses required positional starter counts and therefore does not shift its QB baseline when a superflex slot is added. It cannot express the league-level QB opportunity-cost change that the scenario is designed to test.

This is a replacement/context specification failure, not evidence for Model B.

**Expected appreciation / decline**

- adjacent-fold same-player changes: 2,856;
- directional accuracy: **43.17%**;
- change correlation: **-0.2620**;
- result: **FAIL**.

This is the most important substantive failure. Absolute multi-year surplus prediction is strong, but year-over-year changes in Model A value do not track subsequent changes in realized multi-year surplus. Before adding a richer economic function, this should be decomposed into Forecast trajectory updates, overlapping-horizon target mechanics, replacement-level movement, and the fixed time-weight assumption.

## 7. Market-independence diagnostics

Historical DynastyProcess values were joined only after Model A construction and were never used as Model A inputs, calibration targets, or replacement targets.

Point-in-time market overlap was available for **3 chronological folds**.

Across those folds:

- Pearson Model-A/market correlation: **0.6670**;
- Spearman rank correlation: **0.5918**;
- material percentile disagreement rate: **40.86%**;
- mean absolute standardized residual: **0.3955**;
- adding market to Model A improved downstream holdout MAE by **31.09%** on average;
- market added incremental information in **100%** of overlapping diagnostic folds.

### Interpretation

Model A is **not merely reproducing broader market consensus**. A rank correlation around 0.59 plus a roughly 41% material-disagreement rate is inconsistent with a disguised market clone.

The fact that market values still add substantial incremental predictive information is also important. Independence is preserved, but the market contains information Model A does not currently capture. That does not mean intrinsic should be trained to market. It means the independent comparison is doing useful work and identifies missing information or model limitations that should be investigated through football/economic evidence rather than copied from consensus prices.

The market diagnostic remains thinner than the football-outcome benchmark because only three historical folds have safe overlap. It is sufficient to reject the hypothesis that Model A is simply market consensus, but not sufficient to treat the exact correlation/incremental-gain estimates as highly stable long-run constants.

## 8. Production-promotion decision

**Production promotion is not justified.**

The positive evidence is substantial:

- 17 chronological holdouts;
- 9,430 evaluated observations;
- 24.2% MAE improvement over affine;
- 17/17 replacement-policy fold wins for the best raw-error candidate;
- strong aging-RB and developing-player economic behavior;
- clear empirical independence from market consensus.

But the predeclared promotion standard is intentionally stricter than aggregate predictive accuracy. The winning specification fails:

- uncertainty calibration (91.2% vs <=90% acceptable upper bound);
- position-scarcity sensitivity;
- expected appreciation/decline behavior;
- the 5-of-6 economic-usefulness threshold (only 4/6 pass).

No coefficient or model should be promoted on this evidence yet.

## 9. Does the evidence justify Model B complexity?

**Not yet.**

The benchmark's exploratory aggregate residual check detected a large enough top-of-distribution versus middle-distribution residual gap to raise one specific possible challenger: a **bounded nonlinear surplus transformation** for the elite tail.

However, that result is not yet sufficient to fit or promote Model B because:

1. the benchmark has not yet established that the elite-tail residual pattern is persistent across chronological folds and positions rather than an aggregate artifact;
2. the position-scarcity failure is directly attributable to replacement/context specification and should be repaired there;
3. the uncertainty miss belongs first to Forecast/replacement uncertainty calibration;
4. the appreciation/decline failure could arise from Forecast trajectory updating, overlapping horizon targets, replacement movement, or fixed time weighting before it implies a nonlinear intrinsic-value transform.

Therefore the current evidence identifies a **specific Model B hypothesis worth retaining**, but does not justify activating Model B work yet. Model A remains the primary research candidate.

## 10. Recommended next research step

Before any Model B fit or production proposal:

1. refine the replacement candidate set so the league-level opportunity baseline responds correctly to flex/superflex scarcity while retaining the strong chronological error performance of `starter_threshold`;
2. recalibrate/diagnose uncertainty so nominal intervals are not systematically too wide;
3. decompose the expected-appreciation/decline failure into Forecast-update, replacement-movement, horizon-overlap, and fixed-weight components;
4. rerun the same frozen chronological benchmark after those Model A/replacement repairs;
5. only if a stable, repeated elite-tail residual remains after those repairs should the bounded nonlinear surplus transformation become a concrete Model B challenger.

Time preference should remain **unidentified** during this work. The fixed benchmark weights should not be promoted as an empirical discount curve. Market data should remain an external diagnostic and must not become an intrinsic training target.

## 11. Reproducibility artifacts

The PR #131 research harness produces:

- `model_a_benchmark_results.json` — full aggregate/fold metrics and conclusions;
- `model_a_benchmark_report.md` — generated benchmark summary;
- `model_a_point_in_time_rows.csv` — fold/asset/horizon/replacement/forecast/realized evidence rows;
- `fold_forecast_calibration.csv` — fold-level Forecast calibration provenance and parent evidence;
- `career_transition_coverage.csv` — historical source coverage.

The dedicated workflow is:

`.github/workflows/multiyear-intrinsic-model-a-research.yml`

The runner is:

`scripts/run_multiyear_intrinsic_model_a_benchmark.py`

with research-only compatibility entrypoint:

`scripts/run_multiyear_intrinsic_model_a_benchmark_entry.py`

## Guardrails preserved

- Model B was not fitted.
- Production intrinsic-value behavior was not changed.
- Production authority was not changed.
- Market values were not used as Model A inputs or targets.
- Team-specific roster need or strategic posture was not used inside intrinsic value.
- Forecast remains authoritative for football trajectory/uncertainty.
- Replacement remains a model-selection problem.
- Time preference remains unidentified.
- PR #131 remains a research-only draft pending explicit review and promotion authorization.
