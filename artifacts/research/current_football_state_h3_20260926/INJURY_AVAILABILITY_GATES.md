# Injury Availability / Time-to-Return Validation Gates

Frozen before model scoring.

## Minimum support

Overall:
- at least 1,500 scored OOT episodes across the six holdouts;
- all six holdout seasons represented.

Position safety is evaluated where a position has at least 100 OOT episodes.

## Return-timing gate

The candidate must beat the **severity-only** baseline on the pooled OOT episode set by:
- >= **2% relative improvement** in mean Brier score across return-by-1/2/3/4-week and any-return probabilities; and
- >= **1% relative improvement** in return-time integrated Brier score.

Safety:
- pooled probability log loss may not worsen >3%;
- absolute calibration error may not worsen >0.02;
- no supported position may worsen mean Brier >7%;
- candidate must improve mean Brier in at least 4 of 6 holdout seasons.

If both full linear/logistic and nonlinear models clear, prefer the simpler model unless nonlinear mean-Brier improvement is additionally >=1%.

## Remaining-availability gate

The candidate must beat severity-only by:
- >= **2% relative MAE improvement** on bounded remaining-season availability.

Safety:
- RMSE may not worsen >3%;
- absolute mean bias may not worsen by >0.02 participation share;
- no supported position may worsen MAE >7%;
- candidate must improve MAE in at least 4 of 6 holdout seasons.

If both challengers clear, prefer the simpler model unless nonlinear MAE improves by an additional >=1%.

## Uncertainty

For any accepted remaining-availability model:
- derive absolute-residual conformal bands from prior-season OOT residuals only;
- target nominal 80% and 90% coverage;
- final interpretation must report actual pooled and position coverage.

No zero uncertainty and no cross-target covariance claim.

## Contract outcome

Possible outcomes are component-specific:
- return timing accepted, remaining availability rejected;
- remaining availability accepted, return timing rejected;
- both accepted;
- neither accepted.

A rejected component falls back to coarse direct status/severity evidence only. Rejection does not authorize a generic injury multiplier.

## Authority guard

No result from this phase may:
- change conditional healthy production;
- change post-return role;
- change recurrence/durable H2/H3;
- alter production H3 or Intrinsic;
- override authoritative provider ROS;
- be interpreted as a causal biological injury penalty.
