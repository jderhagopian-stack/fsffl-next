# Workstream — Market / Trade Discovery

## State
**IMPLEMENTATION COMPLETE — PHYSICAL IPHONE ACCEPTANCE GATE**

## Why this workstream moved forward
Physical-iPhone Market acceptance exposed a product-level problem rather than a narrow presentation defect.

Observed acceptance evidence:
- the four-surface Market structure is understandable: For You, Trade Finder, Player Board, Free Agents;
- Trade Finder intent selection is directionally strong;
- Player Board and Free Agents can report unavailable even while the global readiness strip reports 7/7, which requires separate readiness/consumption diagnosis;
- the For You surface labels five items as high-signal while showing repeated opportunity neighborhoods and packages that still require full evaluation;
- examples observed include multiple Jahmyr Gibbs paths, including very expensive Superflex packages;
- the current experience therefore spends scarce user attention before enough inexpensive discovery/economic/bilateral screening has occurred;
- Market mobile presentation is materially denser and harder to scan/navigate than the accepted Home/Franchise/League North Star standard.

## Objective
Redesign the governed definition, discovery, screening, ranking/diversification, and presentation contract for a Market opportunity **before** deep Decision/Simulation evaluation.

This is an architecture/product-definition review. Do not begin broad implementation until Management accepts the resulting contract.

## Architecture-review outcome — 2026-09-24
The review is complete and persisted in:
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

The implementation-ready contract establishes:
- OpportunityHypothesis → MarketOpportunity → CandidatePath as distinct discovery layers;
- raw package variants as subordinate paths, not top-level opportunities;
- a staged funnel that uses cheap Decision-owned economics and a bounded pre-Simulation bilateral screen before For You eligibility;
- exact changed-state Simulation only after transaction-level escalation;
- descriptive Owner Intelligence as optional plausibility context, never fabricated acceptance probability or universal Value;
- family clustering, within-family dominance pruning, and a separate diversity selector;
- a For You `worth_attention` gate that cannot be satisfied by Search generation or “Needs full evaluation” alone;
- a four-card private-beta For You cap with explicit target/need/counterparty diversity rules;
- a bounded eight-path pre-Simulation Decision budget as tunable product compute policy, not model authority;
- revised four-surface Market information architecture and mobile drill-down grammar;
- a truthful split between Core 7/7 lifecycle readiness and per-surface Market readiness;
- nonblocking Player Board / Free Agents behavior when optional Intrinsic or player-level enrichment is still building;
- deterministic Gibbs-neighborhood, extreme-Superflex, bilateral-dominance, readiness, and Simulation-call-count fixtures;
- a seven-phase bounded migration and acceptance sequence.

No broad Market implementation was performed. Management acceptance is required before Phase 1 implementation begins.

## Core product question
What should FSFFL NEXT have to establish cheaply and governably before telling a user that an opportunity is worth attention?

## Target discovery funnel
Use this as a hypothesis to test and refine, not as an implementation shortcut:

`League State → strategic needs/opportunity hypotheses → candidate assets/counterparties → broad cheap package generation → economic screening → bilateral utility/plausibility screening → diversity/deduplication → high-signal opportunity frontier → targeted Decision/Simulation → deep analysis`

Simulation is a microscope, not the searchlight.

## Required architecture decisions
1. Define an Opportunity object distinct from a raw generated trade package.
2. Define which governed authorities may contribute at each stage: State, Forecast, Value, Team Utility, Decision, Owner Intelligence, Search/Optimization, Simulation.
3. Preserve authority boundaries. Search may rank/filter evidence; it may not invent Decision truth, Value, Forecast, or acceptance probability.
4. Define cheap pre-deep-dive screening sufficient to reject obviously poor neighborhoods/packages without exact Simulation.
5. Define bilateral plausibility without fabricating an acceptance probability.
6. Define strategic relevance to the user's roster/competitive state.
7. Define opportunity-family clustering/deduplication so near-duplicate packages or repeated target ideas do not monopolize For You.
8. Define diversity/novelty requirements for a deliberately small high-signal feed.
9. Define when a candidate is allowed to say “worth your attention,” versus “market match only,” “needs full evaluation,” or should not surface at all.
10. Define escalation criteria for targeted Simulation/deep Decision analysis.
11. Determine how Market vs. Intrinsic disagreement should function as one discovery lens rather than the repeated organizing block for every Market surface.
12. Diagnose the Player Board / Free Agents 7/7-readiness contradiction and specify the truthful readiness contract, without weakening fail-closed authority.

## Product / UI review
Recompose Market around SEE → UNDERSTAND → INTERACT → DRILL DEEPER.

### For You
Should answer: **What are the few strategic paths actually worth my attention right now, and why?**

Evaluate organizing first by opportunity/strategy rather than raw package. Candidate concepts include:
- strategic objective / need;
- why now;
- expected benefit;
- cost/risk;
- plausible counterparty or acquisition path;
- 1–2 representative packages only after the opportunity is established.

### Trade Finder
Retain intent-first discovery, but evaluate progressive disclosure. Do not present irrelevant controls merely because they exist. The selected intent should determine the controls and results required.

### Player Board
Define a visual, read-only player-market discovery surface using separate governed Value lenses. It should not feel like another long utility page.

### Free Agents
Should answer: **Who can improve my roster without a trade?** Discovery should be immediate when governed evidence is available; explicit add/drop evaluation remains an interaction/deepening step.

### Mobile standard
Bring Market to the readability/navigation standard of the accepted North Star surfaces:
- stronger information hierarchy;
- less repeated explanatory chrome;
- fewer simultaneously visible controls;
- reduced card repetition;
- faster scanability;
- progressive disclosure;
- preserve useful context without making the user read the model.

## Required evidence / analysis
- inspect the actual current Market/Search/Decision implementation and PR #195 behavior;
- trace how the observed For You candidates and Trade Finder paths are generated, filtered, ranked, and labeled;
- identify where expensive Simulation is or is not invoked;
- identify duplicate/redundant opportunity generation;
- identify which current cheap signals already exist and which governed signals are missing;
- distinguish UI defects from upstream Search/Decision architecture defects;
- use deterministic examples/fixtures, including the observed repeated Gibbs neighborhood and extreme Superflex package shapes, to test the proposed funnel;
- preserve current accepted authority chain and anti-double-counting rules.

## Required outputs
Persist an implementation-ready handoff containing:
- current-state pipeline trace;
- failure-mode diagnosis;
- canonical Opportunity contract;
- stage-by-stage authority/input/output contract;
- cheap-screening and bilateral-plausibility contract;
- clustering/diversity/ranking contract;
- deep-evaluation escalation contract;
- revised Market information architecture for all four surfaces;
- mobile interaction/presentation requirements;
- truthful readiness contract for Player Board / Free Agents;
- deterministic fixture/test matrix;
- migration plan from current implementation;
- unresolved risks;
- bounded implementation sequence and acceptance tests.

Include lightweight mockups/wireframes in Markdown where they materially clarify the proposed Market composition.

## Acceptance
Management should be able to answer from the persisted handoff:
- why each For You item deserves scarce attention;
- why obviously dominated or incoherent packages were removed before deep evaluation;
- why repeated variants do not crowd the feed;
- what evidence supports bilateral plausibility without fake acceptance probability;
- when exact Simulation is worth spending;
- how each Market tab has a distinct consumer job;
- why 7/7 readiness cannot coexist with a misleading “still loading” Market artifact state;
- how the revised mobile experience is materially easier to scan and navigate.

## DO NOT
- Do not fabricate trade acceptance probability.
- Do not let Owner Intelligence contaminate universal Value.
- Do not make Search the authority for Forecast, Value, or Decision truth.
- Do not use exact Simulation as broad package discovery.
- Do not hide poor discovery quality behind presentation polish.
- Do not redesign accepted Home/Franchise/League surfaces.
- Do not change Forecast/K/DST work owned by the parallel implementation workstream.
- Do not merge/deploy broad Market redesign before Management accepts this architecture review.

## Operating behavior
Follow `../OPERATING_PROTOCOL.md`. Own the architecture-review outcome through an implementation-ready persisted recommendation. Maximize each turn and stop only at DIRECTIVE COMPLETE, BLOCKED, MANAGEMENT GATE, or unavoidable continuation.


## Management-approved North Star concept — 2026-09-24
Management reviewed and approved the revised Market concept direction. Treat this as **product intent**, not permission to force analytical outputs to match a mockup.

### Visual / interaction intent
The Market must use the same calm North Star grammar as Home, Franchise, and League: clear hierarchy, compact governed intelligence, progressive disclosure, strong scanability, and fewer simultaneous controls. Avoid a separate dense “fantasy management app” aesthetic.

### Four top-level jobs
- **For You:** “Your best paths right now.” A deliberately small set of distinct strategic opportunities. Opportunity first; packages second.
- **Trade Finder:** “What are you trying to do?” Intent first. Reveal only controls relevant to the chosen intent, with advanced controls behind progressive disclosure.
- **Player Board:** visual/read-only market exploration using separate governed Value lenses; player rows lead to Player Intelligence and contextual actions.
- **Free Agents:** “Available players who can help.” Roster-fit discovery first; explicit add/drop evaluation only after interaction.

### Canonical drill-down grammar
All Market interactions should follow:
`SEE → UNDERSTAND → INTERACT → DRILL DEEPER → DECIDE`

Representative paths:
- For You strategic card → **Opportunity Detail** → candidate acquisition paths → **Candidate Path Detail** → specific transaction → **Trade Center** → targeted Simulation/full evidence when warranted.
- Market-disagreement/player item → **Player Intelligence**, contextualized to Market → “Find trade paths” returns to Trade Finder pre-filtered to that player.
- Free-agent item → lightweight fit/context → **Add/Drop Evaluation** → governed roster/value/team-impact comparison.
- Player Board row → **Player Intelligence**; owner/team context may link to Owner Intelligence; contextual “Find a deal” enters Trade Finder pre-populated.

### Opportunity Detail
Must explain *why this opportunity exists before showing a trade*:
- strategic need/opportunity hypothesis;
- why now;
- governed expected benefit signals available at this stage;
- cost/risk band without invented precision;
- plausible counterparties/acquisition paths;
- a small set of materially distinct candidate paths;
- evidence/authority status.

### Candidate Path Detail
Must explain why a particular path survived preliminary screening:
- target and counterparty;
- representative package or package family;
- strategic fit for user;
- bilateral rationale supported by governed evidence;
- important sacrifices/risks;
- alternative realistic paths;
- clear escalation to Trade Center rather than pretending preliminary screening is a final trade verdict.

### Trade Center handoff
Market discovery must not duplicate Trade Center. Trade Center receives a specific transaction/candidate path for full bilateral Decision analysis. Exact Simulation is invoked selectively when it adds decision value.

### Product acceptance implication
A Market item earns scarce For You space only after the architecture can explain why it deserves attention. “Search generated it” or “Needs full evaluation” alone is insufficient.


## Architecture closeout
Current stop state: **MANAGEMENT GATE — MARKET / TRADE DISCOVERY ARCHITECTURE REVIEW**.

The review found that the shipped failure is upstream of presentation: package-row generation, exact-only deduplication, pre-family truncation, and sparse Decision enrichment allow repeated target neighborhoods and economically questionable packages to reach For You before they have earned attention. Presentation density then amplifies the problem.

Management should review the persisted handoff and either:
1. accept the governed contract and authorize the bounded implementation sequence; or
2. return explicit architecture changes while keeping broad Market implementation gated.


## Management acceptance — 2026-09-25
**DIRECTIVE COMPLETE — ARCHITECTURE / BOUNDED IMPLEMENTATION AUTHORIZED**

Management accepts the persisted implementation handoff without architecture changes. The implementation workstream is authorized to execute the handoff's phased migration and acceptance sequence, including the approved North Star interaction/presentation direction.

Implementation is not authorized to weaken evidence/authority gates, fabricate acceptance probability, turn Owner Intelligence into universal Value, use broad exact Simulation for discovery, or relabel unevaluated Search rows as worth-attention opportunities.

Repeat physical-iPhone acceptance is required before Market North Star can be closed.


## Bounded implementation outcome — 2026-09-25
Management-authorized implementation is complete on PR #220 and implementation-level acceptance is green.

Durable implementation evidence:
- `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`

Accepted implementation now includes:
- OpportunityHypothesis → MarketOpportunity → CandidatePath runtime contracts;
- target-family-first Search admission before candidate truncation;
- cheap Decision-owned economic screening before family pruning;
- bounded family-first eight-path pre-Simulation bilateral screening;
- package-family clustering and deterministic categorical diversity/ranking;
- For You `worth_attention` gating with no raw-row quota fill;
- explicit Trade Finder intent grouping;
- descriptive-only Owner Intelligence;
- zero broad changed-state Simulation;
- Core 7/7 versus Market-surface readiness;
- partial Player Board delivery while optional Intrinsic builds;
- Opportunity-first / Candidate-Path drilldown North Star presentation;
- hosted static generation `20260925-market-discovery1`;
- deterministic Gibbs, extreme-economic, dominance, readiness, ranking, observability, and Simulation-boundary coverage.

Implementation-level automated acceptance is satisfied. Market North Star product acceptance is **not closed** until the merged/deployed build passes repeat physical-iPhone/Safari validation.


## Physical iPhone acceptance failure — 2026-09-25

**State: ACCEPTANCE FAILED — BOUNDED CORRECTIVE IMPLEMENTATION AUTHORIZED**

Management physically tested the deployed Market implementation on iPhone/Safari after the existing FSFFL league returned to a visible 7/7 state. The Market architecture remains accepted; this is a bounded corrective pass, not authorization to redesign the accepted architecture or lower evidence standards.

Observed acceptance evidence:
- Core readiness displayed 7/7 with “last-good intelligence retained.”
- For You displayed **0 worth-attention opportunities**. Zero is permissible if no opportunity clears the governed bar; do not manufacture recommendations. However, this must be reconciled with the incomplete downstream screening state below.
- Trade Finder displayed 26 candidate paths, while visible paths were uniformly `incomplete · incomplete` / `Needs preliminary screen`.
- Changing intent among Target a position, Explore an owner/team, and Shop a player appeared to preserve substantially the same ordered RB result neighborhood. Trace whether intent is actually constraining/reranking discovery and fix any defect; do not tune outputs to these screenshots.
- In Explore owner/team with `Anthonyder` selected, visible results included assets owned by other teams. Determine whether that is contractually intended; if not, correct intent semantics.
- Player Board rendered, but its Player identity column is far too wide on mobile and pushes comparison/value columns off-screen. This is a presentation defect, not evidence that those columns are absent.
- Player Board must use a compact frozen/anchored Player identity column, horizontal scrolling for remaining quantitative columns, and interactive sortable applicable quantitative headers with clear ascending/descending state. Preserve Broad Market and FSFFL Intrinsic as separate governed dimensions; never blend them to solve layout.
- Free Agents rendered candidates, but all visible examples showed PPG and 17-game Forecast as Unavailable despite Core 7/7. Trace whether this is truthful per-player evidence absence or a consumer/readiness wiring defect. Do not fabricate missing Forecast.
- iPhone safe-area/status-bar overlap remains visible on Market headings/navigation in multiple tabs and fails physical mobile acceptance.

Corrective objective:
1. Trace the deployed data path for For You and the 26 Trade Finder Candidate Paths through Search → cheap economics → bounded Decision preliminary screen → Market presentation. Explain why paths remain preliminary/incomplete and correct implementation defects.
2. Verify each Trade Finder intent materially applies its accepted semantic constraints/ranking. Add deterministic tests for intent-specific behavior rather than screenshot-specific outputs.
3. Reconcile Core 7/7 with Market-surface readiness and consumer evidence. Player Board and Free Agents may partially render, but unavailable fields must be truthful and the reason must be governed/observable.
4. Correct Player Board mobile table composition: compact anchored identity column, reachable comparison columns, horizontal scroll, and sortable quantitative columns.
5. Correct Market safe-area/status-bar handling on physical-iPhone/Safari without redesigning accepted surfaces.
6. Preserve the accepted For You evidence bar. Zero For You opportunities is valid when genuinely earned; never quota-fill or relabel unscreened Search output.
7. Preserve zero broad changed-state Simulation, authority boundaries, no fake acceptance probability, and all accepted architecture constraints.
8. Run focused regressions plus relevant Market/Home/Franchise/League and authority tests; merge/deploy only when warranted.
9. Persist meaningful checkpoints in this workstream file and canonical operations state as execution advances.
10. Return to Management for another physical-iPhone acceptance only after all non-physical validation has been exhausted.

Required terminal behavior: follow `OPERATING_PROTOCOL.md`. A commit, PR, green CI, or deploy is not completion. Stop only at a permitted terminal state, and immediately before returning ask whether another authorized action can advance this corrective directive; if yes, perform it.


## Management clarification — opportunity discovery quality + compute discipline — 2026-09-25

This clarification is part of the currently authorized corrective acceptance work. It does **not** reopen the accepted Market architecture. It makes explicit what Implementation must prove about the discovery engine.

### Product objective
Market is not an equal-value trade generator. Broad Market / FSFFL Intrinsic equivalence is useful evidence for acquisition-cost and economic sanity, but approximate value equality alone does not constitute a real opportunity and must not be the primary discovery objective.

The discovery engine should cheaply identify transactions or acquisition neighborhoods that have a governed strategic reason to exist for the actual franchises involved, then spend expensive compute only when the user chooses to investigate more deeply.

### Required cheap-to-expensive funnel
Implementation must preserve and demonstrate this ordering:

`League/roster state → actionable need/surplus/opportunity hypotheses → complementary counterparties → candidate assets → economically plausible package families → cheap bilateral Decision screen → dominance/dedup/diversity → small opportunity frontier → user-selected deep Decision/Simulation`

Simulation remains the microscope, not the searchlight.

### Initial discovery acceptance
- Trace candidate admission at the earliest Search stage for every Trade Finder intent.
- Intent and its selected parameters must influence candidate discovery itself where semantically appropriate, not merely filter or rerank a generic post-generated universe.
- For **Improve my team**, begin from governed franchise diagnosis / actionable opportunity hypotheses, not generic player rankings or nearest-value assets.
- For **Target a player**, discovery should identify plausible counterparties/package ingredients around that target.
- For **Shop a player**, discovery should use the outgoing asset plus actual roster consequences/counterparty complementarity, not simply return generic similarly valued players.
- For **Target a position**, the target position must materially govern candidate admission.
- For **Explore an owner/team**, the selected counterparty must materially govern the relevant discovery neighborhood.
- Legitimate overlap between intents is allowed when upstream evidence supports it; do not manufacture difference for test satisfaction. Overlap must be explainable.

Add deterministic fixtures proving materially different intents/parameters produce appropriately different early candidate neighborhoods before package generation.

### Readily available evidence first
Use already-governed inexpensive evidence wherever available before invoking expensive evaluation, including:
- roster construction, starters, depth and fragility;
- positional strength / replacement exposure;
- current governed Forecast outputs;
- Broad Market and FSFFL Intrinsic where covered, kept separate;
- draft-pick holdings and roster constraints;
- competitive/team state already governed by upstream authorities;
- counterparty holdings, needs and surpluses derived from governed team evidence;
- descriptive Owner Intelligence only where its existing authority permits it.

Do not create a hidden composite/master score. Do not duplicate upstream authority inside Search.

### Economic evidence is a screen, not the opportunity definition
Market/Intrinsic values may:
- reject absurd economic neighborhoods;
- estimate acquisition-cost bands;
- identify meaningful disagreement;
- help construct plausible package families;
- support cheap dominance comparisons.

They must not reduce discovery to “find two sides whose values are approximately equal.” A balanced package with no strategic bilateral rationale should not become a high-signal opportunity merely because its generic values match.

### Cheap bilateral opportunity screen
Before a path can consume scarce attention, cheaply determine from existing governed evidence whether:
- it addresses a real user need/opportunity;
- the counterparty has a coherent roster/economic reason to engage;
- roster constraints, replacement effects and mandatory cut costs are represented where applicable;
- economics are within a plausible neighborhood without demanding artificial equality;
- the path is not obviously dominated for either side by another generated construction;
- it adds a materially distinct opportunity rather than duplicating an existing family.

This preliminary screen is not final Decision authority and must not fabricate acceptance probability.

### Compute budget / observability acceptance
Instrument the discovery funnel so Management can inspect, for a representative request:
- candidate counts entering/exiting each major stage;
- rejection reason counts;
- number of preliminary Decision screens;
- exact changed-state Simulation call count;
- wall-clock timing for major stages;
- cache/reuse behavior where relevant.

The existing bounded eight-path pre-Simulation Decision budget remains product policy unless a separately justified change is brought to Management. Broad discovery must continue to make **zero exact changed-state Simulation calls**.

Optimize by pruning cheaply and early rather than weakening evidence. Expensive Simulation/deep Decision belongs after the user selects a promising transaction/path, except for any separately governed bounded escalation already authorized by the accepted architecture.

### Acceptance question
Implementation is not accepted merely because it can generate economically similar packages quickly. It must demonstrate that FSFFL can surface a small, diverse set of **strategically grounded, bilaterally coherent, economically plausible** opportunities using inexpensive governed evidence first, with deep compute reserved for investigation after selection.


## Corrective execution checkpoint — discovery quality + compute discipline — 2026-09-25

**State: ACTIVE — PR #232 VALIDATION.**

Implementation resumed from the existing corrective branch after Management's discovery-quality clarification. Completed corrective work at branch head `756bbd598dbc1907de4454db6e3065eb81bc7acd` includes:

- restored the approved eight-path bounded pre-Simulation Decision budget; the temporary two-path compute-policy reduction was reverted because Management did not authorize that policy change;
- automatic Improve-my-team discovery now admits neighborhoods from existing governed positional weakness / fragility evidence and complementary counterparty strength/need evidence **before** package construction;
- Target a position, Target a player, Shop a player, Explore an owner/team, and Consolidate now constrain candidate admission before package generation where semantically appropriate; an exact user-selected target may override the automatic focal-need gate;
- Cardinal / market evidence is used to bound acquisition-cost neighborhoods after strategic admission rather than defining an opportunity through approximate value equality;
- focused Trade Finder requests now obtain Search-only base context and reserve the approved eight preliminary Decision screens for the selected intent neighborhood instead of first spending Decision work on a generic workspace;
- Market preliminary screening no longer calls the full Trade Center roster-consequence analysis. A Decision-owned lightweight pre-Simulation screen consumes existing baseline optimized lineups, changed-roster legality, mandatory-cut economics, optimized starter replacement effects, and optional descriptive owner history. Full Trade Center Decision and exact 50,000-run Simulation remain downstream of user-selected investigation;
- broad Market discovery continues to make zero exact changed-state Simulation calls;
- funnel diagnostics now expose pre-package counterparty/target/asset admission counts, rejection reason counts, package/economic/family/preliminary-screen/aggregation timings, preliminary Decision screen count, and Search/workspace cache behavior; Render logs emit a compact representative funnel line;
- the earlier physical-iPhone corrective work remains on the same PR: all-player governed Forecast consumption and coverage truth for Player Board / Free Agents, compact anchored Player identity, horizontal quantitative scrolling, sortable quantitative headers, safe-area correction, intent response race guards, and screened-path-first presentation.

Production evidence motivating the lightweight screen remains the 2026-09-25 Render trace in which full pre-Simulation trade analysis spent approximately 16–114 seconds per path in roster-consequence Decision work while package economics was approximately 0.1 seconds. The corrective implementation preserves the eight-path policy by changing the broad screening primitive and pruning earlier, not by weakening the approved evidence budget.

Validation is in progress on PR #232. The first clarified full-CI run found only stale implementation-string/cache-identity assertions; five focused/authority workflows passed. Those tests were updated to assert the new semantic contracts and the replacement full-CI run is active. Merge/deploy and production non-physical validation remain pending. Physical-iPhone/Safari acceptance remains the final Management gate.


### PR #232 merge checkpoint — 2026-09-25

PR #232 merged to canonical `main` at `eac3ac1074b80e4199e4e4f4cd3c708ffffbd02b` after the latest head passed full CI, Home North Star focused validation, Franchise North Star focused validation, League Atlas focused validation, the live Forecast corrective trace, and the focused regression suite.

The merged implementation preserves the Management-approved eight-path preliminary Decision budget and the zero-broad-Simulation boundary. It moves strategic need/counterparty admission ahead of package construction, reserves focused Decision spend for the selected intent neighborhood, replaces the full Trade Center roster-consequence call in broad screening with the lightweight Decision-owned preliminary screen, and emits stage/count/cache diagnostics for production validation.

Render production deployment and non-physical production funnel validation are the remaining implementation actions before the physical-iPhone/Safari Management acceptance gate. Do not mark Market accepted from merge/CI alone.


### PR #232 deployed corrective checkpoint — 2026-09-25

**State: MANAGEMENT GATE — REPEAT PHYSICAL IPHONE / SAFARI ACCEPTANCE.**

The bounded corrective implementation is merged and deployed:
- PR #232 merge commit: `eac3ac1074b80e4199e4e4f4cd3c708ffffbd02b`;
- canonical deployed main at corrective deployment time: `33657f9f612fad2cbc4d112531e0912e04140762`;
- Render deploy: `dep-dar9cdrtqb8s73819ap0` — **LIVE**;
- hosted static generation: `20260925-market-corrective1`.

Non-physical validation is exhausted:
- PR #232 head `02c0d0be5b83491fca22703f02d9f22bd302657b` passed full CI, Home North Star, Franchise North Star, League Atlas North Star, PR164 corrective regression, and the live Forecast corrective trace;
- the deployed process restored `jimmy` / Sleeper league `1312071960615731200` on promoted state `203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed` with Forecast=True, Simulation=True, Value=True, complete=True;
- application startup completed successfully and no post-deploy error logs are present;
- the merged static bundle exposes the corrective safe-area, compact sticky Player column, horizontal quantitative Board scrolling, sortable Board headers, all-player Forecast consumption, focused-intent response guards, and screened-path-first presentation;
- deterministic tests prove early strategic/counterparty admission, intent-specific pre-package discovery, the approved eight-path preliminary Decision budget, lightweight pre-Simulation screening, cache observability, and zero broad changed-state Simulation.

Production funnel diagnostics are instrumented and will emit on the next authenticated Market request. No authenticated Market request has occurred on the new instance yet; an unauthenticated external probe correctly returned HTTP 401. There is no safe non-physical mechanism available to impersonate the Management session, so production request-level funnel timing/cache telemetry must be observed from the next real authenticated Market interaction rather than fabricated.

No further implementation action is authorized or warranted before repeat physical-iPhone/Safari validation. The device test should exercise all four Market surfaces and at least one explicit Trade Finder intent so the new production funnel telemetry can be inspected afterward.


## Physical iPhone acceptance — current-beta corrective directive — 2026-09-25

**State: ACCEPTANCE FAILED — BOUNDED CORRECTIVE IMPLEMENTATION AUTHORIZED.**

Management completed a current-beta physical-iPhone/Safari Market acceptance pass after PR #232 and the live PR #235 Performance optimization. Earlier screenshots from a prior beta are explicitly excluded from this acceptance evidence. Current production request telemetry generated by this pass is valid.

### What is accepted and must not regress
The accepted Market architecture remains intact. Current production evidence demonstrates that automatic discovery can explore a broad candidate universe, spend the bounded eight preliminary Decision screens, surface a small opportunity set, and make zero broad exact changed-state Simulation calls. Do not redesign the architecture or weaken its evidence bar.

Preserve:
- strategic/intent-driven admission before package construction;
- cheap governed Search/economic evidence before expensive evaluation;
- the eight-path preliminary Decision budget;
- zero broad changed-state Simulation;
- dominance/dedup/diversity;
- For You worth-attention standards;
- Forecast/Value/Decision/Owner Intelligence authority boundaries;
- truthful zero-result behavior.

### Acceptance failure 1 — competitive lens
Physical testing showed that changing the competitive lens between Contend / Win now and Rebuild did not change the visible options presented.

Trace the competitive lens end-to-end from submitted request through strategic hypothesis, early Search admission, candidate neighborhood, package families, preliminary Decision screening, aggregation/order and Presentation. The lens must materially govern discovery where upstream evidence warrants a difference; it must not be decorative or only a post-generation filter/reranker.

Do not manufacture differences solely for test satisfaction. Add deterministic fixtures proving that materially different competitive lenses can create appropriately different early candidate neighborhoods, and make legitimate overlap explainable from governed evidence.

### Acceptance failure 2 — explicit search lifecycle
The current Trade Finder silently launches/replaces work as controls are changed. Physical testing provides no clear acknowledgement that a new search is taking place, which is especially unacceptable while focused discovery remains expensive.

Implement an explicit configuration → submission lifecycle:
- changing intent, competitive lens, target player, shop player, target position, or owner/team configures the request and marks prior results stale;
- do not launch expensive focused discovery merely because a selector changed;
- provide a clear primary action such as **Find opportunities**;
- after submission, visibly acknowledge that discovery is running;
- do not fabricate percentage progress;
- stale prior results must not masquerade as results for the newly configured request;
- completion and genuine zero-result states must be visibly associated with the submitted criteria;
- guard against response races / older requests overwriting newer submitted searches.

### Acceptance failure 3 — focused zero-result semantics and search exhaustion
Current physical testing produced genuine visible zero-result states for materially different requests, including:
- Target position: WR;
- Shop player: Jonathon Brooks;
- Explore owner/team: chuckthegoat77.

Zero results are allowed and must not cause standards to be lowered. However, implementation must determine whether each zero means:
1. the appropriate requested neighborhood was meaningfully explored and no candidate survived; or
2. Search/admission/budget behavior failed to meaningfully explore the requested neighborhood.

Instrument and persist, for focused requests, candidate/counterparty/asset admission, package-family generation, cheap economic rejection, preliminary-screen selection and rejection, dominance/dedup, and final path counts/reasons. The eight-screen budget bounds expensive preliminary Decision work; it must not arbitrarily restrict cheap Search exploration.

Presentation should give a concise truthful reason when a submitted focused search returns zero rather than an unexplained empty state.

### Acceptance failure 4 — Forecast / FSFFL Intrinsic availability
Physical testing shows governed Forecast evidence is available in parts of the product (Player Intelligence and covered Free Agents), while Market surfaces still expose unavailable intelligence, especially FSFFL Intrinsic on Player Board / related Value coverage.

Trace Forecast and Intrinsic separately end-to-end for representative players visible in the physical test, including a player whose Player Intelligence has governed Forecast evidence. Determine whether each unavailable state is caused by:
- legitimately missing upstream evidence;
- coverage/authority gate;
- stale or incompatible state identity;
- Value build/promotion state;
- consumer/readiness wiring;
- or Presentation behavior.

Do not infer that Forecast availability automatically entitles Intrinsic authority. Conversely, do not present generic “Unavailable” when governed evidence exists but the Market consumer failed to consume it. Where unavailability is legitimate, expose the actual missing prerequisite/reason in a bounded user-facing way.

### Production performance evidence from this physical pass
The authenticated current-beta pass produced direct post-PR-#235 telemetry:
- automatic Improve-my-team discovery: 80 rows, 10/11 counterparties, 73/224 targets, 8 preliminary screens, 3 opportunities, 1 For You opportunity, 0 Simulation calls, total approximately **44.1s**; hosted full workspace approximately **44.9s**;
- immediate cached full workspace approximately **0.137s**;
- focused Target Player requests observed at approximately **31.8s**, **41.4s**, and **47.8s**, each with one preliminary screen and zero Simulation calls.

Therefore PR #235 preserved the Market discovery contract but did **not** satisfy the cold/focused foreground-responsiveness gate. Market implementation should preserve this evidence in its diagnostics. Performance owns general cold-path optimization; Market may remove Market-owned redundant work where doing so does not alter discovery semantics. Do not solve latency by weakening admission, evidence, the eight-path policy, diversity/dominance, or authority boundaries.

### Mobile / presentation
Retain the improvements already achieved in Free Agents Forecast coverage, Player Board compact identity/horizontal quantitative layout/sorting, and Player Intelligence handoff. Correct remaining physical-iPhone safe-area/status-bar crowding where still reproducible, but do not let cosmetic work displace the functional acceptance failures above.

### Required closeout
Execute the bounded corrective pass under OPERATING_PROTOCOL.md. Exhaust nonphysical tracing, deterministic tests, regression tests, CI, deployment and production validation before asking Management for another physical-device pass. Persist exact findings, fixes, telemetry, limitations and any genuine Management gate in this workstream file and the applicable canonical operations state. Do not return merely at diagnosis, commit, PR, merge or deploy.
