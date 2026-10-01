# 2026-10-01 — Sleeper postseason estimate correction

## Management decision

For ordinary Sleeper leagues, `playoff_week_start` and `playoff_teams` are sufficient basic configuration to keep postseason estimates available. Do not blank postseason estimates merely because the provider has not supplied a fully described bracket graph.

- Always calculate `playoff_probability` from the simulated regular-season finish distribution using the best supported qualification assumption. When exact qualification rules are absent, use the top `playoff_teams` finishers, with the simulator's governed standings order (wins, points for, stable team ID).
- Always calculate `championship_probability` when an exact provider bracket is available or when settings support the standard seeded 2-, 4-, 6-, or 8-team fixed bracket. Derive round weeks from `playoff_week_start` and preserve `provider_observed_exact` versus `settings_derived_standard` as internal provenance only.
- Product output remains ordinary **Playoffs %** and **Championship %**. Do not surface a provisional class or visual downgrade.
- If `playoff_teams` is valid but the bracket size is outside the standard 2/4/6/8 formats, keep qualification odds and withhold title odds unless exact bracket evidence resolves the structure.
- Reserve unavailable/UNKNOWN for missing or corrupt basic configuration, unsupported exact qualification rules, or genuinely unmodelable bracket structures. Keep explicit reasons.
- Derived qualification odds must feed the existing calculated competitive-state classification so Search/Trade Finder does not remain UNKNOWN when the configured estimate is available.

This decision supersedes stricter fail-closed wording in earlier #320 history and the prior requirement to hold the next roadmap item solely for a hosted check of the old blank-output behavior. It does not authorize skipping the targeted hosted acceptance of the corrected capability.

## Execution and acceptance

Implement as a focused correction against merged #320, update module-contract and downstream classification regressions, run the focused suites and ordinary full CI/review, then perform one targeted hosted postseason acceptance. Do not rerun unrelated platform/runtime/lifecycle gates. Do not advance the already-approved week-by-week engine until the corrected odds and classification are directly verified on the hosted path and the exact closeout is written to canonical operations state.
