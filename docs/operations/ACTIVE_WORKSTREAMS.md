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
- **Forecast Research — FUMBLES_LOST:** **DIRECTIVE COMPLETE — FIRST-PARTY MODEL READY FOR IMPLEMENTATION.** The governed first-party calibrated position-opportunity model clears chronological OOT accuracy/stability/coverage gates. Durable handoff: `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`. External provider permissions are fallback only.
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
- **Research:** **DIRECTIVE COMPLETE — FIRST-PARTY MODEL READY FOR IMPLEMENTATION.** Accepted model is `next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`; combined OOT RMSE 0.8105 vs 1.0425 omission, current identity coverage 97.61%, non-zero position/cold-start uncertainty persisted.
- **External provider permission path:** FALLBACK ONLY; no longer the immediate dependency for restoring FSFFL.
- **Implementation:** **AUTHORIZED NEXT — FIRST-PARTY MODEL INTEGRATION / PRODUCTION ACCEPTANCE.** Reuse PR #253/#255 supplement plumbing; preserve all other offense coordinates and PIT/preseason guards; rebuild current FSFFL and promote Simulation only after implementation tests and current authority acceptance.
- **Existing FSFFL:** current partial state remains non-accepted; target remains legitimate full current Forecast + Simulation.
- **Market acceptance:** paused until FSFFL Simulation is restored.


## Intrinsic Value Research — Horizon Term Structure
**State:** **MANAGEMENT GATE — LONG-HORIZON INTRINSIC ARCHITECTURE**

Research is complete. The evidence supports `H1 | governed H3 | H5 challenger | terminal/career band`, while rejecting an exact Y6-Y8/career cardinal extension under current evidence. Production H3 is unchanged and no implementation authority is granted. Durable handoff: `artifacts/research/intrinsic_term_structure_20260926/RESEARCH_CLOSEOUT.md`.


## 2026-09-26 latest recovery / horizon checkpoint
- **FSFFL restoration:** PR #258 and #259 are merged; main CI is green; #259 is live. Production reached FULL Forecast/Simulation/Value once after deploy, but a later fresh State exposed two WRs without first-party FUMBLES_LOST coverage, returning current capability to partial and withholding Simulation. Forecast/Product remains ACTIVE on that generic two-player coverage gap.
- **Long-horizon Intrinsic Research:** **MANAGEMENT GATE.** Historical selection and post-selection current shadows are complete. H5 carries useful separate horizon signal; exact terminal/career cardinal value is not supported. Production H3 remains unchanged; no implementation authority.
- **Market physical acceptance:** remains paused until current FSFFL Simulation is stably restored.


## Current Management direction — localized partials + horizon report
- **Forecast/Product:** ACTIVE. Fix the generic current-subject reconciliation gap so two provider-absent/current-State WRs do not unnecessarily hold league Simulation hostage; preserve fail-closed semantics only where an unresolved subject can materially affect the consumer.
- **Intrinsic term-structure Research:** **MANAGEMENT GATE.** Current-player/position diagnostics are complete and the Management architecture recommendation is persisted. Plain-language PDF is the human-readable closeout; no production implementation is authorized.


## Simulation readiness scope correction — 2026-09-26
- **Forecast/Product:** ACTIVE. Current two partial FUMBLES_LOST players are verified unrostered. Simulation must gate on roster/consumer dependencies, not every universal Forecast row. Preserve the player-level partials while restoring roster-based Simulation, then complete generic supplement-universe reconciliation and production acceptance.


## 09:12 ET production checkpoint
- **Forecast/Product:** ACTIVE, but the original FSFFL scoring/Simulation restoration is now proven FULL in production on PR #260. Remaining acceptance issue is a Hodor-switch durable checkpoint timeout during the cross-league sequence. Fix only that persistence/switch defect and rerun end-to-end acceptance.
- **Intrinsic term-structure Research:** superseded by the completed comparative Y4+ study below. The updated plain-language Management PDF has now been produced; durable authority is the comparative Research closeout.


## Intrinsic long-horizon comparative modeling — 2026-09-26
**State:** **MANAGEMENT GATE — LONG-HORIZON MODEL ARCHITECTURE**

The reopened six-family Y4+ comparison is complete. No defensible cardinal model-family breakpoint or position/horizon routing is promoted. `two_part_state` remains the robust annual Y4-Y8 Research family across all positions; hazard and career-transition models remain diagnostic/terminal-state challengers. Production H3 remains unchanged. Durable handoff: `artifacts/research/intrinsic_y4plus_model_family_20260926/FINAL_CLOSEOUT.md`.


## PR #261 live acceptance — switching still open
- **Forecast/Product:** ACTIVE. Existing FSFFL is FULL in production, but cross-league State-first acceptance still fails on Hodor switch because the persisted first-party FUMBLES_LOST supplement is bound to a different State than the checkpoint target. Do not call full app switching accepted yet.


## Latest physical acceptance findings — Intrinsic + readiness UI
- **Forecast/Product Implementation:** ACTIVE. In addition to the exact-State Hodor switch defect already open, physical iPhone acceptance now exposes a production H3 Intrinsic subject-scope regression: unrelated players outside the frozen Future-I1 standard coordinate can collapse Intrinsic globally. Fix by scoping H3 compatibility to its governed subjects while preserving per-player unavailability outside authority.
- **Presentation:** mobile shared readiness strip must be compacted. FULL = one-line intelligence-current + Refresh; building = progress + short active phase; capability chips appear only for exceptions/details.
- **Y4+ Intrinsic Research:** **MANAGEMENT GATE.** Comparative model-family work is complete and remains separate from the production H3 restoration corrective; do not use Y4+ research to patch H3.

## 2026-09-26 current execution reconciliation
- **Forecast/Product Implementation:** ACTIVE — PR #262 open, not merge-ready. Fix exact-compatible same-State Forecast reuse plus static-generation regressions, then green CI/focused workflows, deploy, and complete FSFFL → Hodor → FSFFL → restart acceptance. This is the app critical path.
- **Intrinsic Research:** ACTIVE — bounded next phase only. Comparative Y4+ model-family selection is complete and accepted by Management. Research now owns terminal/career-state representation plus the uncertainty/presentation contract required before any H5/Y4+ production promotion. Production H3 remains unchanged.
- **Market:** HOLD for core acceptance; accepted corrective remains deployed and should be physically exercised after #262 closes the switch/Intrinsic/readiness path.
- **Performance:** ACTIVE only on Market foreground latency; await fresh authenticated post-core Market timings.
- **Home × Franchise / broader Scoring Coverage:** deferred pending current reliability/acceptance gates.

## Long-horizon Research scope expansion — comprehensive architecture
- **Intrinsic Research:** **MANAGEMENT GATE — COMPREHENSIVE LONG-HORIZON ARCHITECTURE.** The expanded feature/model/routing search is complete. A richer development-selected hierarchical route failed the untouched final-holdout QB-Y8 safety rule, so the final Research architecture preserves separate position×horizon fits of `forecast10 + two_part_ridge` across Y4-Y8. No breakpoint/router/shared architecture is promoted; production H3 remains unchanged.
- **Production H3:** unchanged and not part of this implementation path.
- **Forecast/Product Implementation:** remains the app critical path independently; Research expansion must not block or alter PR #262 corrective acceptance.

## PR #263 core-acceptance transition
- **Implementation:** ACTIVE — PR #263 merged at `4cd5715...`; post-merge CI/deploy/full FSFFL → Hodor → FSFFL → restart production acceptance is the immediate blocker to Management Market testing.
- **Performance:** ACTIVE but downstream of that acceptance by only one gate. As soon as core acceptance passes, immediately collect fresh authenticated Market timings and continue cold/focused latency optimization; no further Management authorization is needed.
- **Market:** accepted corrective remains deployed; physical acceptance resumes as soon as core switch/Intrinsic/readiness reliability is proven.

## Queued near-term Performance phase — Simulation engine
- **General Simulation efficiency:** QUEUED. After core #263 acceptance and the immediate Market foreground-latency pass, Performance should move directly into the deferred fresh 50,000-run Simulation kernel optimization phase.
- Existing cache/reuse/coalescing/progressive-delivery work does not close this objective; the fresh kernel itself remains the target.
- First exhaust exact-output-preserving software optimizations. Any non-bit-identical but mathematically equivalent kernel change requires a separate Management reproducibility/statistical-equivalence gate.
- Do not reduce the canonical 50,000 runs merely for speed.

## Sequenced legacy recovery pipeline
- **NOW:** PR #263 production acceptance → Market physical acceptance → Market foreground latency.
- **NEXT:** dedicated Simulation modernization: convergence-count study + fresh-kernel/vectorization work + preserve replayable Multiverse identity.
- **THEN:** historical intelligence foundation: PIT State reconstruction, player franchise history, asset lineage, dated intelligence snapshots.
- **AFTER FAST SIMULATION:** repeated-seed Decision sensitivity and context-normalized Owner Intelligence.
- **LATER PRODUCTIZATION:** Multiverse stories, trade genealogy, Record Book, historical trade review, Alternate History, preseason media guide and other league-memory surfaces.
- **PARALLEL:** comprehensive long-horizon Forecast/Intrinsic Research continues independently.

## Post-PR263 Management reconciliation — core closed, Performance now critical path
- **Forecast/Product Implementation:** **DIRECTIVE COMPLETE.** Post-PR263 production acceptance passed FSFFL → Hodor → FSFFL → restart, exact-State/user isolation, FSFFL FULL Forecast/Simulation/Value, governed H3 non-regression, and compact mobile readiness. Do not continue or reopen this corrective absent a new regression.
- **Market:** physical iPhone/Safari acceptance is now unblocked on the fully governed FSFFL league. Use the already-deployed PR #240 corrective; no redesign is authorized.
- **Performance:** **ACTIVE — IMMEDIATE CRITICAL PATH.** Resume Market cold/focused latency work now using fresh authenticated FSFFL traffic and the existing ~44.9s cold / ~31.8–47.8s focused baseline. Exhaust profiling/optimization/deploy/remeasure to terminal state.
- **Simulation modernization:** immediately follows Market latency; Performance is already authorized to continue into convergence-count study + fresh-kernel/vectorization work + Multiverse identity preservation without another sequencing decision.
- **Intrinsic Research:** comprehensive Y4-Y8 architecture study continues independently in parallel.

## Physical regression after post-PR263 closeout — app acceptance reopened
- **Forecast/Product Implementation:** **ACTIVE AGAIN — PRODUCT-SURFACE CORRECTIVE.** The narrower State-first/restart acceptance remains valid, but Management physical testing found hosted Intrinsic/future-forecast unavailability, incomplete Player Intelligence trajectory output, and a League Atlas presentation-module failure.
- **Readiness presentation:** ACTIVE within the same corrective. While loading, expose the actual phase + served last-good/as-of state; once complete, collapse to the thin strip with a governed “as of” timestamp. Do not claim unqualified “Intelligence current” when supported Intrinsic or another required product capability is unavailable.
- **Performance / Market latency:** **HOLD FOR THIS CORRECTIVE.** Do not optimize Market against a product state that Management cannot yet accept. Preserve prior Performance evidence and resume immediately after physical product acceptance.
- **Simulation modernization:** remains queued behind Market latency.
- **Intrinsic Y4-Y8 Research:** **MANAGEMENT GATE.** Comprehensive study is closed pending Management architecture/product/promotion decisions; no production authority.

## Long-horizon Research reopened after all-or-nothing fallback review
- **Intrinsic Y4-Y8 Research:** **MANAGEMENT GATE — CELL-SPECIFIC LONG-HORIZON ARCHITECTURE.** Repeated rolling validation selects soft cell shrinkage as the best general Y4-Y7 Research policy; exact support clears QB Y4, WR Y4 and QB Y6, while 13 other Y4-Y7 cells remain shrinkage-with-uncertainty and all Y8 cells remain coarse/uncertain for insufficient outer evidence. The incumbent has no blanket authority. The required age/experience/exposure audit is complete; nonlinear QB target-age/exposure is the strongest trajectory challenger. Production H3 remains unchanged.
- **Production H3:** unchanged.
- **Implementation/Product:** independent critical path; do not mix this Research corrective into the beta-restoration work.

## PR #265 physical acceptance remains open
- **Forecast/Product Implementation:** ACTIVE — deployed PR #265 improved lifecycle truth and restored League backend serving, but physical iPhone acceptance still fails on (a) vNext mapped-subject / governed Year-1 Intrinsic compatibility and (b) catastrophic mobile completed-readiness layout collapse.
- **Performance / Market latency:** HOLD until this deployed product gate closes.
- **Intrinsic long-horizon Research:** **MANAGEMENT GATE.** Cell-specific routing/shrinkage and age/experience/exposure corrective is complete pending Management architecture/promotion decisions.

## 2026-09-26 latest Forecast / Product availability checkpoint
- **Player Intelligence history memory corrective:** implementation **COMPLETE / DEPLOYED** at PR #267, merge `d737012079345768ef5cfd19debff97e0ede1bba`, exact Render deploy `dep-das4k27avr4c73909lsg`.
- **Acceptance state:** **BLOCKED — AUTHENTICATED HOSTED HISTORY LOAD + PHYSICAL IPHONE/IPAD ACCEPTANCE REQUIRED.**
- The corrective removes multi-season concurrency/full-population process retention, adds player-season + final career persistence/reuse, and preserves 202/loading/coalescing.
- Deterministic acceptance is green at 1,704 tests plus all configured focused workflows.
- No post-deploy authenticated PI history request has yet reached the new instance; fresh-start memory alone is not promoted as a memory-under-load pass.
- Do not reopen Intrinsic, State-first persistence, or broader Forecast authority for this blocker absent new direct evidence.
- Durable evidence: `artifacts/implementation/player_intelligence_history_memory_20260926/IMPLEMENTATION_HANDOFF.md`.

## 2026-09-26 — Current critical path after Intrinsic refresh diagnosis
- **Implementation — ACTIVE / immediate beta critical path**
  1. dependency-scoped Intrinsic compatibility/reuse so ordinary State advances do not trigger 3–4 minute cold Shapley rebuilds;
  2. correct Intrinsic readiness semantics so complete authorized 335-player vNext Intrinsic is not labeled partial solely because legacy provenance flags are absent;
  3. remove the redundant large Home intelligence-status card while preserving the thin readiness strip;
  4. preserve the PR #267 Player Intelligence memory corrective and revalidate physical PI history after the next deploy.
- **Research — ACTIVE / parallel Forecast freshness study**
  - add a governed current-football-state update layer for H3 covering injury/return, NFL trade, cut/signing, promotion/demotion, suspension/retirement;
  - explicitly decompose temporary availability from conditional healthy production, post-return role, recurrence risk and durable survival/career effects;
  - do not alter production H3 until Management accepts the research result.
- **Performance / Market latency — HOLD** until the Implementation beta-reliability gate closes.

## 2026-09-26 23:56 ET — Availability incident supersedes physical acceptance
- **Implementation — ACTIVE, highest priority:** restore last-good serving across restart / State sync / intelligence rebuild; preserve canonical roster display; correct readiness truth; coalesce automatic refresh; then re-run hosted lifecycle acceptance.
- **Research — ACTIVE / parallel:** historical current-football-state H3 validation and current-provider capture are complete; interpretation/closeout is now the only authorized Research work. Reconcile 4,793 injury episodes and 7,603 non-injury events against the frozen gates, preserve the no-double-counting rule and unchanged production H3, then persist a valid OPERATING_PROTOCOL terminal state. Detailed closeout directive is in `workstreams/RESEARCH.md`.
- **Performance — Simulation cold-kernel latency remains queued behind availability restoration.**
- **Market — HOLD** until the beta is again stably usable.


## Current football-state H3 Forecast Research
**State:** **MANAGEMENT GATE — CURRENT FOOTBALL-STATE H3 FORECAST UPDATE**

Historical and current-provider studies are complete. No broad event-rich H1-H3 updater is promoted. Recommended Research contract is provider/current-state aware and componentized: H1 availability is separated from healthy production, no double-counting is allowed when current ROS owns H1, temporary injuries do not receive generic H2/H3 penalties, and release/cut carries only a coarse H3 attachment/survival signal. Production H3 remains unchanged.

Durable handoff:
`artifacts/research/current_football_state_h3_20260926/RECOMMENDED_FORECAST_CONTRACT.md`.


## PR #270 availability transition — 2026-09-27
- **Implementation:** **MANAGEMENT GATE — PHYSICAL IPHONE / SAFARI AVAILABILITY ACCEPTANCE.** PR #270 merged at `2c63a9b05225759ba521da3e75fb65146b30fbbe`; exact Render deploy `dep-dasa5vg473hc73fd8uo0` is LIVE. All seven configured validations are green, startup restores FSFFL core + Intrinsic FULL, and the hosted acceptance runner recorded PASS across FSFFL → Hodor → FSFFL plus two manual refreshes. Physical verification is now the remaining availability gate.
- **Research:** **MANAGEMENT GATE — CURRENT FOOTBALL-STATE H3 FORECAST UPDATE.** Interpretation/closeout is complete; no broad event-rich updater is promoted, production H3 remains unchanged, and the narrow recommended contract is persisted.
- **Market:** HOLD until physical beta-availability acceptance passes.
- **Performance:** HOLD until physical beta-availability acceptance passes; ~390s cold 50K Simulation latency remains queued afterward.


## 2026-09-27 physical acceptance failure after PR #270
- **Implementation — ACTIVE / highest priority:** PR #270's hosted acceptance is superseded by physical failure under real cold-wake traffic. Correct combined cold wake + auto-sync + product hydration + PI memory pressure, restart restoration, cross-surface readiness truth, League/PI degradation, and the observed HTTP 429 recovery path. Home last-good serving partially worked and must be preserved.
- **Research — MANAGEMENT GATE:** current-football-state H3 closeout remains complete; do not reopen it.
- **Market — HOLD:** no physical Market acceptance until beta availability is stable.
- **Performance — HOLD:** preserve the queued ~390s Simulation kernel work, but do not pull general performance work ahead of the availability incident. Memory/lifecycle work necessary to keep the beta usable remains Implementation-owned.

## Runtime architecture corrective supersedes narrow PR #270 repair
- **Implementation — ACTIVE / sole product critical path:** perform the structural runtime architecture corrective in `workstreams/IMPLEMENTATION.md`; first trace regressions from the last usable PR #235-era baseline, then enforce bounded memory ownership/concurrency, restore-first lifecycle, compact last-good serving, and unified readiness. Do not close with endpoint-specific patches.
- **Research — MANAGEMENT GATE:** unchanged.
- **Market — HOLD.**
- **Performance — HOLD** except implementation-level profiling/resource techniques required by the availability corrective.

## 2026-09-27 research sequencing after Management decision
- **Implementation — ACTIVE / sole product critical path:** structural runtime architecture corrective remains highest priority.
- **Research — ACTIVE in parallel, non-production:** injury availability/time-to-return model + prospective ROS/event snapshot-retention architecture. No production H3 or Intrinsic change is authorized.
- **Market — HOLD.**
- **Performance — HOLD** except Implementation-required resource work.

## Research portfolio clarification — 2026-09-27
- **Research Track A — ACTIVE / non-production:** injury availability/time-to-return + prospective ROS/event snapshot retention.
- **Research Track B — ACTIVE / non-production:** Y4–Y8 long-horizon architecture and validation remains first-class and must not be dropped. Continue from the existing cell-specific Management gate; do not restart completed work.
- Production H3 and Intrinsic remain unchanged unless Management separately promotes a result.

## Joint injury-availability challenger — 2026-09-27
- **Research Track A remains ACTIVE:** after the separate availability/time-to-return result, run a separately frozen joint injury-availability challenger now. It must compare one coherent shared architecture against the separate-model benchmarks without post-hoc tuning or production promotion.


## 2026-09-27 10:55 ET — PR #271 physical gate remains FAILED
- **Implementation — ACTIVE / sole product critical path:** fix changed-State continuity after automatic Sleeper refresh. Preserve usable last-good presentation through State advance using a compact/durable read model, not a second heavy graph; repair the PR #273 hosted acceptance runner/deploy path; rerun full hosted journey with memory telemetry.
- **Resource evidence:** startup ~281 MB peak; changed-State physical path ~411 MB observed peak, below but close to the ~429 MB ceiling.
- **Market — HOLD:** Market did not cause the reset and must not receive a page-specific workaround.
- **Performance — HOLD:** no general latency work until availability passes.
- **Research — remains independent/parallel under its existing non-production directives.**


## Runtime architecture completion clarification — 2026-09-27
- **Implementation remains ACTIVE / sole product critical path.**
- Preserve PR #271 as the architectural foundation; complete its missing compact persisted presentation-continuity layer on current `main`.
- Repair PR #273's acceptance-harness startup/deployment path and use that harness to validate the corrected runtime end to end.
- No page-specific adapters or Market-specific workaround are authorized.


## 2026-09-27 — Management sequencing after model-selection governance correction
- **Implementation — ACTIVE / sole product availability critical path:** complete PR #274 runtime presentation continuity + hosted startup repair; no Forecast semantic changes.
- **Research — ACTIVE / foundational model-authority audit:** symmetric retrospective Forecast comparison with no incumbent privilege; joint injury practical-materiality reinterpretation included; determine whether a bounded new-family challenge is needed.
- **Y4-Y8 Research — PRESERVED:** exploratory work may continue, but no new production promotion until the foundational Forecast authority audit establishes the base model-selection standard.
- **Market / general Performance — HOLD** behind product availability acceptance.


## 2026-09-27 — Forecast audit completeness
Research remains ACTIVE. Before closeout, it must directly include the exact deployed Y2/Y3 package `forecast-vnext-a2-burr-20260922` as an audit candidate. Historical A2/D0/D1 evidence may inform interpretation but cannot substitute for direct evaluation of the deployed package. Production remains unchanged.


## 2026-09-27 15:37 ET — Physical beta priority shift
- **Implementation / Performance — ACTIVE, immediate product critical path:** ordinary iPhone/Safari use is functional enough to resume testing, but live read latency is unacceptable under concurrent background work (`/api/home` 24.2s, `/api/my-team` 25.6s, `/api/product-context` 39.4s). Make persisted/read-only product surfaces responsive while heavy intelligence work runs.
- **League Atlas interaction corrective — ACTIVE within same workstream:** team-position drawer is z-index 1003 while Player Intelligence root is z-index 1000, causing PI opened from a player in the drawer to render behind it until the drawer closes. Fix the overlay-stack contract and validate heat-map → position drawer → player → PI on mobile.
- **Runtime RSS reclaim:** continue in parallel as engineering headroom work; a narrow self-imposed budget miss alone no longer blocks ordinary beta testing absent real availability failure.
- **Research:** remains independent; Y4-Y8 symmetric authority work continues under its existing directive.


## 2026-09-27 — Forecast/Value next step after Management decision
- **Research — ACTIVE:** define and validate the Long-Term Intrinsic consumption contract from the continuous governed Y4-Y7 Forecast trajectory. No additional Forecast-family search is authorized.
- **Forecast production:** Y1 current authority and deployed coherent Y2/Y3 vNext remain unchanged for now; model-authority disagreement must be preserved as uncertainty in the next contract.
- **Long-horizon Forecast:** Y4-Y7 continuous trajectory is the accepted target; H5 may be the clearest headline horizon but must not be shipped as a Y5-only discontinuity. Y8 remains coarse.
- **Value:** maintain separate Current Intrinsic (Y1-Y3) and future Long-Term Intrinsic (Y4-Y7). Do not blend them into a single master value.
- **Implementation:** no Long-Term Intrinsic production implementation until Research freezes the consumer/economic contract. Existing latency/interaction work remains independent.


## 2026-09-27 17:18 ET — Implementation after PR #277
- **Implementation remains ACTIVE.** PR #277 is live and partially successful: Atlas→PI overlay is corrected and warm Home/My Team reads improved to low-single-digit seconds in some windows.
- **Not accepted:** heavy-work overlap still drives 26–43s foreground reads; one hosted run exceeded the internal RSS target (~473 MB max observed) and another failed because cold PI history lacked Y2/Y3 during initial reconciliation.
- **Next corrective:** preserve #277, eliminate heavy-work read starvation, repair cold PI future-Forecast continuity, and reduce transient memory risk on current main. No broad architecture rewrite.


## 2026-09-27 18:02 ET — PR #278 live; Long-Term Intrinsic Research complete
- **Implementation — ACTIVE / hosted acceptance running:** PR #278 merged as `07d61a82bb17bc75bbec317b513be8406a8a49cf` and is live on Render as `dep-dasp2q8jo6nc73cp9v30`. It preserves #277, adds hosted-only cooperative CPU yielding in Forecast loops, durable same-league PI Y2/Y3 continuity across cold wakes, explicit cache reclamation, and allocator trimming between heavy phases. Startup restored full FSFFL readiness with ~296 MB peak RSS and began the full State-first acceptance journey. No post-deploy error has been observed yet; terminal hosted acceptance is still pending.
- **Research — MANAGEMENT GATE: LONG-TERM INTRINSIC CONSUMPTION CONTRACT.** Research froze and validated `LT_RAW=(phi4+phi5+phi6+phi7)/4`, a separate annual-equivalent Y4-Y7 Shapley lens. It preserves set-valued Forecast authority, separate within-model vs model-authority uncertainty, excludes Y8 cardinally, and uses a separate rank-calibrated 0-10,000 display index. Historical replay supports the continuous Y4-Y7 consumer over Y5-only/Y7-only shortcuts. No production change yet.


## 2026-09-27 — Long-Term Intrinsic shadow implementation authorized
- **Implementation Track A — runtime corrective:** PR #278 remains in hosted acceptance. Latest evidence fixes the prior cold PI continuity failure: cold PI now returns Forecast years [1,2,3], with initial full reconciliation around ~384 MB max observed and no application errors in the checked window.
- **Implementation Track B — Long-Term Intrinsic shadow:** AUTHORIZED to begin on a separate branch from the frozen Research contract. Build continuous Y4-Y7 Forecast authority materialization + separate Long-Term Intrinsic Value consumer + persistence/API shadow. No Market/Team Utility/Decision authority and no Current Intrinsic change.
- **Merge/deploy guard:** Track B must not be merged/deployed onto live main until Track A (#278) completes hosted acceptance cleanly.


## 2026-09-27 — Sequencing update
- **Implementation runtime corrective — ACTIVE / sole implementation priority.**
- **Long-Term Intrinsic shadow — AUTHORIZED BUT PAUSED.** Do not start until regular Implementation reaches a clean terminal state and Management reopens the shadow phase.


## 2026-09-27 18:16 ET — #278 not yet accepted
- **Implementation runtime corrective remains ACTIVE / sole implementation priority.**
- #278 fixed cold PI continuity and restored full presentation correctly, but hosted acceptance failed the internal RSS target at ~450.4 MB peak and still exposed a ~64.9s Market workspace build under the heavy journey.
- Continue narrowly on remaining memory residency/contention/Market-build latency. Preserve #278 architecture and semantics.
- **Long-Term Intrinsic shadow remains PAUSED.**


## 2026-09-27 — Remaining runtime corrective narrowed to Market execution boundary
- **Implementation — ACTIVE / sole priority:** preserve #278 and move full Market Search/Decision off foreground read requests.
- Persisted/current Market shell must remain immediately usable; explicit structural search may start separately; bilateral Decision enrichment becomes progressive; deep Simulation remains explicit drill-down.
- Treat the ~429.5 MB RSS target as engineering headroom, not a standalone blocker absent real availability failure. Continue hard-limit monitoring.
- PI history should serve compatible persisted evidence first and reconcile in background.
- **Long-Term Intrinsic remains PAUSED** until this runtime track reaches terminal acceptance.


## 2026-09-27 19:01 ET — repeated #278 rerun confirms next action
- A fresh-instance rerun reproduced ~63.6-64.0s Market builds under the heavy sequence and ~40.7s active-reconciliation PI history.
- Cold PI/history and light Market reads remain healthy; therefore the defect is workload-path specific, not universal app slowness.
- RSS reached ~469.6 MB but remained below the hard Render limit.
- **Do not rerun unchanged #278 again as the next action. Implement the nonblocking Market execution boundary already authorized by Management.**


## 2026-09-27 — Research parked; Implementation remains sole active priority
- **Research — DONE / PARKED.** The Forecast authority program, Y4-Y8 symmetric study, and Long-Term Intrinsic consumption contract have reached the intended durable state. No additional Research work is required before implementation.
- **Implementation — ACTIVE / sole product-critical path.** Finish the nonblocking Market/runtime corrective, merge/deploy it, and pass hosted acceptance.
- After runtime acceptance, Management may reopen the already-defined Long-Term Intrinsic shadow implementation directly from the frozen Research handoff; do not send it back through another Research cycle without new evidence.


## 2026-09-27 late evening — PR #279 green and ready for merge/deploy acceptance
- **Implementation — ACTIVE / sole product-critical path.**
- PR #279 `Market: make foreground discovery nonblocking` is OPEN, non-draft, GitHub-mergeable, head `00503a43aa657a9bf1ca93c488f38561813e206f`.
- All current head workflows are green, including CI plus Home, Franchise, League Atlas, live Forecast corrective trace, Intrinsic diagnostics, and focused corrective regression.
- The stale hosted acceptance hard-failure on the ~429.5 MB soft RSS target is corrected on the PR: soft-budget misses are logged diagnostically; the hard Render limit remains terminal.
- No #279 code is live yet. Render still serves PR #278 merge `07d61a82bb17bc75bbec317b513be8406a8a49cf`.
- Next action: merge #279, deploy the exact merge SHA, then run the full hosted acceptance journey. Do not expand product scope before that evidence.
- **Research remains DONE / PARKED. Long-Term Intrinsic remains paused until runtime acceptance.**


## 2026-09-27 22:23 ET — #279 deployment blocked at process startup
- **Implementation remains sole active priority.**
- PR #279 is merged as `916f87e0661475d9ae5c0458c788ba356e802262`; build succeeded.
- Render deploy `dep-dassq1rbc2fs73a74b10` is stuck `update_in_progress`.
- New instance `qvhhw` launches the uvicorn command but never reaches Uvicorn/app startup logs or request handling; hosted acceptance has not started.
- Next action is narrow startup/import/initialization diagnosis on the exact merge SHA, not further Market changes.
- Research remains DONE/PARKED; Long-Term Intrinsic remains paused.


## 2026-09-28 — Runtime corrective validated for primary FSFFL; Hodor source-health blocker remains
- **Primary FSFFL runtime:** materially healthy on live PR #280. Cold PI ~0.5s, overlapping PI ~2.9s, Market read ~0.3s / cache hit ~0s, post-sync max RSS ~412.5 MB, continuity preserved.
- **Hosted acceptance failure:** isolated to `hodor_switch`, where fresh live Forecast acquisition failed because only one independent source (Razzball) was healthy. This is not evidence that the nonblocking Market/runtime correction failed.
- **Implementation:** do not broaden or rewrite the runtime path. Track only the cross-league/Hodor Forecast continuity issue.
- **Physical testing:** Management may resume a bounded primary-FSFFL smoke test now; cross-league switching remains unaccepted.
- **Research:** remains DONE / PARKED. Long-Term Intrinsic remains paused until Management decides runtime is sufficiently closed.


## 2026-09-28 — Hodor replay continuity is the sole remaining runtime gate
- **Implementation — ACTIVE / sole product-critical path.** Do not classify the current Hodor failure as resolved external provider downtime. Diagnose and correct why governed persisted Hodor raw Forecast evidence did not carry the league switch before fresh provider acquisition.
- Separate raw Forecast replay compatibility from downstream State/scoring compatibility; rebuild only layers whose inputs changed.
- Preserve PR #244/#245 truthful partial authority and PR #280 primary-FSFFL latency/memory gains. Do not weaken the two-source gate.
- Required terminal proof is the hosted FSFFL → Hodor → FSFFL journey, including provider-outage-compatible replay, exact rejection telemetry, persistence/restart continuity, no cross-league contamination, and hard-limit safety.
- Canonical directive: `docs/operations/directives/20260928_HODOR_FORECAST_REPLAY_CONTINUITY.md`.
- **Research remains DONE/PARKED; Long-Term Intrinsic remains PAUSED.**


## 2026-09-28 — Post-merge P1 blocks #281 deployment
- **Implementation — ACTIVE / sole priority.** PR #281 is merged but is not deployable/acceptable as-is because post-merge review found a P1 same-State replay hole: stale downstream supplement compatibility can cause early return before raw Forecast replay, forcing unnecessary live provider acquisition.
- Fix the narrow replay branch and add deterministic regression coverage first; then merge, deploy the corrected SHA, and run hosted FSFFL → Hodor → FSFFL acceptance.
- Preserve all existing source-health/two-source rules and PR #280 performance gains. Long-Term Intrinsic remains paused.


## 2026-09-28 — PR #282 follow-up P1 is the sole runtime blocker
- **Implementation — ACTIVE / sole product-critical path.** PR #282 fixed same-State raw Forecast replay but is not deployable as-is because replay can leave stale same-State Simulation durable and later restart can combine it with rebuilt Forecast.
- Fix Forecast↔Simulation persistence compatibility (or explicitly invalidate dependent Simulation on replay), add interruption/restart regression coverage, then merge, deploy corrected SHA, and complete hosted FSFFL → Hodor → FSFFL acceptance.
- Preserve source-health/two-source rules and all prior latency/memory gains. Long-Term Intrinsic remains paused.


## 2026-09-28 — In-season ROS sequencing
- **Implementation:** runtime/Hodor acceptance remains the sole product-critical path. After terminal acceptance, in-season Forecast integration (Actual YTD + governed third-party ROS) is authorized as the next season-critical production feature and may precede Long-Term Intrinsic deployment.
- **Data/Research:** begin bounded PIT capture of governed ROS raw-stat projections and contemporaneous status/actuals immediately; this must not modify production authority or interfere with runtime work.
- **Native ROS model:** shadow Research only until comparative PIT evidence earns promotion.
- Directive: `docs/operations/directives/20260928_IN_SEASON_ROS_FORECAST_POLICY.md`.


## 2026-09-28 — Current live blocker moved to PI history during active reconciliation
- **Implementation — ACTIVE / sole product-critical path.** #283 merge `047b3386e81bb843cc8b71408d05b0b81f38b792` is deployed and live.
- Hosted acceptance fails at `pi_history_during_active_reconciliation` because PI history times out while reconciliation is active.
- Diagnose whether this is real foreground starvation/contention versus a stale acceptance threshold; correct the narrow cause without undoing #280/#283 continuity and persistence fixes.
- After correction, rerun the complete hosted acceptance journey. Research and Long-Term Intrinsic remain paused.


## 2026-09-28 — Runtime root cause: atomic intelligence publication
- **Implementation — ACTIVE / sole product-critical path.** Physical live testing proves same-State reconciliation leaks intermediate Forecast/Simulation/Value/Intrinsic states to users.
- Replace incremental live publication with a working-generation -> atomic published-generation contract. Same-State refresh must preserve prior compatible published surfaces until the replacement is terminal and durably promoted.
- Global `Intelligence current` status must reflect the published cross-surface capability generation, not only job/stage readiness.
- The PI-history overlap timeout is now treated as one manifestation/acceptance symptom of this publication/read-isolation problem, not as sufficient scope by itself.
- Directive: `docs/operations/directives/20260928_ATOMIC_INTELLIGENCE_PUBLICATION.md`.
- Research, ROS production work, and Long-Term Intrinsic remain paused until runtime stabilization closes.


## 2026-09-28 — Work red-team leaves one P2 before deploy
- **Implementation — ACTIVE / sole product-critical path.** Independent read-only audit of merged #284 found no new atomic-publication defect except one managed-team commit race.
- A team switch can occur after durable publication writes begin but before the in-memory finalization recheck, potentially advancing restart authority for the old team and then aborting runtime publication.
- Fix by serializing/guarding team selection across publication commit or validating/rebasing before durable commit; add deterministic race + restart regression.
- Keep #284 HOLD until this P2 is fixed, then deploy corrected SHA and run full hosted + physical acceptance.


## 2026-09-28 — Runtime code corrected through #287; hosted proof needs repair
- **Implementation — ACTIVE / sole product-critical path.** #285 fixed the managed-team publication race; #287 fixed cold exact-State restoration of team + publication generation identity.
- Current main: `2c0c6d0aefc0cc21913e6090b70f706c29e0b430`.
- Remaining gate is acceptance correctness: #286's managed-team hosted test may switch after reconciliation already completes and asserts copied context rather than actual Franchise surface team identity.
- Repair that narrow acceptance interleaving/assertion, then deploy corrected SHA and rerun the full hosted atomic-publication journey. No model or product-scope expansion.


## 2026-09-28 — After runtime closure: foundation program queued
- Runtime/atomic publication remains the only active product-critical path.
- After terminal hosted + physical acceptance, begin the post-stabilization foundation sequence in `docs/operations/directives/20260928_POST_STABILIZATION_FOUNDATION_SEQUENCE.md`.
- First production priority after closure: in-season Actual YTD + governed third-party ROS Forecast, while preserving PIT ROS capture.
- Then: Long-Term Intrinsic -> PIT market/history evidence -> League Market / Owner Intelligence -> Trade Decision -> Market/Search optimization -> Intelligence surface exploitation.


## 2026-09-28 — Foundation sequence expanded: Simulation + origin-aware picks
After runtime closure and in-season ROS Forecast, the next foundational program now includes Simulation 2.0 and origin-aware draft-pick valuation before downstream Market/Trade exploitation. Simulation owns each future pick's team-of-origin slot distribution under actual league draft-order rules; Value converts that distribution through governed pick-coordinate/draft-class evidence. Generic year/round values remain fallback priors only. Long-Term Intrinsic, PIT market evidence, League Market/Owner Intelligence, Trade Decision and Search follow downstream.


## 2026-09-28 — Simulation 2.0 is a near-term foundation
After runtime stabilization and in-season Forecast, execute `docs/operations/directives/20260928_SIMULATION_2_0_PROGRAM.md` before origin-aware pick Value. Bring forward/re-derive legacy weekly distributions, legal weekly lineups, byes, availability/bench substitution, real schedule/division/playoff rules, finish/playoff/title outputs, deterministic replay and Multiverse examples. Rebuild around compiled reusable state, vectorized/batched 50k Monte Carlo, cached lineups, common random worlds, selective scenario recomputation, persisted exact reuse and progressive non-authoritative scenario batches. Canonical 50,000-run authority remains until convergence evidence earns any change.


## 2026-09-28 — Stabilization narrowed to final publication edges
- **Implementation — ACTIVE / sole product-critical path.** #289 merged the deterministic managed-team acceptance correction.
- Remaining P2 A: team selection can still invalidate a working generation during checkpoint/presentation promotion before the final publication critical section, yielding generic FAILED rather than serialized completion/interruption.
- Remaining P2 B/C in open #288: served publication generation must be team-matched and must satisfy the same visible-snapshot validity predicate before product/readiness diagnostics expose it.
- Fix these narrow publication/diagnostic edges, then merge/deploy and rerun full hosted acceptance. No model/research scope expansion.


## 2026-09-28 — One remaining P1 after #290 merge
- **Implementation — ACTIVE / sole product-critical path.** #290 merged and full CI is green, but post-merge review found a real cross-user deadlock risk.
- Root cause: store-global publication and restore locks can be acquired in opposite order by publication/checkpoint and another user's cold restore.
- Fix with per-user publication sequencing or a provably consistent lock order; add deterministic concurrent regression.
- Do not declare runtime stabilization complete until corrected SHA is merged/deployed, hosted acceptance passes, and physical Safari smoke passes.


## 2026-09-28 — Stabilization closure protocol replaces one-fix-at-a-time loop
- **Implementation — ACTIVE / sole product-critical path.** Current known P1 remains the cross-user publication/restore lock inversion after #290.
- Do not handle it as another isolated patch/deploy. Close the entire publication/persistence/restore/identity concurrency class under `20260928_STABILIZATION_CLOSURE_PROTOCOL.md`.
- Required before next production acceptance claim: whole-class red-team, deterministic single-user/two-user concurrency matrix, bounded repeated stress, full CI, then one merge/deploy/hosted acceptance sequence.
- Bounded runtime lifecycle/lock refactor is authorized if needed. Forecast/Simulation/Value/Intrinsic semantics remain frozen.


## 2026-09-28 — Product-critical active workstream
**Implementation: first-load regression recovery** is the sole product-critical workstream. Controlling directive: `docs/operations/directives/20260928_FIRST_LOAD_REGRESSION_RECOVERY.md`.

Goal: restore the previously reliable Sleeper connect/team-selection/initial-intelligence journey while preserving #291 lifecycle safety. No Simulation 2.0, Long-Term Intrinsic, Market expansion or new Research work until hosted + physical first-load acceptance closes.


## 2026-09-28 — Parallel read-only architecture audit
A separate Work review is authorized under `docs/operations/directives/20260928_RUNTIME_ARCHITECTURE_RECONCILIATION_AUDIT.md`.

This is read-only and may run in parallel with Implementation. It must not modify code/docs, open PRs, deploy, or alter persistence. Its purpose is to reconcile the current runtime/application design against the founding FSFFL NEXT architecture and identify the smallest architectural simplification needed to prevent recurrence without discarding valid #261/#284-#291 safety properties.


## 2026-09-29 — FUMBLES_LOST Research closed; Implementation resumes
- **Implementation — ACTIVE / sole product-critical path.**
- PR #297 Research authority is merged as `9b3e07c14583918c08fae893d5087f0ed013826c`; no bounded P1/P2 remains.
- Implement only the frozen FUMBLES_LOST Week-0/1 omission, Week-2→17 rolling, corrected `NON_MATERIAL_PARTIAL`, Week-18 no-projection, and annual-freeze contracts from `artifacts/research/fumbles_lost_rolling_authority_20260929/IMPLEMENTATION_HANDOFF.md`.
- Preserve Y2/Y3, Y4-Y7, K/DST, Intrinsic mathematics, and #294/#295/#296 runtime architecture.
- After focused/full CI and bounded review, deploy on the existing runtime lineage and resume the complete hosted lifecycle acceptance through restart/restored-session.
- **Research — DONE / PARKED** for this directive. Do not reopen without new evidence.
- Physical Safari remains HOLD until terminal hosted PASS.


## 2026-09-29 — PR #298 validation strategy
- **Implementation — ACTIVE / sole product-critical path.**
- PR #298 has the bounded FUMBLES_LOST implementation written, but validation is mixed and it is not merge-ready.
- Reconcile current failures by root cause, then run a bounded whole-contract P1/P2 red-team across the complete FUMBLES_LOST lifecycle and adjacent authority/restart/invalidation behavior. Do not patch tests one-by-one without first identifying the governing failure class.
- Preserve #294/#295/#296 runtime architecture and all frozen Forecast/Intrinsic boundaries.
- Merge/deploy only after focused regressions, full CI and bounded review are green; then resume full hosted lifecycle acceptance through restart/restored-session.
- Physical Safari remains HOLD until hosted terminal PASS.


## 2026-09-29 — PR #298 immediate execution
- **Implementation — ACTIVE / sole product-critical path.**
- Fix the annual-rollover validation-class defect so incomplete fallback eligibility fails closed with the governed validation error instead of `KeyError`.
- Reconcile the live-provider completed-Week-2 versus canonical-State Week-3 mismatch at the authority/harness boundary; Atlas itself currently passes all focused Atlas/PI tests and should not be changed without evidence of an Atlas regression.
- Then rerun full CI + affected focused workflows and finish the whole-contract P1/P2 review before merge.
- Continue directly to merge/deploy/hosted lifecycle acceptance only if those gates are clean. Preserve #294/#295/#296 and all frozen model boundaries.


## 2026-09-29 — PR #298 final bounded review gates
- **Implementation — ACTIVE / sole product-critical path.**
- All current CI/focused workflows are green on `bccb3f547d0f9d4df68c0c0faa6f258c66967346`.
- Two P2s still block merge: require governed annual rolling-adequacy proof before promotion, and preserve a finite/positive/non-decreasing cold-start uncertainty floor across rollover.
- Fix only those annual validation-class defects, add deterministic regressions, rerun full CI/affected focused checks, and repeat bounded exact-head P1/P2 review.
- Preserve #294/#295/#296 and all frozen model boundaries. No Research reopen or broader scope.


## 2026-09-29 — #298 merged; hosted acceptance active
- **Implementation — ACTIVE / sole product-critical path.**
- PR #298 merged as `5d8daf7a84237baa9ad148061bc1b9bd23405eac`; all required pre-merge CI/focused checks passed and final bounded exact-head P1/P2 review is clean.
- Do not continue annual-rollover review unless new evidence appears.
- Deploy the merged #298 lineage and execute the full hosted lifecycle acceptance: clean-first-run / managed-team selection / FSFFL -> Hodor -> FSFFL / same-State / restart / restored-session.
- Preserve #294/#295/#296 runtime architecture and all frozen model boundaries.
- Physical Safari remains HOLD until hosted terminal PASS.


## 2026-09-29 — Hosted acceptance blocked only by PR #301 harness P1
- **Implementation — ACTIVE / sole product-critical path.**
- #299 and #300 are merged hosted-acceptance harness corrections; no product/model/runtime authority changed.
- PR #301 is open with all ordinary CI/focused workflows green, but bounded review found a P1 in the acceptance probe: `TeamState.roster` entries are objects and must be filtered by their `player_id`, not compared directly to canonical id strings.
- Correct that harness bug, regress it deterministically, rerun affected checks, then continue the full hosted lifecycle acceptance immediately.
- Preserve #294/#295/#296, #298 FUMBLES_LOST authority, PI readiness semantics, and all frozen model boundaries.


## 2026-09-29 — Hosted hard-memory blocker root-cause phase
- **Implementation — ACTIVE / sole product-critical path.**
- #301 is merged and the hosted journey now reaches coherent FSFFL and Hodor publication before stopping on the hard-memory gate.
- Do not loosen the ~512 MB gate. Isolate whether the observed peak is production runtime retention, a bounded transient switch allocation, allocator high-water, or acceptance-harness accumulation.
- Add phase-level memory/lifecycle evidence around clean FSFFL -> Hodor, verify release of prior league/runtime/artifact state, and repeat the switch to distinguish transient peak from accumulating leak.
- Fix only the owning layer, add deterministic/resource regression, redeploy, and resume FSFFL return / same-State / restart / restored-session acceptance.
- Preserve #294/#295/#296, #298, PI readiness semantics, and frozen model boundaries.


## 2026-09-29 — #302 post-merge corrective completion
- **Implementation — ACTIVE / sole product-critical path.**
- Preserve #302's valid root-cause diagnosis and State-transition reclaim boundary, but do not treat it as accepted yet.
- Close three post-merge findings in one bounded pass: clear `MarketDecisionEnrichmentCoordinator` user records at the same transition boundary; apply reclaim to the supported synchronous Sleeper connect path as well as background connect; redact/hash/omit identity-bearing keys from retained public phase telemetry.
- Add deterministic A -> B -> A coverage with completed Market enrichment and both connect paths, plus public-health telemetry privacy regression.
- Then rerun full CI + bounded resource/lifecycle review, redeploy, and resume hosted FSFFL return / same-State / restart / restored-session acceptance under the unchanged hard memory gate.
- Preserve #294/#295/#296, #298, PI readiness semantics, and frozen model boundaries.


## 2026-09-29 — Resource boundary closure directive active
- **Implementation — ACTIVE / sole product-critical path.**
- Controlling directive: `docs/operations/directives/20260929_RESOURCE_BOUNDARY_CLOSURE.md`.
- Do not create another narrow patch for only the three visible #302 findings.
- Close the entire cross-league resource-ownership boundary: complete holder inventory, complete transition-path inventory, single shared cleanup/reclaim boundary, deterministic closure matrix, full CI, whole-class P1/P2 review, then deploy and resume hosted lifecycle.
- Preserve the unchanged memory gate, #294/#295/#296, #298, PI readiness semantics, and all frozen model boundaries.


## 2026-09-29 — PR #303 final closure gate
- **Implementation — ACTIVE / sole product-critical path.**
- Exact head `12b7d69baaeedc4952ab93fe07ba396c44b2681d`; focused workflows green; full CI is 1 failure / 1,865 passes.
- Reconcile the remaining stale Behavioral-refresh regression to the resource-boundary invariant, rerun full CI + deterministic closure matrix, then perform a fresh exact-head whole-class P1/P2 review.
- Do not merge until CI and that review are clean. If clean, merge/deploy and resume full hosted lifecycle acceptance immediately.
- No further architecture broadening absent new evidence; preserve the hard-memory gate and all frozen boundaries.


## 2026-09-29 — Resource test realism clarification
- Repeated A -> B -> A is only a bounded leak-detection probe, not a product requirement for rapid league switching.
- Hosted acceptance should prove one realistic FSFFL -> Hodor -> FSFFL journey with settle points, stable post-switch memory baseline, and prior-scope release.
- Use at most one additional bounded repetition only if needed to distinguish monotonic retention from transient/allocator peak behavior.
- If ownership is clean and baseline is stable but legitimate heavy compute still exceeds the unchanged memory gate, escalate to capacity/compute-staging instead of continuing leak hunting.


## 2026-09-29 — Public-scale principle recorded; no #303 scope expansion
- Public-scale architecture directive is now authoritative: the current free/small Render footprint is a stress constraint, not the design target.
- Current PR #303 remains narrowly focused on resource ownership/lifecycle correctness and the existing private-beta gate.
- Do not introduce a premature microservice/distributed-systems rewrite into #303.
- After hosted + physical beta acceptance, Management will gate a dedicated production-readiness/scaling workstream before any public launch.


## 2026-09-29 — Free-Render usability is the immediate acceptance target
- **Implementation — ACTIVE / sole product-critical path.**
- Public-scale architecture is future-facing; current acceptance is reliable single-user/private-beta use on the existing free Render service.
- Finish #303 for lifecycle/resource correctness, then prove one realistic full hosted journey without hard-memory failure and with acceptable foreground responsiveness.
- Do not add synthetic rapid-switch or commercial-scale requirements to this gate.
- If normal beta use still cannot fit after ownership is clean, escalate to the smallest practical beta-specific capacity/compute-staging decision instead of continuing open-ended leak hunting.


## 2026-09-29 — Efficient beta / scalable structure rule
- Optimize current free-Render usage aggressively where waste is avoidable.
- Do not treat free-tier CPU/memory/throughput as the future production-capacity target.
- Current acceptance is reliable normal private-beta use; once that is restored, return to capability development.
- Future public scale should be solved primarily by added infrastructure capacity on top of the same clean authority/lifecycle structure.


## 2026-09-29 — PR #303 exact-head P1 closure
- **Implementation — ACTIVE / sole product-critical path.**
- Exact head `1944aca9cdf527d0600fc5f6107240446baf060c`: CI/focused checks GREEN; fresh whole-class review found three in-scope P1s.
- Close the boundary atomically: serialize same-user activation+cleanup+ownership revalidation; prevent/re-clear prior-published Market repopulation before replacement publication; epoch/ownership-guard Intrinsic restore attachment and analogous async result attachment.
- Add deterministic race regressions for those three cases.
- Then rerun full CI + closure matrix + fresh exact-head whole-class P1/P2 review.
- If clean, merge/deploy and immediately resume the realistic free-Render hosted journey. No broader architecture work.


## 2026-09-29 — PR #303 clean; merge/deploy/hosted acceptance next
- **Implementation — ACTIVE / sole product-critical path.**
- Exact head `38d77fc7ce700dba9c0a5866ffc20c0a0ac6272b`: 1,874 tests GREEN, all focused/closure/live lanes GREEN, fresh exact-head whole-class P1/P2 review CLEAN.
- Pre-merge resource-boundary layer is accepted.
- Merge #303 now, deploy the exact merged lineage, and run the realistic free-Render FSFFL -> Hodor -> FSFFL / settle / restart / restored-session journey under the unchanged memory gate.
- No rapid-switch stress and no new architecture work unless hosted evidence exposes a concrete defect.
- If hosted normal-use passes, move immediately to physical Safari acceptance and then back to capability development.


## 2026-09-29 — Bounded free-Render first-load staging corrective
- **Implementation — ACTIVE / sole product-critical path.**
- #303 is merged/live and its resource-ownership class is accepted.
- Hosted normal-use reached coherent FSFFL publication, then failed only because lifetime peak RSS hit 544,358,400 bytes versus 536,870,900-byte gate; current RSS had already fallen to ~342.7 MB and no monotonic retention was observed.
- Perform one bounded beta-specific staging pass: use existing phase telemetry to prevent avoidable overlap among memory-intensive first-load phases while preserving all model outputs/semantics and foreground responsiveness.
- No leak hunt, no model-fidelity reduction, no architecture broadening, no rapid-switch stress.
- After CI/focused validation, deploy and rerun the realistic hosted lifecycle journey. If still over gate with clean bounded ownership, return to Management for capacity decision rather than further micro-optimization.


## 2026-09-29 — #304 merged; hosted acceptance pending
- **Implementation — ACTIVE / sole product-critical path.**
- PR #304 merged as `6a531d3d27fa2d63c459b1888e162b5086a36a38`; CI/focused/live validation is green.
- No durable post-merge hosted result is recorded yet.
- Deploy exact #304 lineage and run the realistic free-Render lifecycle journey now. Record peak/current memory and foreground usability.
- If PASS, move directly to Safari. If still over gate with clean ownership/staging, stop and return to Management for capacity decision.


## 2026-09-29 — Realistic journey cleared; final restore rerun pending
- **Implementation — ACTIVE / sole product-critical path.**
- #305 merged as `d126ef3b952d2f49e3a95ac484194ac5ccf59dd5`; realistic FSFFL -> Hodor -> FSFFL journey advanced through the unchanged hard-memory gate to the restart step.
- Exact restart restored FSFFL State, managed team, publication generation, Forecast, Simulation and Value correctly.
- The remaining failure was harness-only: restore mode required Intrinsic before the normal staged PI/product path rehydrated it.
- #306 merged as `c5e6e23596a0fd2489f82c309ffdc241a5e06e80` to align that restore assertion with actual staged product behavior; no runtime/model/product-route change.
- Final action: deploy exact #306 lineage and rerun staged restore acceptance. If PASS, move immediately to physical Safari. No broader corrective work unless new runtime evidence appears.


## 2026-09-29 — Physical Safari Connect blocker
- **Implementation — ACTIVE / sole product-critical path.**
- Hosted lifecycle acceptance through #306 remains accepted, but physical iPhone/Safari validation fails at the first user action: the league will not connect.
- Reopen only the browser/manual Connect path. Reproduce the live UI flow, trace tap/prompt -> `/api/connect/sleeper/background` -> job polling -> product-context handoff, and inspect Safari asset freshness/interception behavior.
- Fix the smallest concrete defect, add a deterministic browser-path regression, deploy, and return directly to physical Safari retest.
- Do not reopen model/resource architecture or replace this with another server-only acceptance run.
## 2026-09-29 — #307 merged; physical Safari retest is the sole remaining gate
- **Implementation — ACTIVE / sole product-critical path.**
- PR #307 merged as `326a79ce8dfcd37d1e5f30d3dd0f11762e3de71a` with exact-head full CI and focused lanes green.
- Manual Connect is now self-healing: an explicit tap always uses the idempotent background handoff and re-applies canonical context instead of rejecting a same-league server/browser identity.
- The completed startup acceptance harness has been disabled on Render so the free instance is not competing with server-only acceptance work during physical testing.
- Deploy current main, then run the physical iPhone/Safari Connect path through visible league/team selection. That physical result controls closure.
- Do not reopen Forecast, Simulation, Value, Intrinsic, resource-boundary architecture, or #306 hosted restore acceptance absent new contradictory evidence.


## 2026-09-30 — Physical Safari exposed refresh lifecycle and restart-recovery defect
- **Implementation — ACTIVE / sole product-critical path.** New directive:
  `docs/operations/directives/20260930_PHYSICAL_REFRESH_MEMORY_ROOT_CAUSE.md`.
- Physical Safari submitted `/api/intelligence/jobs` at about 04:11:47Z while
  automatic Sleeper background refresh was still being polled. Render RSS rose
  from 344–349 MB to 522.4 MB / 536.9 MB, CPU saturated and the process
  restarted. Canonical State survived; Forecast, Simulation and Value did not;
  runtime reported `forecast=False simulation=False value=False complete=False`.
- Confirmed code defect: Hosted Connect and manual Intelligence had separate
  State-load owners during the automatic-refresh handoff window; production
  State load also bypassed HeavyWorkCoordinator. Its claims serialized declared
  model phases and reported RSS, but did not reserve phase memory or constrain
  one active phase. Exact object-level attribution cannot be recovered from
  coarse incident telemetry; boundary RSS instrumentation is added.
- Market value-lens first-load remained staged and lightweight; foreground
  product-context/home latency is consistent with CPU starvation, with no
  evidence of expensive reconstruction. PR #306 measured warm durable restore
  (~308.5 MB), not a cold State sync plus live Forecast/Simulation/Value build
  with concurrent browser reads. #307 fixed Connect presentation only.
- Restart converted in-progress work to `INTERRUPTED/server_restart`; missing
  exact-State layers were not automatically rebuilt, permitting persistent
  2/7 readiness. Browser polling now resumes that work from durable exact State
  with atomic publication; direct State sync checkpoints the job's new State ID
  so recovery can verify the intended State.
- Corrective implementation: coalesce manual refresh into active automatic
  Sleeper refresh, serialize State materialization in the heavy-work lane,
  report lifecycle RSS boundaries, resume interrupted exact-State builds, and
  add deterministic Safari-like concurrent-read/value-lens regression.
- Keep hard Render memory limit and all Forecast/Simulation/Value semantics
  unchanged. PR #308 merged as `dbbab4a67a8366de9e90fad094236e1f779ebda5`;
  full CI and triggered focused/live lanes passed (the external Atlas authority
  audit passed on retry after a connection reset). Render deploy
  `dep-dau9kng93c1s73datfl0` is live and application startup completed cleanly.
- **Current status: READY FOR PHYSICAL IPHONE/SAFARI ACCEPTANCE.** The next real
  fresh build must include concurrent foreground reads and Market/value-lens
  polling so the new RSS boundary logs capture per-phase memory and usability.
  The old incident has no object-level allocation profile, and no fresh build
  has run on the corrective deploy yet.


## 2026-09-30 — Physical #308 follow-up: propagation/latency blocker
- **Implementation — ACTIVE / sole product-critical path.**
- Physical iPhone/Safari no longer reproduced the catastrophic restart/2-of-7 failure: Home reached current with 50,000-run Simulation, Franchise showed projections/Broad Market, and PI showed Market + Intrinsic.
- Acceptance is still NOT clean because value/readiness state propagated inconsistently: Franchise and Assets & Picks still showed Intrinsic preparing, League Value Map kept loading, and position detail omitted Market/Intrinsic percentiles after PI already had those values.
- Load time was still significant.
- Correlate the run with #308 phase RSS telemetry first. Then fix the narrow publication/readiness/presentation propagation or polling/cache owner and measured latency bottleneck.
- Preserve #308 lifecycle/restart changes and model semantics unless telemetry directly contradicts them.

## 2026-09-30 — Cross-surface propagation corrective
- Live 11:27–11:33Z evidence binds PI, Atlas, and the published surfaces to the same State `810f710608a9d2b1422f3abf2c65f0d413bb65a2537f5db332f140ac3b8299e8` and one publication generation. The inconsistency was stale payload content inside that generation, not a generation mismatch.
- During presentation promotion, the value-lens route treated any active working generation as a reason to stage `loading`, even when the promoted read context already had selected team, Forecast, and completed Intrinsic evidence. Promotion persisted that staged payload; GETs then served it from the exact-generation cache and clients eventually reported unavailable.
- Fix removes the active-generation staging condition. Staging remains while required team/Forecast inputs are absent. Added an end-to-end promotion regression asserting ready Broad Market and Intrinsic rows survive publication and resolve through the published route.
- Repeated published-surface reads now validate the manifest fingerprint once per runtime cache and verify the requested artifact on each read, instead of hashing all seven surfaces per poll. Full validation remains on cold/changed-manifest restore.
- #308 phase telemetry showed RSS 381 MB at Intrinsic reconciliation complete and 387 MB at publication complete; peak 524.7 MB, no restart, Render coarse memory stable near 410 MB. Free-tier headroom remains narrow.
- While 50K Simulation was active (~173s), concurrent Home/My Team calls took ~12–22s and product context ~29–33s; after it completed they fell to ~2.5–6s. Active Simulation owns the measured foreground delay. This corrective does not change simulation or resource-boundary architecture.
- Added Server-Timing to status, Atlas, team views, and value-lens endpoints. Focused regressions and full suite pass (1,888 tests). Deployment and hosted acceptance remain before physical Safari confirmation.


## 2026-09-30 — Market For You zero-result blocker
- **Implementation / Work — ACTIVE, bounded Market acceptance gate.**
- Physical core app is materially usable after #310.
- Live Market discovery is functioning: automatic discovery produced 2 opportunities and a focused target produced 1, but both ended with `for_you=0`.
- Trace the promotion/eligibility/dominance/diversity layer that removes all discovered opportunities. Preserve accepted economic/bilateral screens and zero broad Simulation.
- Fix the smallest concrete defect or make a legitimate zero-result explainable to the user.
- After one physical Market pass, proceed to Simulation modernization.


## 2026-09-30 — Simulation modernization authorized
- **Simulation modernization — ACTIVE / primary capability workstream.**
- Runtime stabilization is no longer the primary program after materially usable post-#310 physical Safari validation.
- Market For You zero-result evidence is preserved but held: do not tune current selection merely to force cards while major future Market inputs are still pending. Interrupt only for a proven mechanical defect that makes defensible opportunities impossible to surface.
- First tranche: profile current fresh/changed-State 50k Simulation, recover compatible vectorization/batching ideas from the predecessor as reference, implement exact-output-preserving kernel efficiency, preserve replay identity/Multiverse capture, and run the convergence study without changing the 50k production contract.
- Work/Implementation may modify code, tests and governed operations docs; open PR(s), run focused/full validation, and deploy only after exact-head review is clean.
- Return to Management before any non-bit-identical RNG/reduction change, model-fidelity change, or Simulation authority change.


## 2026-09-30 — Simulation RNG candidate moves to downstream/hosted validation
- **Simulation modernization — ACTIVE / primary capability workstream.**
- PR #311 has completed its initial 100-seed equivalence study and reached the Management gate.
- Management does **not** require a massive additional seed study solely to prove ±0.001 expected-wins equivalence. Preserve the original result as inconclusive; do not widen the margin or call it a pass.
- Immediate Work ownership: reconcile with current main; validate changed-State downstream Team Utility/Decision/Search/Optimization/Analytics behavior; exact-head CI/review; then controlled reversible private-beta Render measurement if clean.
- Hosted validation must measure full Simulation and refresh wall time, heavy-work wait, RSS/headroom, concurrent foreground responsiveness, publication/readiness, and restart behavior. Batch 500 is the current preferred experimental default.
- No merge to main / production adoption until Management receives that evidence and makes the final adoption decision.
- After the RNG decision, re-profile the entire hosted Simulation path and continue modernization by measured bottleneck order.
- **Current handoff:** PR #311 is open/draft at validation head `689f6c979aca7b0f06cae003a8c1f6ede3aed7a8`, based on current main `3671ba0e6ff29ab750b71b8aaa467be0f56e55a9`; code head `4b87e80ac1ce0881938a3dbe21b229898032e824` has the four bounded restore/cache/Decision corrections. Changed-State fixtures and original study remain unchanged (expected-wins ±0.001 inconclusive). Controlled Render batch-500 validation completed all governed capabilities and publication, but **failed the resource gate** at 576,552,960-byte process high-water RSS against the 536,870,900-byte limit. End-to-end refresh/publication was ~256.7s; measured details and limitations: `docs/operations/evidence/simulation_rng_hosted_validation_20260930.md`. Private beta has been restored to main/#310 at deploy `dep-daunc2nlk1mc73di9b1g` / SHA `3671ba0e6ff29ab750b71b8aaa467be0f56e55a9`; no merge or adoption. Next: Management reviews this failed resource result; before a repeat, identify/bound the transient memory peak under the unchanged limit.

## 2026-09-30 — Simulation modernization: bounded hosted memory corrective
- **Simulation modernization — ACTIVE / primary workstream.**
- PR #311 hosted correctness/downstream behavior is sufficiently encouraging to continue evaluation, but production adoption is withheld because the controlled Render run peaked at 576,552,960 bytes versus the 536,870,900-byte hard limit.
- Immediate Work ownership: instrument and identify the transient peak owner(s); apply only narrow ownership/lifetime/reclaim/duplicate-work corrections that preserve all Forecast/Simulation/Value semantics and 50,000 trials.
- Then rerun the reversible batch-500 hosted journey with true concurrent Home/My Team/Product Context reads, readiness/publication, restart restore, and exact RSS evidence; restore main afterward.
- If the peak cannot be brought safely under the unchanged limit without broader architecture or fidelity changes, stop at Management for a capacity decision.


## 2026-10-01 — PR #311 memory corrective: exact-head gates
- Latest pushed head `b85f62f6d5f3bcbe570cf50ffbb907ee2556f37c` corrects the Python artifact-key P2; CI #4081 passed. Fresh whole-PR review found a second P2 in the production-output digest test: it included patch-specific `rng_runtime_version` while selecting baselines by major.minor and failed for supported new minors.
- The candidate correction normalizes only that identity label to major.minor for the digest, preserves known 3.11/3.12 result baselines, and requires exact same-runtime replay for supported new minors. Focused 6 passed; full local 1,903 passed (one existing Starlette deprecation warning).
- **Do not change Render until the correction is pushed and exact-head CI plus a fresh whole-PR P1/P2 review are clean.** Then immediately perform the authorized reversible batch-500 private-beta test: actual concurrent Home/My Team/Product Context reads; full 50k readiness/publication; exact app RSS/high-water and Render metrics; restart restore; rollback to main. Stop at the unchanged 536,870,900-byte hard limit and return for Management capacity decision if exceeded.
- The failed live provider numerical trace is source-health evidence (only one independent provider), not a code failure for PIT-history streaming. No merge/adoption authorized.
- Follow-up: exact-head CI #4082 on `9d9c3e45fba165768ec67faf6b5dcaf953958756` failed only because the newly normalized Python 3.11 digest baseline had not yet been updated; observed digest was `63660717b6f9d6cd71142fe16dd27c3146a8a24058c2a5c951ea08f32d4a76c2`. Python 3.12 local focused test passes with its normalized baseline. The 3.11 baseline is corrected in the current candidate and focused suite is 6 passed. Push, rerun exact-head CI and fresh review before Render. The live provider numerical trace #279 passed this time, consistent with the earlier #278 failure being transient source health.
- Exact-head review on `70d75285bf97b56eae584392477b267457836ccb` correctly flagged a P1 in the pushed operations State file: an earlier GitHub blob push copied an output-truncation warning/splice because the full file was read through a capped command response. Local source history remained intact. Restore the full local canonical document via bounded chunk transfer and verify remote line count/markers; see `docs/operations/CURRENT_STATE.md` 2026-10-01 recovery note. The test fallback is removed: add reviewed fixed digests for a new Python minor before validating that runtime. Require exact-head CI and fresh review before Render.
- Review of repaired head `6e5e39e760b71e5b806fb966267d97b2d5b69855` found a remaining mismatch between fixed 3.11/3.12 output digests and unbounded package metadata. `pyproject.toml` now declares `requires-python = ">=3.11,<3.13"`; current Render is Python 3.12 and CI/primary validation is 3.11/3.12. No draw or model semantics change. Exact-head CI and fresh whole-PR review must pass before the authorized Render run.
- Latest tested code head `2b198f80836b8ec29205da9627ca68a627765b7f`; latest operations-only head `a5c4c78b3ec1425ef62c93015bbaf66085478d2d`. Full local suite 1,903 passed; code-head review #5923771919 found no major issues; exact CI #4087 and all focused/live workflows passed on a5c4. Exact-head review on a5c4 is pending. Canonical docs were re-pushed via chunked reads and remote blob SHAs match complete local source. Hosted validation is blocked: CUA browser explicitly refused any further read of the product host and prohibited alternate-browser/indirect retries. Render settings remain main/flags off; do not partially deploy or substitute sequential probes. Resume only with platform-approved exact-host concurrent foreground access, then authorized reversible batch-500 journey and rollback.


## 2026-09-30 — Active next step: attribute peak, advance Simulation 2.0 only where causal
- PR #311 remains the active Simulation modernization branch.
- First action is memory attribution, not speculative micro-optimization.
- Explicitly test whether the hosted high-water peak is caused by Forecast → Simulation duplicated representations/lifetimes that the planned Simulation 2.0 compiled-state / compact-array / reusable-buffer / invariant-reuse architecture would eliminate.
- If yes, implement the smallest reusable 2.0 primitive now and measure it.
- If no, fix the independently proven Forecast/player-history owner narrowly.
- Do not rewrite the whole engine or reduce 50k/model fidelity.
- Then exact-head CI/review → reversible batch-500 Render rerun → concurrent foreground/readiness/restart/RSS evidence → rollback → Management gate if still over limit.


## 2026-09-30 — PR #311 memory owner isolated; bounded PIT history correction
- **Simulation modernization — ACTIVE / primary capability workstream; PR #311 experimental only.**
- Hosted high-water attribution is now localized: `forecast.raw_replay_history_discovery` grew process max RSS by 231,202,816 bytes in 83.494s on `dr292`. The phase loaded historical PIT State payloads; Simulation's 50k kernel and prep phases did not raise the earlier 361,902,080-byte process high-water.
- Root cause is the Postgres State-history `recent_at_or_before()` path materializing/decoding up to 32 full JSONB State snapshots and retaining them in a tuple although replay evaluates candidates sequentially. This is independent of Simulation 2.0 representations.
- A narrow fix adds ordered State-ID selection and one-payload-at-a-time validation/iteration; replay discovery consumes the iterator and releases each candidate. It preserves all ordering/PIT/identity/compatibility/fallback semantics. Added deterministic lazy-payload regression.
- Focused persistence/replay: 61 passed. Full suite before last local cleanup: 1,902 passed; rerun full suite on exact pushed PR head. No fresh CI/review or corrective hosted run yet.
- Render has rolled back to current main `878a2a32d5826ff990eed76c4985ae9e8f39bba3`; profiler/acceptance disable-flag deploy `dep-dauouj49v7es73adle10` must be confirmed live.
- **Next executable action:** apply four source/test files onto PR #311 remote head `4408848e970c21093e54804d0cb40f7abb49fd3b`; push to `work/simulation-modernization`; exact-head CI and fresh review; reversible batch-500 hosted journey with genuinely concurrent Home/My Team/Product Context reads, complete 50k readiness/publication and restart restore, exact RSS/high-water evidence; restore main afterward. If the fixed 536,870,900-byte limit still fails, stop at Management gate for capacity.

## 2026-10-01 — PR #311 review correction + hosted handoff
- **Simulation modernization — ACTIVE / PR #311 experimental only.** Fresh whole-PR review on exact head `e5268054f49fd8743bc952a35b528a73d1462b2c` found a P2: newly generated Python artifacts shared a base key across runtime patch versions before publication. The bounded correction qualifies new durable/cache keys by protocol, batch, count, seed, and runtime while retaining read-only compatibility for `legacy-unrecorded` rows; a same-State staged-write/restart regression covers it.
- The corrective live numerical trace failed its source-health minimum with only Razzball available; this is live evidence failure, not the PIT-history corrective. Local full suite is 1,903 passed / one known Starlette warning; focused restore/cache 70 passed and two direct identity checks passed.
- Secure Render email/password login succeeded; `fsffl-next-private-beta` remains on main and profiler/acceptance flags off. Next: exact-head CI + fresh P1/P2 review of the Python runtime-key correction, then reversible batch-500 50k hosted journey with true concurrent Home/My Team/Product Context HTTP reads, full readiness/publication, exact RSS/high-water, restart restore, rollback to main. If RSS >536,870,900 bytes, stop at Management capacity gate. No merge/adoption.

## 2026-10-01 — Immediate executable: external hosted concurrency acceptance
- PR #311 code/review is clean enough for final hosted measurement.
- Browser policy is no longer a reason to park the workstream.
- Build/use a short-lived external runner to issue genuine concurrent Home / My Team / Product Context HTTP reads against the actual Render host while batch-500 50k refresh runs.
- Capture exact RSS/high-water, readiness/publication, restart restore, then roll back to main.
- PASS -> Management adoption decision immediately. Memory > 536,870,900 bytes -> Management capacity gate. Auth path unavailable -> INPUT GATE with the smallest explicit user action requested.


## 2026-10-01 — Superseding #311 closure and next workstream

- **#311 production continuity: CLOSED / PRODUCTION ACTIVE.** Management authorized promotion of merged #311 with the documented residual statistical uncertainty accepted. Live Render main is PR #314 merge `f2aad88af25f77d72d6feee64d1d6679e1523728`; production config is Python 3.12.10, `numpy-pcg64-batched-gauss-v1`, batch 500, 50,000 trials. The prior external/browser authorization handoff is superseded; the product auth path was not weakened.
- **Actual continuity defect:** asynchronous context persistence omitted the exact published generation ID. PR #314 fixes it and has deterministic regression coverage; exact-head CI and focused suites passed. The first complete refresh and post-fix process restore both showed State/artifact identity consistency and full readiness. Details and deployment timeline are in `docs/operations/CURRENT_STATE.md` under “#311 production continuity incident closed”.
- **Capacity:** refresh process high-water was 352,358,400 bytes (184,512,500 bytes headroom); fresh restore acceptance high-water was 289,976,320 bytes (246,894,580 bytes headroom). Hard rollback gate remains 536,870,900 bytes. No hard-capacity rollback condition occurred; the earlier generation mismatch was a separate, real continuity trigger and is corrected by PR #314.
- **Temporary acceptance:** restore-only startup harness passed and was turned off. Clean no-harness restart `dep-dav4lls1nsns738k81n0` is verified live/full; acceptance flags are `0` and no runner log was emitted on that restart.
- **Render recovery note:** rollback deploy `dep-dauu5l97lnhs739vjujg` timed out on port detection; manual recovery deploy `dep-dav2ti41nsns738ckne0` made pre-#311 `878a2a32d5826ff990eed76c4985ae9e8f39bba3` live at 10:00:11Z. Later logs show Render's replacement-process delay before Uvicorn binds while the old instance keeps serving. Verify actual process/port/live commit, not the requested deploy label. Do not lengthen startup timeout without evidence.
- **Next active workstream: Simulation modernization.** Re-profile the hosted 50k NumPy path by queue/admission, Forecast/State preparation, Simulation prep/kernel/aggregation, and publication phases. Preserve protocol, batch 500, 50k trials, replay identity, and all product semantics. Select the next optimization only from measured bottlenecks. The Market For You zero-result finding remains recorded but held per the September 30 roadmap decision.


## 2026-10-01 — Simulation 2.0 after #319

- **#311/#314 continuity:** CLOSED; no contradictory production evidence. Production remains NumPy/PCG64, batch 500, 50,000 trials, Python 3.12.10; hard RSS rollback limit 536,870,900 bytes.
- **PR #319:** merged/deployed/hosted-validated on `de40ffd2a33bb51f1e9705cdd4978494c933ca53`. Its measured weekly-panel wall time was 11.408s versus prior 25.111s, with exact local output equality. Hosted full readiness and restore/publication identity passed; process high-water 353,918,976 bytes; temporary flags are off. See CURRENT_STATE's 2026-10-01 profile entry for exact job, phases, identities, and caveats.
- **Next capability:** league-governed playoff contract. Do not hardcode FSFFL postseason dates, sizes, byes, seeding, reseeding, bracket or scoring. Normalize source settings into canonical LeagueRules. If a material rule is absent/unsupported, championship/bracket values stay explicitly unavailable. Fixtures must cover different sizes/start weeks/bye structures and a non-FSFFL bracket.
- **Current implementation:** PR #320 (`https://github.com/jderhagopian-stack/fsffl-next/pull/320`), branch `work/sim20-league-configured-playoffs`, tested code head `78076c0da7b5140eb3c298807c355779a8ad55b5`, based on #319 main. Adds canonical playoff rules, validated explicit fixed-bracket execution, fail-closed qualification/title outputs where their respective policies are unsupported, downstream reasons/unavailable state, and model-version invalidation. Deterministic fixture suite covers 4-team/no-bye, 6-team/two-bye, and non-FSFFL 5-team/three-bye structures. Full local suite: 1,921 passed on Python 3.12.14 and 3.11.16. Next: exact-head GitHub CI and independent P1/P2 review if available; then deploy to private beta and verify 50k readiness, correctly unavailable playoff metrics absent canonical rules, identity, responsiveness, RSS, restart/restore before closure.
- Continue the directive's legacy capability order after this contract: week-by-week engine, lineup/availability/substitution, league-rule finish/playoff distributions, counterfactual deltas, origin-team pick distributions, Multiverse/common-world replay, selective recomputation/progressive scenarios, convergence and PIT calibration. Do not invent a replacement program.

### 2026-10-01 Management clarification to PR #320

PR #320 must emit the ordinary `championship_probability` if either an exact provider bracket is observed or a standard seeded fixed bracket is defensibly compiled from governed canonical league settings. Preserve `provider_observed_exact` versus `settings_derived_standard` only as authority/provenance metadata; no provisional user-facing class or visual downgrade. Qualification probability remains independent when its rules are known. Withhold title probability only for materially ambiguous or unsupported/custom brackets. Update tests, docs, and PR body to this rule before merge; ensure current non-null consumers remain safe.


## 2026-10-01 — PR #320 merged and deployed; hosted capability acceptance blocked

- PR #320 was squash-merged as `149ba9a8e9824aeb41d2aec695df3590713be3e4` after its 2-team settings-derived championship correction and the nullable-playoff consumer fix. Exact PR head: `2f63ee79a705b184c01f55e4aaa703d48e34d0db`.
- Exact-head full CI run `36894306343` passed; focused PR164, League Atlas, Home, and provider-trace workflows completed successfully. Local full suite passed 1,935 tests on Python 3.12.14 and 3.11.16; diff check was clean.
- The newest automated review had found a P1 in Market/Trade Finder when qualification odds were unavailable. The shared posture helper now returns calculated state `UNKNOWN` when league-relative playoff thresholds cannot be derived, with regression coverage. All active inline P1/P2 review threads are resolved. A separate automated summary review for the corrected head was requested but did not post before merge.
- Render deploy `dep-dav907ek1f9s73d9tggg` is `live` on the exact merge SHA at 2026-10-01 16:55:31Z. New instance `srv-dae6k7vqj5pc73af7bt0-67qsc` started Uvicorn and completed application startup; startup log showed user `jimmy` with no selected league/State and unavailable intelligence. Process RSS was 211,296,256 bytes; no active or waiting job was reported.
- **Targeted hosted playoff/championship acceptance is NOT COMPLETE.** Work Mode browser policy blocked reloading the hosted FSFFL page and explicitly prohibited retrying through another browser surface or an indirect request. Render logs confirmed the unauthenticated root returned 401; this does not exercise the authenticated Atlas/Sleeper path. No hosted probability result is claimed.
- Keep #320 at **MERGED/DEPLOYED — HOSTED ACCEPTANCE BLOCKED**, not Directive Complete. No rollback is justified by the available evidence. The only remaining #320 gate is an approved authenticated hosted run that refreshes/uses the exact current State and verifies governed playoff qualification/title outputs and explicit reasons when rules are unavailable.
- Hold the next approved Simulation 2.0 roadmap item until that targeted gate is directly exercised. The documented next item after the playoff contract is the week-by-week current-season engine; do not re-run unrelated runtime/lifecycle acceptance.


## 2026-10-01 — Superseding Management correction: Sleeper postseason estimates

- Apply `docs/operations/directives/20261001_SLEEPER_POSTSEASON_ESTIMATE_CORRECTION.md`. This supersedes earlier #320 wording that required complete explicit qualification rules before emitting odds.
- For ordinary Sleeper settings, derive qualification from the simulated finish distribution and top `playoff_teams`; derive standard seeded 2/4/6/8 championship odds from `playoff_week_start` when no exact provider bracket is available. Keep exact-vs-derived provenance internal and product labels ordinary.
- Restore downstream calculated competitive-state classification from the newly available qualification odds. Missing/corrupt basic settings and genuinely unsupported structures retain explicit unavailable reasons.
- #320 remains merged/deployed, but its old hosted gate only recorded an unavailable result under the superseded rule. The corrective implementation and one targeted hosted estimate/classification acceptance are required. Do not re-prove unrelated platform/runtime layers or advance the week-by-week engine before this acceptance is complete.


## 2026-10-01 — PR #321 correction deployed; hosted capability gate remains open

- PR #321, **Restore Sleeper postseason estimates from basic settings**, exact head `ed1c4a5744103cd1ad3176b1cac783acf82aabdb`, was squash-merged as `a658002713d496f9787dcd9aeac7f40b5f651a1d`.
- Exact-head CI run `36901136291` passed; focused workflows `36901136482` (PR164 regression), `36901136303` (corrective live provider numerical trace), and `36901136404` (Forecast corrective trace) passed. Full local suite: 1,941 passed on Python 3.12.14 with one existing Starlette/httpx warning; fixed 50k replay digest checked on Python 3.11.16 and 3.12.14; focused postseason/provider/classification checks: 45 passed.
- Render service `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`, auto-deploy off) deploy `dep-dav9ng2a3nsc73fdpabg` is live on merge SHA `a658002713d496f9787dcd9aeac7f40b5f651a1d` at 2026-10-01 17:45:11Z. Instance `srv-dae6k7vqj5pc73af7bt0-flvjl` reported application startup complete at 17:45:09Z. The platform's unauthenticated root request returned 401; this does not exercise postseason estimates.
- **Hosted postseason odds/classification acceptance remains OPEN/BLOCKED, not passed.** Prior Work Mode browser policy explicitly denied reloading the hosted product and prohibited alternate-browser/indirect-request retries. No authenticated hosted result is claimed. Keep Simulation 2.0's already-approved week-by-week engine on hold until one targeted authenticated check verifies ordinary Playoffs % / Championship % and the restored classification on the live path. Do not re-prove unrelated runtime/lifecycle layers.


## 2026-10-01 — ACTIVE: bounded reconciliation/readiness continuity correction before week-by-week Simulation

- #321 postseason correction is physically accepted on authenticated Safari: projected wins, Playoffs %, Championship %, and calculated classification are restored in production. Do not reopen postseason model design absent contradictory evidence.
- Current blocker is narrower: served/published-generation readiness is being conflated with working-generation progress during legitimate refresh/restart recovery. The earlier heavy refresh was user-initiated; the later clean reload coincided with a Render process restart and automatic stale-while-revalidate. Core Forecast/Simulation/Value remained reusable; the new reconciliation began while `intrinsic_restore` already owned heavy work.
- Required correction: dependency-aware completion. Reuse exact compatible artifacts; restore/build only missing/stale/invalidated capabilities and actual downstream dependents; atomic publication does not require recomputing current modules. If only Intrinsic is missing, do only Intrinsic. If all authoritative artifacts are current, reconciliation should be a no-op/cheap verification.
- Presentation/readiness must distinguish the fully usable served generation from a working replacement. Last-good availability must keep affected surfaces usable; `7/7 + all required capabilities Full` cannot remain overall Partial without an explicit unresolved reason.
- Apply focused/risk-proportionate validation only. After one targeted physical acceptance, resume the canonical next Simulation 2.0 item: **week-by-week current-season engine**.


## 2026-10-01 — #322 physical acceptance failed; restart/served-generation pinning remains active

- #322 is merged/deployed as `150c7b68...`, but authenticated Safari acceptance failed after a Render process restart.
- The product simultaneously exposed a valid prior published League Atlas generation and an incomplete replacement/current runtime to Franchise: top banner could say `Intelligence current` while League warned last-good/rebuilding and Franchise lost classification, Forecast/Simulation-derived fields, Market, and Intrinsic.
- Live sequence: old instance shut down ~19:57:58Z; replacement started 19:58:56Z; League Atlas served prior state `a2ad414e...` with Simulation; automatic Sleeper refresh began 19:59:40Z; replacement state `cc094159...` materialized; reconciliation started 20:00:26Z; startup readiness for replacement State had Forecast/Simulation/Value absent and Intrinsic unavailable.
- Required fix is narrow: on restart/restore and legitimate changed-State revalidation, every affected surface must remain pinned to the same served publication generation for derived intelligence until atomic promotion. Canonical current-State facts may advance separately, but incomplete replacement intelligence must not blank last-good derived fields if continuity is claimed.
- Use focused restart/changed-State continuity regressions and one physical acceptance. Do not reopen model math or broad platform acceptance. Then continue directly to the week-by-week Simulation 2.0 engine.

- Follow-up: the replacement did eventually converge cleanly (Intrinsic complete ~20:03:27Z; replacement Atlas served ~20:03:45Z; publication complete ~20:04:37Z; product current again by ~20:06). This narrows the blocker further: not stuck recovery, but **temporary mixed-generation degradation across surfaces while recovery is legitimately in progress**. Fix continuity/pinning, not model math or recovery speed.

- Management UI requirement: remove the large Franchise/League last-good/rebuilding hero cards. When published last-good intelligence is usable, recovery status must be compact/non-blocking (thin status strip or small inline annotation) and normal product content must remain primary. Do not make a usable surface look unavailable merely because replacement intelligence is building.

- #323 physical continuity/compact-presentation acceptance now passes. First-entry Franchise/League can still show a brief loading placeholder/blank skeleton before successful payload arrival; treat that as non-blocking UX/perceived-latency polish (candidate prefetch/layout skeleton), not a continuity blocker. Resume the Simulation 2.0 roadmap now.

## 2026-10-01 — PR #324 ACTIVE: current-season factual baseline / future-only Simulation

PR #324, **Simulation 2.0: seed current season from completed results**, is the first implementation slice of the canonical week-by-week current-season engine after #323 physical acceptance. Branch `work/sim20-current-season-weekly-engine` is based on current canonical main `42f05da2ad30abb16bb84ff0444ef5b2cc14af68`.

Authority/semantics:
- `LeagueState.completed_through_week` is the factual boundary. Completed fantasy matchup scores are immutable Simulation inputs; rows after that boundary remain unresolved even if a provider emitted numeric placeholders.
- Monte Carlo worlds now begin from actual completed wins and points-for and sample only unresolved future regular-season matchups. Final standings/finish distributions/postseason execution therefore combine factual past + simulated future instead of redrawing completed weeks.
- Existing `expected_wins` remains expected **final** regular-season wins. New `expected_remaining_wins` exposes the forward component and is carried through League Analytics and competitive scenario-delta contracts.
- Completed factual results participate in Simulation input fingerprint/replay identity. Simulation/result model identities advance so pre-#324 full-schedule-resimulation artifacts cannot restore as current-season authority.
- Live weekly scoring panels are materialized only for unresolved fantasy weeks. The existing governed season-mean + bye-aware empirical weekly-volatility bridge remains the future-week scoring evidence for this slice; ROS/WEEK uncertainty is still explicitly not promoted to Simulation authority.
- The newly recorded trade/waiver effective-date invariant is preserved by this primitive: completed weeks are common immutable facts; downstream alternate-State scenarios may affect only future eligible weeks. No arbitrary late-season discount multiplier belongs in Simulation.
- Frozen preseason expectation / in-season expectation history remains Phase 2 historical intelligence after Simulation 2.0 stabilization and does not interrupt this workstream.

Validation on the current source/test tree:
- ordinary Python 3.11 full suite: **1,952 passed**, one existing warning;
- explicit Python 3.12 full-suite replay validation: **1,952 passed**, one existing warning;
- fixed 50,000-world replay digests are now reviewed for both supported runtimes: Python 3.11 `f551968d5a00a6668cd236f90179f3b45480972f955f801c3ee8fe117dd09527`; Python 3.12 `c6a85f92a0938ec4db2caa7db89ca48c5a93d17f62c9f85e6a8277f68fedd5ea`;
- focused PR164 corrective and Live Forecast trace lanes passed on the proven source tree.
The temporary dual-runtime CI matrix used only to establish the 3.12 fixed baseline was removed; repository CI policy is unchanged.

Promotion remains Tier B / risk-proportionate: freeze the exact docs-complete head, require ordinary exact-head CI plus a fresh P1/P2 review of the bounded Simulation/consumer diff, then merge/deploy and run one targeted hosted current-season acceptance. Do not reopen #323 continuity, #321 postseason design, Forecast model design, or unrelated platform layers.

### 2026-10-01 — PR #324 Codex P1 correction: postseason week scoring + zero remaining regular games

Exact-head Codex review of `bbf30a25a60a838b78d42697f1773d1b773e14a3` found two related P1s inside the new current-season Simulation contract. Both are closed as one bounded scoring-boundary correction:

- postseason strength no longer reuses/averages the narrowed unresolved regular-season weekly panel;
- live Simulation now resolves the governed playoff structure first, builds forward scoring evidence over the union of unresolved regular-season weeks and the actual configured playoff round weeks, and partitions that evidence into `weekly_scoring` versus separate `playoff_weekly_scoring`;
- championship execution consumes the scoring distribution for each configured playoff matchup's actual week;
- when the regular season is complete, an empty unresolved regular-season schedule is valid. Actual completed standings/points remain the deterministic baseline and configured postseason Simulation continues from them;
- the scoring-dispersion diagnostic uses remaining regular-season evidence when available and playoff-week evidence once the regular season is complete;
- Simulation live/result model identities advance to the playoff-week-scoring contract so persisted pre-correction title odds cannot restore as current authority;
- the accepted #324 invariant remains unchanged: completed regular-season outcomes are immutable facts, only unresolved regular-season games contribute `expected_remaining_wins`, and completed facts remain shared by future counterfactual worlds.

Deterministic regressions prove (1) a last regular-season week whose team strengths are the opposite of the playoff week does not leak into championship scoring and (2) fully completed regular-season standings with zero remaining games still produce postseason odds from the configured playoff week.

Validation on corrected source/test head `508237237ffd7a50d261d59d26abf9bac9701499`: ordinary CI **1,954 passed**, one existing warning; PR164 focused corrective regression PASS; Live Forecast corrective trace PASS. One stale static-source assertion was updated to assert the stronger separated regular/postseason week contract rather than the old literal `weeks=fantasy_weeks` call shape.

Next gate: freeze the docs-complete exact head, rerun ordinary exact-head workflows, request fresh Codex review, and close any remaining P1/P2 before merge/deploy. Keep promotion risk-proportionate; do not reopen #321 postseason structure, #323 continuity, Forecast model authority, or unrelated platform layers.


- #324 reached a valid published current-season result in physical Safari (2-1, Contender, 9.2 wins / 91% playoffs / 12% championship), but repeated API redeployments of the identical merged commit restarted the runtime again. Finish #324 acceptance on one stable deployment; do not reset the instance absent a code/config change. This is acceptance-execution churn, not evidence to reopen Simulation math.

## 2026-10-01 — #324 ACCEPTED: current-season factual baseline / future-only Simulation

PR #324 was squash-merged as `1e5e3ff982e0507b9dbf10fc35e07d0886996571`. The accepted capability preserves completed regular-season results as immutable facts, simulates only unresolved regular-season games, exposes expected remaining versus expected final wins, and uses separate scoring evidence for each configured playoff week. A zero-length remaining regular-season schedule is valid after the regular season ends so final factual standings can feed postseason Simulation.

Risk-proportionate validation is complete:
- exact-head ordinary CI: **1,954 passed**, one existing warning;
- focused PR164 corrective regression: PASS;
- Live Forecast corrective trace: PASS;
- the two Codex P1 findings (playoff-week scoring and post-regular-season execution) were corrected and their review threads resolved;
- authenticated physical Safari reached a valid published current-season result for the managed franchise: **2-1, Contender, 9.2 projected final wins, 91% playoffs, 12% championship**.

Stable hosted acceptance used one deployment only after management stopped the repeated same-commit redeploy loop:
- Render deploy `dep-davdthqd0e5s73fkcbq0` on merged #324 commit `1e5e3ff9...` became live at **22:31:11Z** and remained the newest/live deployment through the latest available acceptance evidence;
- the stable instance `...-2cpdj` served League Atlas at **22:31:35Z** on State `68eac82b...` with `standings=12 simulation=True`;
- startup settle at **22:32:32Z** restored that State with `forecast=True simulation=True value=True complete=True`, product readiness `full`, and Intrinsic `full`;
- no subsequent shutdown, background refresh, reconciliation, working-generation, or replacement-deploy event appeared in the settle window;
- Render memory settled near **267 MB** against the 512 MiB service limit, with the product readiness log reporting ~290 MB RSS / ~290.5 MB peak and no active heavy-work owner.

This is sufficient acceptance for the Tier B #324 capability. Do not redeploy or re-prove #324 absent contradictory evidence.

**Simulation 2.0 roadmap advances immediately to item 2:** legal lineup optimization, player availability/missed-game uncertainty, bye handling, empty-slot behavior, and legal bench substitution. Reconcile against existing lineup/bye-aware machinery and add only the missing governed capability; do not redo accepted #324 current-season, #321 postseason, or #323 continuity work.

## 2026-10-01 — Simulation 2.0 item 2 ACTIVE: exact weekly availability + legal substitution

#324 current-season Simulation is accepted and must not be reopened absent contradictory evidence. The active roadmap position is item 2: legal weekly lineup optimization, availability/missed-game uncertainty, bye handling, explicit empty slots, and legal bench substitution.

Reconciliation against current main shows that most of item 2 already exists:
- the lineup optimizer handles league-legal QB/RB/WR/TE/FLEX/SUPERFLEX/K/DST assignment;
- taxi/IR players are excluded;
- canonical NFL byes create week-specific exclusions;
- the optimizer legally substitutes from the bench;
- if no legal replacement exists, Simulation can retain an explicit zero-point unfilled slot;
- identical exclusion states reuse cached optimized lineups.

The missing governed production contract is non-bye weekly availability. Research does **not** authorize a generic injury multiplier or fabricated missed-game probability: H1 availability must remain separate from conditional active production, authoritative ROS must not receive a second injury haircut, and absence of direct availability evidence cannot be guessed.

Active bounded implementation on branch `work/sim20-weekly-availability-substitution` therefore adds a provider-neutral exact State coordinate only:
- `PlayerWeekAvailability(player_id, week, status, provenance)`, with exact `available` / `unavailable` facts;
- no row means exact availability is unknown, not assumed available or unavailable;
- exact unavailable facts merge with canonical bye exclusions and feed the existing legal substitution/empty-slot optimizer;
- an exact available fact cannot override an NFL bye;
- populated availability is material State evidence and invalidates downstream Simulation, while raw provider Forecast acquisition remains reusable;
- empty availability remains serialization/State-ID compatible with durable snapshots written before this additive coordinate existed.

Probabilistic missed-game sampling remains **deferred**, not silently approximated, until Forecast/Research supplies a governed probability/time-to-return authority. This first slice establishes the correct Simulation consumer contract without inventing medical/availability math.

Promotion classification: additive State/Simulation authority coordinate with no live provider population yet. Use focused State serialization/material-fingerprint/lineup-substitution tests, full CI and exact-head P1/P2 review. Do not require another #324-style physical proof for an unpopulated source coordinate; any future live provider adapter that begins populating weekly availability must receive its own targeted acceptance.

## 2026-10-01 — #325 ACCEPTED: exact weekly availability + legal substitution

PR #325 was squash-merged as `814ab2f081616370a5aad9f67071877ccacf8469`. Exact head `d9ac7b21d76071189be862ae28af3324bc5113e7` passed full CI (**1,960 passed**, one existing warning), PR164 focused corrective regression, and Live Forecast trace.

Accepted item-2 capability now includes:
- league-legal weekly lineup optimization including FLEX/SUPERFLEX;
- taxi/IR exclusion;
- canonical NFL-bye exclusion;
- provider-neutral exact `PlayerWeekAvailability` facts;
- legal bench substitution for either bye or exact unavailability;
- explicit zero-point unfilled slots when the legal depth chart is exhausted;
- cached lineup reuse by effective exclusion set;
- State/material invalidation for populated weekly availability while raw Forecast acquisition remains reusable;
- backward-compatible State identity when the additive coordinate is empty.

Automated Codex review was unavailable because the code-review quota was exhausted. A bounded manual exact-head P1/P2 review found one lineage-truth defect (availability provenance was initially stamped onto unaffected teams); it was corrected before merge and covered by regression. No remaining P1/P2 issue was found.

No live provider populates `PlayerWeekAvailability` in #325, so no Render deployment or physical feature claim was performed. Any future adapter that begins populating the field requires its own targeted acceptance.

Probabilistic missed-game uncertainty remains explicitly deferred until Forecast/Research provides governed per-week availability/time-to-return authority. Do not infer probabilities from coarse current player status or apply a generic injury haircut.

**Simulation 2.0 roadmap advances to item 3:** reconcile the existing full finish-position distribution, expected finish, first-place/playoff/championship outputs, canonical playoff rules and bye seeds against the remaining finish/seed/postseason output contract. Add only missing governed outputs; do not rebuild #324 current-season mechanics or #321 postseason execution.

## 2026-10-01 — Simulation 2.0 item 3 ACTIVE: finish / seed / bye outputs

#325 exact weekly availability + legal substitution is accepted. The active roadmap position is item 3: finish/seed distributions and the remaining league-governed postseason outputs on top of the accepted weekly engine.

Reconciliation shows the engine already owns:
- expected final and remaining wins;
- exact full regular-season rank probabilities;
- expected finish;
- first-place and playoff qualification probabilities;
- league-governed fixed postseason execution where supported;
- championship probability with exact-versus-settings-derived provenance;
- fail-closed unsupported qualification/bracket reasons.

The bounded item-3 gap is output completeness, not postseason reimplementation:
- add discrete median regular-season finish;
- expose playoff seed probabilities explicitly when canonical qualification seeding is supported;
- emit bye probability when canonical playoff rules identify the bye seeds;
- keep bye authority independent from championship execution, so a known opening bye can remain available even if a later reseeding policy is not executable;
- withhold seed/bye outputs with explicit reasons when seeding or bracket structure is not governed.

No division probability is invented because current canonical LeagueRules do not yet carry a governed division structure/seeding contract; it remains "where applicable" and fail-closed until that State authority exists.

This slice advances Simulation output identity because the persisted authoritative result contract changes. Preserve the accepted #324 current-season facts/future-only mechanics, #324 playoff-week scoring, #325 availability/substitution, 50,000-world authority, and deterministic RNG protocol.

## 2026-10-01 — #326 ACCEPTED: finish / seed / bye output contract

PR #326 was squash-merged as `199c11550cf6d2ca7668a41e6dc7e2a318b09777`. It completes the bounded Simulation 2.0 item-3 output slice without reopening accepted #324 current-season execution or #325 weekly availability/substitution.

Accepted capability:
- discrete median regular-season finish;
- full finish-rank distribution retained and exposed through the ordinary League Atlas payload;
- explicit playoff-seed probability vectors when qualification seeding is governed;
- bye probability when canonical playoff rules identify bye seeds;
- bye authority remains independent from later championship execution, so a known opening bye can remain available even if a later reseeding rule is unsupported;
- unsupported qualification/seeding/bracket structures fail closed independently rather than fabricating seed/bye output;
- League Analytics and scenario-delta transport carry the new governed outputs;
- no division probability is fabricated because canonical State still lacks a governed division-membership/seeding contract.

Validation:
- exact-head full CI: **1,961 passed**, one existing warning;
- League Atlas North Star focused validation: PASS, including real-league composition sanity and live-provider authority audit;
- PR164 focused corrective regression: PASS;
- Live Forecast trace: PASS;
- fixed 50,000-world replay baselines were explicitly re-established on Python 3.11 and Python 3.12, then the temporary dual-runtime workflow change was removed;
- automated Codex review was unavailable because the repository/account review quota was exhausted; bounded manual exact-head P1/P2 review found and corrected one presentation-truth issue (unavailable seed distributions must remain `null`, not `[]`) and found no remaining P1/P2.

Single targeted hosted acceptance used Render deploy `dep-davecnjbc2fs73ciml40` only:
- exact merged commit `199c1155...` became live at **23:03:30Z**; no same-commit redeploy was triggered;
- startup correctly rejected the pre-#326 persisted Simulation artifact because model/output identity changed: State `68eac82b...` restored with `forecast=True simulation=False value=True complete=False`;
- Forecast, Value and full Intrinsic remained reusable, proving output-identity invalidation stayed localized to Simulation rather than blanking unrelated accepted layers;
- resource readiness at startup was ~271 MB RSS / ~276 MB peak against the ~429 MB soft engineering budget and 512 MiB service limit; steady memory settled around **247–250 MB** with idle CPU;
- no 5xx, OOM/recycle, repeated reconciliation loop, replacement deployment, or broad continuity regression appeared during the stable hosted window;
- the free instance later shut down normally from inactivity at 23:18:30Z. No product request occurred during that window, so no unnecessary canonical recomputation was forced merely for acceptance.

This is sufficient Tier-B hosted acceptance because the new field semantics/presentation were already proven on the exact head, while the hosted-only contract change was persisted Simulation identity invalidation and localized restore behavior. Do not redeploy or broadly retest #326 absent contradictory evidence.

**Simulation 2.0 roadmap advances immediately to item 4:** governed counterfactual competitive-outcome deltas using common Monte Carlo worlds where mathematically valid. Simulation returns deltas only; Decision/Trade/Market retain transaction economics, owner preference and acceptance authority.

## 2026-10-01 — Simulation 2.0 item 4 ACTIVE: governed common-world counterfactual deltas

#326 finish/seed/bye output authority is accepted and remains closed. Item 4 implements the directive's counterfactual/scenario contract on top of the existing trade, waiver and What-If paths rather than creating a parallel scenario engine.

Reconciliation found that production baseline/scenario runs already use the same configured seed, but **same seed alone is not sufficient common-world evidence**. Both supported RNG paths can consume a different number/order of random draws when an alternate State changes whether a team/week scoring distribution is deterministic (zero variance) versus stochastic. Postseason participant changes can create the same problem when possible teams have mixed deterministic/stochastic playoff distributions.

The bounded item-4 implementation therefore:
- keeps canonical 50,000-run probability math unchanged;
- adds a topology-only regular-season common-world coordinate to each Simulation result, covering factual completed results, ordered unresolved schedule/team identities, deterministic-vs-stochastic draw mask, and governed qualification rules while intentionally excluding changed scoring means/standard deviations;
- adds a stricter postseason common-world coordinate only when configured bracket execution has a stable draw topology (all possible playoff scoring rows stochastic or all deterministic); mixed deterministic/stochastic postseason paths remain valid Simulation but cannot claim paired title worlds;
- requires matching Simulation model, count, seed, RNG protocol/runtime/bit-generator/batch/dtype/layout/seed-derivation plus matching topology coordinates before labeling a counterfactual delta `common_random_numbers`;
- otherwise returns the same mathematically valid aggregate competitive delta with explicit `aggregate_difference` provenance and a concrete pairing-unavailability reason;
- creates a Simulation-owned typed `CounterfactualCompetitiveOutcomeDelta` for expected/future wins, playoff, bye, first-place and championship probability deltas;
- routes Trade Decision, Waiver and injury/availability What-If competitive deltas through that Simulation contract;
- leaves Team Utility responsible only for wrapping the Simulation competitive delta with non-competitive consequence channels such as resilience;
- leaves Value, transaction economics, materiality, owner strategy, negotiation, disposition and acceptance authority downstream and unchanged;
- preserves exact scenario-cache reuse as performance-only. Cache hits may reuse an exact changed-State Simulation result but never create comparison authority.

Because the persisted Simulation result gains common-world coordinates and downstream scenario APIs expose explicit pairing provenance, this is a Tier B Simulation/output-contract change. Simulation artifact identity advances; pre-item-4 Simulation artifacts must not silently claim common-world comparability.

Validation must remain bounded to the changed contract: deterministic common-world/topology tests, Team Utility/Trade/waiver/What-If consumer tests, fixed 50,000-world replay baselines for supported runtimes, full CI, and exact-head P1/P2 review. Hosted acceptance, after merge, should target one baseline + one alternate-State scenario path and confirm the comparison metadata; do not rerun broad #324-#326 acceptance.

### 2026-10-01 — PR #327 bounded review corrections / dual-runtime replay proof

PR #327 remains the active item-4 branch. Bounded P1/P2 review found two provenance/topology issues before promotion and both are corrected on-branch:

- **both-side replay provenance:** aggregate fallback comparisons may intentionally occur when baseline/scenario seed, count, model or RNG identity differ. The typed Simulation delta now carries baseline **and** scenario model version, simulation count, seed and RNG protocol rather than exposing only the baseline values as if they were shared.
- **postseason topology precision:** common-world postseason eligibility is now evaluated per playoff week. Every possible participant within a given week must consume the same number of draws, but one round may be fully stochastic while a later round is fully deterministic. Participant-dependent mixed deterministic/stochastic rows still fail closed for paired-title claims.

The typed counterfactual delta now also validates its own provenance invariants: paired regular-season worlds require matching exposed replay coordinates and `common_random_numbers`; unpaired comparisons require an explicit reason and `aggregate_difference`; paired postseason worlds require paired regular-season worlds and a paired championship delta; unavailable/unpaired title deltas must carry consistent provenance.

Corrected source/test tree replay proof:
- Python 3.11: **1,970 passed**, one existing warning;
- Python 3.12: **1,970 passed**, one existing warning;
- fixed 50,000-world replay digests remain the reviewed item-4 values already recorded in `tests/test_simulation_hot_loop_equivalence.py`;
- the temporary dual-runtime CI matrix was removed after proof; normal repository CI policy is restored.

Final gate is ordinary exact-head CI plus final bounded review. No #324-#326 reproof is authorized.

## 2026-10-01 — #327 ACCEPTED: governed common-world counterfactual competitive deltas

PR #327 was squash-merged as `4ddf4c6b16272eda803ea5ad0af8c06b6407c617`. It completes Simulation 2.0 roadmap item 4 without reopening #324-#326.

Accepted contract:
- Simulation owns typed competitive-outcome deltas for authorized alternate States;
- matching model/count/seed/RNG replay identity plus topology coordinates earns `common_random_numbers` provenance;
- same seed alone is insufficient;
- incompatible draw topology remains a valid aggregate before/after difference with an explicit unavailability reason rather than a false paired-world claim;
- regular-season and postseason pairing are governed separately;
- postseason pairing requires stable draw consumption within each playoff week, while different rounds may legitimately be uniformly stochastic versus uniformly deterministic;
- Trade, Waiver and What-If consume Simulation competitive deltas; Team Utility adds only its non-competitive consequence channels; Value/economics/materiality/owner behavior/negotiation/disposition/acceptance remain downstream;
- exact scenario-cache reuse remains performance-only and does not create comparison authority.

Review/validation:
- final exact head `99d7376c47b2dab644df7e505a9f545e9c78102e`: ordinary CI **1,970 passed**, one existing warning; PR164 focused corrective PASS; Live Forecast trace PASS;
- corrected source tree explicitly passed **1,970 tests on both Python 3.11 and 3.12**;
- reviewed fixed 50,000-world replay digests are Python 3.11 `5d76c6d46163171af810ac825f303529689d17a00884fd3f1409730180d70279` and Python 3.12 `9105dcf63c6d46827a9005e60abf919ea8b5edf8e045c2ae0365e1f87038c2bf`;
- the temporary dual-runtime CI matrix was removed and normal repository CI policy restored;
- Codex review was requested on the immutable head but unavailable because the code-review quota was exhausted;
- bounded manual P1/P2 review corrected both-side replay provenance, per-week postseason draw-topology precision, and contradictory pairing-metadata validation. No remaining P1/P2 issue was found.

Single targeted hosted deployment:
- Render deploy `dep-davfcjhsrm7s73bprjag` checked out exact merge `4ddf4c6b...`, became live at **2026-10-02 00:11:46Z**, and remained the newest deployment; no same-commit redeploy occurred;
- startup on instance `...-4k4mq` correctly rejected the pre-item-4 Simulation artifact while retaining reusable Forecast and Value with full Intrinsic: `forecast=True simulation=False value=True complete=False`;
- startup resource readiness was ~278 MB RSS / ~279 MB peak against the ~429 MB soft engineering budget; steady hosted memory settled near **308 MB** against the 512 MiB service limit and CPU returned to idle;
- no error logs, OOM/recycle, repeated reconciliation loop or replacement deploy occurred in the acceptance window.

The private beta requires Basic Auth and no authenticated scenario POST occurred during this stable deployment window. No claim is made that a physical browser scenario was re-exercised. Under the risk-proportionate/module-contract rule, this is not a promotion blocker: the changed scenario orchestration and comparison payload were exercised by exact-head product/integration tests, while the hosted-only artifact identity/restore/resource boundary was directly proven on the merged build. A later physical scenario use may provide additional confirmation but must not reopen item 4 absent contradictory evidence.

**Simulation 2.0 roadmap advances immediately to item 5: team-of-origin future-pick Simulation.** Build exact-slot/expected-slot distributions from governed origin-team football outcomes and actual league draft-order rules; preserve current owner separately from origin team; do not convert generic early/mid/late labels into authority and do not invent future-team strength beyond supported horizons.

## 2026-10-01 — #327 ACCEPTED: governed common-world counterfactual deltas

PR #327 was squash-merged as `4ddf4c6b16272eda803ea5ad0af8c06b6407c617`. It completes Simulation 2.0 item 4 without reopening accepted #324–#326 work.

Accepted capability:
- Simulation persists explicit topology-only common-world coordinates for regular-season and postseason random-draw structure;
- common-random-number provenance is emitted only when baseline/scenario model, count, seed, RNG replay identity and relevant draw topology all match;
- otherwise Simulation still returns the mathematically valid aggregate competitive-outcome delta with explicit fallback provenance/reason;
- typed Simulation-owned competitive deltas cover expected/future wins, playoff, bye, first-place and championship probability;
- Trade, Waiver and What-If consume Simulation competitive deltas; Team Utility only adds non-competitive consequence channels; Decision/Value/owner/acceptance authority remains downstream;
- scenario-cache reuse remains performance-only and does not create comparison authority;
- postseason common-world eligibility is evaluated per playoff week, so round-to-round stochasticity may differ when every possible participant within each round consumes the same draw count;
- both baseline and scenario replay provenance is retained on aggregate-fallback comparisons.

Validation before merge:
- corrected Python 3.11 full suite: **1,970 passed**, one existing warning;
- corrected Python 3.12 full suite: **1,970 passed**, one existing warning;
- fixed 50,000-world replay digests were reviewed for both supported runtimes and normal CI policy restored;
- bounded P1/P2 review corrected both-side replay provenance and postseason topology precision before promotion;
- deterministic tests prove same seed alone is insufficient, draw-topology mismatch fails common-world claims closed, uniform topology enables common-world deltas, and mixed participant-dependent postseason topology falls back explicitly.

Single targeted hosted acceptance used only Render deploy `dep-davfcjhsrm7s73bprjag`:
- exact merged commit `4ddf4c6b...` became live at **00:11:46Z** on one replacement instance; no same-commit redeploy followed;
- startup restored canonical State `68eac82b...` with Forecast and Value reusable while correctly rejecting the pre-#327 Simulation artifact (`simulation=False`) because Simulation result identity changed;
- startup resource evidence was ~278 MB RSS / ~279 MB peak against the ~429 MB engineering budget and 512 MiB service limit; memory then settled near **308 MB** with idle CPU;
- no 5xx, OOM/recycle, repeated reconciliation loop or replacement deployment appeared in the stable window;
- no authenticated trade/waiver/What-If request occurred during that window. Private-beta scenario routes require Basic Auth, and acceptance did not retrieve/use private credentials or trigger a second same-commit deployment. The counterfactual execution/provenance contract itself is therefore supported by exact-head deterministic/runtime tests, while the single hosted deployment proves the hosted-only restore/resource/identity boundary. This limitation is explicit and must not be rewritten as a physical scenario request.

This is sufficient risk-proportionate Tier-B closeout under the no-redeploy/no-credential boundary. Do not reopen or redeploy #324–#327 absent contradictory evidence.

**Simulation 2.0 roadmap advances immediately to item 5:** team-of-origin future rookie-pick distributions under the actual league draft-order rules. Simulation owns the football-outcome distribution; Value/Decision consume it downstream. Generic early/mid/late labels are summaries only, never the primary authority.


## 2026-10-01 — Management policy: estimates require explicit sanity-check visibility

Management clarified that NEXT should not default to unavailable merely because an exact rule/fact is missing. Use the strongest available evidence hierarchy: exact observed/configured rule -> deterministic derivation -> league historical inference -> governed standard-domain fallback -> bounded probabilistic estimate. Return unavailable only when even a bounded estimate would be materially misleading or unmodelable.

Any materially new estimate/fallback that can affect authoritative outputs must be surfaced to Management before promotion with: the missing exact fact, available evidence, proposed method, rationale/alternatives, affected outputs, uncertainty treatment, and what future evidence would supersede it. Management receives a sanity-check opportunity. Do not silently label an estimate as a verified league rule. Once a recurring fallback method is accepted, later unchanged uses need provenance/traceability but not repeated approval unless context or consequences materially differ.

For active Simulation item 5, remove unsupported FSFFL-specific draft-order assumptions. Draft-order rules must use explicit league evidence when available; otherwise use the separately approved governed standard fallback with explicit derived provenance. Placement games affect rookie order only when explicitly governed.

## 2026-10-02 — Simulation 2.0 item 5 ACTIVE: team-of-origin future-pick slot distributions

#327 common-world counterfactual Simulation is accepted and remains closed. Item 5 replaces the diagnostic early/mid/late proxy for the **next rookie draft only** with governed exact slot distributions keyed to the pick's original team.

### Draft-order authority correction

Draft order is resolved in this order:
1. **Explicit league rule evidence first.** A supported `DraftOrderPolicyEvidence` for the target draft season is authoritative and retains `explicit_league_rule` provenance.
2. **Governed standard fallback when explicit league evidence is absent.** This is a derived rule, not a claim about written league bylaws, and retains `derived_standard_fallback` provenance.
3. An explicit but unsupported/custom policy does **not** silently fall back; it remains unavailable until that explicit rule can be modeled.

Governed standard fallback:
- non-playoff teams: worse regular-season record, then resolvable head-to-head among tied teams, then lower regular-season Points For;
- playoff teams: earlier elimination round first; within the same elimination round use the same regular-season tiebreak sequence;
- runner-up then champion last;
- placement/consolation games do not affect draft order unless explicit league policy says they do;
- if the governed sequence still leaves an exact tie, preserve uncertainty across the unresolved tied slots rather than inventing a hidden team-ID tiebreak.

Unsupported FSFFL-specific assumptions are removed: Max PF is not the default draft-order metric, no FSFFL league ID is hard-coded into live Simulation authority, and 5th-/3rd-place games are not used unless explicitly governed.

Implementation boundary:
- exact next-season slot probability mass accumulates inside existing season worlds;
- completed and simulated regular-season outcomes supply record, H2H and Points For;
- accepted canonical playoff execution supplies elimination-round facts;
- exact slot probabilities, expected slot, median slot and earliest-to-latest percentile are primary authority;
- early/mid/late remain derived summaries only;
- current owner remains separate from original team, and the origin-team slot carries across rookie-draft rounds;
- explicit-vs-derived draft-order authority/provenance is product-visible;
- 2028+ distributions remain unavailable in this slice rather than extrapolating unsupported future team strength.

Promotion remains Tier B: focused explicit/fallback rule, tiebreak, elimination, placement-game, unresolved-tie and origin/ownership tests; full CI; reviewed fixed 50,000-world replay baselines if changed; exact-head P1/P2 review; then one targeted hosted next-season-pick acceptance. Do not reopen #324-#327.

## 2026-10-02 — PR #328 dual-runtime replay validation closed

PR #328 remains the active Simulation 2.0 item-5 branch. The Python 3.12 failure was isolated to the governed fixed 50,000-world complete-output replay digest after the intentional item-5 Simulation result-schema expansion. No item-5 football/draft-order logic failed.

Validated source/test tree:
- Python 3.11: **1,979 passed**, one existing warning;
- Python 3.12: **1,979 passed**, one existing warning;
- reviewed fixed 50k digests: Python 3.11 `f87a5f68430dbcd1e0ebeceb60d448bcd79ba615b2812a7d1ea26aa6273cc481`; Python 3.12 `c3b9b1f0348a0e7c6440ae61a765a51176d7159396fe8dd8ea67b3310bcdd495`;
- League Atlas North Star focused validation: PASS;
- PR164 focused corrective regression: PASS;
- Live Forecast corrective trace: PASS.

The 3.12 digest change is expected because `RegularSeasonSimulationResult` now carries item-5 future-pick distribution/unavailability fields in the canonical serialized output even for the fixed replay fixture. The temporary dual-runtime CI matrix was used only to establish the reviewed 3.12 baseline and has been removed; normal repository CI policy is restored.

Remaining promotion gate: ordinary exact-head CI on the docs/workflow-restored head plus bounded exact-head P1/P2 review. If clean, merge #328 and perform one targeted hosted next-season-pick acceptance. Do not reopen accepted #324-#327.

## 2026-10-02 — PR #328 final bounded review / promotion gate

The Python 3.12 validation blocker is closed. The item-5 source tree passed **1,979 tests on both Python 3.11 and Python 3.12** with reviewed fixed 50,000-world replay digests; normal single-runtime repository CI was then restored.

A fresh bounded exact-head P1/P2 review was required because Codex review remains unavailable under the repository/account quota. The review found one explicit-policy authority defect: a policy using the supported mechanism could include an unknown extra parameter that the compiler silently ignored. That contradicted Management's rule that explicit-but-unsupported league behavior must remain unavailable rather than be partially interpreted. The compiler now rejects unknown explicit parameters, with a deterministic regression proving no pick distribution is emitted for such a policy.

The review correction does not change RNG draws, Simulation result serialization, or the fixed 50k replay payload, so the completed Python 3.11/3.12 replay proof remains standing under the risk-proportionate rule.

Final corrected code head `8227f32bcb75d9406544693b1381d3dddc29d31e` validation:
- ordinary full CI: **1,980 passed**, one existing warning;
- League Atlas North Star focused validation: PASS, including real-league composition sanity and live-provider authority audit;
- PR164 focused corrective regression: PASS;
- Live Forecast corrective trace: PASS.

No remaining P1/P2 issue was found in the bounded item-5 review. Remaining promotion step is one docs-complete exact-head standard validation, then exact-head merge and one targeted hosted next-season-pick acceptance. Do not reopen #324-#327.

## 2026-10-02 — #328 ACCEPTED: governed team-origin future-pick slot distributions

PR #328 was squash-merged as `dd93e7246ed4435e7ec2760d775bd3224ad1509b`. It completes Simulation 2.0 item 5 without reopening accepted #324-#327.

Accepted item-5 authority:
- next-rookie-draft exact slot probability distributions are keyed to the pick's **origin team**, while current owner remains a separate State coordinate and the origin slot carries across rookie-draft rounds;
- explicit governed league draft-order evidence is authoritative when supported and retains `explicit_league_rule` provenance;
- absent explicit evidence, the approved governed standard fallback uses worse regular-season record -> resolvable head-to-head -> lower Points For for non-playoff teams; playoff teams are ordered by elimination round with the same regular-season sequence within a round; runner-up then champion are last;
- placement/consolation games affect order only under explicit governed policy;
- unresolved exact ties split probability across the unresolved slots rather than inventing a team-ID tiebreak;
- explicit-but-unsupported mechanisms or unknown explicit parameters fail closed and are not silently replaced by the standard fallback;
- early/mid/late remain summaries only; exact slots/expected slot/median slot/percentile are primary Simulation authority;
- 2028+ slot distributions remain unavailable in this slice rather than extrapolating unsupported future team strength.

Validation/review:
- dual-runtime source tree: **1,979 passed** on Python 3.11 and **1,979 passed** on Python 3.12, one existing warning each;
- reviewed fixed 50,000-world replay digests: Python 3.11 `f87a5f68430dbcd1e0ebeceb60d448bcd79ba615b2812a7d1ea26aa6273cc481`; Python 3.12 `c3b9b1f0348a0e7c6440ae61a765a51176d7159396fe8dd8ea67b3310bcdd495`;
- final corrected code head `8227f32bcb75d9406544693b1381d3dddc29d31e`: ordinary CI **1,980 passed**, one existing warning; League Atlas North Star focused PASS including real-league composition/live-provider authority audit; PR164 focused PASS; Live Forecast trace PASS;
- docs-complete exact head `a46d1a2cbf7d09755c6f0034b86f191e1ec56e61`: ordinary CI **1,980 passed**, with all three focused lanes PASS;
- Codex review remained quota-blocked. Bounded manual exact-head P1/P2 review found one explicit-policy defect (unknown extra parameters were silently ignored); it was corrected to fail closed with regression coverage. No remaining P1/P2 issue was found.

Single targeted hosted acceptance used only Render deploy `dep-davgtjk9v7es73fp0550`:
- exact merged commit `dd93e724...` became live at **01:56:05Z** on instance `...-mxcrc`; no same-commit redeploy followed;
- startup restored canonical State `68eac82b...` with Forecast and Value reusable and full Intrinsic while correctly rejecting the pre-#328 Simulation artifact: `forecast=True simulation=False value=True complete=False`;
- startup resource readiness was ~277 MB RSS / ~281 MB peak against the ~429 MB engineering budget; hosted memory settled around **252 MB** against the 512 MiB service limit;
- no 5xx, OOM/recycle, repeated reconciliation loop, replacement deploy, or error event appeared in the stable acceptance window;
- no authenticated product request occurred during the stable hosted window. Private-beta routes require Basic Auth; acceptance did not retrieve/use private credentials or force a second deploy merely to build a new Simulation artifact. Exact pick-slot/provenance behavior is therefore supported by the final exact-head product/League Atlas real-league validation, while the single hosted deployment directly proves localized persisted-Simulation invalidation, restore/resource safety and deployment continuity. This limitation must not be rewritten as a physical pick-card acceptance claim.

This is sufficient Tier-B closeout under the risk-proportionate/no-redeploy/no-private-credential boundary. Do not reopen #324-#328 absent contradictory evidence.

**Simulation 2.0 roadmap advances to the next directive capability: replayable Multiverse / explainability worlds.** Reconcile existing replay identity and retained diagnostics first; add only the missing bounded representative-world contract (median/expected-like, upside/downside, unusual credible/tail and notable outcome examples) with Simulation ID/seed and rarity context. This is explanation, not a second probability model. Selective recomputation/progressive scenarios, convergence and PIT calibration remain later directive work.

## 2026-10-02 — Simulation 2.0 item 6 ACTIVE: replayable Multiverse / representative futures

#328 team-of-origin future-pick distributions are accepted and must not be reopened absent contradictory evidence. The active roadmap position is item 6: replayable Multiverse/common-world explainability and representative tail outcomes.

Bounded implementation contract:
- Multiverse is an explanation layer over the **same canonical 50,000 Simulation worlds**, not a second probability model and not a separate stochastic run.
- The kernel retains no 50,000-world season-path archive. It keeps four compact scalar diagnostic series plus only the currently selected bounded exemplar summaries.
- Selected categories are: expected-like/typical world, plausible league-scoring upside, plausible downside, extreme tail, biggest future blowout, biggest future upset when observed, strongest expected-scoring team missing the playoffs when observed, and lowest-seed champion observed when championship Simulation is governed.
- Every exemplar carries root seed, RNG protocol/batch coordinate, canonical Simulation input fingerprint, deterministic Simulation ID, world index/world ID, final standings/team outcomes, optional notable matchup, and empirical rarity/percentile context from the same canonical run.
- Representative upside/downside targets are one governed league-total standard deviation above/below the Simulation input expectation; final rarity is empirical from the actual Monte Carlo sample.
- Exact rerun of the same governed request/seed must reproduce the same exemplar set and IDs.
- Model/persistence identity advances so pre-item-6 Simulation artifacts cannot masquerade as Multiverse-capable output.
- League Atlas exposes the bounded Multiverse payload as governed Simulation explanation evidence; presentation creates no new model truth.
- Player-specific superstar-week/season examples are explicitly deferred: current production Simulation samples governed team-week scoring distributions, not retained player-level stochastic draws. Do not fabricate player attribution.

Performance boundary:
- item 6 may add bounded diagnostic overhead but may not reintroduce a large raw-world archive or second 50,000-run pass;
- canonical probability/standings/playoff/pick outputs, RNG draw order, common-world coordinates and 50,000-run authority remain unchanged.

Promotion classification: Tier B Simulation output/explainability contract. Require focused deterministic replay/category/rarity tests, League Atlas payload coverage, full CI, reviewed fixed 50k replay digests if result serialization changes, exact-head P1/P2 review, then one targeted hosted acceptance of localized Simulation artifact invalidation and Multiverse-capable publication. Do not reopen #324-#328.

## 2026-10-02 — #329 ACCEPTED: replayable Multiverse representative worlds

PR #329 was squash-merged as `e0d4f6a1d8ca9cd6862fe1ef8203813387c971b1`. The accepted capability adds a bounded Multiverse explanation layer over the same canonical 50,000 Simulation worlds without a second probability model or raw-world archive.

Accepted item-6 contract:
- representative expected-like, plausible-upside, plausible-downside, extreme-tail and notable-outcome worlds are selected from the canonical run only;
- every exemplar carries deterministic Simulation/world identity, root seed, RNG/replay provenance, input fingerprint, empirical rarity/percentile context and final standings/team outcomes;
- same governed request/seed reproduces the same exemplar set and IDs;
- no additional Monte Carlo pass or RNG draws are introduced;
- retained all-world diagnostics remain four compact float64 scalar series (~1.6 MB at 50k) plus bounded full data for selected exemplars;
- League Atlas transports governed Multiverse evidence only; Presentation adds no model authority;
- player-specific superstar examples remain deferred until player-level stochastic authority exists.

Exact-head promotion evidence on `932cce25c6af26ddf61b4c3a9e64f7b3dd2fa53a`:
- full CI: **1,985 passed**, one existing warning;
- League Atlas North Star focused validation: PASS, including real-league composition sanity and live-provider authority audit;
- PR164 focused corrective regression: PASS;
- Live Forecast corrective trace: PASS;
- fixed 50,000-world serialized replay baselines were explicitly reviewed on Python 3.11 and Python 3.12;
- Codex review was requested but unavailable because the account/repository review quota was exhausted; bounded manual exact-head P1/P2 review closed all identified issues and found no remaining P1/P2.

Single targeted hosted Multiverse acceptance used Render deploy `dep-davhsbtg1s2s73aiqke0` only:
- exact merged commit `e0d4f6a1...` became live at **03:01:50Z** on instance `...-9h6c2`; no same-commit redeploy followed;
- startup correctly rejected the pre-#329 persisted Simulation artifact because Multiverse-capable model/output identity changed: State `68eac82b...` restored with `forecast=True simulation=False value=True complete=False`;
- Forecast, Value and full Intrinsic remained reusable, proving Multiverse invalidation stayed localized to Simulation;
- startup resource readiness was ~278 MB RSS / ~282 MB peak against the ~429 MB engineering budget; hosted memory settled around **243-244 MB** against the 512 MiB service limit and CPU settled near idle;
- no ERROR, OOM/recycle, repeated reconciliation loop, replacement deploy or broad continuity regression appeared in the stable hosted window;
- no authenticated private-beta request occurred during the stable window, so acceptance did not retrieve/use private credentials or force a recomputation/redeploy merely to materialize a new Multiverse artifact;
- the free instance later shut down normally from inactivity at **03:16:50Z**. Exact Multiverse category/replay/League Atlas behavior is therefore supported by the final exact-head product validation, while the single hosted deployment directly proves localized persisted-Simulation invalidation, restore/resource safety and deployment continuity. This limitation must not be rewritten as a physical Multiverse-card acceptance claim.

This is sufficient Tier-B closeout under the risk-proportionate/no-redeploy/no-private-credential boundary. Do not reopen #324-#329 absent contradictory evidence.

**Simulation 2.0 roadmap advances immediately to item 7:** progressive scenario computation plus dependency-based selective recomputation for interactive consumers. Reconcile the existing scenario cache, common-world counterfactual path, Forecast/lineup/Simulation dependencies and product callers first; add only missing governed reuse/progression contracts. Convergence and PIT calibration remain item 8.

## 2026-10-02 — Simulation 2.0 item 7 ACTIVE: progressive + dependency-selective scenarios

#329 Multiverse is accepted and must not be reopened absent contradictory evidence. The active roadmap position is item 7: progressive interactive scenario computation plus dependency-based selective recomputation.

Reconciliation before implementation:
- exact changed-State scenario results already had bounded in-memory/durable caching and in-flight coalescing;
- #327 already governs common-world competitive deltas;
- canonical current-State Simulation remains 50,000 trials and is never downgraded;
- trade, waiver and player-unavailable scenarios already share the same authoritative Simulation loader.

Bounded item-7 implementation on `work/sim20-progressive-selective-scenarios`:
- persisted canonical Simulation results now carry a compact `ScenarioSimulationPreparation` bundle: baseline optimized lineups, forward weekly team-scoring panel, scoring weeks, global-structure fingerprint and exact Forecast dependency fingerprint;
- alternate-State dependency planning distinguishes bounded roster changes from global Simulation changes. Compatible roster-only scenarios recompute only affected teams' deterministic lineups/weekly scoring inputs while reusing unaffected teams exactly; global rule/schedule/availability/Forecast dependency changes fall back to full input recomputation;
- alternate States with **no competitive roster dependency change** reuse the existing canonical competitive Simulation result exactly, even if the caller requested a lower stage, because an authoritative 50k result is stronger than a new preview;
- interactive stages are explicit: `screening=1,000`, `provisional=5,000`, `confirmation=50,000`;
- screening/provisional results are labeled `non_authoritative_scenario_preview`, expose a deeper-stage coordinate, and use distinct cache/model identities;
- only 50,000-run confirmation or exact reuse of an already-authoritative canonical competitive result may cross Trade Decision / Opportunity materiality, disposition or action-authority boundaries;
- Trade, waiver and What-If endpoints accept an explicit `scenario_stage`, defaulting to confirmation so existing product behavior remains authoritative;
- scenario preparation is validated against the exact baseline State/result before reuse; mismatched/stale preparation fails closed;
- the full league Monte Carlo outcome kernel still recomputes whenever competitive roster inputs actually change. Item 7 selectively reuses **unaffected deterministic preparation** rather than pretending unrelated league outcomes are independent.

Authority boundaries:
- Simulation owns stage fidelity, dependency planning, competitive results and common-world deltas;
- Team Utility consumes Simulation competitive deltas and adds resilience/non-competitive channels;
- Decision/Opportunity may inspect preview deltas but cannot promote materiality/disposition/action authority until confirmation;
- Presentation/API transports stage/progression metadata only;
- no calibrated adaptive run-count rule is introduced. The separate convergence/PIT study remains item 8 and 50,000 remains canonical authority.

Promotion classification: Tier B Simulation execution/performance contract with versioned persisted preparation. Require focused dependency/stage/authority tests, full CI, fixed 50k replay review if serialization baselines change, exact-head P1/P2 review, then one targeted hosted acceptance of localized Simulation invalidation/resource/continuity plus the selective/progressive contract through exact-head tests. Do not broadly retest #324-#329.

## 2026-10-02 — #330 ACCEPTED: progressive + dependency-selective scenario computation

PR #330 was squash-merged as `b5b2fe57060f1b9b415f1634a9743c7e29bdbc77`. The accepted item-7 contract adds explicit progressive interactive stages and dependency-aware selective preparation reuse without changing canonical 50,000-run Simulation authority.

Accepted capability:
- explicit scenario stages: `screening=1,000`, `provisional=5,000`, `confirmation=50,000`;
- screening/provisional outputs are labeled non-authoritative previews and expose the next deeper stage;
- only 50,000-run confirmation or exact reuse of an already-authoritative canonical competitive result may cross Decision/Opportunity materiality, disposition, candidate or action-authority boundaries;
- compact persisted `ScenarioSimulationPreparation` carries the baseline optimized lineups, forward weekly scoring panel, scoring weeks and exact structure/Forecast dependency fingerprints;
- compatible roster-only alternate States rebuild only affected teams' deterministic lineup/weekly scoring inputs and reuse unaffected teams exactly; the league Monte Carlo outcome kernel still reruns whenever competitive roster inputs change;
- global schedule/rules/availability/Forecast dependency changes fall back to full recomputation;
- State changes with no competitive roster dependency change may reuse the authoritative canonical 50,000-run competitive Simulation result while rebuilding the changed-State analytics envelope;
- trade, waiver and player-unavailable What-If endpoints default to authoritative confirmation but may explicitly request a preview stage;
- exact scenario cache/durable identities remain stage- and model-specific, and equivalent progressive stage loaders now share a stable explicit process-cache identity so identical preview requests can reuse/coalesce exact work.

Validation / exact-head review:
- final exact head `b1c5b5ae151a33a45599c5c207313db69cb957d1`;
- full CI: **1,998 passed**, one existing warning;
- Home North Star focused validation: PASS;
- League Atlas North Star focused validation: PASS;
- PR164 focused corrective regression: PASS;
- Live Forecast corrective trace: PASS;
- automated Codex review was unavailable because the code-review quota was exhausted;
- bounded manual exact-head P1/P2 review found one P2 performance/coordination issue: process-local cache identity included Python callable identity even for progressive loaders with an explicit governed cache identity, defeating in-memory reuse/in-flight coalescing across equivalent loader instances. The final head fixes that boundary and includes a regression proving the second identical screening request is an exact cache hit. No remaining P1/P2 was found in dependency planning, selective-input reuse, canonical competitive reuse, stage/durable cache separation or preview promotion gates.

Single targeted hosted acceptance used only Render deploy `dep-davj3vugekts73e91gg0`:
- exact merged commit `b5b2fe57...` became live at **04:26:16Z** on instance `...-l4hd4`; no same-commit redeploy or replacement deploy followed;
- startup restored canonical State `68eac82b...` with `forecast=True simulation=False value=True complete=False` at **04:26:46Z**. This is the expected localized invalidation of the pre-#330 Simulation artifact under the new persisted preparation/model identity;
- startup product readiness was partial only because Simulation was intentionally stale; Intrinsic remained `full`;
- startup resource readiness was ~279.6 MB RSS / ~281.8 MB peak against the ~429.5 MB engineering budget;
- hosted memory then settled near **246.1 MB** against the 512 MiB service limit while CPU fell to effectively idle;
- no ERROR/Traceback, 5xx evidence, shutdown/restart, reconciliation loop or publication churn appeared in the stable acceptance window;
- the only unauthenticated platform probe returned the expected private-beta 401. No private credentials were retrieved or used, so no hosted screening/provisional scenario was forced solely for acceptance. Progressive/selective semantics and authority gates are therefore supported by the final exact-head tests, while the single hosted deployment directly proves localized persisted-Simulation invalidation and resource/continuity safety.

This is sufficient Tier-B closeout under the risk-proportionate/no-redeploy/no-private-credential boundary. Do not reopen #324-#330 absent contradictory evidence.

**Simulation 2.0 roadmap advances to item 8:** governed convergence study and point-in-time calibration. Production remains at 50,000 canonical runs until convergence evidence supports a contract change and Management explicitly approves it. Calibration must use point-in-time inputs/outcomes without future leakage; do not convert the progressive preview counts into a new production-authority rule by assumption.


## 2026-10-02 — Simulation 2.0 item 8 execution clarification

Active item 8 scope is now explicit: run the convergence/stability study, then establish the reusable PIT calibration framework and use only authentic timestamped Forecast+State checkpoints that actually exist. Do not manufacture multi-year historical Forecasts from current projections or reconstructed league State. Report evidence coverage/sample size and limitations. Historical tests not requiring Forecast evidence may still use governed historical facts. Counterfactual scenario work measures stability/sensitivity, not unknowable alternate-world causal accuracy. Production remains 50,000 until Management explicitly approves any authority change.

## 2026-10-02 — Item 8 no-hunt execution rule

Do not spend implementation time hunting for historical PIT Forecasts. Complete convergence first. Calibration work is limited to verifying the prospective capture/scoring framework and using only authentic PIT checkpoints already present and immediately discoverable from canonical storage/repo evidence. If the sample is insufficient, state that explicitly and proceed; do not broaden into archive discovery or reconstruction.
