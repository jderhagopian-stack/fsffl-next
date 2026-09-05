# NEXT-4 Authority & Anti-Double-Counting Audit

This audit applies the FSFFL NEXT charter to Team Utility & Simulation.

## Authoritative homes

| Effect | Authoritative home | NEXT-4 treatment |
| --- | --- | --- |
| Canonical rosters, rules, taxi/IR, picks | State (NEXT-1) | Consume only |
| Player football distributions | Forecast (NEXT-2) | Consume only |
| Market/intrinsic/pick/transaction economics | Value (NEXT-3) | Consume as typed economic evidence; do not recalculate |
| Legal optimized lineup | Team Utility / Decision | Authoritative in NEXT-4 |
| Real-roster replacement consequence | Team Utility / Decision | Authoritative in NEXT-4 |
| Team scoring distribution | Team Utility bridge from Forecast | Authoritative mean; current covariance treatment explicitly provisional |
| Wins/playoff/first-place outcomes | Simulation | Authoritative in NEXT-4 simulation |
| Calculated competitive state | Team Utility / Decision | Derived from simulation through explicit governed policy |
| Owner strategic posture | Owner input / Decision | Separate from calculated state |
| Roster resilience | Team Utility / Decision | Derived from real replacement pathways |
| Before/after team consequences | Team Utility / Decision | Structured deltas only |
| Bilateral trade desirability | NEXT-5 Trade Decision | Out of scope |
| Candidate generation / balancing | Search/Optimization | Out of scope |
| Reports / charts / league analytics | NEXT-7 Analytics/API + Presentation | Out of scope |

## Anti-double-counting conclusions

- NEXT-4 does not add a generic Superflex/QB premium. League rules affect legal lineup and replacement consequences; NEXT-3 already owns market/scarcity economics.
- Market value cannot change lineup optimization or simulation unless roster composition changes through an explicit scenario.
- Competitive simulation outputs enter the utility vector once; NEXT-4 does not invent a second wins-impact estimate.
- Roster resilience measures team-specific consequences only and does not become a second player-value system.
- Owner strategic posture cannot rewrite calculated competitive state.
- The utility vector remains non-collapsing until an evidence-backed mapping justifies scalar utility; no arbitrary blended master score is hidden in NEXT-4.

## Provisional assumptions

- Team scoring variance currently combines starter forecast variances under an explicit independence assumption until a calibrated player covariance model is promoted.
- Competitive-state thresholds are supplied through an explicit versioned policy and are not hidden constants; empirical threshold calibration remains future work.
- The current non-negative normal scoring sampler is transparent and challengeable rather than presented as a final empirical distribution family.

## Automated boundary protection

`tests/test_team_utility_authority_boundaries.py` prevents the NEXT-4 package from importing downstream FSFFL authority. Team Utility may depend on State, Forecast and Value, but not Trade/Search/Analytics/Presentation modules.
