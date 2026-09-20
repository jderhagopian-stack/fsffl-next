# One unfitted successor boundary: gap-aware log1p partial pooling

This is a specification only. It was not fit, scored, tuned, or promoted.

## Coordinate
Train only on prior-origin prospective D1 residuals:
r_i = log1p(target_points_i) - log1p(D1_mean_for_realized_state_i).

At forecast origin T, calibration training rows must come from earlier source origins whose target outcomes are fully resolved by T-1, using the D1 mean that was generated prospectively at that earlier origin. Do not use in-sample residuals from a D1 model fit on the same calibration row.

Let u=source_percentile, z=2(u-0.5), A=log(1.5).

## Four parameters
Shared upper response:
c_U(u) = A * tanh(a0 + a1*z).

Lower-group deviation score:
h(u) = d0 + d1*z.

Use the same upper/lower groups:
upper = starter/premium/elite
lower = depth/usable.

## Ordering-safe lower correction
For each forecast row r define the D1 log1p cross-group gap:
G(r) = log1p(D1_starter(r)) - log1p(D1_usable(r)) > 0.

Define:
c_L(u,r) = c_U(u) + G(r) * tanh(h(u)).

Adjusted means:
upper state s: m'_s = expm1(log1p(D1_s) + c_U(u))
lower state s: m'_s = expm1(log1p(D1_s) + c_L(u,r))

Because tanh(h)<1:
log1p(m'_usable) - log1p(m'_starter)
= -G(r) + G(r)*tanh(h(u)) < 0.

Therefore usable < starter is guaranteed by construction while allowing the lower correction itself to be above or below the upper correction. Within-group ordering is inherited because every state in a group receives the same log1p offset.

## Regularization
Keep the prior frozen support-based penalties to isolate the representation change:
0.05*(a0^2+a1^2) + 0.10538922155688623*(d0^2+d1^2).
No penalty sweep.

## Support-domain behavior
No p75/p90/p95 state, knot, breakpoint, or hand-selected magnitude region. Source percentile remains continuous over the full supported domain. The row-specific D1 gap supplies the exact ordering headroom available for that forecast row.

## Frozen components
D1 p_out and all positive-state probabilities remain unchanged. Distribution scale remains unchanged in the first test. No new survival classifier or latent state is introduced.

## Why this resolves the exact failure
1. It trains on the same prospective residual coordinate that produced the stable feasibility signal.
2. It constrains final ordered state means, not the relative ordering of correction functions.
3. It preserves the four-parameter partial-pooling idea and prior regularization.
4. It can express the empirically supported lower-vs-upper magnitude-response difference without discarding D1's substantial starter/usable baseline separation.

A future test requires a new directive and preregistration. Source-2023 -> target-2026 must remain untouched.