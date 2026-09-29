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
