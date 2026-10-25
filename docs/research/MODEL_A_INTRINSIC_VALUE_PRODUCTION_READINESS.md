# Model A FSFFL Intrinsic Value — Production-Readiness Review

**Status:** production-readiness audit only; Model A remains research-only/non-authoritative; no production Value change; no production PR; PR #131 remains research provenance, draft, open, and unmerged.

## Executive conclusion

**Recommendation: DO NOT PROMOTE Model A on the current production contract.**

The central Model A research result remains strong and real: the transparent three-year replacement-adjusted surplus architecture materially outperforms the chronologically refit affine control overall, improves every one of the 17 chronological holdout folds under the context-valid `marginal_lineup_opportunity` replacement definition, preserves Superflex/1QB structural scarcity, retains market independence, and remains substantially more accurate after removing the most extreme 1% of predicted/realized observations.

The two old 4-of-6 economic failures should not be treated identically. The expected-appreciation/decline failure is best classified as a **known limitation rather than a hard Intrinsic Value blocker**: the prior decomposition localizes the failure primarily to changes in upstream Forecast trajectories across adjacent vintages, while equal annual weights do not repair it and suppressing replacement updates makes it worse. Intrinsic Value is a point-in-time fundamental football-economic coordinate, not a promise to predict its own next vintage or future market price.

The elite-QB longevity failure is more serious. Under the context-valid Model A, the elite-QB rank signal is positive but weak (`~0.1948` versus the old `>0.25` research check), all-QB MAE improves only about **0.8%** versus the affine control, and all-QB rank ordering is worse than the affine ordering even though RB/WR/TE results improve materially. The historical research universe also contains several pathological deeper-horizon Forecast paths—concentrated heavily among QBs—that can create raw Model A surplus values far beyond the realized historical range. The latest Value-residual study correctly found no robust evidence for a QB bonus, superstar premium, or nonlinear Value correction, so this review does not patch that problem in Value.

Most decisively for production readiness, the exact current authoritative live Forecast runtime does **not currently publish a governed multi-year Forecast path**. It publishes the current full-season ensemble (plus a league-regular-season derivative). Production contains reusable multi-year career-transition primitives and an evidence fitter, but those are not wired into the current live Forecast evidence bundle with an authoritative current-player transition-selection/materialization contract. Model A requires Years 1–3 of authoritative Forecast truth and Years 1–3 of governed league replacement paths. Letting Value privately generate those future Forecasts would cross the Forecast/Value authority boundary and would make the production implementation differ materially from the reviewed architecture.

The current live NEXT-3 runtime is likewise a market-value runtime; the action-facing Decision contract already reserves a distinct intrinsic/franchise-value dimension and fails closed when that evidence is absent. That is the correct present behavior. Model A should not be inserted by bypassing the missing authoritative multi-year Forecast contract.

Therefore no clean production Model A PR is created. The blocker is primarily **production Forecast/integration authority**, with **elite-QB long-horizon safety** as an unresolved economic/Forecast interaction. It is not lack of aggregate Model A signal, market contamination, or a need for Model B.

## 1. Exact state inspected

At the start of this review:

- exact current `main`: `f38e2f029a0d9563986635012336434a3f9beb63`;
- live Render deployment: the same exact commit `f38e2f029a0d9563986635012336434a3f9beb63`;
- PR #131 before this report: `ff8a47d90ba1877da774003ddbf58a6a32a350fc`, open, draft, unmerged, research-only;
- the only other open PR inspected was #132, roadmap/documentation-only and non-overlapping with this review.

Recent production work #128–#130 made long-term intrinsic franchise value an explicit action-facing Decision dimension and made final Simulation-backed Decision completeness fail closed when required dimensions are missing. This review preserves that newer work.

## 2. What current production Intrinsic Value actually is

The authoritative intrinsic conversion primitive on current `main` lives in `src/fsffl/value/intrinsic.py`.

It is a one-Forecast affine mapping:

`intrinsic mean = intercept + economic_units_per_forecast_unit × Forecast mean`

with uncertainty:

`intrinsic variance = (slope × Forecast SD)^2 + conversion residual SD^2`.

The mapping records:

- the Forecast model version it was calibrated against;
- slope;
- intercept;
- residual standard deviation;
- conversion model version;
- evidence-through season;
- sample size.

The function fails if the Forecast postdates the Value cutoff or if the mapping was calibrated for a different Forecast model version. It therefore already has useful provenance/version safety.

This affine primitive remains the correct research control. However, current live product Value evidence is market-focused: `CurrentMarketValueRuntimeResult` contains market estimates/cardinal scores, and the Product-layer `cardinal_market_profiles(...)` adapter currently populates `AssetValueProfile.market_price` rather than live player `intrinsic_value`. The Decision contract correctly treats intrinsic as a separate coordinate and marks it incomplete when the profile lacks it.

Accordingly, Model A would not merely swap one arithmetic expression inside a fully populated live intrinsic runtime. Production promotion would require a governed current intrinsic runtime and its upstream multi-year Forecast evidence.

## 3. Model A definition

Model A is intentionally simple and transparent.

For each of three future seasons:

`surplus_y = max(0, player Forecast_y - replacement Forecast_y)`

The research benchmark combines those annual surplus terms as:

`raw Model A = 1.00 × surplus_1 + 0.85 × surplus_2 + 0.70 × surplus_3`.

The canonical context-valid replacement definition is:

`marginal_lineup_opportunity`.

Its league-format behavior comes from optimized lineup opportunity/replacement mechanics, not a QB multiplier or team-specific need. Forecast survival is already embedded in future Forecast means and is not multiplied through again by Value.

The `1.00 / 0.85 / 0.70` weights remain transparent Version-1 benchmark policy parameters. This review does **not** claim they are empirically identified universal time preference.

## 4. Predeclared production-readiness gates

Before new shadow/stress output was inspected, this review froze the following gates:

1. **Control improvement:** at least 15% aggregate chronological MAE improvement versus the exact affine control.
2. **Chronological stability:** Model A improves at least 70% of chronological folds and no fold is more than 10% worse.
3. **Market independence:** no Broad Market/League Market input enters Model A; historical diagnostics must retain material disagreement rather than reveal a disguised market clone.
4. **Format structure:** Superflex/1QB effects must arise through governed replacement/opportunity mechanics.
5. **Economic usefulness:** all four previously passing checks must remain passing; the two known failures are separately classified as blockers or limitations rather than automatically waived or automatically fatal.
6. **No double counting:** no duplicate survival, scarcity, Forecast uncertainty, Team Utility, market, or owner preference.
7. **Scale/monotonicity:** raw Model A must remain monotone in weighted non-negative replacement-adjusted football surplus; display transformation, if needed, must be separate.
8. **Elite-tail safety:** no hidden superstar/QB bonus or penalty and no unexplained tail rule.
9. **Outlier robustness:** the aggregate advantage must not disappear when the most extreme 1% of historical predicted/realized observations are excluded.
10. **Operational safety:** no material latency/memory/serialization/cache/API regression and no module may manufacture another module's authority.
11. **Interpretability:** the result must be explainable as three-year weighted replacement-adjusted expected football surplus.
12. **Completeness/confidence:** missing required Forecast/replacement evidence must fail closed rather than expose a partial value as complete.

## 5. Canonical control comparison

The governed context-valid canonical benchmark remains:

| Metric | Affine control | Model A | Relative improvement |
|---|---:|---:|---:|
| Chronological MAE | 26.968 | **20.307** | **24.7%** |
| Holdout observations | 9,430 | 9,430 | — |
| Chronological holdouts | 17 | 17 | — |

The 24.7% reduction decisively clears the 15% production-review threshold.

The canonical Model A uncertainty calibration remains inside its prior frozen envelope at approximately **87.3% coverage for a nominal 80% interval** after the existing rolling point-in-time calibration. Current production Forecast itself already carries recursive uncertainty structurally; this review does not add another survival or uncertainty term.

## 6. Chronological fold stability

Reconstruction from the governed PR #131 point-in-time artifact reproduces the exact canonical aggregate results and shows Model A beating the affine control in **17 of 17** chronological holdouts:

| Target season | Model A MAE | Affine MAE | Improvement |
|---:|---:|---:|---:|
| 2006 | 21.477 | 27.428 | 21.7% |
| 2007 | 23.674 | 29.436 | 19.6% |
| 2008 | 21.706 | 27.263 | 20.4% |
| 2009 | 20.409 | 27.394 | 25.5% |
| 2010 | 20.141 | 27.642 | 27.1% |
| 2011 | 21.475 | 28.435 | 24.5% |
| 2012 | 20.160 | 26.675 | 24.4% |
| 2013 | 24.873 | 28.384 | 12.4% |
| 2014 | 20.910 | 27.381 | 23.6% |
| 2015 | 18.499 | 26.208 | 29.4% |
| 2016 | 18.598 | 24.888 | 25.3% |
| 2017 | 16.159 | 23.922 | 32.5% |
| 2018 | 22.174 | 29.586 | 25.1% |
| 2019 | 18.760 | 25.176 | 25.5% |
| 2020 | 19.301 | 26.050 | 25.9% |
| 2021 | 18.882 | 26.724 | 29.3% |
| 2022 | 18.681 | 26.302 | 29.0% |

Chronological stability therefore **PASSes decisively**. There is no holdout fold regression.

## 7. Rank and position behavior

Across the 17 scored holdouts, the aggregate Spearman relationship with realized three-year replacement-adjusted surplus is approximately:

- Model A: **0.531**;
- affine/Y1 ordering: **0.526**.

So Model A does not win primarily by reshuffling every player. Its larger benefit is improving the *magnitude* of fundamental football-economic value through replacement adjustment and a multi-year path.

By position:

| Position | N | Model A MAE | Affine MAE | MAE improvement | Model A rank signal | Affine rank signal |
|---|---:|---:|---:|---:|---:|---:|
| QB | 1,191 | 56.932 | 57.398 | **0.8%** | ~0.521 | ~0.569 |
| RB | 2,860 | 20.450 | 27.612 | **25.9%** | ~0.536 | ~0.530 |
| WR | 3,452 | 14.825 | 23.235 | **36.2%** | ~0.536 | ~0.538 |
| TE | 1,927 | 7.282 | 13.894 | **47.6%** | ~0.431 | ~0.430 |

This is a major production-readiness nuance. The overall Model A result is excellent, but its advantage is not uniform. In particular, all-QB error is almost unchanged versus the affine control and all-QB rank ordering is worse.

## 8. Economic-usefulness checks

Canonical `marginal_lineup_opportunity` results remain:

| Economic check | Result | Statistic |
|---|---|---:|
| Aging RB vs young RB | **PASS** | 68.28% directional accuracy |
| Developing WR | **PASS** | rank correlation ~0.5133 |
| Developing TE | **PASS** | rank correlation ~0.3981 |
| Superflex / 1QB scarcity | **PASS** | positive QB relative gain in 17/17 folds |
| Elite-QB longevity | **FAIL** | rank correlation ~0.1948 |
| Expected appreciation / decline | **FAIL** | 44.6% direction; ~-0.269 correlation |

Model A remains 4/6 under the old research scoreboard, but this production review does not mechanically require 5/6.

## 9. Elite-QB longevity failure — classification: STRUCTURAL/READINESS BLOCKER TODAY

The elite-QB failure is not evidence for a QB bonus. The latest Value residual-identification work explicitly rejected that interpretation; the unresolved elite-tail residual actually points toward possible compression, and that pattern itself failed influence-robustness, so no nonlinear Value rule is justified.

The production concern is instead that the context-valid replacement architecture does not materially improve QB outcomes over the affine control:

- all-QB MAE improvement is only about **0.8%**;
- all-QB Model A rank signal (~0.521) is below the affine ordering (~0.569);
- the elite-QB subset's dedicated longevity rank correlation is only ~**0.1948**;
- historical deeper-horizon Forecast paths include extreme QB outliers that can dominate individual Model A values.

This is too important to waive merely because the global MAE is much better. Superflex structurally makes long-lived elite quarterbacks one of the most economically consequential asset classes. A supposedly authoritative intrinsic coordinate should not be promoted while its biggest positional class of long-duration assets shows essentially no MAE improvement over the existing control and weaker ranking.

The upstream Forecast audit provides an important nuance: elite-QB **one-step updates are generally informative** (about 81% direction and ~28% revision-error improvement over no update), so the failure is not a simple claim that Forecast knows nothing about elite QBs. The weakness is deeper-horizon/trajectory economics and current live multi-year materialization.

**Classification: production-readiness blocker under the current evidence/contract.** This task does not repair it.

## 10. Appreciation / decline failure — classification: KNOWN LIMITATION, NOT A HARD INTRINSIC BLOCKER

The adjacent-vintage check remains poor:

- directional accuracy ~**44.6%**;
- change correlation ~**-0.269**.

However, the existing decomposition strongly argues against treating this as proof that the Model A *level* architecture is wrong:

- equal annual weights move the diagnostic only to about 50.2% / -0.240;
- suppressing replacement-update movement makes it worse (~34.6% / -0.332);
- diagnostically suppressing the shared Forecast-update component improves it to about **68.5% / +0.205**.

That does **not** mean Forecast updates should be frozen. It means the failure is primarily about how the upstream multi-year Forecast path changes between vintages, not a demonstrated Value-owned transform.

Moreover, FSFFL Intrinsic Value answers: “What is the player's fundamental replacement-adjusted football-economic value at this cutoff?” It is not Broad Market Value and it is not a future-price target. Requiring a point-in-time intrinsic coordinate to predict the direction of its own next vintage as a hard gate is conceptually stronger than the product purpose requires.

**Classification: real known limitation, to be surfaced in confidence/completeness and monitored, but not independently fatal to Model A production readiness.**

## 11. Market independence

Market remains a diagnostic only and never enters Model A fitting or replacement construction.

Across the three safe point-in-time market-overlap folds:

- Pearson Model-A/market correlation ~**0.689**;
- Spearman ~**0.654**;
- material percentile disagreement ~**38.75%**;
- market adds incremental information in all available overlap folds.

This is a useful result: Model A is related to market, as a sensible football-value coordinate should be, but it is not a disguised market calculator. The fact that market adds incremental information is not grounds to train Intrinsic to market; it validates preserving the separate Broad Market and Intrinsic coordinates.

**Market independence: PASS.**

## 12. Outlier and elite-tail robustness

The latest residual study already showed that an apparent elite-tail nonlinear residual is too sensitive to influential observations to justify Model B. This review additionally tested whether Model A's *overall advantage versus affine* disappears when the most extreme historical cases are removed.

On the 17 scored holdouts:

- full Model A advantage: **24.7%**;
- excluding the top 1% by predicted Model A value: approximately **28.9%** improvement remains;
- excluding the top 1% by realized value: approximately **26.9%** remains;
- excluding the top 1% by Year-1 Forecast magnitude: approximately **27.0%** remains;
- excluding the worst 1% of Model A absolute errors: approximately **30.8%** remains on the common retained rows.

Therefore a handful of stars/outliers do **not** explain the aggregate advantage.

But individual-path safety is still a problem for the upstream deep Forecast. In the historical research reconstruction, raw Model A reaches approximately **1,341 weighted surplus points**, while the largest realized target in the same scored universe is about **587**. One illustrative 2013 QB path begins below replacement in Year 1 (~66 forecast vs ~121 replacement) but jumps to roughly **1,004** forecast points in Year 2 and ~840 in Year 3, producing a Model A value of ~1,341 while realized three-year replacement-adjusted surplus is zero.

That is not a reason to cap Model A in Value. It is evidence that production must receive a governed, production-safe multi-year Forecast path rather than reusing research-only transition materialization blindly.

**Aggregate outlier robustness: PASS. Individual live multi-year Forecast safety: NOT ESTABLISHED.**

## 13. Current authoritative Forecast compatibility — decisive operational gate

Current production contains two relevant pieces that must not be confused:

1. `forecast/career.py` and `forecast/career_calibration.py` provide governed **primitives** for fitting/applying a career transition and recursively propagating a `ForecastDistribution`.
2. `forecast/current_runtime.py` is the current **authoritative live Forecast runtime** used by the private beta.

The live runtime acquires multiple current-season providers, constructs the authoritative current ensemble, scores it under league rules, adds empirical current-season uncertainty, and optionally derives a fantasy-regular-season horizon. It does **not** currently publish Years 2 and 3 of an authoritative player career path, nor a current transition-evidence selector/provenance bundle for those years.

The historical PR #131 harness built fold-local multi-year trajectories from a historical transition panel. That was appropriate for research, but the panel-driven materialization is not presently a current live Forecast authority.

Model A cannot solve this by calling Forecast calibration functions privately from Value. Doing so would make Value decide:

- which career-transition cohort applies;
- what evidence cutoff/calibration artifact is authoritative;
- how to handle cohort fallback;
- how to materialize Years 2 and 3;
- what current population forms each year's replacement path.

Those are Forecast (and league-structural replacement) responsibilities, not Value coefficients.

**Current production-equivalent live Model A cannot therefore be produced without first exposing an authoritative multi-year Forecast path from Forecast.** That is a concrete production-contract blocker, not a request for new Model A research.

## 14. Current/live player shadow review

A trustworthy current-player shadow table was **not produced**, by design.

The live service is on the exact inspected production SHA, but its Forecast evidence contains only the authoritative current-season outputs described above. Producing a Lamar/Mahomes/aging-QB/elite-RB/young-WR/etc. three-year Model A table would require inventing or privately reconstructing Years 2–3 outside the current live Forecast contract.

That would make the shadow look more complete while violating the central authority rule this review is supposed to test.

The historical point-in-time artifact was therefore used for archetype, fold, position, outlier, and economic diagnostics, but **not** mislabeled as a current 2026 live shadow.

The inability to produce the required current-player Model A shadow from production-authoritative Forecast evidence is itself a failed readiness gate.

## 15. Scale and normalization decision

No production display normalization is promoted in this review.

The clean underlying Model A economic quantity is already interpretable:

**weighted three-year replacement-adjusted expected fantasy-point surplus**.

If Model A later clears readiness, that raw quantity should be the authoritative Intrinsic economic output on its own explicit `ValueScale`, for example a versioned weighted-surplus unit. It should not be rescaled to 0–10,000 by reference to Broad Market Value.

If Product later wants a friendlier display coordinate, it should be a separate monotone display transform with explicit version/provenance. The raw economic output and display coordinate must not be conflated.

There is no evidence-based reason in this review to anchor Intrinsic to Stats Guy, FantasyCalc, DynastyDealer, DynastyProcess, startup ADP, or another market scale.

## 16. Double-counting review

The Model A research architecture itself respects the main boundaries:

- **survival:** already embedded in future Forecast means; no second Value multiplier;
- **Forecast uncertainty:** consumed as Forecast uncertainty; not recreated as another Value risk channel;
- **replacement/scarcity:** one `marginal_lineup_opportunity` mechanism; no QB premium layered on top;
- **Team Utility:** absent from raw intrinsic economics;
- **competitive posture:** absent;
- **owner preference/Behavioral Intelligence:** absent;
- **Broad/League Market Value:** absent from intrinsic construction and fitting.

The production Decision layer also keeps current market economics and long-term intrinsic economics as separate action-facing evidence dimensions rather than blending them into a master score.

**No-double-counting architecture: PASS.**

## 17. Decision, API, cache and operational integration

Current Decision integration is structurally ready for a future intrinsic source:

- `AssetValueProfile` has a distinct `intrinsic_value` field;
- trade economics sums intrinsic and market concepts separately and requires same-scale compatibility within each concept;
- economic net emits no partial delta when either package lacks complete evidence;
- Decision materiality consumes intrinsic exactly once;
- the product decision-dimensions contract labels it `intrinsic_franchise_value` under NEXT-3 Value;
- Simulation-backed final disposition fails closed if the long-term intrinsic dimension is unavailable.

That is the desired behavior and should not be redesigned.

A future Model A promotion would nevertheless require:

1. authoritative current multi-year Forecast evidence with model versions/provenance;
2. current league-format replacement paths for each horizon;
3. an explicit raw Intrinsic `ValueScale`;
4. a current intrinsic runtime that adds `IntrinsicDynastyValueEstimate` to `AssetValueProfile` while leaving market estimates untouched;
5. model/fingerprint changes so cached downstream economics/Decision artifacts invalidate when Forecast/Value versions change;
6. tests proving missing player or replacement paths leave intrinsic incomplete rather than substituting zero/market value;
7. stable API serialization of the existing intrinsic dimension (no new master score).

The arithmetic itself is cheap. The blocker is authoritative evidence/materialization, not computational latency.

## 18. Acceptance-gate results

| Gate | Result | Finding |
|---|---|---|
| Control improvement | **PASS** | 20.307 vs 26.968 MAE; 24.7% improvement. |
| Chronological stability | **PASS** | 17/17 holdouts improve; no fold regression. |
| Market independence | **PASS** | No market inputs; ~38.75% material disagreement in overlap data. |
| Format structure | **PASS — research architecture** | SF/1QB QB relative gain positive in 17/17 folds through replacement opportunity. |
| Aging-RB behavior | **PASS** | ~68.28% directional check. |
| Developing WR behavior | **PASS** | ~0.5133 rank signal. |
| Developing TE behavior | **PASS** | ~0.3981 rank signal. |
| Elite-QB longevity | **FAIL / BLOCKER** | ~0.1948 dedicated signal; only ~0.8% all-QB MAE gain; QB rank worse than affine. |
| Appreciation/decline | **FAIL / KNOWN LIMITATION** | Poor adjacent-vintage change signal, localized mainly to upstream Forecast path updates rather than proven Value transform. |
| No double counting | **PASS** | Survival/scarcity/market/Team Utility remain separated. |
| Scale/monotonicity | **PASS for raw Model A** | Weighted non-negative surplus is transparent and monotone; no market normalization required. |
| Aggregate outlier robustness | **PASS** | >26% control improvement remains under multiple 1% extreme-case exclusions. |
| Individual deep-path safety | **FAIL / NOT ESTABLISHED** | Historical transition materialization contains extreme future paths; no current live multi-year authority exists to validate against. |
| Operational current Forecast compatibility | **FAIL / BLOCKER** | Current live Forecast bundle lacks authoritative Years 2–3. |
| Current-player shadow | **FAIL / BLOCKER** | Cannot be produced without inventing non-authoritative future Forecasts. |
| Completeness/fail-closed | **PASS in current Decision contract** | Missing intrinsic keeps final Decision incomplete. |
| Interpretability | **PASS conceptually** | Value is three-year weighted replacement-adjusted expected football surplus. |
| Operational cost | **PASS conceptually** | Model A arithmetic is cheap; evidence authority is the issue. |

## 19. Production implementation decision

**No clean production branch/PR is created.**

Creating a Model A production PR now would require one of two unacceptable shortcuts:

- Value would privately manufacture Years 2–3 of Forecast truth; or
- the PR would quietly add new authoritative Forecast runtime behavior beyond the scoped Model A Value promotion.

Both would violate this review's authority boundary and make the supposedly narrow Value promotion depend on unreviewed upstream production behavior.

This is not a reason to reopen Model B, Forecast persistence, stable player-level correction redesign, League Market Value, Trade Grades, Buy Low/Sell High, or Search exploitation.

## 20. Evidence provenance and testing status

The historical production-readiness calculations reuse the governed PR #131 research artifact:

- workflow run: `34724290153`;
- artifact ID: `10307760543`;
- artifact name: `pr131-model-a-intrinsic-forecast-audit`;
- SHA-256: `3748c331105a163fc3a2ba9b4fc8439811e623a27e4258b06368eeba31f2779c`;
- repository suite from that successful research run: **1,153 passed, 2 warnings**.

The earlier Model A repair cycle also recorded:

- workflow run `34718486362`;
- artifact ID `10306016763`;
- repository suite **1,153 passed**.

This production-readiness review makes no production-code change, so there is no candidate production workflow/artifact to report. The documentation commit itself should run normal PR #131 CI/research automation; those runs are evidence that the report did not break the repository, not proof of economic validity.

## Management recommendation

**DO NOT PROMOTE Model A on the current production contract.**

The important distinction is that **Model A remains the preferred simple Intrinsic Value architecture**. The evidence against promotion is not that the model lacks signal; its overall historical advantage is unusually strong and chronologically stable, and no evidence supports a more complex Model B.

Promotion is blocked today because authoritative production does not yet expose the multi-year Forecast path Model A is supposed to consume, and the elite-QB/deep-horizon behavior is not safe enough to waive while that upstream contract is absent. Appreciation/decline should be carried forward as a disclosed limitation, not used to justify a Value patch.

Return to management here. Do not open another Value family and do not merge PR #131.