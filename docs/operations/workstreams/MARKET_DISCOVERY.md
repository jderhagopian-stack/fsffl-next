# Workstream — Market / Trade Discovery Architecture Review

## State
**MANAGEMENT GATE — ARCHITECTURE REVIEW COMPLETE**

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
