# FSFFL NEXT — Active Workstreams

Updated: 2026-09-25

## Management
**State:** ACTIVE  
Owns sequencing, scope, gates, product decisions, and cross-workstream conflict resolution.

## Performance
**State:** ACTIVE — MARKET FOREGROUND LATENCY ONLY

The Hodor / `jder52` app-wide lifecycle corrective is **DIRECTIVE COMPLETE — PERFORMANCE** at PR #242 / merge `6bc184487e7e6619350337b374f67976457f8317`, live as Render `dep-darbvcm0tbcc73b02bg0`. Production closeout proves valid Hodor State and a 16-player roster remain usable, the exact blocked stage is Forecast, no cross-league last-good bundle is served, startup launches no heavy intelligence job, and all eight configured workflows are green.

Hodor's inability to reach full Forecast/Simulation/Value readiness is no longer Performance implementation work. It remains blocked on Forecast/Product authority and evidence gates.

The separately open Performance-owned dimension is Market foreground latency. Current physical-device evidence remains approximately 44.1s internal / 44.9s hosted for cold automatic discovery and approximately 31.8s, 41.4s, and 47.8s for focused Target Player requests, versus ~0.137s warm full-workspace response. Further Performance work must reduce cold/focused latency without changing accepted Market discovery, Decision-screen, or Simulation-authority semantics.

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


## Forecast Research — Auxiliary Single-Source Authority
**State:** MANAGEMENT GATE — SINGLE-SOURCE AUXILIARY AUTHORITY DECISION

The bounded materiality/source-quality study is complete. Durable evidence is in `artifacts/research/auxiliary_single_source_authority_20260925/`.

Research supports a generalized certified auxiliary single-source tier in principle but recommends **zero initial source/coordinate promotions**. Materiality-side candidates are the K 60+ incremental premium, K XP miss, D/ST safety, and defensive two-point return. None currently passes the full proposed source-quality/rights/stability contract.

FUMBLES_LOST, FG misses, common 2PT, D/ST blocked kicks/ST TD/FF/FR, nonlinear PA, and ordinary volume/TD/reception coordinates remain core/material under the measured thresholds.

Production authority is unchanged. Management must accept or reject the proposed certification policy before authority-infrastructure implementation or source-specific certification begins.

## Product / Forecast Implementation
Management now defines Refresh Intelligence as the canonical manual league sync/update: refresh Sleeper State first, then reuse/rebuild governed intelligence for that exact State. Current code forecasts against pre-refresh State before provider State refresh, so the active corrective must reconcile this ordering.
Management clarified that persisted-bundle restoration is optional for correctness: if a selected league's current State has no compatible reusable bundle, Product/Forecast must automatically rebuild governed intelligence for that State and expose truthful progress/blockers. Acceptance must cover both reuse and rebuild paths.
Physical iPhone switching Hodor → FSFFL now exposes a non-regression failure: the current FSFFL State is newer than the preserved complete bundle, but the shell shows green 7/7 while current Simulation/position strength/classification are unavailable. The old complete artifacts remain safely persisted. Market physical acceptance is paused until Forecast/Product fixes switch/restoration/readiness truth and validates the existing fully supported league.
Management physical-iPhone acceptance now shows Hodor at green 7/7 while Simulation, position strength, classification and Intrinsic remain unavailable. This is an acceptance failure in readiness/presentation semantics: pipeline completion must not masquerade as full core-intelligence readiness. Canonical corrective detail is in `workstreams/IMPLEMENTATION.md`.
**State:** ACTIVE — HODOR SHARED-FORECAST POPULATION / PARTIAL-COVERAGE CORRECTIVE / PR #238 HARDENING  
Management has superseded the prior blanket Forecast implementation stop for the current Hodor population issue. Full K/DST authority remains externally gated, but valid canonical forecastable coordinates must populate under the newly codified FULL/PARTIAL/UNSUPPORTED rule; bounded unsupported rare/special-event coordinates may remain explicit omissions and must not collapse unrelated Forecast coverage. Canonical detail is in `workstreams/IMPLEMENTATION.md`.

PR #244 is merged at `edb9c0f9a1ccea4250761c63f65694d449c2d285`, resolving the league-scoring/source-health coupling and adding league-agnostic source health, scoring-family isolation, explicit partial coverage, separate Simulation gating, exact-state provisional K/DST materialization, and current Forecast coverage diagnostics.

PR #245 is merged at `7ad0d5ce4be038a2615433467227cdcfd3da85a4`. Its accepted head `342f8c8e0ec4b0c8b1ffb5695abaf81ed98cb518` passed 1,620 full-suite tests plus PR164, Live Forecast, Home and League Atlas focused validations. It adds generic acceptance across unrelated synthetic Sleeper league identities/scoring profiles and makes partial-authority job completion text truthful.

Render deploy `dep-daredcl9fdbs7398s55g` is live on PR #245's exact merge. Production Hodor now durably restores `forecast=True simulation=False value=True complete=False` on refreshed State `d28de4cc...`. The shared Forecast corrective is complete; the absent Simulation is an explicit authority outcome, not a Forecast pipeline failure.

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

PR #237 is merged on canonical main at `33b969b04180893f7e582c0ebd76c54bea81961d`, implementing the Management-authorized 2026 provisional partial-rule tier with machine-readable downstream gating: Presentation/readiness/analytics may expose the provisional contract, while Value/Simulation/Team Utility/Decision/Search remain blocked from silently treating it as full Forecast truth.

PR #238 is closed unmerged as superseded/reconciled: its six non-test implementation files were verified byte-identical to current main, so its exact league/state provisional K/DST safety hardening is already present and no replay merge is required.

Provider/source rights, qualifying production ROS evidence, second-source exact Hodor-coordinate coverage, live exact-capability API validation, and target-compatible full-score uncertainty remain external gates for **full** K/DST authority. No heuristic substitute is authorized.


Durable corrective closeout:
- `artifacts/implementation/hodor_shared_forecast_20260925/IMPLEMENTATION_HANDOFF.md`

This Product / Forecast corrective has reached **DIRECTIVE COMPLETE**. The external full-K/DST gates above are residual authority dependencies, not unfinished shared-Forecast implementation.

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
**State:** MANAGEMENT GATE — PR #240 DEPLOYED; REPEAT PHYSICAL IPHONE / SAFARI  
PR #240 is merged at `7b7f44ef0b3bf22008d80a3363aec1e6ce6f19d9` and live as Render deploy `dep-darb4lid0e5s73e2nnkg`, static generation `20260925-market-beta-corrective2`. Full CI and every configured focused/authority workflow are green.

The corrective pass makes competitive posture an early Search-admission lens where governed evidence supports it, changes Trade Finder to explicit configure → **Find opportunities** → running/completion, publishes focused-search exhaustion reasons, and separates Forecast from Intrinsic build/coverage truth. The eight-path preliminary Decision budget and zero broad exact changed-state Simulation boundary are unchanged.

All non-physical Market validation is exhausted. The current deployed process restored Hodor/new-league State without Forecast/Simulation/Value, consistent with the separate active Performance lifecycle blocker; no authenticated PR #240 Market request has yet emitted the new production focus/value-lens telemetry. Repeat physical iPhone/Safari Market acceptance plus subsequent telemetry inspection is now required. If Hodor remains too incomplete to exercise Market, the prerequisite belongs to Forecast/Product, not Performance and not a Market authority workaround.

## Home × Franchise audit
**State:** DEFERRED  
Resume after the Market discovery architecture is settled unless Management explicitly reprioritizes it.


### 2026 provisional K/DST Management exception
Management has authorized a second bounded 2026-only private-beta exception: Forecast Implementation may produce provisional current-ROS K/DST Forecast evidence using only governed supported scoring coordinates, while explicitly omitting unsupported 60+ K increments, nonlinear D/ST PA-bucket expectation, and unsupported rare events rather than fabricating them. Provisional/partial-rule authority must be machine-readable and visible downstream; full-authority gates remain unchanged; the mode must fail closed for 2027+. Canonical detail is in `workstreams/RESEARCH.md`.


## Performance / App-wide League Lifecycle Corrective
**State:** DIRECTIVE COMPLETE — PERFORMANCE

PR #242 closed the Performance-owned Hodor lifecycle defect and is merged/deployed/production-validated. Current Hodor State and roster remain usable while derived intelligence is incomplete; the terminal blocked stage is truthfully Forecast; cross-league intelligence is not served. Remaining Hodor full-intelligence authority is owned by Forecast/Product, not Performance.


## Current superseding checkpoint — 2026-09-26
- **Forecast/Product Implementation:** **MANAGEMENT GATE — FUMBLES_LOST FORECAST AUTHORITY.** State-first sync/reuse-or-rebuild/truthful-readiness is complete and deployed through PR #246/#249/#251/#252. Current FSFFL rebuild is truthfully partial because the governed raw Forecast lacks FUMBLES_LOST; Simulation is not promoted.
- **Forecast Research — FUMBLES_LOST:** **BLOCKED — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS.** Management superseded the same-horizon/whole-ROS alternatives with a bounded current-only supplement. Research's shortest technical pair is now JerryGM + LineupExperts Premium, with normalization/uncertainty and historical guards persisted in `artifacts/research/fumbles_lost_current_only_certification_20260926/`. No unrelated offense Forecast coordinate is rebased.
- **Auxiliary single-source policy:** **MANAGEMENT ACCEPTED — ZERO INITIAL CERTIFICATIONS.** FUMBLES_LOST is explicitly outside that exception.
- **Market acceptance:** **PAUSED** for full product acceptance until current FSFFL can legitimately promote Simulation. Physical lifecycle/readiness truth may still be tested independently.
- **Performance:** State-first/lifecycle work is closed; separate Market foreground latency remains its only open dimension.


## Superseded history — 2026-09-26 ordinary-offense ROS recovery
The whole ordinary-offense ROS recovery path was authorized briefly and then explicitly superseded by Management's bounded current-only FUMBLES_LOST correction. It is **not an active workstream** and must not be resumed unless Management re-authorizes it.
- **Research:** SUPERSEDED / CLOSED.
- **Implementation:** SUPERSEDED / NOT AUTHORIZED.
- **Existing FSFFL:** current partial state remains non-accepted pending the bounded FUMBLES_LOST supplement.
- **Market acceptance:** remains paused until FSFFL full current-forward capability is legitimately restored.


## Superseding critical path — bounded FUMBLES_LOST supplementation
- **Research:** **BLOCKED — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS.** Current-only normalization/uncertainty is implementation-ready; shortest technical pair is JerryGM + LineupExperts Premium. Certification awaits written rights/independence confirmation plus authenticated full-pool live captures.
- **Implementation:** **BLOCKED — EVIDENCE-INDEPENDENT SUPPLEMENT PLUMBING COMPLETE / EXTERNAL PROVIDER RIGHTS + LIVE CREDENTIALS REQUIRED.** PR #253 merged at `407050092186b72386f4b264cf675837ebeaa606`; Research-aligned PR #255 merged at `91ee2acef8e8dc8e1f2371d237c9c765f2061ae1`. Provider-neutral evidence/persistence, 17-game current-pace normalization, non-zero uncertainty, separate mixed-vintage scorer input, schedule freshness and selective invalidation/rebuild contracts are implementation-complete. No provider is registered and no production FUMBLES_LOST authority is promoted. Durable handoff: `artifacts/implementation/fumbles_lost_current_supplement_20260926/IMPLEMENTATION_HANDOFF.md`.
- **Whole ordinary-offense ROS rebase:** SUPERSEDED / NOT AUTHORIZED.
- **Historical/preseason use:** supplemental fumble evidence is explicitly ineligible before its acquisition time and must never be written into the preseason baseline.
- **Market acceptance:** remains paused until current FSFFL Simulation is legitimately restored.


## Superseding FSFFL recovery path — first-party FUMBLES_LOST model
- **Research:** ACTIVE — build/validate a first-party FSFFL exact FUMBLES_LOST Forecast model from governed historical outcomes and current point-in-time inputs.
- **External provider permission path:** FALLBACK ONLY; no longer the immediate dependency for restoring FSFFL.
- **Implementation:** supplement plumbing from PR #253/#255 remains reusable. Production promotion waits for a validated first-party Research handoff.
- **Existing FSFFL:** current partial state remains non-accepted; target remains legitimate full current Forecast + Simulation.
- **Market acceptance:** paused until FSFFL Simulation is restored.
