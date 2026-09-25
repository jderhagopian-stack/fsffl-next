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
**State:** MANAGEMENT GATE — CONTRACT READY, NOT YET AUTHORIZED  
Research has supplied the governed implementation sequence. Do not begin speculative K/DST/model work until Management explicitly authorizes the implementation directive.

The remaining production dependency includes:
- K/DST subject + rule-complete scoring implementation;
- historical calibration/source-evidence promotion;
- governed new-league bootstrap/migration behavior;
- downstream compatibility and lifecycle acceptance.

## Deferred sequence
After Forecast implementation is authorized, completed, and the new-league lifecycle passes acceptance:
- Market physical-iPhone acceptance
- Home × Franchise redundancy audit
- Trade Discovery architecture review before Trade Center expansion
