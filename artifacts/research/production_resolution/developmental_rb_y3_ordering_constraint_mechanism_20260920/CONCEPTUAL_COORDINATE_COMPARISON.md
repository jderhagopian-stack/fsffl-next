# Conceptual coordinate comparison

This is a mechanism comparison only. No alternative candidate was fit or scored.

## Raw additive point residual: target - D1_state_mean
Pros: directly interpretable in fantasy points; final ordering can be enforced on final means.
Cons: strongly heteroskedastic across state levels; upper states dominate squared-error fitting. It is not the coordinate used by the feasibility signal.

## Raw log-ratio residual: log(target / D1_state_mean)
Pros: naturally multiplicative and scale-free.
Cons: unstable for low positive-state means and low point totals. In the actual challenger fitting inputs it produced a large positive lower-state intercept even though the canonical out-of-sample feasibility residual for lower states was negative. This coordinate materially contributed to the mechanism conflict.

## log1p residual: log1p(target) - log1p(D1_state_mean)
Pros: exactly matches the feasibility diagnostic; preserves error sign; remains well behaved for low states; supports smooth multiplicative-like corrections in (1+points) space.
Cons: requires final-mean ordering to be enforced after transformation rather than by ordering correction functions.

## Source-retention residual
Example: target/source - D1_state_mean/source.
Pros: directly tied to the production-retention issue.
Cons: changes weighting with source denominator, can overemphasize smaller source seasons, and is not needed to explain the current conflict.

## Bounded state/group residual offset in log1p mean space
Pros: aligns the fitting coordinate with the stable feasibility signal; can share a common upper curve with one shrunk lower-group deviation; final state ordering can be enforced using D1's actual adjacent-state gap rather than forcing correction functions themselves to be ordered.
Cons: requires a fresh preregistered test.

Mechanism conclusion: log1p residual is the most natural coordinate already implied by the evidence. The failed test used a raw log-ratio fitting target and an unnecessarily strong correction-order constraint.