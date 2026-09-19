# FSFFL NEXT - Elite RB collapse risk vs premature mean reversion

## Frozen method

This diagnostic is research-only. It uses the exact frozen P0 fitted package and frozen historical prediction artifact. No fit, retrain, retune, route change, coefficient change, scoring change, production-code change, merge, or deploy is performed.

Historical selection evidence is source seasons 2014-2020. Source seasons 2021-2022 are locked post-freeze replication only and never alter thresholds or conclusions from the selection window. Current-player names are overlaid only after historical cohort rules and source-magnitude bands are frozen.

## Cohorts and thresholds

Top-decile RB means `source_percentile >= 0.90`; top-5% means `>= 0.95`. Career stage is the frozen `developmental`, `established`, or `veteran` coordinate. Source-magnitude bands are stage-specific tertiles of 2014-2020 top-decile source points. For developmental RBs the cutoffs are 188.9 and 225.5 standard points.

Outcome decomposition uses directive-specified interpretable retention regions: inactive/out; active major collapse below 0.40; active middle 0.40-0.60; productive survivor at least 0.60. The decision proxy uses 0.70 as a clearly productive realized outcome and 0.40 as collapse, with 0.60 as the predeclared action threshold.

## Distributional comparison

D0 is evaluated as the frozen two-point production distribution: out at zero plus one common active conditional mean. D1 uses the frozen out/depth/usable/starter/premium/elite probabilities and their frozen state-specific conditional means. Continuous Ranked Probability Score (CRPS) is computed on retention ratios; lower is better. This does not reselect a route. It asks whether the already-frozen alternatives that were selected by point MAE differ materially in distributional fidelity.

A simple Gaussian-mixture diagnostic is reported only as a descriptive formal check. BIC does not support claiming statistically proven bimodality. The classification therefore does not rely on a formal mixture claim; it relies on transparent mass in downside/productive regions, source-magnitude bias, proper-score comparisons, and out-of-time replication.

## Economic-error proxy

Because the recovered frozen evidence package does not contain point-in-time historical dynasty asset-value snapshots for these rows, the bounded economic proxy is normalized retained production. Underprediction loss is `max(realized retention - P0 expected retention, 0)`; overprediction loss is the reverse. Results are reported under symmetric, 2x-undervaluation, and 2x-overvaluation weightings. This is a decision-sensitivity diagnostic, not a replacement Value model.