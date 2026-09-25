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
The newly connected league cannot complete governed intelligence because production Forecast authority for its K/DST scoring configuration is not implemented/promoted.

Forecast Research has completed the architecture and late-connect bootstrap contract. See:
- `RESEARCH.md`
- `../../../artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Research completion does not remove the runtime blocker.

## Boundary
Do not change Forecast rules, evidence requirements, scoring authority, or fabricate projections to make lifecycle acceptance pass.

Do not treat Research completion as authority for Performance to implement Forecast changes.

## Resume condition
Resume lifecycle acceptance only after Management-authorized Forecast implementation and required evidence promotion remove the upstream blocker. Then complete every gate in `../ACCEPTANCE_GATES.md`, including 7/7, atomic promotion, correct-league populated surfaces, restart survival, stale-job reconciliation, and foreground latency.
