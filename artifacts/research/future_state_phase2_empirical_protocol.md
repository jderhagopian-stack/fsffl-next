# FSFFL NEXT — Future-State Resolution Phase 2 Historical Empirical Protocol

**Status:** management-authorized Phase 2 research only. Frozen before results are generated or inspected.

## Management boundary

This study answers only three diagnostic questions:
1. whether within-state player-specific production residuals carry predictive information into future seasons across QB/RB/WR/TE;
2. whether the current I1 age/experience representation is materially miscalibrated, especially at extreme ages;
3. whether repeated over- or under-performance relative to point-in-time expected age/state production predicts subsequent production, persistence, role loss, or career end/non-return.

No challenger architecture is designed, fit, selected, tuned, or promoted. No production Forecast, Value, Shapley, Team Utility, Simulation, Decision, Search, or market authority changes. PR #147 is not modified.

## Evidence

Use the same historical seasonal production source and nflverse identity source already used by governed Forecast research. Build a player-season panel with standard fantasy production, age, experience, games, pass attempts, carries, targets, and role opportunity per game. Positions are QB/RB/WR/TE.

Source seasons scored: 2005–2022. Outcomes may use up to 2025 so h=1/2/3 are fully observable. All baselines, state boundaries, state means, survival expectations, and residual normalization for a source season use only evidence available at or before that historical cutoff. Predictor residuals from prior seasons are themselves point-in-time residuals calculated at their own earlier cutoffs.

## Frozen I1 representation under test

Use the production I1 state-boundary semantics and the current frozen age/experience rules:
- QB age: young <=25, prime 26–31, aging 32+;
- RB/WR/TE age: young <=23, prime 24–27, aging 28+;
- experience bands: 0–1, 2–3, 4–6, 7+;
- continuous experience is capped at 15 years.

## Test 1 — within-state production residual persistence

At each source cutoff, fit position state boundaries from seasons strictly before the source season. Within-state residual is source production minus the prior-only position/state mean, divided by the prior-only state SD.

For each h=1/2/3 active target, calculate a target residual against the horizon/position/realized-state mean estimated only from transitions resolved by the source cutoff. Primary diagnostics by position and current age band:
- Spearman correlation(current residual, target residual);
- OLS slope of target residual on current residual with source-season clustered uncertainty.

This separates conditional production from persistence. Missing target rows are excluded from the conditional-production residual test and scored separately as persistence outcomes.

## Test 2 — age / experience calibration

Do not build an alternative age model. Ask whether exact age still predicts errors inside the current coarse age bands after controlling diagnostically for current residual and capped experience.

Report by position, current age band, and h=1/2/3:
- survival-calibration residual per exact age year;
- conditional target-production residual per exact age year.

Extreme-age display bins are frozen as:
- QB: <=25, 26–31, 32–34, 35–37, 38–40, 41+;
- RB/WR/TE: <=23, 24–27, 28–29, 30–31, 32+.

Experience-cap diagnostic: among players with experience >=15, test whether each additional year beyond 15 predicts survival residual or conditional target-production residual after controlling for age and current residual.

A pattern is considered materially concerning for management review if a survival gap is roughly >=5 percentage points or a conditional-production residual is roughly >=0.25 state SD, especially when direction replicates across horizons. Small-N extreme-age cells must be reported with support and not generalized.

## Test 3 — repeated residual history

Require a point-in-time residual in both the source season and immediately prior season. Classify the two-season pattern as:
- over: both residuals >0;
- under: both residuals <0;
- mixed: opposite signs.

Primary incremental test: coefficient on prior-season residual after controlling for current residual. Report separately for:
- target-season row presence (persistence);
- conditional target-production residual among active targets;
- role loss among players who were established at source and active at target;
- three-year terminal non-return proxy.

Role is a direct opportunity metric:
- QB: pass attempts/game;
- RB: (carries + targets)/game;
- WR/TE: targets/game.
Within each completed season and position, established means at/above the contemporaneous median; weak means below it. Role loss means established at source and weak at target, conditional on target presence.

The source does not contain transaction-level retirement declarations. Therefore “retirement” is not asserted from a single missing row. The terminal outcome is explicitly labeled **no production row in any of the next three seasons**, which is a career-end/non-return proxy only.

## Stop rule

Return the empirical results to management after Phase 2. Do not design, tune, or test a replacement model until management separately authorizes Phase 3.
