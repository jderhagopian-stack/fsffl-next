# Authoritative Multi-Year Forecast — Production-Readiness Review

**Status:** production-readiness review only; no production Forecast change; no production PR; PR #131 remains research-only, draft, open, and unmerged.

## Executive conclusion

**Recommendation: DO NOT PROMOTE the multi-year Forecast contract yet.**

The current repository contains sound, Forecast-owned multi-year **primitives**: empirical career-transition evidence, recursive mean propagation, explicit survival/attrition, and mathematically correct uncertainty propagation. The original NEXT-2 exit review correctly established those primitives as part of the Forecast authority layer.

However, the current live authoritative Forecast runtime does **not** materialize a governed Year-2/Year-3 player path. It produces the current-season authoritative ensemble (and a regular-season derivative), but it has no production contract that selects the applicable career-transition evidence for each current player, applies a governed fallback/pooling hierarchy, materializes Years 2 and 3, records that selection provenance, or publishes completeness for those horizons.

More importantly, the later PR #131 historical work showed that the research materialization of deep career paths can produce pathological individual trajectories, concentrated especially among QBs. That research harness was not line-for-line the current production `career.py` path: it used a research-only transition selector/calibration wrapper and its own recursive `forecast_one(...)`. Therefore the strong historical Model A results do **not** constitute validation of an exact production-authoritative Year-2/Year-3 runtime.

This resolves the requested A/B distinction as **B**:

> The production multi-year Forecast itself is not yet sufficiently materialized and validated for authoritative downstream use. Exposing a schema around the existing primitives would not solve the missing authority; it would merely make ungoverned Year-2/Year-3 estimates look authoritative.

No contract-only production PR is created. Value must continue to fail closed rather than privately manufacture future Forecast truth.

## 1. Exact state inspected

At the start of this review:

- exact current `main`: `f38e2f029a0d9563986635012336434a3f9beb63`;
- live Render deployment: the same exact commit;
- PR #131: `d04e70fc53e43ad8fc2a3311ccdade92961e6f7d`, open, draft, mergeable, unmerged, research-only;
- PR #132 remains the only other open PR and is roadmap/documentation-only.

No newer production Forecast implementation superseded the inspected code.

## 2. Current Forecast authority in plain English

### Current-season authority

`src/fsffl/forecast/current_runtime.py` is the live authoritative current-season Forecast runtime. It:

1. acquires independent current projection sources concurrently;
2. normalizes them to canonical player observations;
3. requires at least two independent sources;
4. builds the authoritative live ensemble;
5. applies league scoring;
6. applies empirical season fantasy-point uncertainty;
7. optionally derives the fantasy regular-season horizon;
8. records source coverage, failures, evaluation cutoff, and model version.

`LiveForecastRuntimeResult` currently exposes:

- `raw_ensemble`;
- `fantasy_point_forecasts`;
- `fantasy_regular_season_forecasts`;
- provider/coverage evidence;
- `evaluation_as_of`;
- runtime model version.

It does **not** expose a governed Year-2 or Year-3 career path.

### Multi-year primitives

`src/fsffl/forecast/career.py` provides Forecast-owned multi-year primitives:

- `CareerTransitionEvidence`;
- `apply_career_transition(...)`;
- `build_multi_year_forecast(...)`;
- `MultiYearForecastPoint`.

The recursive implementation is structurally good. Each transition:

- applies conditional production change;
- applies survival as a zero-production mixture;
- carries incoming uncertainty through the full second moment;
- includes transition dispersion and estimation uncertainty;
- returns a new `ForecastDistribution`;
- feeds the complete distribution into the next horizon.

This is the correct authority location and contains no market, dynasty-value, roster-fit, contender, or owner-preference inputs.

### Calibration primitives

`src/fsffl/forecast/career_calibration.py` provides point-in-time cohort selection and evidence fitting. Narrow unsupported cohorts fail closed. The core deliberately does not hard-code universal career-stage or production thresholds; those definitions belong to a versioned calibration study.

The historical NEXT-2 calibration workflow also produced an empirical-Bayes research evidence table from the career-transition panel. That work established useful production primitives, not a live per-player transition selector.

## 3. Do Year 2 and Year 3 already exist internally?

**Mechanically, yes. Authoritatively, no.**

Given a base `ForecastDistribution` and an explicit tuple of `CareerTransitionEvidence`, `build_multi_year_forecast(...)` can generate arbitrary subsequent horizons.

What production does **not** currently have is the governed function that answers, for each current player and each next horizon:

- which exact transition cohort is authoritative;
- which point-in-time evidence artifact/version supplies it;
- what deliberate fallback/pooling rule applies when the narrow cohort is unsupported;
- how the player's state is updated between Year 1 -> Year 2 -> Year 3 for re-selection;
- how completeness is represented when evidence is unavailable;
- how the materialized path is versioned/cached/persisted for downstream reuse.

Therefore the missing link is not merely serialization. It is authoritative **selection + materialization + provenance**.

## 4. Why the original NEXT-2 PASS is not enough for this promotion

The NEXT-2 exit review correctly marked multi-year football treatment PASS because the architecture could roll forward explicit empirical career-transition evidence and kept Forecast/Value boundaries clean.

That review did not establish a current live multi-year runtime or a present-day per-player transition-selection contract. It also predated the much deeper PR #131 chronological multi-year audits.

PR #131 later showed two important things:

1. multi-year replacement-adjusted value has strong aggregate historical signal;
2. the historical career-path materialization can generate extreme deep-horizon trajectories, especially among QBs.

The PR #131 benchmark is not an exact production-runtime backtest. Its `FoldCalibration` and `forecast_one(...)` are research-only materialization logic built around the historical career panel. That means its Year-2/Year-3 errors cannot simply be relabeled as validation of current production `career.py`.

This is the key readiness gap.

## 5. Validation status by horizon

### Year 1

The current-season Forecast authority has real held-out evidence. The NEXT-2 modern benchmark used 2024 as training and 2025 as held-out evaluation. On the common 438-player cohort, the equal-weight baseline achieved approximately:

- MAE: **44.60**;
- RMSE: **62.13**.

The learned challenger improved only slightly and was correctly not promoted. Current production continues to use governed live multi-source ensemble behavior rather than a research-only learned weighting shortcut.

**Year-1 authority: established.**

### Year 2

PR #131 research produced direct deeper-horizon diagnostics, but through the research materialization path rather than an exact current production multi-year runtime. The canonical research baseline reported Year-2 MAE around **36.98** in its common-path trajectory diagnostics.

That is useful evidence that the underlying career-transition concept contains signal, but it is not sufficient to certify a live authoritative production Year-2 contract.

**Year-2 production authority: not established.**

### Year 3

The same limitation applies. PR #131 research reported Year-3 MAE around **35.56** for the canonical research baseline, but exact current-production materialization does not exist to validate.

**Year-3 production authority: not established.**

### Cumulative path

The PR #131 baseline cumulative common-path MAE was approximately **67.40**, and newer research variants could improve or worsen portions of the path. Again, this validates that multi-year path quality can be studied chronologically; it does not certify the missing live production selector/materializer.

**Cumulative production authority: not established.**

## 6. QB / deep-horizon assessment

This is the most important safety issue.

The Model A production-readiness review found:

- all-QB Model A MAE improved only about **0.8%** versus the affine control;
- all-QB rank signal was worse under Model A than affine;
- elite-QB longevity signal remained weak at roughly **0.195**;
- historical deep-horizon Forecast paths contained extreme individual QB trajectories.

One research example began below replacement in Year 1 and then jumped to roughly **1,004 fantasy points in Year 2** and roughly **840 in Year 3**, creating an enormous multi-year surplus despite no realized surplus.

That example came from the research materialization path, not a current live production contract. Therefore it does not prove `career.py` itself is mathematically wrong. It does prove that a current production selector/materializer must be validated before authority is granted; otherwise the same empirical cohort evidence can be combined into unsafe individual paths.

The appropriate classification is:

- **not a Value-owned QB premium problem**;
- **not evidence for a superstar override**;
- **not grounds for a new persistence model**;
- primarily an **unresolved Forecast materialization / deep-horizon safety problem**, with historical sparsity/uncertainty contributing.

**QB deep-horizon safety: NOT CLEARED.**

## 7. Uncertainty and survival

### Uncertainty

The production recursion itself is structurally correct. `apply_career_transition(...)` propagates the incoming second moment through an uncertain multiplier and survival mixture, then derives the next variance. This already includes the recursive carry-forward behavior that PR #131 separately validated as important.

The PR #131 uncertainty study showed that omitting carried variance led to deep-horizon undercoverage, while adding it moved far-horizon nominal-80% coverage from roughly **67.7% to 83.0%** without changing mean-path metrics.

Production already contains the correct structural propagation, so no new uncertainty coefficient is needed.

However, because there is no exact live Year-2/Year-3 materialization, **production-horizon calibration of the full live path is not yet established**.

### Survival

Survival/attrition belongs to Forecast and is already embedded in the recursive mean as a zero-production mixture. Downstream Value must not multiply survival again.

The production types explicitly retain cumulative survival probability in `MultiYearForecastPoint`.

**Survival architecture: PASS.**

## 8. Point-in-time chronology and provenance

The calibration primitives support strict evidence cutoffs. Historical transition outcomes must be resolved by the cutoff before entering fitted evidence. This is correct.

The missing production piece is not the ability to store provenance; it is the absence of a current authoritative transition-evidence artifact/selector linked to each materialized player horizon.

A future authoritative path must carry at minimum:

- player ID;
- base/current Forecast model version;
- forecast/evaluation cutoff;
- target season / season offset;
- resulting `ForecastDistribution`;
- cumulative survival probability;
- transition model/evidence version for each step;
- evidence-through season;
- selected cohort identity/fallback level;
- completeness status;
- source/provenance references already governed by Forecast.

## 9. Proposed authoritative contract shape

No production contract is promoted in this review, but the smallest correct future domain contract is clear.

Prefer a Forecast-owned object such as:

`AuthoritativeMultiYearPlayerForecast`

containing:

- `player_id`;
- `evaluation_as_of`;
- `base_forecast_model_version`;
- `career_model_version`;
- `status` / completeness;
- `points: tuple[MultiYearForecastPoint, ...]` for Years 1–3;
- transition-selection provenance for each point.

The existing `ForecastDistribution`, `CareerTransitionEvidence`, and `MultiYearForecastPoint` types should be reused rather than duplicated.

The materializer—not Value—must own transition selection and fail closed when an authoritative transition cannot be selected.

## 10. Single-authority review

No inspected Value/Decision/Search code currently needs to be removed for duplicating Years 2–3. The present problem is the opposite: downstream Decision correctly fails closed when intrinsic evidence is missing, and Value does not yet have an authoritative multi-year Forecast to consume.

That is the desired current failure mode.

Do not make Value call calibration helpers directly.
Do not make API/Product adapters choose transition cohorts.
Do not make Decision/Search reconstruct future paths.

## 11. Persistence, cache, and versioning

A future production implementation should treat the materialized multi-year path as a derived Forecast artifact keyed by the material Forecast inputs and model lineage, not as independent truth.

At minimum its cache/fingerprint must change when any of these change:

- authoritative current-season Forecast/version;
- player identity/position/age/experience inputs used by the selector;
- career-transition calibration artifact/model version;
- evidence cutoff;
- league scoring when the base fantasy-point Forecast changes.

Stale paths must never survive a model-version mismatch.

Whether the derived path is persisted or computed on demand is secondary to establishing a canonical fingerprint and single materializer. Because the arithmetic recursion itself is cheap, performance is not currently the blocker.

No new cache or persistence implementation is introduced because the underlying authoritative materialization has not cleared validity.

## 12. Current-player shadow review

A legitimate current-player Y1/Y2/Y3 shadow **cannot be produced from the current authoritative runtime**.

Year 1 is available. Years 2 and 3 would require this review to invent the missing transition selector/materializer, which is exactly the authority gap under examination.

Therefore no Lamar/Mahomes/young-QB/RB/WR/TE table is fabricated from research-only future paths.

The inability to produce the requested current-player shadow from production-authoritative evidence is itself a failed acceptance gate.

## 13. Consumer compatibility

Once Forecast eventually publishes a complete authoritative three-year path, it can support without changing authority boundaries:

- Model A Intrinsic Value;
- player career-trajectory views;
- Trade Center long-term consequences;
- My Team age/value-duration views;
- future player pages/reports.

Those consumers should receive the same Forecast-owned object or a read-only projection of it. They must not calculate future football truth independently.

Current Decision behavior is already correctly fail-closed when long-term intrinsic evidence is missing.

## 14. Predeclared acceptance gates

| Gate | Result | Finding |
|---|---|---|
| Authority | **FAIL / INCOMPLETE** | Forecast owns the primitives, but no live authoritative Y2/Y3 selector/materializer exists. |
| Current production compatibility | **PASS for primitives / FAIL for path** | Current-season runtime and career primitives are compatible, but not wired into one governed live path. |
| Year-2/3 validity | **FAIL / NOT ESTABLISHED** | Research evidence exists, but not for an exact current-production materialization. |
| QB deep-horizon safety | **FAIL / NOT CLEARED** | Research paths show extreme QB trajectories; exact production live path cannot yet be tested. |
| Uncertainty | **PASS structurally / calibration incomplete** | Production correctly propagates recursive variance; full live Y2/Y3 calibration is unavailable. |
| Survival | **PASS structurally** | Survival is Forecast-owned and embedded once in the recursive football distribution. |
| Chronology | **PASS in calibration/research design** | PIT cutoffs are governed; exact live multi-year validation is still absent. |
| Provenance | **PASS primitives / FAIL materialization** | Types carry versions/evidence cutoff; no current player-level selected-transition lineage exists. |
| Completeness | **FAIL for Y2/Y3 authority** | No authoritative materializer exists to emit complete/incomplete paths. |
| Operational performance | **NOT A BLOCKER** | Recursion is cheap; evidence selection/materialization is the issue. |
| Cache/persistence safety | **NOT YET IMPLEMENTED** | Must key on base Forecast + transition evidence/model lineage when authority exists. |
| Consumer safety | **PASS TODAY BY FAILING CLOSED** | Value/Decision do not currently manufacture missing Y2/Y3 truth. |

## 15. Production implementation decision

**No clean production PR was created.**

Creating one now would require either:

1. exposing `build_multi_year_forecast(...)` while leaving callers to invent transition selection, which violates single Forecast authority; or
2. silently promoting a current transition-selection/materialization policy that has not cleared exact production historical validation or QB deep-horizon safety.

Neither is acceptable.

This review does not reopen Model B, player-specific persistence, the failed stable player-level correction, or Intrinsic Value implementation.

## 16. Testing/evidence status

No production code was changed, so there is no candidate production workflow or candidate production artifact.

Relevant governed evidence includes:

- current repository full suite on the latest PR #131 report head before this review: **1,153 passed, 2 warnings**;
- PR #131 research workflow: `34739623960`, successful;
- PR #131 research artifact: `10311729246`, SHA-256 `ecb47343ed2c2d2ec75c9271e86dc5179716c6130e85f7339a95871ed875ca8f`;
- original NEXT-2 career calibration used approximately 14.9k historical transition rows and established the empirical career-transition primitives;
- the original NEXT-2 exit review classified multi-year football treatment as architecturally ready, but did not provide the missing current live selector/materializer now required by Model A.

The documentation commit from this review should run ordinary CI/PR #131 automation. Those tests establish repository integrity, not Year-2/Year-3 production validity.

## Management recommendation

**DO NOT PROMOTE the authoritative multi-year Forecast contract yet.**

The project should not treat this as a mere API exposure task. The missing work is a bounded Forecast implementation problem:

1. define one governed current-player transition-selection/materialization policy inside Forecast using the already-existing empirical evidence machinery;
2. validate that exact production materializer chronologically, with explicit Year-2/Year-3 and QB deep-horizon safety gates;
3. only then expose/cache the authoritative three-year path.

This is **not** a request for another broad Forecast research family. It is a narrow production-materialization validation gap discovered because Model A finally requires the Forecast authority contract to be real end-to-end.

Return to management here. Do not begin Model A implementation and do not create a downstream workaround.