# Workstream — Performance

## State
**MANAGEMENT GATE**

## Last accepted checkpoint
Production PR #211 / SHA `2fd62e9786843a35c0aa335362cf7e6fa061fe98`.

Observed/worker-reported checkpoint:
- new Sleeper league switch is durably active;
- refresh control is physically actionable and visibly changes to Refreshing;
- refresh is single-flight;
- restart does not automatically launch heavy intelligence;
- CI was green for PR #211.

## Current blocker
The newly connected league cannot complete governed intelligence because Forecast fails closed under its scoring configuration, including K/DST, with insufficient qualifying independent full-season sources and no preserved preseason baseline for that newly connected league.

## Boundary
Do not change Forecast rules, evidence requirements, scoring authority, or fabricate projections to make lifecycle acceptance pass.

## Resume condition
Resume lifecycle acceptance after Research/Forecast and governed implementation remove the upstream blocker. Then complete every gate in `../ACCEPTANCE_GATES.md`, including 7/7, atomic promotion, correct-league populated surfaces, restart survival, stale-job reconciliation, and foreground latency.
