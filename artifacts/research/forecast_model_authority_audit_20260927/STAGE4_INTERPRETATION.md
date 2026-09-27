# Stage 4 — Forecast Authority Impact Through Intrinsic

Date: 2026-09-27  
Authority: **Research only / production Forecast, H3 and Intrinsic unchanged**

## Execution integrity

Locked workflow:
- run: `36338430538`
- successful durable output commit: `b8920be58f7319cd71317e2ce625aa4226c62409`
- complete artifact: `10937742480`
- artifact digest: `sha256:52de1782ef1eb411b484d4afc51608789914ce3bfdea76576ddfe063e58641c5`

The current sandbox used exactly the four candidates frozen before scoring:
- deployed `VNEXT_A2_BURR`;
- D1;
- N1 HistGB;
- N2 spline two-part.

No current named player, rank, Value result or market information selected or tuned a Forecast family.

## Production parity

The deployed vNext Stage-4 path reproduces the existing production H3 Intrinsic reference:
- matched: **335/335**;
- maximum absolute raw-Intrinsic delta: **5.68e-13**;
- mean absolute delta: **1.40e-13**;
- Spearman: **1.0000**.

Thus the sandbox measures alternative Forecast impact against the real deployed Value economy rather than a neighboring approximation.

## Trajectory effect

Current mean connected-league future points differ materially across the frozen families:

| Model | Mean Y2 pts | Mean Y3 pts | Mean Y2 persistence | Mean Y3 persistence |
| --- | ---: | ---: | ---: | ---: |
| deployed vNext | 94.78 | 76.45 | 0.749 | 0.629 |
| D1 | 87.39 | 70.57 | 0.749 | 0.629 |
| N1 | 71.68 | 61.43 | 0.659 | 0.561 |
| N2 | 79.96 | 68.51 | 0.706 | 0.601 |

vNext and D1 share the same A2 probability/persistence surface; their current difference is conditional magnitude. N1/N2 also change state/persistence behavior.

These current magnitudes are downstream impact diagnostics only. They do not override the historical OOT evidence that deployed vNext is positively biased on central points and trades central MAE against superior CRPS.

## Intrinsic ranking/value impact

### Deployed vNext vs D1

These two remain extremely close economically:
- Spearman: **0.9988**;
- median absolute rank difference: **3**;
- p90: **8**;
- max: **23**;
- only **4.8%** move at least 10 ranks;
- **0.3%** move at least 20;
- median raw-Intrinsic difference: **6.10**;
- p90 raw difference: **19.68**.

This confirms that adding the richer Stage-D magnitude/uncertainty package did not radically reorder the existing Value economy relative to its closest ancestor.

### Deployed vNext vs N1

- Spearman: **0.9808**;
- median absolute rank difference: **7**;
- p90: **24.6**;
- max: **94**;
- **40.9%** move at least 10 ranks;
- **15.5%** move at least 20;
- median raw-value difference: **16.99**.

### Deployed vNext vs N2

- Spearman: **0.9776**;
- median absolute rank difference: **10**;
- p90: **34**;
- max: **82**;
- **51.9%** move at least 10 ranks;
- **26.3%** move at least 20;
- median raw-value difference: **16.93**.

N1-vs-N2 is even less stable in the tail: maximum rank difference **126**.

## Frozen material-reversal rule

Across all four models:
- material player reversals: **203 / 335 = 60.6%**;
- median four-model rank envelope: **17 ranks**;
- p90 rank envelope: **46.6**;
- maximum: **126**;
- median raw-Intrinsic envelope: **27.08**;
- p90: **67.53**;
- maximum: **106.05**.

This means Forecast-family ambiguity is economically meaningful after passing through lineup-capacity Shapley; it is not washed away by Value.

The largest mechanically selected reversals are concentrated among lower-current/developmental players, but the phenomenon is not confined to them.

## Archetype reversals

All **12/12** position × career-stage × age-band archetypes with at least 10 players meet the predeclared material-archetype rule.

Selected cohort-level examples:
- developmental young QB: **72.2%** material; median Value envelope **42.8%** of cohort median;
- developmental prime RB: **66.7%**; envelope **43.9%**;
- developmental prime WR: **72.3%**; envelope **29.5%**;
- developmental prime TE: **60.9%**; envelope **26.1%**;
- established prime QB: **43.5%** material despite only **7.7%** median envelope share;
- established prime WR: **42.3%**; envelope **10.4%**.

The pre-frozen rule therefore rejects an interpretation that model-family choice matters only for speculative prospects.

## Mechanically surfaced player examples

These names were selected only after the material rule was frozen and applied.

Examples of large rank envelopes:
- Eli Stowers: **126 ranks**;
- Quinn Ewers: **101**;
- Justin Fields: **96**;
- Ted Hurst: **95**;
- J.J. McCarthy: **94**;
- Nicholas Singleton: **91**;
- Kenyon Sadiq: **89**;
- Antonio Williams: **84**.

These examples illustrate model sensitivity. They are not evidence for or against any named player's football outlook.

## Uncertainty propagation

The current Value engine captures state-mixture uncertainty but does not consume deployed Burr/Gamma within-state tails in its central Value calculation.

For deployed vNext, median Forecast uncertainty illustrates the missing layer:

| Position | Y2 state-only SD | Y2 full SD | added within-state variance sqrt | Y3 state-only SD | Y3 full SD | added within-state variance sqrt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QB | 98.0 | 120.8 | 46.5 | 111.2 | 128.6 | 54.9 |
| RB | 80.3 | 94.2 | 45.5 | 77.2 | 84.3 | 34.5 |
| WR | 68.5 | 79.7 | 31.6 | 70.3 | 75.2 | 27.8 |
| TE | 48.5 | 57.2 | 26.8 | 56.5 | 63.6 | 26.0 |

At the current Value boundary, median state-mixture H2/H3 Intrinsic uncertainty for deployed vNext is:
- zero-covariance RSS proxy: **59.38 raw Value**;
- p90: **96.86**;
- perfect-positive-covariance median upper envelope: **83.13**;
- p90: **136.50**.

These are **not** exact total-Intrinsic standard deviations:
- cross-horizon covariance is unvalidated;
- current Value does not propagate the Burr/Gamma within-state distribution through Shapley;
- therefore the richer deployed Forecast uncertainty is preserved separately instead of silently coerced into a false precise Value SD.

## Stage-4 conclusion

The downstream economy amplifies enough of the Forecast-family differences that the authority question matters to actual player ordering and cardinal Value.

At the same time:
- deployed vNext and D1 remain economically very close because their state surface is shared;
- nonlinear N1 and smooth N2 can create large player/archetype reversals;
- those reversals cannot be used retrospectively to choose the Forecast model.

Stage 4 therefore supports **retaining explicit model/forecast uncertainty wherever Forecast authority is tied or a tradeoff**, rather than hiding the disagreement behind one point estimate.

No production behavior changed.
