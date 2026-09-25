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

## Forecast Research — League-Agnostic Scoring Coverage
**State:** DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY  
The cross-platform scoring-rule and Forecast-input audit is complete.

Durable artifacts:
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PLATFORM_COVERAGE_MATRIX.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/GAP_ANALYSIS.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/IMPLEMENTATION_HANDOFF.md`

The registry covers 89 canonical coordinate/rule-semantic requirements and the matrix records 48 primary-source platform/preset or rule-family mappings. The audit confirms conventional linear offense is strong, while material gaps remain in direct 2PT/returns, volume/first-down/target coordinates, nonlinear game-threshold distributions, cross-platform rule semantics, IDP subject support, and raw-provider field retention.

Research recommends a bounded zero-authority-change Stage 0 + Stage 1 implementation: canonical registry/rule/capability contracts plus provider raw-superset preservation. New scoring/model authority is not authorized by this Research completion.

## Product / Forecast Implementation
**State:** ACTIVE — 2026 PROVISIONAL K/DST DEGRADED-AUTHORITY MODE AUTHORIZED  
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

## Scoring Coverage Implementation
**State:** MANAGEMENT GATE — STAGE 0/1 PLAN READY, NOT AUTHORIZED  
Research recommends the first bounded package contain only:
- Scoring Coordinate Registry definitions;
- canonical scoring-rule semantics;
- FULL/PARTIAL/UNSUPPORTED capability diagnostics;
- compatibility compilation for existing scoring;
- rights-permitted raw provider superset preservation.

It must introduce **zero new production scoring/model authority** and preserve current outputs as a regression oracle.

Stages for direct new coordinates, nonlinear distributions, IDP, punter/head-coach families, or new production authority require separate authorization/evidence gates.

## Market / Trade Discovery Architecture Review
**State:** DIRECTIVE COMPLETE — MANAGEMENT ACCEPTED  
The actual shipped Market/Search/Value/Team Utility/Decision/Owner Intelligence/Simulation paths were inspected and the implementation-ready governed contract is persisted in:
- `workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

The review separates OpportunityHypothesis, MarketOpportunity, CandidatePath, and raw package variants; moves bounded pre-Simulation Decision screening before For You eligibility; defines clustering/diversity; preserves zero broad changed-state Simulation calls; and separates Core 7/7 lifecycle readiness from Market surface readiness.

Management accepts the governed architecture. Bounded Market implementation is now authorized under the persisted handoff; the architecture review itself is complete.

## Market / Trade Discovery Implementation
**State:** IMPLEMENTATION COMPLETE — CORRECTIVE DEPLOYED  
PR #232 contains the Management-authorized physical-iPhone corrective implementation plus the discovery-quality / compute-discipline clarification. It is merged at `eac3ac1074b80e4199e4e4f4cd3c708ffffbd02b` and live on Render through deploy `dep-dar9cdrtqb8s73819ap0` from corrective deployment main `33657f9f612fad2cbc4d112531e0912e04140762`.

Full/focused CI is green. Production startup restored the correct existing league with Forecast/Simulation/Value complete and no startup errors. Broad discovery preserves the approved eight-path preliminary Decision budget and zero exact changed-state Simulation calls; strategic and explicit-intent admission occurs before package generation, and the lightweight Decision-owned screen replaces broad full Trade Center analysis.

## Market acceptance
**State:** MANAGEMENT GATE — REPEAT PHYSICAL IPHONE / SAFARI  
All available non-physical corrective validation is exhausted. No authenticated Market request has yet hit the newly deployed instance, so production funnel telemetry cannot be truthfully observed until the next real authenticated interaction. Repeat physical-iPhone/Safari validation must exercise the four surfaces and at least one Trade Finder intent; afterward inspect the emitted candidate-count/rejection/timing/cache/preliminary-screen diagnostics before product closeout.

## Home × Franchise audit
**State:** DEFERRED  
Resume after the Market discovery architecture is settled unless Management explicitly reprioritizes it.


### 2026 provisional K/DST Management exception
Management has authorized a second bounded 2026-only private-beta exception: Forecast Implementation may produce provisional current-ROS K/DST Forecast evidence using only governed supported scoring coordinates, while explicitly omitting unsupported 60+ K increments, nonlinear D/ST PA-bucket expectation, and unsupported rare events rather than fabricating them. Provisional/partial-rule authority must be machine-readable and visible downstream; full-authority gates remain unchanged; the mode must fail closed for 2027+. Canonical detail is in `workstreams/RESEARCH.md`.
