# FSFFL NEXT — Cell-Specific Y4-Y8 Intrinsic Research Management Handoff

Date: 2026-09-26  
State: **MANAGEMENT GATE — CELL-SPECIFIC LONG-HORIZON ARCHITECTURE**  
Authority: Research only. Production H3 is unchanged. No Y4-Y8 implementation is authorized.

## Executive conclusion

Management reopened the prior all-or-nothing fallback conclusion because the frozen 75/25 architecture failed one cell (QB Y8) while other cells contained independent evidence of improvement.

The corrective used a general routing/shrinkage policy frozen before repeated rolling validation. It did **not** use the already-seen comprehensive final-holdout artifact to select or tune cells.

The result is:

**Soft cell shrinkage is the best-supported general Y4-Y8 Research architecture.**

It beats the incumbent baseline in 15 of 20 cells on the rolling multi-objective composite and materially improves aggregate RMSE, tail RMSE, rank ordering and bias. Hard cell switching is less robust. The previously rejected blanket 75/25 architecture remains competitive on aggregate averages but retains a materially worse worst-cell failure profile.

The evidence is not strong enough to grant exact cardinal authority to every cell:
- **QB Y4 — soft shrinkage exact support**
- **WR Y4 — soft shrinkage exact support**
- **QB Y6 — soft shrinkage exact support**
- **13 Y4-Y7 cells — soft shrinkage with explicit uncertainty; policy differences are too small/unstable for hard exact routing**
- **all four Y8 cells — coarse/uncertain only; there are only two valid repeated outer origins, below the frozen three-origin minimum for exact authority**

The incumbent comparator earns **no automatic blanket authority** and no cell is classified as `baseline_earned`.

## General policy comparison

Repeated rolling validation, 11,940 player-origin rows:

| Policy | RMSE | MAE | Bias | Spearman | Tail RMSE | Cells better than baseline | Worst cell RMSE ratio vs baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Soft shrinkage | **43.20** | 20.73 | **+0.23** | **0.5067** | **113.34** | **15/20** | 1.074 |
| Rejected blanket 75/25 | 43.48 | 20.71 | +0.17 | 0.5034 | 114.19 | 14/20 | **1.311** |
| Hard router | 44.03 | 20.91 | +0.44 | 0.4964 | 113.52 | 15/20 | 1.095 |
| Incumbent baseline | 45.64 | **19.96** | -5.70 | 0.4942 | 134.77 | 0/20 | 1.000 |

Relative to the incumbent, soft shrinkage improves:
- RMSE by about **5.3%**;
- top-tail RMSE by about **15.9%**;
- Spearman by **0.0125**;
- systematic bias from **-5.70** to approximately neutral **+0.23**.

Its cost is about **3.8% worse MAE**. That tradeoff is explicit rather than hidden.

## Why soft shrinkage wins over hard routing

The cell candidate pool contains:
- richer specialists selected from development-only evidence;
- the incumbent comparator;
- a shared continuous-horizon football-history anchor.

The soft policy blends the top three candidates from earlier-origin evidence rather than committing each cell to one model.

That is valuable because:
- hard router and soft shrinkage both beat the baseline in 15/20 cells;
- soft shrinkage has better aggregate RMSE and Spearman than hard routing;
- soft shrinkage has a lower worst-cell RMSE ratio (1.074 vs 1.095);
- many cells have small score margins that do not justify hard model-family switching.

The Research recommendation is therefore **shrink when evidence is ambiguous, specialize only when repeated outer validation makes the case**.

## Preservation of the prior QB Y8 failure

The previously frozen 75/25 architecture's QB Y8 failure remains valid evidence.

In the corrected rolling comparison:
- QB Y8 baseline RMSE: **78.00**
- soft shrinkage RMSE: **78.35**
- hard router RMSE: **83.12**
- old blanket 75/25 RMSE: **102.23**
- blanket/baseline ratio: **1.311×**

There are only two defensible Y8 outer origins after preserving earlier-origin selection chronology. Research therefore does not claim a replacement exact QB Y8 route. QB Y8 and every other Y8 cell remain coarse/uncertain.

This corrective does not pretend a second untouched final Y8 holdout exists.

## Cell-level disposition

Exact shrinkage support:
- QB Y4
- WR Y4
- QB Y6

Soft shrinkage with uncertainty:
- RB Y4, TE Y4
- QB/RB/WR/TE Y5
- RB/WR/TE Y6
- QB/RB/WR/TE Y7

For some of those cells the baseline or hard router has the lowest aggregate rolling score, but the margin/stability gate is not strong enough to grant that policy exact authority. The recommended representation remains soft shrinkage with explicit uncertainty.

Y8:
- QB/RB/WR/TE: **coarse or uncertain; no exact route**.

Machine-readable disposition:
`FINAL_CELL_ROUTING_STATUS.csv`.

## Age / NFL experience / accumulated-exposure audit

Management required a separate audit because inherited base-season age and experience could be too coarse.

The audit froze five variants before results:
1. inherited linear base age/experience;
2. nonlinear target-horizon age/experience;
3. nonlinear target age/experience + recent role, without cumulative exposure;
4. nonlinear target age/experience + cumulative PIT workload and interactions;
5. nonlinear two-part gradient-boosted target-age/exposure model.

Cumulative workload was built strictly from seasons before the forecast base season.

No manual age cliff, youth bonus, or dynasty curve was imposed.

### QB

QB is the clearest positive result.

Nonlinear target-age/exposure HistGB beats the inherited linear age model in **5/5 Y4-Y8 cells** on the audit composite.

At Y4-Y7:
- RMSE ratios vs inherited linear are approximately **0.92 / 0.91 / 0.92 / 0.95**;
- tail-RMSE ratios **0.74 / 0.75 / 0.75 / 0.77**;
- conditional-production RMSE ratios **0.86 / 0.80 / 0.86 / 0.89**;
- overall outer-origin win shares **100% / 100% / 100% / 75%**.

The effect is stable across earlier/later rolling eras at Y4-Y7.

However, the age/exposure model does not dominate the already-selected soft stack overall; it is best treated as a **meaningful QB component/challenger**, not an automatic replacement.

Y8 remains diagnostic only.

### RB

Accumulated exposure adds modest information beyond age/experience/recent role in **5/5** cells on the incremental composite, but the mechanism is mostly survival/relevance:
- survival improves in **4/5**;
- conditional production improves in only **1/5**.

This does **not** support a universal RB workload wear penalty. Historical high-workload players are selected for talent and role as well as exposed to wear.

Nonlinear age/exposure HistGB is clearly useful at RB Y4, mixed later, and Y8 is evidence-limited.

### WR

WR provides an important negative result:
- nonlinear target age/experience alone is slightly useful in 4/5 cells;
- cumulative exposure improves conditional production in **0/5** cells;
- the full nonlinear age/exposure model is better than inherited linear in only **1/5** cells.

The strongest age/workload effect is on survival/relevance/tail behavior, not on the scoring level of WRs who remain active.

Do not add cumulative workload as a general WR conditional-production feature.

### TE

Simple target-age polynomial terms are worse than inherited linear age in 5/5 cells, but the nonlinear HistGB age/exposure model improves 4/5 cells, especially Y4-Y5.

Y6-Y7 gains are smaller and more era-sensitive; Y8 is worse/evidence-limited.

TE therefore supports nonlinear interactions more than a simple polynomial age curve.

## What the age curves actually say

The strongest long-horizon aging signal is usually **survival**, not a mechanical scoring penalty applied to every active veteran.

Examples from rolling validation:
- QB Y4: modeled active rate falls sharply from younger target-age groups to the oldest groups, while conditional scoring among active QBs changes much less.
- QB Y7: the survival difference becomes much larger while conditional scoring remains comparatively stable.
- TE shows a similar survival-dominant pattern.
- RB shows both lower survival and lower conditional production at older target ages.
- WR shows both effects, but survival is stronger.

This argues for keeping the decomposed model structure: aging should primarily change the chance of remaining relevant when the evidence says so, rather than multiplying every player's future fantasy points by a manual age discount.

## Accumulated workload is not a wear-and-tear coefficient

High historical cumulative workload often correlates with **higher** future survival and conditional production because it also identifies players who earned and sustained major roles.

Therefore Research does **not** interpret cumulative attempts/touches/targets causally as damage.

Use workload only as a PIT predictive feature where repeated validation supports it, principally in survival/relevance modeling.

## Final Research architecture

Research recommendation for the next governed design target:

1. **Production H3:** unchanged.
2. **Y4-Y7 general architecture:** soft position×horizon shrinkage across development-qualified specialists/shared models.
3. **Exact cell authority today:** only QB Y4, WR Y4, QB Y6 clear the frozen repeated-validation standard.
4. **Other Y4-Y7 cells:** soft shrinkage with explicit model/forecast uncertainty, not hard route authority.
5. **Y8:** coarse/uncertain representation only until independent additional historical evidence becomes available.
6. **Age/experience:** model target-horizon age/experience nonlinearly where evidence supports it; do not use one manual dynasty curve.
7. **Accumulated exposure:** position-specific predictive input, mainly to survival/relevance; not a universal wear penalty.
8. **QB:** nonlinear age/exposure deserves inclusion as a dedicated challenger/component in the next production-promotion study.
9. **Terminal/career:** remains separate from exact annual Y8 cardinal authority.

## What is not authorized

- no production H3 change;
- no Y4-Y8 production implementation;
- no post-hoc repair of the old 75/25 holdout;
- no exact Y8 route;
- no universal age cliff, youth premium, or workload penalty;
- no hidden master Intrinsic score;
- no use of Market, Owner Intelligence, Team Utility, or acceptance probability as Forecast inputs.

## Management decisions required

1. Accept or reject **soft cell shrinkage** as the Research-standard architecture for Y4-Y7.
2. Accept or reject **coarse/uncertain Y8** as the governed Research treatment until new independent evidence exists.
3. Decide whether the next promotion study should incorporate the validated **QB nonlinear target-age/exposure component** into the soft-stack candidate set.
4. Decide whether product-facing long-horizon values should expose only cells/horizons with exact support or also explicitly labeled uncertain shrinkage estimates.
5. Decide whether a separate terminal/career-state representation should proceed for deep horizons where exact cardinal authority is structurally limited.

**MANAGEMENT GATE — CELL-SPECIFIC LONG-HORIZON ARCHITECTURE**
