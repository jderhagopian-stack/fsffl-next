# FSFFL NEXT — Active Workstreams

Updated: 2026-09-25

## Management
**State:** ACTIVE  
Owns sequencing, scope, gates, product decisions, and cross-workstream conflict resolution.

## Performance
**State:** MANAGEMENT GATE  
Lifecycle/league-switch repair remains gated on governed Forecast authority for the newly connected league. Performance must not weaken Forecast/model authority to force 7/7.

## Forecast Research — K/DST + New-League Bootstrap
**State:** DIRECTIVE COMPLETE — RESEARCH  
The implementation-ready research contract is persisted in `workstreams/RESEARCH.md` and `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.

## Product / Forecast Implementation
**State:** AUTHORIZED / ACTIVE — PR #215 RECONCILING WITH CURRENT MAIN  
Management accepted the completed Research contract and authorized bounded implementation. Durable implementation state is in `workstreams/IMPLEMENTATION.md` and `artifacts/implementation/forecast_k_dst_contracts_20260924/IMPLEMENTATION_HANDOFF.md`.

PR #215 implements the governed K/DST subject/scoring contracts, active-rule completeness including fail-closed `fum_lost`, deterministic K/DST realized-outcome reconstruction, and non-promoting calibration harnesses. Required executable checks passed on the implementation head. Main subsequently advanced through Market PR #216, so PR #215 is being reconciled without dropping either workstream's state.

No production K/DST provider authority, uncertainty calibration, fabricated 2026 preseason baseline, or downstream K/DST economics are promoted. After code reconciliation/merge, the workstream is expected to stop at the empirical/source evidence gate unless qualifying evidence is already present.

## Market / Trade Discovery Architecture Review
**State:** MANAGEMENT GATE — ARCHITECTURE REVIEW COMPLETE  
The actual shipped Market/Search/Value/Team Utility/Decision/Owner Intelligence/Simulation paths were inspected and the implementation-ready governed contract is persisted in:
- `workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

The review separates OpportunityHypothesis, MarketOpportunity, CandidatePath, and raw package variants; moves bounded pre-Simulation Decision screening before For You eligibility; defines clustering/diversity; preserves zero broad changed-state Simulation calls; and separates Core 7/7 lifecycle readiness from Market surface readiness.

No broad Market code is authorized by this state. Management acceptance is the next gate.

## Market acceptance
**State:** NOT ACCEPTED  
Do not close Market North Star on the current implementation. The architecture diagnosis is now complete, including the Player Board / Free Agents readiness contradiction, but bounded implementation and repeat physical-iPhone acceptance remain outstanding.

## Home × Franchise audit
**State:** DEFERRED  
Resume after the Market discovery architecture is settled unless Management explicitly reprioritizes it.
