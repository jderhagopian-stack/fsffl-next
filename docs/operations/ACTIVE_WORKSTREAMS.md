# FSFFL NEXT — Active Workstreams

Updated: 2026-09-24

## Management
**State:** ACTIVE  
Owns sequencing, scope, gates, product decisions, acceptance of the completed Forecast research contract, and authorization of any implementation directive.

## Performance
**State:** MANAGEMENT GATE  
Lifecycle/league-switch repair has reached an upstream Forecast dependency. See `workstreams/PERFORMANCE.md`. Performance must not change Forecast/model authority to force 7/7.

## Forecast Research — K/DST + New-League Bootstrap
**State:** DIRECTIVE COMPLETE — RESEARCH  
The implementation-ready research contract, evidence, unresolved risks, fixture matrix, and downstream handoff are persisted in:
- `workstreams/RESEARCH.md`
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Research PR/history: #213 / `91018b39967a0775ad830a6a750a2588e7f041d0`.

No production K/DST authority was promoted and no implementation was begun.

## Product / Forecast Implementation
**State:** AUTHORIZED / ACTIVE — PR #215 IN ACCEPTANCE VALIDATION  
Management accepted the completed Research contract and authorized bounded implementation. Durable implementation state is in `workstreams/IMPLEMENTATION.md`.

PR #215 implements the Stage 1 governed subject/scoring contracts and the non-promoting Stage 2 outcome/calibration harness. It does not promote live K/DST providers, K/DST uncertainty, a 2026 K/DST preseason baseline, or downstream K/DST economics. Merge remains gated on regression-clean CI and fail-closed evidence behavior.

After code acceptance, the next dependency remains empirical/source evidence promotion, not speculative implementation.

## Deferred sequence
After the bounded Forecast implementation and empirical evidence gates are completed, and the new-league lifecycle passes acceptance:
- Market physical-iPhone acceptance
- Home × Franchise redundancy audit
- Trade Discovery architecture review before Trade Center expansion
