# Forecast Recursive Uncertainty Carry-Forward — Production-Readiness Review

**Status:** production-readiness audit only; no production code change; no new production PR; PR #131 remains research-only, draft, non-authoritative, and unmerged.

## Executive conclusion

**Recommendation: DO NOT PROMOTE A NEW CHANGE.**

The research finding is valid for the PR #131 historical research recursion, but the specific structural defect does **not** exist in the current production Forecast implementation on `main` at `f38e2f029a0d9563986635012336434a3f9beb63`.

Current production already carries incoming Forecast uncertainty recursively. It does so by propagating the full second moment of the incoming Forecast distribution through the uncertain career-production multiplier and the survival mixture, then reconstructing variance from the propagated second moment. That is mathematically at least as complete as the narrow research repair that added the carried incoming-state variance term.

Because the requested prerequisite defect is absent in current production, the review stops here under the management stopping rule. Creating a production branch or PR would duplicate behavior that already exists and would risk introducing a regression.

## What the research found

PR #131 correctly identified a defect in its historical research Forecast recursion: deeper horizons recalculated uncertainty from the new transition without carrying the incoming forecast state's existing variance forward.

In that research harness:

- nominal-80% near-horizon coverage was **75.6%**;
- nominal-80% far-horizon coverage was **67.7%**;
- carrying recursive uncertainty forward changed far-horizon coverage to **83.0%**;
- near coverage remained **75.6%**;
- mean-path metrics were unchanged;
- the far/near Forecast-SD ratio moved from **0.858** to **1.303**.

The research repair was parameter-free and added the mathematically implied carried-state term:

`(survival * production_multiplier)^2 * incoming_state_variance`

That result remains useful research evidence, but it must not be confused with proof that current production lacked the same uncertainty propagation.

## Current production inspection

Current production authority is `src/fsffl/forecast/career.py`.

`apply_career_transition(...)` receives the full incoming `ForecastDistribution`. It computes:

- incoming second moment as `distribution.stddev**2 + distribution.mean**2`;
- career-multiplier second moment as multiplier variance plus multiplier mean squared;
- active second moment as the product of those two second moments;
- unconditional mean after survival;
- unconditional second moment after survival;
- next-horizon variance as `second_moment - mean**2`.

`build_multi_year_forecast(...)` then assigns the returned distribution to `current` and feeds that complete distribution into the next transition. The incoming variance therefore survives each recursive horizon.

This implementation also propagates uncertainty in the career multiplier and handles survival as an explicit zero-production mixture. It does not need a new arbitrary long-horizon uncertainty coefficient.

The Forecast package publicly exports `apply_career_transition` and `build_multi_year_forecast` as its canonical multi-year Forecast primitives.

## Why this belongs to Forecast

The existing implementation is correctly located in Forecast. It represents uncertainty in future football production caused by:

- uncertainty already present in the incoming football projection;
- empirical dispersion and estimation uncertainty in the career transition;
- survival/attrition in the future football state.

No Value, market, team-fit, contender, Decision, Search, or owner-preference input is involved.

## Mean invariance

The production variance propagation is separate from the production mean calculation. Carrying the incoming second moment affects `stddev`, not the expected production mean beyond the already-authoritative survival and conditional-production transition.

The research repair likewise left mean Forecast metrics unchanged. There is therefore no evidence-supported reason to alter production means as part of this component.

## Research calibration versus production readiness

The historical 67.7% -> 83.0% result demonstrates that carrying incoming uncertainty matters in the research recursion. It is **not** a current-production before/after result because current production already performs recursive uncertainty propagation.

A new shadow candidate would therefore be artificial: its intended behavior is already present in production. Replacing production with an equivalent alternate formula merely to reproduce a delta would not constitute a legitimate promotion test.

## Chronology and subgroup evidence

The research comparison was point-in-time and chronological. The uncertainty-only repair improved the direct target without changing mean-path metrics.

The same research program found the under-propagation issue most visibly at deeper horizons, including elite QBs, while aging RBs provided an important counterexample against a universal deterministic persistence rule. Later player-specific and innovation studies continued to support keeping unresolved persistence primarily in uncertainty rather than inventing another mean rule.

Those findings support the **concept** of recursive uncertainty carry-forward. They do not establish a missing production implementation because current production already carries that uncertainty.

## Double-counting / integration review

No new production uncertainty is being introduced by this review, so there is no new double-counting path to repair.

The current authority boundary remains correct:

- Forecast owns football projection uncertainty;
- Value may consume Forecast outputs but should not independently recreate Forecast uncertainty;
- Simulation owns stochastic competitive outcomes rather than re-defining the Forecast distribution;
- Decision confidence may describe decision/evidence completeness but should not multiply Forecast variance as a second football-risk term;
- presentation may display uncertainty but is not authoritative.

Because no Forecast output is changing, downstream serialization, cache fingerprints, API contracts, Simulation inputs, Value inputs, report confidence, and presentation bands receive no incremental uncertainty from this review.

No unrelated downstream redesign is justified.

## Production acceptance gates

These gates were defined for a candidate promotion. The prerequisite defect check prevents entry into candidate validation because current production already has the behavior.

| Gate | Result | Reason |
|---|---|---|
| Structural correctness | **PASS — current production** | Incoming variance is retained through recursive second-moment propagation. |
| Mean invariance | **PASS — current production** | Variance propagation is distinct from mean propagation. |
| Calibration improvement | **RESEARCH PASS / PRODUCTION DELTA N/A** | Research repair improved far coverage 67.7% -> 83.0%; there is no missing production behavior to compare against. |
| No pathological width | **RESEARCH PASS / PRODUCTION DELTA N/A** | Near coverage stayed 75.6%; mean metrics were unchanged; no new production widening is proposed. |
| Chronological robustness | **RESEARCH-SUPPORTED** | PR #131 used strict point-in-time folds. |
| Subgroup safety | **RESEARCH-SUPPORTED; NO NEW PROD CHANGE** | No candidate production delta exists to create subgroup regression. |
| No double counting | **PASS FOR THIS REVIEW** | No new uncertainty term is introduced downstream. |
| Market independence | **PASS** | Production career recursion contains no market/value signal. |
| Architectural fit | **PASS** | Logic already resides in authoritative Forecast code. |
| Operational safety | **PASS / NO-OP** | No code, serialization, caching, persistence, API, latency, or memory behavior changes. |

## Production PR decision

**No production branch or PR was created.**

A production PR would be redundant because the structural carry-forward behavior is already present on current `main`.

PR #131 remains the research provenance for the historical calibration finding and is not merged by this review.

## Management decision

**DO NOT PROMOTE a new recursive-uncertainty change.** Treat this production-readiness item as already satisfied by the current Forecast architecture, with PR #131 supplying supporting historical evidence that recursive uncertainty carry-forward is the correct structural behavior.

Do not proceed automatically to the stable player-level Forecast correction or Model A. Return to management before beginning the next component.
