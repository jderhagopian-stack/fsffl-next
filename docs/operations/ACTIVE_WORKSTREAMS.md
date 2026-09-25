# FSFFL NEXT — Active Workstreams

Updated: 2026-09-25

## Management
**State:** ACTIVE  
Owns sequencing, scope, gates, product decisions, and cross-workstream conflict resolution.

## Performance
**State:** ACTIVE — PRODUCTION ACCEPTANCE / LAST-GOOD RESTORATION  
The prior PR #211 K/DST-only Management Gate is obsolete for the active Performance directive.

The existing FSFFL Dynasty league regressed from previously valid 7/7 to visible 3/7 after Market PR #220. Performance traced this to last-good restoration semantics: terminal failed/interrupted enrichment could leave a newer state-only checkpoint restart-authoritative instead of the independently promoted complete bundle.

Durable repair chain:
- PR #222 / merge `514b27e9...`: preserves same-league complete intelligence across revalidation, restores same-league last-good after failed/interrupted refresh, keeps cross-league restore fail-closed, makes restored complete context truthful 7/7, and fixes the narrow mobile Refresh Intelligence grid/button;
- PR #226 / merge `50614b1d...`: startup readiness observability; this is the current live Render SHA;
- PR #227 / merge `ee221b29...`: test-only interrupted-refresh restoration regression.

Production #226 has already restarted twice with `jimmygoodjob` restored on state `203227df...` and `forecast=True simulation=True value=True complete=True`, with no automatic heavy intelligence launch and no startup errors.

Post-restart physical-device traffic has fetched the repaired static generation and successfully exercised product context, intelligence status, Home, Franchise, and Market. Home/Franchise are responsive, but Market cold load remains an active Performance defect: quick workspace took 36.705s and initial full workspace 48.396s before a cached full call dropped to 0.172s.

Remaining Performance gate is truthful visible 7/7/mobile-control confirmation plus repair of the cold Market foreground path. Do not require repeated manual refreshes.

## Forecast Research — 2026 Late-Start K/DST Exception
**State:** DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY  
Management's one-season-only 2026 current-date ROS exception has been fully researched and decomposed.

Durable handoff:
- `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- `artifacts/research/k_dst_late_start_exception_20260925/SOURCE_ACQUISITION_LEDGER.json`

The exception removes missing pre-Week-1 K/DST evidence from **current-forward 2026** authority. It does not create preseason evidence and cannot be used in 2027+.

Research has now:
- measured bounded empirical K and D/ST season-error and weekly-volatility on explicit reduced fingerprints;
- identified JerryGM as one current ROS provider candidate capable of Hodor-style 60+ K scoring and distributional D/ST PA-tier pricing;
- exhausted materially distinct public paths without finding a second independent source proving those same hard coordinates.

Current-forward Hodor authority still fails closed on second-source exact-coordinate coverage, live API/source-health validation, target-compatible whole-score uncertainty promotion, and deployable provider rights.

## Product / Forecast Implementation
**State:** BLOCKED — BOUNDED IMPLEMENTATION COMPLETE / EXTERNAL SOURCE-AUTHORITY GATES REMAIN  
PR #215 remains merged on canonical main at `407c1bf85e5dc75f92b9906719f82bcd11d97c31`. PR #233 merged on canonical main at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8` after its reconciled head passed full CI, focused corrective regression, Live Forecast corrective trace, and Corrective live provider numerical trace. Durable implementation detail is in `artifacts/implementation/k_dst_late_start_20260925/IMPLEMENTATION_HANDOFF.md`.

Management now explicitly authorizes execution of the bounded 2026 late-start implementation plan in `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`. This authorization permits implementation, testing, persisted evidence acquisition where source rights permit, and integration of the already-governed contracts. It does **not** authorize production Forecast promotion where evidence/rights gates remain red.

The bounded implementation must:
- persist a dedicated 2026-only current ROS artifact, never a preseason artifact;
- preserve exact acquisition/provenance/horizon/source-health;
- enforce schedule-aware subject-row freshness;
- retain >=2 independent sources per required metric/group;
- keep Hodor K fail-closed until the 60+ coordinate has two independent governed sources;
- keep Hodor D/ST fail-closed until PA-tier distribution and rare-event coordinates have two independent governed sources;
- reproduce the persisted reduced-fingerprint empirical measurements and promote uncertainty only after target compatibility is proven;
- reject the late-start path for 2027+.

All presently authorized evidence-independent implementation is complete. Provider/source rights, second-source exact Hodor-coordinate coverage, live exact-capability API validation, and target-compatible full-score uncertainty remain external evidence gates for deployed authority. No heuristic substitute is authorized.

## Market / Trade Discovery Architecture Review
**State:** DIRECTIVE COMPLETE — MANAGEMENT ACCEPTED  
The actual shipped Market/Search/Value/Team Utility/Decision/Owner Intelligence/Simulation paths were inspected and the implementation-ready governed contract is persisted in:
- `workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

The review separates OpportunityHypothesis, MarketOpportunity, CandidatePath, and raw package variants; moves bounded pre-Simulation Decision screening before For You eligibility; defines clustering/diversity; preserves zero broad changed-state Simulation calls; and separates Core 7/7 lifecycle readiness from Market surface readiness.

Management accepts the governed architecture. Bounded Market implementation is now authorized under the persisted handoff; the architecture review itself is complete.

## Market / Trade Discovery Implementation
**State:** IMPLEMENTATION COMPLETE — PHYSICAL IPHONE ACCEPTANCE GATE  
PR #220 implements the Management-accepted Opportunity/Search/Market contract. Full CI, Home, Franchise, League Atlas, PR164 corrective regression, and live Forecast corrective trace are green on the final code head. Durable evidence is in `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`.

No further broad Market implementation is authorized before deployed physical acceptance unless that validation reveals a defect.

## Market acceptance
**State:** MANAGEMENT GATE — REPEAT PHYSICAL IPHONE / SAFARI  
Implementation-level acceptance is satisfied, but Market North Star is not product-closed until the merged/deployed build is validated on the physical iPhone/Safari experience against the accepted For You, Trade Finder, Player Board, Free Agents, readiness, and mobile scanability contract.

## Home × Franchise audit
**State:** DEFERRED  
Resume after the Market discovery architecture is settled unless Management explicitly reprioritizes it.
