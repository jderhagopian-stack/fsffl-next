# FSFFL NEXT — Market / Trade Discovery Architecture Handoff

Date: 2026-09-24  
Workstream: Market / Trade Discovery Architecture Review  
Scope: architecture and implementation handoff only; no broad Market redesign implemented  
Base inspected: main after PR #216 plus the merged Forecast work present at commit 407c1bf85e5dc75f92b9906719f82bcd11d97c31  
Stop state after persistence: MANAGEMENT GATE

## 1. Executive outcome

The current Market problem is not primarily a styling problem and it is not caused by exact Simulation being overused. The core defect is that the unit of broad discovery is a raw trade package, while the product is presenting those raw package rows as if they were distinct opportunities.

Current Search intentionally generates, for every opposing player target, the nearest one-, two-, and three-asset focal package by additive FSFFL Cardinal value. It then interleaves those package rows across market-fit, premium-target, roster-need, counterparty-fit, and package-complexity lanes. Deduplication removes only exact package identity. The result is mechanically capable of producing several variants of the same target neighborhood, including multiple expensive Superflex paths for one elite target, before package economics, mandatory-cut cost, bilateral consequences, or owner-specific descriptive evidence have been applied.

The first progressive Market payload makes this worse from a product perspective: the quick route explicitly returns Search-only evidence with zero bilateral Decision enrichment. The full workspace normally evaluates only one package. For You then fills its five-card feed from the remaining raw Search order and labels the collection high-signal even when cards still say Needs full evaluation.

The governed fix is to make Opportunity the primary discovery object, Candidate Path the transaction-level implementation of an Opportunity, and raw packages subordinate variants inside a Candidate Path family. A small, bounded pre-Simulation Decision screen should be moved ahead of For You eligibility. Search remains the orchestrator and ranker; Decision remains the authority for package economics, roster-adjusted economics, bilateral consequences, and negotiation-feasibility shapes. Owner Intelligence may add descriptive context but must not become universal Value or an invented acceptance probability. Exact post-trade Simulation remains downstream of a selected candidate path and is never a broad-discovery engine.

The Player Board / Free Agents 7/7 contradiction is a separate readiness-contract defect. The global 7/7 strip currently means the core runtime has State, Forecast, current Simulation, and Value attached. Player Board and Free Agents independently lazy-load an all-player Value-lens contract that may start a separate Shapley Intrinsic background build. That downstream build is not one of the seven core lifecycle phases. The UI currently treats its loading response as a surface-level failure, so a truthful core 7/7 can coexist with a misleading Market still-loading state. The fix is to scope 7/7 explicitly to Core Intelligence and give each Market surface an independent ready/degraded/building/blocked contract with partial rendering.

This handoff is implementation-ready, but Management acceptance is required before broad implementation.

## 2. Governing boundaries

The authority chain remains:

Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation

The architecture below adds no new model authority.

Hard boundaries:

- State owns current league identity, roster ownership, league rules, and asset ownership.
- Forecast owns player and team projection evidence and uncertainty.
- Value owns Broad Market, FSFFL Intrinsic, and the existing FSFFL Cardinal economic coordinate. The concepts remain separate.
- Team Utility owns franchise-specific roster and competitive evidence. It is not universal market Value.
- Decision owns bilateral trade economics, package concentration, bounded package-economics robustness, mandatory-cut economics, roster consequences, materiality, and negotiation-feasibility shape.
- Owner Intelligence owns descriptive observed owner behavior and any separately governed contextual behavioral evidence.
- Search/Optimization may generate, filter, cluster, diversify, and order evidence from upstream authorities. It may not manufacture Value, Forecast, Decision truth, or acceptance odds.
- Simulation owns competitive outcomes. Exact changed-state Simulation is not used to search the broad market.
- Presentation may progressively disclose evidence but may not upgrade a partial path into a recommendation.

No part of this design authorizes a fabricated acceptance probability. Existing acceptance machinery is outside the broad-discovery contract. If a separately governed acceptance estimate exists in the future, it remains Decision evidence and does not become a Market-generated probability.

## 3. Actual current implementation inspected

### Search and Market orchestration

Inspected:
- src/fsffl/product/opportunity_search.py
- src/fsffl/product/focused_opportunity_search.py
- src/fsffl/product/opportunity_workspace.py
- src/fsffl/product/opportunity_posture.py
- src/fsffl/product/opportunity_spotlights.py
- src/fsffl/product/progressive_delivery_routes.py
- src/fsffl/product/opportunity_workspace_cache.py
- src/fsffl/opportunity/frontier.py
- src/fsffl/opportunity/frontier_search.py
- src/fsffl/opportunity/trade_universe.py
- src/fsffl/opportunity/trade_pairs.py
- src/fsffl/opportunity/trade_evaluation.py

### Value

Inspected:
- src/fsffl/product/league_value_lens_routes.py
- src/fsffl/product/league_value_lenses.py
- src/fsffl/product/value_lens_evidence.py
- src/fsffl/value/market.py
- src/fsffl/value/intrinsic.py
- FSFFL Cardinal use through the product/Decision adapters

### Team Utility and Decision

Inspected:
- src/fsffl/team_utility/utility.py
- src/fsffl/team_utility/models.py
- src/fsffl/product/trade_analysis_runtime.py
- src/fsffl/product/trade_opportunity_runtime.py
- src/fsffl/trade_decision/economic_net.py
- src/fsffl/trade_decision/package_concentration.py
- src/fsffl/trade_decision/package_economics.py
- src/fsffl/trade_decision/roster_economics.py
- src/fsffl/trade_decision/materiality.py
- src/fsffl/trade_decision/material_assessment.py
- src/fsffl/trade_decision/policy_catalog.py
- src/fsffl/trade_decision/feasibility.py

### Owner Intelligence

Inspected:
- src/fsffl/product/behavioral_runtime.py
- src/fsffl/trade_decision/behavioral.py
- src/fsffl/trade_decision/behavioral_trade_shape.py
- contextual owner-signal tests and behavioral binding tests

### Simulation and progressive delivery

Inspected:
- src/fsffl/product/simulation_runtime.py and current Simulation use through runtime
- src/fsffl/product/progressive_delivery_routes.py
- src/fsffl/product/static/progressive_delivery.js
- Trade Center progression from quick economics to pre-Simulation analysis to explicit full Simulation

### Market presentation and readiness

Inspected:
- src/fsffl/product/static/north_star_market.js
- src/fsffl/product/static/north_star_market.css
- src/fsffl/product/static/product_shell.js
- src/fsffl/product/intrinsic_background.py
- src/fsffl/product/intelligence_runtime.py
- relevant current tests, including Market North Star, progressive delivery, structural realism, authority boundaries, and readiness truth

## 4. Current pipeline trace

The current default Market path is:

1. Current runtime must have canonical State, managed team, and FSFFL Cardinal Value.
2. Search builds one catalog of the focal team's one-, two-, and three-asset packages.
3. For every opposing player target, Search selects the nearest package by additive Cardinal total at each package size.
4. Each selected row receives:
   - target position;
   - focal current position-strength evidence if current Simulation analytics exist;
   - counterparty receive-position strength evidence if current Simulation analytics exist;
   - additive market gap and search distance;
   - diagnostic-only authority;
   - unknown acceptance and unevaluated materiality markers.
5. Exact-row duplicates are removed.
6. Search interleaves package rows across categorical lanes: market fit, premium target, focal need, counterparty fit, and package complexity.
7. The workspace truncates the package-row list to the candidate limit.
8. The quick Market route returns this list with bilateral_evaluation_limit = 0.
9. The full workspace normally evaluates one row with the existing pre-Simulation Decision analysis.
10. Spotlight selection can identify the closest Search row and the most promising evaluated row. With the default one-row Decision budget, these usually cannot establish breadth.
11. For You asks for up to five rows and, after available spotlights, fills remaining slots directly from the raw Search order.
12. Trade Finder exposes up to 80 path rows and many controls at once.
13. Candidate detail groups other rows with the same received target as acquisition paths.
14. Trade Center is the first place where a user-selected transaction progresses through deeper analysis and exact 50,000-run changed-state Simulation.

This trace confirms that exact Simulation is already downstream. The problem is insufficient governed screening and grouping before the product spends attention.

## 5. Failure-mode diagnosis

### 5.1 Repeated opportunity neighborhoods are generated by design

The current discovery unit is a package row, not an opportunity.

For every target, the system intentionally keeps the closest one-, two-, and three-asset package. A target such as Jahmyr Gibbs therefore has three immediate variants before any other package-neighborhood expansion. Posture ordering can re-admit those same target variants through different categorical lanes.

Exact deduplication keys on counterparty + exact send refs + exact receive ref. It does not deduplicate:
- same target with different send-package sizes;
- same strategic need with different nearby target players;
- same counterparty/target neighborhood with small package substitutions;
- same acquisition idea repeated because it ranks highly in several lanes.

The current multi-lane order diversifies ranking criteria, not opportunity families.

### 5.2 Candidate truncation happens before opportunity-family diversity

The global candidate list is truncated before any semantic opportunity clustering. If one elite target or one strategic neighborhood produces many high-ranked package rows, those rows can consume scarce candidate slots before another strategic path is represented.

### 5.3 Additive Value closeness is being asked to do too much

Search defines market closeness from additive FSFFL Cardinal totals. For multi-asset packages it explicitly does not apply a consolidation premium. That is correct from an authority standpoint because package economics belong to Decision, but it means additive closeness alone is insufficient to qualify a package as attention-worthy.

The existing Decision layer already has materially better evidence:
- bilateral economic net;
- package concentration;
- the bounded one-for-many 0%-15% package-economics robustness guard;
- mandatory-cut market cost;
- roster-adjusted market net;
- pre-Simulation roster consequences;
- bilateral Decision shapes;
- negotiation-feasibility shape.

Those signals are currently applied too late and too sparsely for a high-signal feed.

### 5.4 Quick Market is Search-only but presentation calls the feed high-signal

The quick Market endpoint intentionally has no bilateral Decision enrichment. That is a good latency boundary, but the UI must not upgrade the resulting rows into high-signal opportunities.

The full workspace normally evaluates only one package. For You still fills remaining cards from unevaluated Search rows. Needs full evaluation is an honest package status, but it is not a sufficient reason to spend a For You slot.

### 5.5 Current spotlights do not solve the breadth problem

Most promising evaluated is selected only from evaluated rows. Under the default Decision budget of one, it cannot validate several distinct opportunity families.

The browser also asks for premium_target and position_need spotlight keys that the inspected server spotlight contract does not currently publish. The fallback fill therefore remains important and package-row driven.

### 5.6 Owner evidence is visible but not part of broad bilateral plausibility

Current Market presentation can show owner history coverage, but the automatic Market evaluation path does not pass a counterparty behavior profile into the pre-Simulation Decision analysis. The current bilateral signal is therefore primarily structural/roster evidence.

This is not a reason to invent acceptance odds. The existing Owner Intelligence system already provides descriptive, governed evidence that can be used later in the funnel:
- completed-trade counts and shape history;
- context-controlled consolidation/diversification/balanced shape fit;
- context-controlled position preference evidence where available;
- evidence coverage and confidence.

That evidence must remain descriptive and Decision-adjacent. It must not alter universal Value.

### 5.7 The current For You card is package-first

The card shows a target plus a specific give/get package immediately. The approved product concept requires the opposite order:
- first establish the strategic opportunity and why now;
- then show a small number of candidate paths;
- only then show package variants.

### 5.8 Trade Finder is intent-first in concept but still control-dense

The implementation has good intent modes, but it renders strategic lens, intent value, position, owner, package shape, asset type, status, and sort controls together. This undermines progressive disclosure on mobile.

### 5.9 Readiness semantics are conflated

Global 7/7 currently means:
- Forecast attached;
- current Simulation attached;
- Value attached;
- lifecycle job completed.

It does not include:
- Shapley Intrinsic all-player background completion;
- Player Board all-player Value-lens materialization;
- per-column Forecast coverage for unrostered players;
- Behavioral Intelligence completion;
- a prebuilt Market workspace;
- Trade Decision or exact trade analysis for any transaction.

Player Board / Free Agents call the all-player Value-lens route independently. That route can start or await the separate Shapley Intrinsic background coordinator and return a loading response. The browser treats this as a blocking surface error. Therefore core 7/7 and Market still loading are currently semantically compatible but product-confusing.

## 6. Canonical discovery object model

Implementation should introduce three distinct layers. Names may be adapted to repository conventions, but the contract must remain distinct.

### 6.1 OpportunityHypothesis

An OpportunityHypothesis is a strategic question before a transaction exists.

Required fields:
- hypothesis_id
- league_state_id
- focal_team_id
- objective_family
- need_dimension
- target_archetype or exact target constraint
- calculated_competitive_state
- requested_owner_posture, if any
- strategic_evidence references
- source: automatic_for_you or explicit_trade_finder_intent
- evidence_status
- model/policy versions used for derived classifications

Examples:
- Improve RB starter quality while contending.
- Consolidate excess WR depth into a premium starter.
- Reallocate current value toward younger assets while retooling.
- Acquire a named player selected by the user.
- Explore one named owner/team.

This object contains no package and no acceptance claim.

### 6.2 MarketOpportunity

A MarketOpportunity is a screened strategic path that may contain several acquisition paths.

Required fields:
- opportunity_id
- hypothesis_id
- league_state_id
- focal_team_id
- objective_family
- need_dimension
- target_family
- why_now evidence
- strategic_relevance classification
- preliminary_economic_band
- bilateral_plausibility classification
- evidence_completeness
- attention_status
- opportunity_family_key
- representative_path_ids
- alternate_path_count
- top risks
- authority manifest
- freshness coordinates

Opportunity-family key:

focal team + strategic objective + need dimension + target family

Target family rules:
- explicit named-player intent: exact player;
- open position upgrade: governed archetype/role bucket, not a raw package;
- owner exploration: owner + strategic objective;
- consolidation/retool paths: objective + destination archetype;
- free agents use their own acquisition type and do not masquerade as trade opportunities.

Counterparty is not generally part of the Opportunity identity. It belongs to Candidate Path. This allows multiple owners/targets to implement one strategic thesis without producing multiple For You cards for the same idea.

### 6.3 CandidatePath

A CandidatePath is one concrete acquisition route inside an Opportunity.

Required fields:
- path_id
- opportunity_id
- counterparty_team_id
- receive_asset_refs
- package_family_key
- representative_package
- alternate_package_ids
- structural_status
- economic_screen
- roster_legality/cut status
- bilateral_decision status
- negotiation_feasibility shape
- owner_context status/evidence, when available
- deep_evaluation_status
- authority manifest
- evidence completeness and missing evidence

Package-family key:

opportunity + counterparty + canonical receive set

All one-, two-, and three-asset send variants for the same target/counterparty begin in the same package family. They are variants, not separate opportunities.

## 7. Stage-by-stage governed funnel

### Stage 0 — Surface readiness and current context

Authorities consumed:
- State
- current Forecast readiness
- current Value readiness
- current attached Simulation/Team Utility evidence if already available

Output:
- MarketSurfaceReadiness
- no candidate generation if required context is absent

Rules:
- do not launch exact changed-state Simulation;
- current baseline Simulation may be consumed because it is already authoritative current-state evidence;
- a missing optional lens must degrade a surface, not fabricate a substitute.

### Stage 1 — Strategic hypothesis generation

Owner:
- Search/Optimization consuming Team Utility/current analytics

Inputs:
- current roster;
- optimized lineup/position strength where available;
- calculated competitive state from current Simulation;
- explicit owner posture as a Search lens;
- explicit Trade Finder intent when supplied.

Output:
- bounded OpportunityHypothesis collection.

Rules:
- For You requires an evidence-backed strategic hypothesis.
- Trade Finder may create a hypothesis directly from explicit user intent even if automatic strategic evidence is incomplete.
- Owner posture does not rewrite calculated competitive state.
- Market-vs-Intrinsic disagreement may nominate a target hypothesis, but it is only one discovery lens.

### Stage 2 — Candidate assets and counterparties

Owner:
- Search

Inputs:
- hypothesis;
- State ownership;
- Value availability;
- current roster/position context.

Output:
- target/counterparty candidates, before package construction.

Rules:
- diversify target candidates before package expansion;
- do not let one named target consume the global target budget;
- missing Value stays unavailable rather than becoming zero.

### Stage 3 — Bounded raw package generation

Owner:
- Search

Inputs:
- target/counterparty pair;
- owned focal assets;
- Cardinal economic coordinate.

Output:
- raw package variants.

Compute policy:
- support current one-, two-, and three-asset package sizes;
- retain a bounded neighborhood of up to three closest packages per size rather than only one, so a single additive nearest match does not become the only path before Decision screening;
- package-neighborhood count is a product compute policy, not model authority;
- exact package identity is deduplicated here.

Raw packages are not user-facing For You objects.

### Stage 4 — Cheap Decision economic screen

Owner:
- Decision, exposed through a dedicated preliminary-screen adapter.

Reuse existing governed primitives:
- summarize_bilateral_trade_economics
- calculate_bilateral_economic_net
- summarize_package_concentration
- assess_package_economics
- live_bounded_package_premium_prior
- live_bounded_materiality_policy economic coordinate

Output per raw package:
- economic evidence completeness;
- focal market materiality;
- counterparty market materiality;
- one-for-many package-economics resolution;
- economic-risk flags;
- no recommendation;
- no acceptance probability.

Canonical economic bands:
- robust_or_ordinary: complete evidence with no package guard concern requiring offsetting evidence;
- bounded_uncertainty: within the governed provisional one-for-many band;
- focal_economic_strain: focal side incurs a material market loss or clears the upper package bound while buying the singleton;
- counterparty_economic_strain: counterparty side is materially disadvantaged or the singleton is underpaid;
- incomplete: required economic evidence missing.

Search may consume these categories. Search must not recalculate them.

A strain classification is not automatically a final rejection because roster/strategic utility may offset market economics. It does, however, prevent automatic For You eligibility until the next bilateral stage supplies countervailing governed evidence.

### Stage 5 — Family-level pruning before heavier bilateral work

Owner:
- Search

Actions:
- group all raw packages by package_family_key;
- remove exact duplicates;
- remove packages strictly dominated inside the same family;
- preserve materially different package shapes or economic bands;
- choose one preliminary representative per family before a second representative is admitted.

Dominance within one package family is a Search ordering rule over upstream evidence:
A may dominate B only when A is no worse than B on every available governed dimension used for the family and strictly better on at least one, with no contradictory missing-evidence advantage.

Permitted dimensions:
- economic-risk class;
- focal package materiality;
- counterparty package materiality;
- package-economics robustness;
- asset count/complexity as a product cost;
- additive market distance only as a final tie-breaker.

Search may not declare a package dominated because of a made-up utility score.

### Stage 6 — Bounded pre-Simulation bilateral screen

Owner:
- Decision.

Purpose:
establish whether a representative path is plausibly bilateral before For You attention is spent.

Reuse the existing pre-Simulation trade-analysis path:
- apply the bilateral State change;
- resolve mandatory cuts;
- charge cut opportunity cost exactly once;
- optimize lineups using current Forecast evidence;
- assemble roster-resilience Team Utility;
- classify bilateral Decision shape;
- assess negotiation feasibility with acceptance = None;
- preserve package economics and economic net.

Do not run exact changed-state Simulation.

Default product compute budget:
- eight representative Candidate Paths per Market workspace;
- round-robin one path per distinct Opportunity family before a second path from any family;
- cache exact results by current State/evidence/path identity;
- this budget is tunable after performance benchmarks without changing analytical semantics.

The value eight is a bounded private-beta compute policy intended to support a maximum four-card For You feed with more than one tested strategic family. It is not an analytical coefficient.

Preliminary bilateral outcome:
- bilateral_supported: complete enough evidence and feasibility is mutual_gain_candidate, mixed, or neutral; focal is not a governed uniform-loss path;
- bilateral_friction: evidence is complete enough but important economic/roster strain remains;
- counterparty_dominated: existing Decision feasibility shape;
- focal_dominated: focal Decision evidence is uniformly adverse;
- incomplete: critical bilateral evidence is missing.

Counterparty_dominated, focal_dominated, and incomplete paths are not For You eligible. They may remain discoverable under explicit Trade Finder intent with clear status and without recommendation language.

### Stage 7 — Optional Owner Intelligence context

Owner:
- Owner Intelligence / Decision binding.

Apply only to the bounded surviving path set.

Permitted evidence:
- observed completed-trade history;
- context-controlled trade-shape fit;
- context-controlled position/acquisition preferences when governed and point-in-time valid;
- evidence coverage/confidence.

Output:
- descriptive owner context attached beside bilateral feasibility.

Rules:
- no numeric acceptance probability is generated by Market;
- no owner evidence changes Broad Market or FSFFL Intrinsic;
- no owner evidence is multiplied into Team Utility;
- owner context may break ties among otherwise similar surviving paths and may explain friction/support;
- missing owner evidence never becomes negative evidence.

### Stage 8 — Opportunity aggregation and attention gate

Owner:
- Search, consuming upstream classifications.

Candidate Paths are aggregated into MarketOpportunity objects.

For You eligibility requires:
- current State and managed team;
- evidence-backed automatic strategic hypothesis;
- complete Cardinal economics for at least one representative path;
- no unresolved mandatory-cut Value needed to interpret that representative path;
- no counterparty_dominated or focal_dominated preliminary Decision result;
- no critical incomplete bilateral evidence on the representative path;
- at least one path that survives the economic and bilateral screen;
- evidence coordinates current for the same State.

Owner Intelligence is optional for eligibility.

Exact changed-state Simulation is not required.

### Stage 9 — Opportunity ranking and diversity selection

Owner:
- Search.

Do not create a synthetic opportunity score.

Use a deterministic lexicographic policy over categorical evidence:

1. attention eligibility;
2. strategic relevance class;
3. bilateral plausibility class;
4. economic robustness class;
5. evidence completeness;
6. current Search market distance only as final deterministic tie-breaker.

Then apply a separate diversity selector.

For You private-beta product policy:
- maximum four Opportunity cards;
- never more than one card for the same opportunity_family_key;
- never more than one card for the same exact named target;
- maximum two cards sharing the same primary need dimension;
- maximum two cards led by the same counterparty;
- first pass admits only candidates satisfying all caps;
- if fewer than three eligible opportunities exist, counterparty and then need-dimension caps may relax in that order;
- exact target duplication never relaxes;
- any relaxation is recorded in diagnostics.

These are presentation/search diversity rules, not model claims.

### Stage 10 — Targeted deepening

Opportunity Detail:
- may load more Candidate Paths for that one Opportunity;
- may run the pre-Simulation Decision screen for an additional path if not already cached;
- does not automatically run exact Simulation.

Candidate Path Detail:
- shows the representative package and at most one materially distinct alternate package initially;
- explains economics, strategic fit, bilateral rationale, owner context, missing evidence, and risks;
- handoff is a specific proposal to Trade Center.

Trade Center:
- receives the exact candidate proposal;
- uses the existing quick Decision economics;
- performs full pre-Simulation bilateral analysis;
- exact 50,000-run changed-state Simulation occurs only after this explicit transaction-level evaluation workflow is invoked;
- cached exact Simulation may be reused for the identical changed State/evidence coordinate.

## 8. Canonical Market statuses

### Opportunity attention_status

worth_attention
- qualifies for For You;
- means the strategic Opportunity has at least one governed preliminarily plausible path;
- does not mean the trade is recommended or accepted.

explorable
- strategically relevant or explicitly requested;
- preliminary evidence is incomplete or mixed enough that it should live in Trade Finder / Opportunity Detail, not For You.

market_match_only
- structurally/economically discoverable, but the system lacks enough strategic/bilateral support to call it worth attention.

suppressed
- dominated, duplicate, counterparty-dominated, focal-dominated, stale, or critically incomplete for the current default experience.

### Candidate Path deep_evaluation_status

prelim_screened
- passed pre-Simulation Decision screen.

needs_deep_evaluation
- viable enough to inspect, but competitive outcome/materiality remains unresolved.

deep_evaluated
- Trade Center Decision/Simulation evidence exists for the exact path and current coordinate.

not_warranted
- path was removed or dominated before deep evaluation.

## 9. For You contract

Consumer question:
What are the few strategic paths actually worth my attention right now, and why?

For You renders only MarketOpportunity objects with worth_attention.

Card composition:
- strategic objective;
- why now;
- target family / example target;
- concise expected-benefit signals available before Simulation;
- cost/risk band;
- number of preliminarily plausible acquisition paths;
- evidence-status indicator;
- Open Opportunity.

Do not show a full give/get package on the first card.

Do not label unevaluated package rows high-signal.

Do not use Recommended unless a separate downstream Decision authority for an exact transaction explicitly warrants that term. The discovery-level label should be Worth attention.

If zero opportunities qualify, say so and direct the user to Trade Finder / Player Board. Do not fill the feed with lower-authority rows merely to reach a visual quota.

## 10. Opportunity Detail contract

Consumer question:
Why does this strategic opportunity exist, and what realistic ways could I pursue it?

Initial content:
- strategic hypothesis;
- current roster/competitive evidence;
- why now;
- benefit signals;
- cost/risk band;
- evidence completeness;
- up to three distinct Candidate Paths;
- each path names target/counterparty and a compact plausibility status;
- packages remain secondary.

Path selection opens Candidate Path Detail.

A named-target opportunity such as Jahmyr Gibbs appears once here, with its materially distinct acquisition paths nested beneath it. One-, two-, and three-asset offers do not become three top-level opportunities.

## 11. Candidate Path Detail contract

Consumer question:
Why did this particular route survive preliminary screening, and what would I actually be giving up?

Content:
- exact target/counterparty;
- one representative package;
- at most one alternate package initially;
- market-economic evidence;
- package-economics guard result where applicable;
- mandatory-cut cost if required;
- focal roster/lineup effect;
- counterparty roster/lineup rationale;
- negotiation-feasibility shape;
- optional owner behavioral context with coverage;
- explicit missing evidence;
- why exact Simulation has or has not been run;
- Evaluate in Trade Center.

This screen must distinguish preliminary plausibility from final Decision.

## 12. Trade Finder contract

Consumer question:
What am I trying to do, and what governed paths fit that intent?

Top-level intents:
- Improve my team
- Target a player
- Shop a player
- Target a position
- Explore an owner/team

The selected intent determines visible primary controls.

Primary controls by intent:

Improve my team
- strategic lens;
- optional position;
- advanced filters collapsed.

Target a player
- player;
- strategic lens;
- advanced filters collapsed.

Shop a player
- player to move;
- strategic lens;
- optional desired position/archetype;
- advanced filters collapsed.

Target a position
- position;
- strategic lens;
- advanced filters collapsed.

Explore owner/team
- owner/team;
- strategic lens;
- optional position;
- advanced filters collapsed.

Advanced controls may expose package shape, asset types, evidence status, and ordering when requested.

Results should be Opportunity groups first, Candidate Paths second. A group can expand to show package variants.

Trade Finder may show market_match_only and explorable items because the user has expressed intent. It must clearly distinguish them from worth_attention.

## 13. Player Board contract

Consumer question:
What does the player market look like, and where do Broad Market and FSFFL Intrinsic disagree?

Rules:
- read-only;
- separate Broad Market and Intrinsic lenses;
- no blended score;
- no Team Utility disguised as player Value;
- no Search/Decision launch merely to render the board;
- rows link to Player Intelligence;
- contextual actions may enter Trade Finder with a named player/owner.

Initial mobile columns:
- Player;
- Broad Market;
- Intrinsic;
- compact trend/disagreement indicator if both are ready.

Secondary columns are progressively disclosed:
- age;
- fantasy owner;
- position/NFL team;
- projection/PPG where Forecast evidence exists;
- presentation-only ranks.

Presentation ranks must be labeled as presentation ordering, not new Value authority.

Market-vs-Intrinsic disagreement belongs here as a discovery lens. It should not be repeated as required chrome on every Market surface.

## 14. Free Agents contract

Consumer question:
Who can improve my roster without a trade?

Rules:
- derive availability from canonical State;
- use governed Forecast/role evidence for roster-fit discovery when available;
- Value is contextual, not a waiver recommendation;
- no waiver priority or FAAB price is invented;
- no exact add/drop Simulation on list render;
- explicit Evaluate add/drop opens the existing governed add/drop workflow.

Initial card:
- player;
- position/team;
- projected role/points if governed;
- simple roster-fit reason from current need evidence;
- Market/Intrinsic only when useful;
- Evaluate add/drop.

If Forecast is missing, the surface may still show available players but must say roster-fit ranking is unavailable. Do not call the entire surface failed when only an optional lens is loading.

## 15. Truthful readiness contract

### 15.1 Core Intelligence readiness

The existing 7/7 strip must be scoped to what it actually proves.

Recommended copy:
Core intelligence current — 7/7

It means the promoted core bundle for the active league has completed the governed lifecycle it tracks. It does not mean every optional downstream artifact has already materialized.

Do not expand the seven phases merely to include every lazy product artifact. Instead separate global lifecycle readiness from consumer readiness.

### 15.2 MarketSurfaceReadiness

Each Market tab publishes:
- status: ready | degraded | building_optional | blocked
- required_dependencies
- optional_dependencies
- blockers
- missing_optional
- league_state_id
- evidence coordinates
- retry hint when applicable

For You required:
- State;
- managed team;
- Cardinal economic evidence;
- enough current Team Utility/baseline strategic evidence to form automatic hypotheses;
- bounded preliminary Decision screen for any item shown.

Trade Finder required:
- State;
- managed team;
- Cardinal Value.
Current Team Utility improves context but explicit user intent permits degraded operation when it is unavailable.

Player Board required:
- State;
- at least one governed Value lens sufficient to render player rows.
Intrinsic is optional to basic rendering and may be building.

Free Agents required:
- State and roster ownership to establish availability.
Forecast is required for claims about who can help. Without it, show degraded availability browsing rather than a false roster-fit ranking.
Value lenses are optional enrichment.

### 15.3 All-player Value-lens route behavior

When the Shapley Intrinsic coordinator is queued/running:
- do not block Broad Market rows behind a route-level loading response if Broad Market is already available;
- return a partial/degraded payload with Broad Market rows;
- mark fsffl_intrinsic.status = building;
- include retry_after_ms for the optional lens;
- do not substitute Broad Market for Intrinsic.

The browser should merge independent evidence channels rather than fail the entire surface from one optional dependency. Implementation may use separate requests or all-settled semantics.

### 15.4 Player analytics join

Unrostered players may not exist in rostered team-view analytics. Their missing projection/role data must remain explicitly unavailable unless the all-player Forecast contract provides it.

Do not infer reserve/starter status from absence.

## 16. Mobile composition

### For You wireframe

Market
Your best paths right now

[ Upgrade RB starter quality ]
Why now: current RB unit is a relative weakness
Benefit: higher starter ceiling / lineup resilience evidence
Risk: acquisition cost elevated
Paths: 2 preliminarily plausible
[Open opportunity]

[ Consolidate WR depth ]
Why now: surplus depth, starter upgrade path
Benefit: roster concentration
Risk: thinner bench
Paths: 1 preliminarily plausible
[Open opportunity]

No full packages on the first screen.

### Opportunity Detail wireframe

Upgrade RB starter quality
Why this exists
- current need
- competitive context
- evidence status

Candidate paths
1. Gibbs — Owner X — bilateral supported
2. Player Y — Owner Z — bounded uncertainty
3. Player Q — Owner W — bilateral supported

[Open path]

### Candidate Path wireframe

Gibbs via Owner X
Why it survived
- market economics: bounded uncertainty
- focal roster effect: favorable
- counterparty roster rationale: mixed/supportive
- package concentration: governed band
- owner history: descriptive support / unavailable

Representative package
You give: ...
You receive: Gibbs

Alternative
...

[Evaluate in Trade Center]

### Trade Finder wireframe

What are you trying to do?
[Improve] [Target player] [Shop player] [Position] [Owner]

Selected: Target player
Player: Jahmyr Gibbs
Strategic lens: Calculated
[Advanced filters]

Opportunities / path families
- Gibbs acquisition — 2 plausible paths
- Gibbs market-match alternatives — 3 collapsed

### Player Board wireframe

Player Board
[Search] [Position] [Owner] [More]

Player | Market | Intrinsic | Δ
...

Tap row → Player Intelligence

### Free Agents wireframe

Free Agents
Who can help without a trade?

[Search] [Position]

Player
Role / projection
Why he fits
[Evaluate add/drop]

## 17. Deterministic fixture and test matrix

Implementation must add deterministic tests before UI acceptance.

### Fixture A — repeated Gibbs neighborhood

Construct one elite RB target owned by one counterparty with:
- nearest one-for-one package;
- nearest two-for-one package;
- nearest three-for-one package;
- at least two nearby substitutions in the multi-asset package neighborhood.

Expected:
- raw Search may generate all variants;
- exact package dedup preserves distinct raw packages;
- all variants map to one named-target Opportunity family;
- Candidate Path family collapses package variants under the same target/counterparty;
- For You contains at most one Gibbs Opportunity card;
- Opportunity Detail exposes no more than the bounded number of distinct paths;
- Candidate Path Detail initially exposes at most two package variants.

### Fixture B — extreme Superflex package

Construct a premium target with an additive package whose Cardinal sum is close but whose Decision package-economics / focal economic materiality indicates substantial focal strain.

Expected:
- additive closeness alone cannot earn worth_attention;
- path requires countervailing governed bilateral roster evidence;
- if focal Decision becomes dominated/uniform loss, path is suppressed from For You;
- if evidence is mixed and strategically favorable, it may remain explorable with cost/risk plainly shown;
- no acceptance probability is created;
- no exact Simulation runs during broad screening.

### Fixture C — counterparty-dominated path

Expected:
- negotiation feasibility = counterparty_dominated;
- path is ineligible for For You;
- explicit named-target Trade Finder may retain it under a clear friction/market-match status;
- Search does not relabel it plausible.

### Fixture D — one-for-many within provisional band

Expected:
- PackageEconomicResolution.WITHIN_PROVISIONAL_BAND is treated as bounded uncertainty, not rejection and not a premium point estimate;
- no 15% value is added to Value or Team Utility;
- uncertainty is visible in Candidate Path detail.

### Fixture E — singleton underpaid

Expected:
- counterparty economic strain is flagged;
- cannot become worth_attention without governed countervailing bilateral evidence;
- if bilateral Decision remains counterparty-dominated, suppress from For You.

### Fixture F — focal overpay beyond upper bound

Expected:
- focal economic strain is visible;
- path requires governed focal strategic/roster benefit to remain explorable;
- focal-dominated result suppresses it;
- no automatic claim that overpay is good because the target is elite.

### Fixture G — duplicate strategic objective across targets

Construct three premium RB targets all serving one RB-upgrade hypothesis.

Expected:
- opportunity aggregation prevents three nearly identical cards from filling For You;
- target alternatives appear inside the Opportunity Detail or a bounded set of distinct target-family opportunities according to the target archetype policy;
- diversity selector preserves other strategic dimensions where eligible.

### Fixture H — owner evidence absent

Expected:
- path remains eligible if State/Value/Decision evidence is sufficient;
- Owner context says unavailable;
- missing history is not negative evidence;
- no acceptance probability is shown.

### Fixture I — owner trade-shape evidence present

Expected:
- context-controlled shape fit is attached descriptively;
- Value remains unchanged;
- Decision consequences remain unchanged;
- the fit may break a tie but cannot override a counterparty-dominated Decision result.

### Fixture J — Player Board core 7/7, Intrinsic building

Expected:
- global strip reads Core intelligence current 7/7;
- Player Board renders Broad Market rows;
- Intrinsic cells say Preparing;
- surface status is building_optional or degraded, not unavailable;
- later Intrinsic completion updates cells without changing Broad Market values.

### Fixture K — Free Agents with State + Value but missing Forecast

Expected:
- available players render from State;
- no claim of roster-fit improvement;
- projection/role says unavailable;
- surface is degraded;
- add/drop deep evaluator remains gated by its required authorities.

### Fixture L — exact Simulation call-count guard

Expected during broad Market load:
- zero changed-state exact Simulation calls;
- current baseline Simulation may be read;
- bounded preliminary Decision screen may run only up to configured budget;
- exact Simulation occurs only after transaction-level Trade Center escalation.

## 18. Acceptance tests

Architecture implementation is not accepted until tests demonstrate all of the following.

Discovery quality:
- repeated exact-target package variants cannot occupy multiple For You cards;
- no For You fill-to-quota with market_match_only or unevaluated raw Search rows;
- at least one representative path behind every For You card has completed the bounded preliminary bilateral screen;
- counterparty-dominated and focal-dominated paths do not qualify for For You;
- missing critical economic evidence fails closed for For You;
- Search ordering never mutates upstream Value/Decision evidence.

Authority:
- Broad Market and Intrinsic remain separate;
- no owner signal changes universal Value;
- no acceptance probability is generated by Market;
- package premium prior is used only through Decision robustness classification and never added to Value;
- mandatory cut cost is charged exactly once;
- current baseline Simulation can inform strategic context, but broad discovery launches zero exact changed-state simulations.

Diversity:
- exact target cap enforced;
- opportunity family cap enforced;
- need/counterparty caps enforced or explicitly relaxed according to product policy;
- diagnostics record why a candidate was suppressed, clustered, selected, or relaxed.

Readiness:
- 7/7 label is scoped to Core intelligence;
- Board/Free Agents have independent surface readiness;
- optional Intrinsic loading cannot blank Broad Market rows;
- unrostered missing Forecast evidence is not silently inferred;
- stale State/evidence coordinates invalidate Market results.

Product:
- For You is opportunity-first;
- Trade Finder is intent-first with advanced controls collapsed;
- Opportunity Detail explains why before packages;
- Candidate Path Detail explains why a package survived;
- Trade Center receives an exact proposal;
- physical iPhone/Safari can scan first-screen Market without dense repeated explanatory chrome.

Performance:
- preliminary Decision budget is enforced;
- repeated exact path analysis is cached/coalesced;
- broad Market load remains foreground responsive on free-tier beta infrastructure;
- performance tuning may change compute budgets but not analytical status semantics.

## 19. Proposed implementation modules and ownership

This is a suggested repository decomposition, not permission to implement before Management accepts.

Opportunity domain:
- extend src/fsffl/opportunity with OpportunityHypothesis, MarketOpportunity, CandidatePath, family-key and evidence-status models;
- keep them immutable / serializable using existing model conventions.

Decision:
- add a preliminary trade-screen adapter under src/fsffl/trade_decision or product Decision runtime that composes existing economics, package concentration, bounded prior, cuts, roster consequences, and negotiation feasibility;
- do not reimplement Decision math in Search.

Search:
- replace package-row-first workspace orchestration with staged hypothesis → target → raw packages → Decision screen → clustering → opportunity aggregation → diversity selection;
- preserve explicit Trade Finder focus before expensive work.

Product/API:
- publish opportunities and candidate paths separately;
- publish MarketSurfaceReadiness;
- make all-player lens delivery partial/nonblocking when only Intrinsic is building.

Presentation:
- recompose north_star_market.js around the new objects;
- retain existing deep links to Player Intelligence, Owner Intelligence, Trade Center, and add/drop evaluation;
- remove package-row fill behavior from For You.

## 20. Bounded implementation sequence after Management acceptance

Phase 1 — contracts and fixtures
- add domain models, family keys, statuses, readiness contract;
- add deterministic Gibbs/Superflex/readiness fixtures;
- no UI change.

Phase 2 — Decision preliminary screen
- compose existing governed Decision primitives;
- add authority-boundary tests;
- benchmark per-path cost;
- no exact Simulation.

Phase 3 — Search funnel
- hypothesis generation;
- target diversification;
- bounded package neighborhoods;
- preliminary economic screening;
- family clustering;
- bounded bilateral Decision budget;
- opportunity aggregation and diversity selection;
- keep legacy payload available behind a compatibility adapter during transition.

Phase 4 — truthful readiness
- separate Core 7/7 wording from MarketSurfaceReadiness;
- nonblocking all-player Value-lens payload;
- partial Board/Free Agent evidence merging;
- explicit retry/update behavior for Intrinsic.

Phase 5 — four-surface recomposition
- For You opportunity-first;
- Trade Finder progressive controls and grouped results;
- Player Board mobile visual simplification;
- Free Agents roster-fit-first cards;
- Opportunity Detail and Candidate Path Detail.

Phase 6 — migration cleanup
- remove legacy package-row For You fill;
- remove duplicated status language and dense controls;
- retain exact Trade Center and add/drop deep-evaluation paths.

Phase 7 — acceptance
- deterministic tests;
- authority/anti-double-counting tests;
- performance budget tests;
- physical iPhone/Safari acceptance;
- verify no cross-league/stale-evidence reuse.

## 21. Observability requirements

Every Market workspace should expose diagnostics sufficient to explain discovery without exposing internal implementation detail to end users:

- hypotheses_generated
- targets_considered
- raw_packages_generated
- packages_removed_exact_duplicate
- packages_screened_economic
- packages_economic_incomplete
- path_families_created
- preliminary_decision_budget
- preliminary_decision_runs
- counterparty_dominated_count
- focal_dominated_count
- opportunities_created
- opportunities_attention_ready
- opportunities_suppressed
- for_you_selected
- diversity_relaxations
- changed_state_simulation_calls_during_discovery, required to equal zero

Each selected Opportunity should carry machine-readable reason codes for:
- why it surfaced;
- why its representative path survived;
- what evidence is missing;
- why a near-duplicate was clustered instead of separately displayed.

## 22. Migration compatibility

During implementation, retain current Trade Center handoff and add/drop evaluator unchanged.

Legacy package candidates may remain internally available for debugging, but the public Market payload should migrate toward:
- opportunities
- candidate_paths
- raw package variants only behind detail/debug boundaries
- surface_readiness

Do not preserve old presentation semantics merely for payload compatibility. Specifically, do not map an unevaluated raw package to worth_attention.

Saved opportunities/watch targets currently stored in the browser should migrate by:
- preserving watched exact player refs;
- mapping saved raw package keys to the containing CandidatePath when an exact match exists;
- otherwise preserving the saved transaction only as a Trade Center draft, not fabricating a new Opportunity identity.

## 23. Unresolved risks

1. Preliminary Decision cost on free-tier infrastructure.
Mitigation: bounded eight-path budget, one-per-family round-robin, exact caching, benchmark before release. Management may lower/raise the compute budget without changing authority semantics.

2. Current pre-Simulation bilateral classification may have incomplete dimensions because competitive outcomes are intentionally absent.
Mitigation: use it as plausibility, not final disposition. Incomplete critical evidence blocks For You rather than triggering broad Simulation.

3. Opportunity target-archetype taxonomy can over-cluster or under-cluster.
Mitigation: start with deterministic position/role/objective families and exact-target overrides. Do not use opaque embedding similarity as authority in the first implementation.

4. Owner evidence coverage varies by league/owner history.
Mitigation: optional descriptive evidence only. Missing evidence is neutral/unavailable.

5. Broad Market all-player coverage and unrostered Forecast coverage may differ.
Mitigation: column-level readiness and partial rendering; no substitute values.

6. Existing frontend localStorage saved package identities are transaction-shaped.
Mitigation: migration rule above; do not silently relabel old package saves as governed Opportunities.

7. Package-economic prior is explicitly provisional.
Mitigation: preserve model/version/provenance and update it through its existing evidence-updating governance, not Search tuning.

## 24. Management gate

The architecture review is complete enough for Management to decide whether to authorize bounded implementation.

Management acceptance should confirm:
- Opportunity/Hypothesis/CandidatePath separation;
- For You worth_attention gate;
- four-card default feed and diversity caps;
- bounded eight-path pre-Simulation Decision budget as a tunable product compute policy;
- no broad exact Simulation;
- Owner Intelligence descriptive-only role;
- Core 7/7 versus MarketSurfaceReadiness separation;
- phased implementation sequence.

No broad Market code was changed by this workstream.

Stop state: MANAGEMENT GATE — MARKET / TRADE DISCOVERY ARCHITECTURE REVIEW.
