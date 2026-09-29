# Rolling FUMBLES_LOST Uncertainty Behavior

Date: 2026-09-29

## Contract

For a normal evidence row:

`stddev = max(sqrt(mean), rolling_position_floor[position, cutoff])`.

For cold-start or identity-light evidence:

`stddev = max(sqrt(mean), rolling_position_floor[position, cutoff], 0.7899186992)`.

The rolling position floor is the predeclared monotone empirical rule:

`floor(p,c) = max(accepted_week2_floor[p], OOT residual RMSE[p,k] for k <= c)`.

This keeps uncertainty non-zero and prevents later, sparser cutoffs from falsely appearing more precise.

## Current Week-3 floors

- QB: **1.7808254003**
- RB: **0.7375205714**
- WR: **0.4424922528**
- TE: **0.4613691858**

## Late-season growth is intentional

By Week 17 the season-equivalent target is inferred from a very small remaining window, so the empirical floors rise to:
- QB **5.1732**;
- RB **2.1161**;
- WR **1.4272**;
- TE **1.4896**.

This is not a reason to invent a late-season model. It is the correct expression of weaker season-equivalent precision.

## Coverage diagnostics

Using the frozen normal-reference interval diagnostic:
- minimum observed 80% coverage across all position/cutoff cells: **81.94%**;
- minimum observed 90% coverage: **85.53%**.

The intervals are not claimed to be exact calibrated Gaussian predictive distributions. They are conservative reference diagnostics around the required non-zero empirical uncertainty floor.

No result was used to retune the mean model or create a position-specific calibration coefficient.
