# NEXT-4 Future Improvements Backlog

This backlog preserves useful refinements that should not block NEXT-4 architectural completion. Items remain non-authoritative until implemented and validated under the FSFFL NEXT charter.

## Simulation and uncertainty

- Calibrate player-to-player covariance/correlation so team scoring uncertainty does not need the current provisional independence assumption.
- Evaluate richer weekly scoring distributions beyond the current non-negative normal approximation.
- Model teammate, opponent, game-environment and positional correlations only where historical evidence supports them.
- Add injury/availability pathways and depth-chart substitution inside simulation without duplicating Forecast authority.
- Validate approximately 50,000 simulations as the standard sample size and identify cases where fewer or more runs are appropriate.

## Computational efficiency

- Add reusable simulation caches keyed by point-in-time state, forecast version, lineup model version and simulation policy.
- Implement mathematically valid delta/incremental simulation for nearby roster scenarios instead of rerunning full seasons unnecessarily.
- Profile lineup optimization and simulation across larger league/roster configurations.

## Competitive-state calibration

- Estimate competitive-state classification thresholds from historical league outcomes rather than relying indefinitely on provisional governed policies.
- Test whether playoff probability, title/first-place probability, expected wins and uncertainty jointly improve state classification.
- Recalibrate policies by league-format family when evidence supports meaningful structural differences.

## Franchise utility

- Fit evidence-backed mappings from the non-collapsing TeamUtilityVector into scalar or ordered franchise utility only when downstream decision use requires it.
- Test horizon-sensitive utility and optionality without double counting NEXT-3 market/intrinsic value.
- Quantify roster fragility and resilience beyond the initial replacement-lineup metrics.

## Validation

- Build historical point-in-time team-state backtests using reconstructed rosters, forecasts, schedules and outcomes.
- Compare NEXT-4 competitive predictions with realized standings, playoff qualification and championships.
- Maintain sanity-case suites for Superflex scarcity, shallow/deep benches, elite-player removal, FLEX substitution and roster concentration.

## Downstream ideas intentionally deferred

- Polished reports, charts and analytics belong to NEXT-7.
- Interactive UI belongs to NEXT-8.
- Trade-specific recommendations and bilateral evaluation belong downstream of NEXT-4 under the roadmap/authority boundaries.
