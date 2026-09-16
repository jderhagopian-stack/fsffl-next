# FSFFL NEXT - Regularization Stability & Developmental Calibration Final Research Handoff

Status: **RESEARCH COMPLETE - KEEP C=0.25 AS-IS**

Authority: research-only follow-up under the 2026-09-15 management directive. This document does not authorize merge, deployment, production-authority change, or modification of the active implementation branch.

## 1. Management answer in plain English

The original I1 regularization choice at `C=0.25` deserved a broader test because the integrated study had selected it from only `{0.25, 1.0, 4.0}` and `0.25` was the strongest-regularization edge of that grid.

The expanded study tested a wider predeclared grid over rolling point-in-time history and one preauthorized lower-bound extension. The result is not that `0.25` is numerically best at every metric. Instead, it survives as the best governed **balanced** setting.

- Stronger regularization (`C < 0.25`) modestly improves some probability/state calibration metrics and improves developmental recall, but materially worsens anticipated-production MAE and bias.
- Weaker regularization (`C > 0.25`) improves anticipated-production MAE but worsens state calibration and does not improve developmental hit recovery.
- A separate higher-C treatment for developmental players moves in the wrong direction: it loses real developmental successes rather than recovering additional ones.
- A genuinely untouched source-2023 / horizon-1 -> 2024 confirmation does not reveal a reason to overturn the frozen selection.

Final disposition: **KEEP C=0.25 AS-IS.**

## 2. What C controls in I1

I1 uses scikit-learn `LogisticRegression` with L2 regularization and `lbfgs` optimization. `C` is inverse regularization strength, so lower `C` means stronger coefficient shrinkage.

The same `C` governs:
1. the binary persistence model; and
2. the four ordered conditional-on-persistence threshold models (`useful+`, `starter+`, `premium+`, `elite`).

Rich-evidence and reduced-evidence paths are fitted separately but use the same regularization parameter. No class weighting is specified. Numeric transforms are governed/manual transforms rather than a generic `StandardScaler`. Categorical fields are vectorized through `DictVectorizer`.

## 3. Expanded rolling-history study

Primary grid: `{0.0625, 0.125, 0.25, 0.5, 1.0}`.

Because `0.0625` won the primary state-Brier comparison at the lower edge, the protocol allowed exactly one extension to `0.03125`. That extension worsened state Brier again, establishing `0.0625` as an interior calibration optimum inside the bounded search rather than another unresolved boundary.

Resolved rolling rows: **8,738**.

| C | State Brier | State log loss | Production MAE | Developmental recall |
|---:|---:|---:|---:|---:|
| 0.03125 | 0.121526 | 1.531268 | 39.877 | 75.9% |
| 0.0625 | **0.121362** | 1.526337 | 39.122 | 73.3% |
| 0.125 | 0.121375 | **1.525228** | 38.573 | 70.1% |
| 0.25 | 0.121514 | 1.527402 | 38.170 | 66.6% |
| 0.5 | 0.121727 | 1.536997 | 37.889 | 63.7% |
| 1.0 | 0.122033 | 1.555102 | **37.685** | 63.7% |

The apparent lower-C state-probability gains are small and do not satisfy the predeclared holistic global-change rule because production MAE and absolute bias worsen. Conversely, higher C improves production MAE but degrades state probability quality. `C=1.0` also exceeds the subgroup safety guard on reserve/practice state-Brier deterioration.

No global challenger qualifies for promotion.

## 4. Developmental-player treatment

Predeclared developmental cohort: young + low-end production using only prediction-time facts.

Developmental evaluation rows: **750**.
Developmental factual useful+ successes: **311**.

| Treatment | Real hits | False positives | Recall | Developmental useful Brier | Developmental state Brier |
|---|---:|---:|---:|---:|---:|
| Global C=0.25 | **207** | 242 | **66.6%** | **0.25879** | **0.12148** |
| Developmental C=0.5 | 198 | 236 | 63.7% | 0.25927 | 0.12230 |
| Developmental C=1.0 | 198 | 231 | 63.7% | 0.26013 | 0.12333 |

Required plain-English tradeoff:

- `C=0.5` caught **no additional real developmental successes**. It lost **9 real hits** while removing **6 false positives**.
- `C=1.0` also lost **9 real hits** while removing **11 false positives**.

The stage-specific hypothesis therefore fails its first promotion requirement. Less regularization for developmental rows does not recover more genuine breakouts and also worsens developmental probability error.

No career-stage-aware override qualifies.

## 5. Untouched confirmation

Source season: **2023**.
Horizon: **1**.
Target season: **2024**.

Rows: **558**.
Resolved: **521** (93.37%).

- State Brier: **0.113810**
- State log loss: **1.372939**
- Production MAE: **35.4719**
- Production bias: **-2.9110**

Developmental confirmation:
- rows: **28**
- factual developmental successes: **11**
- true hits: **8**
- false positives: **9**
- recall: **72.7%**
- developmental state Brier: **0.103887**
- developmental useful Brier: **0.236947**

This untouched confirmation is coherent with the frozen decision and does not expose a hidden reason to change `C=0.25`.

## 6. Final research disposition

**KEEP C=0.25 AS-IS**

Reason: expanded strict point-in-time evidence shows no alternative regularization setting with a clear, repeatable, holistic advantage. Stronger regularization buys modest probability-calibration and developmental-recall gains at a clear production-error/bias cost. Weaker regularization buys production-MAE improvement at a clear state-calibration cost. A separate less-regularized developmental treatment loses real hits. The untouched confirmation remains coherent.

This is a research conclusion, not a production authorization.

## 7. Implementation handoff

Because the active implementation candidate is already frozen at `C=0.25`, this study calls for **no implementation parameter change**.

Management can allow the existing implementation-validation work to continue unchanged with respect to regularization. No special career-stage override should be added. No new coefficient, youth bonus, named-player adjustment, market signal, owner behavior, trade behavior, or Value/Shapley feedback should be introduced from this study.

Production authority remains unchanged. PR #148 remains research-only and must not be merged as production code.
