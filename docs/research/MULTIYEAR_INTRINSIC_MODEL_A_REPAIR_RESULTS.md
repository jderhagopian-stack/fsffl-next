# Model A Repair Cycle Results — PR #131

**Status:** research-only and non-authoritative. No production intrinsic-value behavior or production model authority changed. Model B was not fitted.

## Audit identity

- Clean benchmark workflow run: `34718486362`
- Research artifact: `pr131-model-a-intrinsic-repair`
- Artifact ID: `10306016763`
- Full repository validation: `1153 passed`
- Historical career-transition panel: 14,876 rows, seasons 1999–2024
- Chronological holdouts: 17
- Forecast remains fold-local and uses only pre-cutoff transition evidence.
- Promotion thresholds were frozen before this repair run and were not changed after observing results.

## Replacement/context comparison

The raw-error winner and the structurally valid promotion candidate are deliberately reported separately. A replacement definition cannot become the promotion candidate solely because it minimizes MAE if it fails league-context scarcity behavior.

| Candidate | Model A MAE | Affine MAE | Improvement | Raw nominal-80% coverage | Calibrated coverage | SF/1QB scarcity |
|---|---:|---:|---:|---:|---:|---:|
| `starter_threshold` | 14.018 | 18.485 | 24.2% | 91.2% | 88.7% | FAIL |
| `marginal_lineup_opportunity` | 20.307 | 26.968 | 24.7% | 90.0% | 87.3% | PASS |
| `first_rostered_replacement` | 21.545 | 28.501 | 24.4% | 89.8% | 87.1% | PASS |
| `replacement_pool_quantile` | 45.492 | 52.293 | 13.0% | 81.0% | 81.4% | PASS |
| `eligible_slot_opportunity` | 20.491 | 27.194 | 24.7% | 90.0% | 87.3% | PASS |

`starter_threshold` remains the lowest-error raw candidate, but it remains structurally invalid because it does not respond correctly to 1QB versus Superflex opportunity cost. Among candidates that pass the context test, `marginal_lineup_opportunity` has the lowest MAE and is therefore the current research promotion candidate. The newly introduced `eligible_slot_opportunity` candidate also passes context sensitivity without positional bonuses and performs almost identically, but does not beat `marginal_lineup_opportunity` on error.

For the context-valid promotion candidate, repaired Model A has MAE **20.307** versus **26.968** for the chronologically refit affine control under the same target definition, a **24.7%** improvement. The predeclared material-improvement gate remains passed.

## League-level scarcity repair

The repaired/context-valid candidate passes the 1QB/Superflex sensitivity check in **17 of 17 chronological folds**.

- Mean QB relative intrinsic gain in Superflex versus 1QB: **31.7912**
- Mean non-QB relative gain: **0.0285**
- Folds with positive QB relative gain: **17/17**

This is league-level structural scarcity derived from lineup opportunity. It does not use team-specific roster need or strategic posture, and no arbitrary positional premium was introduced.

## Uncertainty diagnosis and repair

The original over-coverage was not primarily a fold-instability problem. For `marginal_lineup_opportunity`:

- Raw full nominal-80% coverage: **90.01%**
- Raw player-only coverage: **89.10%**
- Replacement share of propagated variance: **38.11%**
- Fold raw-coverage range: **87.90%–92.02%**
- Fold raw-coverage standard deviation: **1.27 percentage points**

Forecast uncertainty is already somewhat conservative, but adding replacement uncertainty/shared propagation pushes the complete interval wider. The repair uses a rolling point-in-time uncertainty calibration based only on standardized residuals from earlier folds. It does not inspect the current holdout and does not apply an arbitrary global shrink factor chosen after seeing the result.

Rolling scale factors ranged from **0.562 to 0.641**, with mean **0.601**. After calibration, nominal-80% coverage is **87.3%**, inside the frozen 70%–90% gate. Uncertainty remains a first-class output rather than being discarded.

## Appreciation/decline decomposition

The expected-appreciation/decline check still fails after the replacement and uncertainty repairs:

- Directional accuracy: **44.60%**
- Change correlation: **-0.2689**
- Scenario sample: **3,390** adjacent player observations

The exact decomposition of adjacent three-year Model A changes is algebraically accurate to numerical noise (`~1.98e-15` mean absolute reconstruction error). Its mean components are:

- prior-year drop: **-9.94**
- overlap reweighting: **+1.71**
- new terminal-year contribution: **+2.98**
- shared Forecast update: **+16.48**
- shared replacement update: **-12.34**

The diagnostic counterfactuals identify the narrowest source:

| Diagnostic | Directional accuracy | Change correlation |
|---|---:|---:|
| Full repaired Model A | 44.75% | -0.2720 |
| Equal annual weights | 50.22% | -0.2403 |
| Remove replacement-update component | 34.56% | -0.3320 |
| Remove Forecast-update component | **68.47%** | **+0.2049** |

The fixed 1.0/0.85/0.70 benchmark weights are not the primary failure. Replacement movement is also not the cause; suppressing it makes the signal materially worse. The failure is concentrated in the **Forecast trajectory/update component across adjacent chronological folds**.

The no-Forecast-update result is diagnostic only. It is **not** a proposal to freeze or suppress Forecast updates. Forecast owns football trajectory and survival, so the next legitimate investigation is Forecast-owned update reliability/calibration using point-in-time evidence—not a Value-layer patch that double-counts or overrides Forecast.

## Economic-usefulness checks

For the context-valid `marginal_lineup_opportunity` candidate:

| Scenario | Result | Key statistic |
|---|---|---:|
| Aging RB vs young RB | PASS | 68.28% directional accuracy |
| Elite QB longevity | **FAIL** | rank correlation 0.1948 |
| Developing WR | PASS | rank correlation 0.5133 |
| Developing TE | PASS | rank correlation 0.3981 |
| Position scarcity shift | PASS | 17/17 positive QB SF gains |
| Expected appreciation/decline | **FAIL** | 44.60% direction; -0.2689 correlation |

Total: **4 of 6 passed**.

The elite-QB result is a second, narrower consequence of moving from the raw-error `starter_threshold` target to a structurally valid replacement target. The context repair fixes Superflex economics but the current winning context-valid replacement definition weakens the elite-QB longevity ranking enough to fail that check. This remains a replacement/model-selection issue; it does not justify an arbitrary QB bonus.

## Market-independence diagnostics

Market remains an external diagnostic only and was not used as an intrinsic training target.

Across the three safely overlapping historical market folds:

- Pearson correlation: **0.6894**
- Spearman correlation: **0.6538**
- Material disagreement rate: **38.75%**
- Market adds incremental information in all available folds

The independence guardrail therefore remains **PASS**. Model A is not merely reproducing broader market consensus.

## Promotion decision

The frozen gates now read:

- material improvement over affine: **PASS**
- structurally valid replacement/context sensitivity: **PASS**
- uncertainty calibration: **PASS**
- market independence: **PASS**
- economic usefulness: **FAIL — 4/6, requirement 5/6**

**Production-promotion gate: NOT CLEARED.**

No production promotion is recommended at this stage.

## Model B status

A chronologically persistent elite-tail residual pattern is still detectable. If all upstream Model A issues were resolved and that residual persisted, it would identify a narrow, testable Model B challenger: a **bounded nonlinear surplus transformation aimed at elite-tail compression/expansion** rather than a broad opaque model.

However, this residual does **not yet genuinely justify fitting Model B**. A known upstream failure remains: adjacent-fold Forecast trajectory updates are the dominant source of the appreciation/decline failure, and the context-valid replacement definition also loses the elite-QB longevity check. Those causes must be addressed or ruled out first; otherwise a nonlinear Value transform could merely absorb errors owned by Forecast or replacement economics.

## Narrowest remaining causes

1. **Appreciation/decline:** Forecast trajectory/update reliability across adjacent point-in-time folds. This is the primary unresolved substantive failure.
2. **Elite-QB longevity:** the current context-valid replacement formulation weakens long-horizon elite-QB ordering. This remains a replacement/model-selection question, not grounds for a hardcoded QB premium.

Until those are resolved, Model B remains blocked and production authority remains unchanged.
