# FSFFL NEXT - Conditional-Production Magnitude Resolution

Date: 2026-09-19  
Authority: one targeted research continuation  
Final outcome: **B - TARGETED RESOLUTION DOES NOT CLEAR PROMOTION**

## Plain-English result

The study identified the source of the credibility defect, but neither of the two authorized repairs solved it well enough in historical evidence to justify another final fit.

The main problem is not persistence. It is how the conditional-production model carries current/source scoring magnitude forward.

The Outcome-B D1 learner predicts future point levels from log-transformed source points, a percentile capped near 1, and pooled state/position baselines. That architecture is historically reasonable around ordinary realized source magnitudes, but it has weak leverage on very large source values. On the known current board, most compression is already present in the raw state-conditioned production means before future-state probabilities are mixed.

## Why the current board looked so compressed

Historically, the source-production upper tail is much lower than the current governed Y1 projection tail.

Position p90 current vs historical realized source points:
- QB: 431.6 vs 305.8 (1.41x)
- RB: 350.4 vs 159.7 (2.19x)
- WR: 269.9 vs 140.3 (1.92x)
- TE: 203.6 vs 89.1 (2.28x)

The model's source-magnitude inputs are log1p(points) plus bounded percentile. Once percentile is near 1, it cannot express more extremeness; log1p also grows slowly. Intercept and future-state baseline terms therefore dominate.

For current top-10 D1 rows:
- Y2 raw elite-state mean is only about 53.6% of Y1 before state mixing; final conditional mean is about 45.2%.
- Y3 D1 raw elite-state mean is about 53.5% of Y1; final conditional mean is about 41.8%.
- Roughly 85% of the Y2 and 80% of the Y3 median compression is already present before state mixing.

So the frozen persistence/state system is not the primary source.

## Historical evidence for a real but smaller tail defect

P0 is broadly calibrated across the historical top decile:
- Y2 top-10 mean retention: predicted 73.3%, realized 72.8%.
- Y3 top-10: predicted 65.3%, realized 66.0%.

But the extreme tail is underpredicted:
- Y2 top-5: predicted 67.4%, realized 72.2%; conditional bias -12.7 points.
- Y3 top-5: predicted 59.4%, realized 64.6%; conditional bias -14.2 points.
- young top-10 retention underprediction is ~1.3 percentage points at Y2 and ~4.2 at Y3.

That was enough to justify exactly the two management-authorized challengers.

## P1 - residual magnitude anchor

P1 learned a single horizon-level pull from P0 conditional production toward source production.

At Y2, every selection-window raw anchor coefficient was negative. The predeclared monotonic rule clipped it to zero, so P1 became exactly P0.

At Y3, P1 did help:
- top-5 absolute retention bias: 0.0521 -> 0.0374;
- top-10: 0.0075 -> 0.0052;
- young top-10: 0.0416 -> 0.0302;
- overall unconditional MAE: 31.3999 -> 31.2933.

But it improves only the three Y3 chronology cells and none of the three Y2 cells. It therefore fails the required two-horizon replication standard.

## P2 - relative log-retention target

P2 modeled future production as log-retention relative to source production while keeping the same route, state probabilities, allowed features and pooling.

It improves broad MAE:
- Y2 unconditional MAE: 32.7880 -> 32.5436.
- Y3: 31.3999 -> 30.4758.

But it makes the targeted defect worse:
- Y2 top-5 absolute retention bias: 0.0481 -> 0.0732.
- Y3 top-5: 0.0521 -> 0.0878.
- Y2 top-10: 0.0051 -> 0.0220.
- Y3 top-10: 0.0075 -> 0.0527.
- young top-10 worsens at both horizons.

Broad MAE cannot override failure on the exact calibration defect this study was authorized to fix.

## Reproducibility

Before any challenger fit:
- the exact P0/P1/P2 specification was committed;
- the exact code was committed and reload-verified;
- no current-player names appeared in candidate code;
- no current-board values were used for candidate selection.

The rerun P0 control matched all 10,336 durable historical rows:
- max conditional difference: 1.56e-13;
- max unconditional difference: 5.68e-14;
- active-probability difference: 0.

## Final decision

**OUTCOME B - TARGETED RESOLUTION DOES NOT CLEAR PROMOTION.**

No candidate passed the predeclared historical selection rules.

Therefore the directive stops here:
- no challenger final fit;
- no challenger replay package;
- no second 335-player materialization;
- no named/current-player tuning;
- no third model family.

The reproducible Outcome-B P0 baseline remains preserved for management.

**STOP FOR MANAGEMENT REVIEW.**
