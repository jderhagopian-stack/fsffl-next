# FSFFL NEXT — Phase 2 Q3 Method Addendum

## Why this addendum exists

The Phase 2 core protocol and first bounded run were frozen before results were inspected. During management-instruction compliance review after that run, a definition mismatch was identified in Test 3 only: the implementation classified repeated over/under-performance using a point-in-time **position/state** residual, while management had explicitly asked for repeated performance relative to expected **age/state** production.

This is treated as a methodological compliance defect, not as a result-driven hypothesis change.

## Correction

Q1 and Q2 are unchanged.

For Q3 only, the repeated-performance residual is recalculated at each historical source cutoff as:

- source fantasy production minus the historical mean for **position × current frozen I1 age band × current state**;
- divided by that cell’s historical standard deviation;
- all means, SDs, age bands, and state boundaries use only seasons strictly before the source season;
- if the position × age-band × state cell has fewer than 10 prior rows, the calculation falls back to the chronology-safe position × state residual, and that fallback is recorded.

The two-season history then uses this age/state-adjusted residual in the source season and immediately prior season. The same pre-specified outcomes remain:

- target-season production-row presence (persistence);
- future production conditional on target presence;
- role loss conditional on target presence;
- no production row in any of the next three seasons as a career-end/non-return proxy.

No thresholds, age bands, horizons, outcome definitions, or reporting groups are changed. No replacement model is designed, fit, tuned, compared, or promoted.

## Authority boundary

This addendum is Phase 2 research only. It does not modify PR #147, main, production Forecast authority, Value, Shapley, Team Utility, Simulation, Decision, Search, or presentation authority.

The corrected Q3 result is the authoritative Phase 2 answer to management question 3. The original state-only Q3 output is superseded for interpretation.
