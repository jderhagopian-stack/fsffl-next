# Conditional-Production Magnitude Resolution - Candidate Rejection Ledger

Date: 2026-09-19  
Historical selection freeze: `6bc47116f031fa0a250d16c4a9e70a4bece76224`

## Stage-1 diagnosis

The current credibility defect is localized to conditional-active magnitude transfer, not primarily to persistence.

The frozen P0 production learner predicts linear future point levels from:
- log-transformed source points;
- bounded source percentile;
- position/source-state/future-state baselines;
- age/experience;
- covered history and two-prior features.

At the current upper tail, the source percentile saturates and log(source points) grows slowly. Current Y1 upper-tail points are also substantially above historical realized source magnitudes. Most of the current compression is therefore already inside the raw state-conditioned production mean before positive-state probabilities are mixed.

Historical P0 is broadly calibrated at the top decile, but does show a smaller, real extreme-tail underprediction:
- Y2 top-5 retention: predicted 67.4% vs realized 72.2%.
- Y3 top-5 retention: predicted 59.4% vs realized 64.6%.
- Young top-10 underprediction is about 1.3 percentage points at Y2 and 4.2 points at Y3.

That historical evidence justified testing only P1 and P2.

## P1 - residual magnitude anchor

P1 learned one horizon-level convex pull from P0 conditional production toward source production.

### Y2
Every 2014-2020 fitted raw anchor coefficient was negative. The predeclared `clip(w,0,1)` rule therefore set `w=0` in all seven selection folds.

Result: P1 is exactly P0 at Y2.
- Top-5 absolute retention bias improvement: **0.0000**.
- No Y2 chronology cell improves.
- Broad Y2 accuracy is unchanged.

### Y3
P1 learned small positive anchor weights (~0.015-0.046) and improves the targeted tail:
- top-5 absolute retention bias: 0.0521 -> 0.0374;
- top-10 absolute retention bias: 0.0075 -> 0.0052;
- young top-10 absolute retention bias: 0.0416 -> 0.0302;
- overall unconditional MAE: 31.3999 -> 31.2933.

It improves all three Y3 chronology blocks.

### Why P1 is rejected
The directive requires a replicated correction at **both** Y2 and Y3. P1 improves only Y3:
- 3 of 6 horizon x chronology cells improve;
- Y2 targeted improvement is zero;
- mean two-horizon top-5 calibration improvement is 0.00734, below the predeclared 0.01 threshold.

P1 is therefore not promotable.

## P2 - relative log-retention target

P2 replaces the absolute production target with:
`log1p(target_points) - log1p(source_points)`,
using the same frozen route, allowed source features, state probabilities, pooling structure, and BayesianRidge settings.

P2 does improve broad unconditional MAE:
- Y2: 32.7880 -> 32.5436;
- Y3: 31.3999 -> 30.4758.

It also improves several role-loss/deep-collapse stress measures.

However, it moves the exact target defect in the wrong direction:
- Y2 top-5 absolute retention bias: 0.0481 -> 0.0732;
- Y3 top-5: 0.0521 -> 0.0878;
- Y2 top-10: 0.0051 -> 0.0220;
- Y3 top-10: 0.0075 -> 0.0527;
- Y2 young top-10: 0.0127 -> 0.0361;
- Y3 young top-10: 0.0416 -> 0.0730.

P2 improves only 3 of 6 top-5 chronology cells and materially worsens several others.

### Why P2 is rejected
Broad MAE gains cannot override failure on the directive's primary calibration defect. P2 worsens upper-tail and young upper-tail retention calibration at both horizons.

## Frozen decision

No challenger clears the predeclared selection standard.

- **P0**: remains the reproducible Outcome-B baseline.
- **P1**: rejected because the improvement does not replicate at Y2.
- **P2**: rejected because it worsens the targeted upper-tail calibration despite broad-MAE gains.

No winning challenger exists. Therefore:
- no new final fit is authorized;
- no fresh-path challenger replay is required;
- no second 335-player board may be generated;
- no current-player output may be used to tune another candidate.

**OUTCOME B - TARGETED RESOLUTION DOES NOT CLEAR PROMOTION.**

STOP FOR MANAGEMENT REVIEW.
