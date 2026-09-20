# FSFFL NEXT Forecast baseline vs player-specific attribution architecture diagnostic

## Final classification

**D. MIXED / ROUTE-SPECIFIC ARCHITECTURE ISSUE**

The Y2/Y3 Forecast is genuinely individualized, not a generic position/state lookup. Player-specific source production, source percentile, prior-year production, prior-two residual history, age, experience, and - in the probability layer - role/opportunity inputs all influence the output. D1 also conditions conditional-production means on the future state.

The amount of individual authority is not uniform. The fitted architecture pools all routes around population/state anchors and then allows player evidence to move both state probabilities and conditional production. In several important routes the conditional-production response to an increasingly exceptional player is much weaker than the historical realized response. Developmental RB Y3 is a clear instance, but it is not unique: high-magnitude developmental QB and WR cohorts also show underprediction, and route-level response elasticities vary substantially across positions and horizons.

For developmental RB Y3, the known compression is created by two interacting mechanisms. Conditional-state production is only modestly individualized: in a controlled elite-source profile, moving source evidence from roughly 120 to 297 standard fantasy points raises the elite conditional mean only from about 186 to 197 points and the total active conditional expectation from about 116 to 142. In the validated top-decile +10% perturbation, the production-only elasticity is about +0.05 while the state-mix contribution is about -0.09, so combined conditional production is approximately flat to slightly negative. Negative ordered-state `dpts` coefficients after spike seasons can therefore add compression to already weak within-state source response.

The issue is not primarily an incorrect single "generic RB baseline" level. It is a route/state-specific balance between pooled state anchors and marginal player response. Premium/elite developmental-RB means are **modestly individualized around shared state anchors**, not fully player-specific trajectories.

Existing P0 Forecast uncertainty only places probability mass on six discrete supports (out plus five state means). It does not use the serialized BayesianRidge posterior variance at runtime. For historical top-decile developmental-RB Y3 active outcomes, about 28% of realized outcomes exceeded the row's maximum Forecast support (the elite-state mean). Therefore the current Forecast distribution does not fully contain productive-survivor upside when the elite mean itself is compressed.

Current regular-season Simulation does not consume the Y2/Y3 P0 state distribution at all; it consumes current-season weekly team means plus independent weekly volatility. It therefore cannot restore missing Y3 survivor paths. Intrinsic/Shapley does consume the Y2/Y3 probabilities and state means directly and applies the frozen 0.85 annual discount. No second age/RB/collapse haircut was found downstream.

## Decision boundary

PR #147 should remain **on hold for one bounded Forecast architecture research question**, not for another downstream correction exercise:

> Can conditional-production means in the specific weak route/state cells be made more responsive to continuous player evidence through a preregistered hierarchical/partial-pooling architecture, while preserving the already-earned state-probability authority, chronological walk-forward validation, and final state ordering - and without globally retuning routes that already show adequate response?

Do not fit or test that model in this diagnostic. Do not alter route authority, state probabilities, Value/Shapley, Simulation, or production. Preserve source-2023 -> target-2026 as prospective external evidence.