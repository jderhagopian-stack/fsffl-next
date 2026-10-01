# FSFFL NEXT — Product Roadmap

## Current parallel critical paths

### Foundation / league-agnostic path
1. K/DST architecture + evidence-independent implementation: **COMPLETE / MERGED**.
2. 2026 K/DST late-start/provisional exception work: **SEPARATE ACTIVE/EXTERNAL-EVIDENCE TRACK** under its persisted contracts.
3. Cross-league scoring-rule / Forecast-input audit: **DIRECTIVE COMPLETE — RESEARCH**.
   - 89-coordinate/rule-semantic registry;
   - 48-row platform coverage matrix;
   - primary-source ledger;
   - provider/historical/scoring-engine gap analysis;
   - deterministic fixtures;
   - implementation-ready handoff.
4. Scoring Coverage Stage 0 + Stage 1: **MANAGEMENT GATE — PLAN READY, NOT AUTHORIZED**.
   - canonical registry/rule/capability contracts;
   - compatibility compilation for existing scoring;
   - raw provider superset preservation;
   - zero new production authority.
5. Later scoring expansion, each separately gated:
   - direct 2PT/returns/common event coordinates;
   - nonlinear per-game milestone distributions;
   - attempts/completions/carries/first downs/targets/returns;
   - IDP subject/Forecast family;
   - advanced long-play/punter/head-coach/conditional rules.
6. League-agnostic validation must prove materially different scoring families without weakening evidence authority before the product claims broad league-agnostic scoring support.

### Product / Market path
1. Prior physical-iPhone Market acceptance: **FAILED / NOT ACCEPTED** as a product gate.
2. Market / Trade Discovery Architecture Review: **COMPLETE**. Handoff: `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`.
3. Management acceptance of revised Opportunity + Market contract: **COMPLETE**.
4. Bounded Market/Search/North Star implementation: **IMPLEMENTATION ACCEPTANCE COMPLETE — PR #220**. Handoff: `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`.
5. Merge/deploy PR #220 and repeat physical-iPhone/Safari Market acceptance: **NEXT GATE**.
6. Home × Franchise redundancy/information-hierarchy audit.
7. Trade Center expansion only after discovery/search order of operations is settled.

## Forecast authority boundary
Implemented contracts and research harnesses do not themselves create production K/DST forecasts. No one-source calibration, offensive-position fallback coefficient, aggregate-source double counting, guessed D/ST bucket math, or current/post-opener data backdated as preseason is permitted.

## Why Market architecture moved forward
The shipped Market shell established useful concepts, but physical-iPhone evidence showed:
- a supposedly high-signal For You feed can contain repeated target neighborhoods and packages still requiring substantial evaluation;
- discovery is spending user attention before enough cheap economic/bilateral screening and diversity control;
- Player Board and Free Agents can be unavailable while global readiness reports 7/7;
- Market is denser and less immediately readable/navigable than the accepted North Star surfaces.

This is not treated as presentation polish alone.

## Trade Discovery principle
Simulation should evaluate shortlisted trades, not perform broad discovery.

Working sequence:
`League State → strategic needs/opportunity hypotheses → candidate assets/counterparties → broad cheap package generation → economic screening → bilateral plausibility → clustering/diversity → high-signal opportunity frontier → targeted Decision/Simulation → deeper analysis`

Simulation is a microscope, not the searchlight.

## Product principle
For You should surface a deliberately small number of genuinely distinct strategic opportunities, not merely raw packages Search can construct. The product must be able to explain why each item deserves scarce user attention before asking the user to enter a deep evaluation.

## League-agnostic validation
“League-agnostic” remains a target, not a fully proven property. Forecast implementation and later lifecycle validation must exercise configurations unlike the original FSFFL league without weakening evidence authority.


## Accepted-for-review Market architecture
The completed review proposes:
- strategic hypotheses before targets/packages;
- Opportunity as the scarce-attention object;
- Candidate Paths as concrete acquisition routes;
- raw package neighborhoods as subordinate variants;
- cheap Decision-owned economic screening and a bounded pre-Simulation bilateral screen;
- family clustering/dominance pruning before feed ranking;
- deterministic diversity selection instead of package-row lane diversity;
- maximum four For You opportunities in the private beta, with no duplicate exact target;
- zero broad changed-state Simulation calls;
- Core 7/7 readiness separated from Market consumer readiness;
- opportunity-first For You, progressive Trade Finder, read-only Player Board, and roster-fit-first Free Agents.

Management accepted these policies on 2026-09-25; PR #220 implements them and has satisfied implementation-level automated acceptance.

## Near-term infrastructure/performance priority — Simulation kernel efficiency
Following completion of current reliability acceptance and the immediate Market foreground-latency corrective, prioritize a dedicated general Simulation efficiency program before lower-priority product breadth.

The product already benefits from persistent exact Simulation reuse, coalescing and progressive delivery, but fresh canonical 50,000-run Simulation remains a core latency dependency for intelligence refresh and deep scenario/trade analysis. The next phase should optimize the engine itself under the existing authority contract, beginning with exact-output-preserving software improvements and only escalating to statistically equivalent/non-bit-identical numerical architecture under a separate Management gate.

## Simulation Multiverse / alternative-futures product
Recover the original FSFFL Multiverse concept after the core Simulation engine is modernized.

Purpose: preserve the richness that disappears when thousands of modeled seasons are reduced to expected wins and probabilities. Surface auditable, model-consistent alternative futures such as surprise breakouts, dominant/collapse seasons, unlikely playoff paths, high-seed champions and historically interesting scoring outcomes.

Product rule: clearly separate **expected outcome** from **interesting possible universe**. Extreme-of-N values are sample-size dependent, so pair them with rarity/percentile/frequency context and avoid presenting them as forecasts.

Prefer deriving the Multiverse catalog from the same canonical Simulation pass with replayable simulation IDs/provenance. Potential surfaces include preseason Reports, Home, League Atlas, team pages and shareable league-story cards.

## Legacy FSFFL capability harvest — preserve proven primitives, not legacy authority
A structured review of `jderhagopian-stack/sleeper-league-data` identified several predecessor capabilities worth preserving as reference implementations or future infrastructure. Do not port legacy authority wholesale; recover concepts only under NEXT's current Data → State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation chain.

High-value harvest targets:

1. **Vectorized Simulator reference.** The predecessor NumPy-based Simulator performed 50,000 preseason universes with batched player draws, scoring, matchup outcomes and playoff evaluation. One archived 2026 snapshot records 50k in 6.286s in its environment. Use this as evidence that NEXT's sequential Python kernel has substantial software-efficiency headroom, not as an apples-to-apples hosted benchmark.
2. **Point-in-time historical state provider.** The old system could reconstruct exact pre-transaction rosters, taxi/reserve, pick ownership and FAAB by reversing completed Sleeper transactions. Preserve the principle of historical FACT reconstruction separately from hindsight or decision models.
3. **Historical analysis with hindsight isolation.** At-the-time trade evaluation and later realized outcomes were explicitly separate layers. Retain this boundary for future historical trade grading/backtesting.
4. **Asset lineage graph.** The predecessor retained a 774-node / 1,434-edge player-and-pick lineage graph, including pick-to-player draft conversions and explicit "mixed inputs / attribution unknowable" labels for multi-asset trades. This is strong infrastructure for trade genealogy, pick conversion history and shareable league stories.
5. **Player franchise history.** The predecessor retained 393 player-history records with acquisition events, reacquisitions and unique FSFFL-team counts. Preserve/migrate this historical identity for Record Book and player-history products rather than recomputing ad hoc.
6. **Simulation snapshot archive.** The predecessor archived dated Simulator outputs with model/input/runtime provenance. NEXT should preserve time-series intelligence snapshots so users can compare preseason/current/weekly beliefs and replay how the league outlook changed.
7. **Simulation-sensitivity gating.** The old Opportunity Engine could rerun candidate utility across multiple seeds and withhold sign-unstable trades from headline actionability rather than hiding uncertainty. Consider this after current latency work, using NEXT Decision authority and without fabricating acceptance probability.
8. **Context-normalized Owner Intelligence.** Behavioral Intelligence research adjusted observed owner choices for roster need and league opportunity environment, used leave-one-manager-out priors, and shrank sparse samples toward neutral. Reuse methodological ideas only as descriptive Owner Intelligence; do not convert them into unsupported acceptance probabilities or Forecast inputs.
9. **Validated position-specific matchup signal.** Old opponent-adjustment research retained small RB/TE effects after holdout but neutralized QB/WR when evidence failed. The lesson is methodological: plausible football features should be position-specific and promoted only after chronological holdout evidence.
10. **Multiverse / media-guide / Record Book storytelling.** The predecessor turned governed analytics into league-specific stories and publications without giving Presentation new decision authority. NEXT should recover this after core reliability/performance, using current North Star interaction patterns rather than legacy report-first UX.

Explicit non-goals:
- do not restore legacy GM/Value/Trade authority;
- do not port hand-set heuristics merely because they were once production;
- do not let historical realized outcomes leak into point-in-time evaluation;
- do not let owner behavior or market behavior enter universal Forecast;
- do not prioritize Record Book/media-guide breadth ahead of current reliability, Market responsiveness and Simulation performance.

## Management sequencing — legacy capability harvest placement

Do not launch all recovered legacy capabilities as parallel feature work. Sequence them by dependency and product leverage.

### Phase 0 — current critical path
1. Complete PR #263 post-merge deploy + FSFFL → Hodor → FSFFL → restart acceptance.
2. Resume physical Market acceptance.
3. Close Market cold/focused foreground latency to a usable beta threshold.

Nothing from the legacy harvest may delay this phase.

### Phase 1 — Simulation modernization
Immediately after Market latency:
1. Benchmark current NEXT fresh/changed-State Simulation.
2. Run the governed simulation-count convergence study; keep 50k production until Management changes the contract.
3. Recover compatible vectorization/batching ideas from the predecessor Simulator under NEXT authority.
4. Optimize the fresh kernel.
5. Preserve replayable universe identity / bounded Multiverse capture as part of the engine redesign so it is not bolted on later.
6. Return at an explicit equivalence/semantics gate if further speed requires non-bit-identical RNG/reduction behavior.

This is the highest-priority legacy recovery because it directly improves intelligence refresh, Trade Center, scenario analysis and future product interactivity.

### Phase 2 — historical intelligence foundation
After Simulation modernization is stable, promote reusable historical infrastructure before broad historical UI:
1. canonical point-in-time historical State reconstruction;
2. durable player franchise history;
3. player/pick asset lineage graph;
4. dated intelligence/simulation snapshot archive and replay provenance.

These are Data/State/Analytics foundations, not new decision authority. Build them so future history/replay features do not reconstruct past truth ad hoc.

### Phase 3 — Decision/Market uncertainty + Owner Intelligence
Once Market and Simulation are fast enough for repeated evaluation:
1. test repeated-seed / simulation-sensitivity confirmation under NEXT Decision authority;
2. keep sign-unstable opportunities visible but not headline-actionable unless evidence supports promotion;
3. revisit context-normalized Owner Intelligence using roster need, opportunity environment and shrinkage;
4. keep Owner Intelligence descriptive/directional unless separate evidence supports stronger claims; no fabricated acceptance probability.

### Phase 4 — productize the league's memory
Only after the shared foundations above are stable:
- Multiverse / alternative-futures cards and drill-down;
- trade/pick genealogy;
- player franchise-history surfaces;
- Record Book;
- historical trade review;
- Alternate History / What-If;
- preseason media guide / season publications;
- league-story/shareable modules.

Prefer integrating these into Home, Franchise, League Atlas, Player Intelligence and Reports instead of creating disconnected mini-products.

### Parallel Research
The comprehensive Y4-Y8 Forecast/Intrinsic architecture study may continue independently because it does not depend on the legacy-history productization path. It must not consume Market/Owner/lineage outcomes as Forecast inputs.

### Ordering principle
Recover **foundational primitives before presentation breadth**:
`reliability → Market responsiveness → Simulation modernization → historical State/lineage/snapshots → Decision/Owner uncertainty intelligence → storytelling/history surfaces`.


## Public launch readiness gate
Before any public launch or material open-beta traffic, execute a dedicated production-readiness/scaling review under `docs/operations/directives/20260929_PUBLIC_SCALE_ARCHITECTURE_PRINCIPLE.md`.

The target is not to make commercial workloads fit the current free Render footprint. The target is to prove that higher traffic can be absorbed primarily by adding web/worker/cache/database capacity rather than rewriting the governed application architecture.

The review must cover at minimum horizontal web scaling, durable/idempotent background jobs, multi-instance lifecycle coordination, workload separation, bounded cache ownership, queueing/backpressure/fairness, provider-rate-limit behavior, tenant isolation/security, observability, realistic burst/load testing, and cost/capacity modeling.


### Immediate beta constraint
Before public-scale work begins, FSFFL NEXT must first be reliably usable on the current free Render private-beta footprint for normal single-user testing. Public-scale readiness must not delay that acceptance gate.


## 2026-10-01 Simulation 2.0 execution checkpoint

Follow the accepted sequence in `directives/20260928_SIMULATION_2_0_PROGRAM.md`: measured engine modernization first, then the already-approved capability recovery in its documented order (week-by-week current-season engine; legal lineups/availability/substitution; league-specific finish/playoff outputs; counterfactual deltas; origin-team pick distributions; replayable Multiverse/common worlds; selective recomputation/progressive scenarios; convergence and PIT calibration). Do not replace this list with an ad hoc feature sequence.

PR #318 is accepted and hosted-validated. PR #319 is the next measured engine slice: it reduces repeated lineup-panel allocation/materialization while preserving exact outputs and replay identity. Hosted acceptance measured the weekly-panel phase at 11.408s / 1.716 CPU seconds versus the prior recorded 25.111s / 3.778 CPU seconds, with 500×168 float64 batches (672,000 bytes); local 48-scenario exact-output benchmark showed median 1.507270s → 0.454371s. See the latest CURRENT_STATE entry for hosted refresh, foreground, memory, and Render cleanup evidence. Continue only with material measured gains.

The next capability contract is league-governed playoffs. The generic bracket is interim only: no FSFFL defaults for playoff timing, qualifier count, rounds, byes, seeding/reseeding, matchups, or scoring/tiebreaks. Persist canonical LeagueRules, consume them in Simulation, and fail closed on unsupported postseason outputs. This is clarification of the accepted Simulation program, not a change in roadmap ordering.
