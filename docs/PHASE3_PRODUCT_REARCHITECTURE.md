# FSFFL NEXT — Phase 3 Product Rearchitecture

This document supplements, but does not replace, `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`. The canonical roadmap remains authoritative. This is a Phase 3 product program: redesign the experience around distinct owner jobs while preserving all current authority boundaries and creating natural homes for later historical, publication, analytics, scenario, evidence-warehouse, and commercialization work.

## North-star principle

Design FSFFL NEXT as if it were being created today from a blank sheet. The existing beta DOM, cards, tables, routes and companion scripts are implementation scaffolding, not product requirements.

Canonical authority remains:
`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Presentation does not create model truth. Search does not create Value or Decision truth. Simulation owns stochastic competitive outcomes. Decision owns bilateral consequences, legality, package economics, materiality and disposition. Behavioral evidence does not rewrite universal Market Value. Strategic posture remains separate from calculated competitive state. No opaque master score is introduced for UI convenience.

## 1. Governed capability inventory

### Already authoritative and surfaced
- Canonical league/team/roster/pick ownership, roster slots and player age state.
- Forecast observations, season projections, optimized lineups and QB/RB/WR/TE position strength.
- Expected wins, playoff/title probabilities, calculated competitive state and roster-resilience evidence.
- Authoritative player/pick FSFFL Cardinal Value, supported additive Market Value portfolios, market-percentile evidence and team player/pick portfolios.
- Canonical/legal trade drafting, bilateral consequences, roster-adjusted Value/cuts, lineup/position impact, Decision shape/materiality/disposition and changed-state Simulation.
- Roster-aware trade Search, target-position/package/search context, fast bilateral evaluation, separate closest-market-match and most-promising-evaluated spotlights, negotiation-feasibility shape, bounded frontier, counter paths and waiver add/drop evaluation.
- Observed owner transaction history, acquired/disposed positions and picks, completed deal shapes, repeat counterparties, evidence dates/seasons and directional proposal fit where governed.
- Read-only Analytics, reports, single-player What-If and multi-player scenario Simulation.

### Exists but is buried, duplicated or poorly productized
- Roster resilience is split across Home, My Team and Trade Center rather than forming one coherent Franchise diagnosis.
- Strongest/weakest positional evidence competes with full roster tables.
- Team pick/player Value portfolios exist but League does not yet turn them into a clear structural picture.
- Competitive-state evidence is presented beside repeated totals instead of explaining league structure.
- Trade Center evidence is spread across multiple presentation companions.
- Opportunities contains roster fit, Decision, owner history and Search context, but the table-first layout makes the user synthesize them manually.
- Behavioral history is useful but still feels like evidence panels rather than an Owner dossier.
- Player/Asset search is a useful object explorer but is treated as one of many peer dashboards.
- Technical readiness/provenance is often too prominent.

### Exists elsewhere but needs a proper product connection
- Behavioral proposal fit into Trade/Opportunity with a deep link to supporting Owner evidence.
- League positional structure into complementary-partner discovery without moving Search authority into League.
- Team Value/pick portfolios into Franchise optionality and League structure without a composite score.
- Changed-state Simulation directly and visibly into Trade Center.
- Durable PIT State history into a governed previous-state/change-feed product contract.
- Historical infrastructure into Franchise/League/Trade timelines later.

### Genuine current capability gaps
- Governed previous-distinct-state / “what changed since last visit” API.
- Full actual-replacement-player / WAR coverage in all desired contexts.
- Mature age/value-duration and longer-horizon dynasty outlook.
- Reliable context-controlled owner preference with recency/stability/confidence across owners.
- Calibrated acceptance probability.
- Production Historical Trade Grader and Historical Pick Coordinate.
- Franchise causality/timeline, league lore/eras/rivalries/record book, first-class recurring publications and saved trade/scenario/watchlist workflows.

### Future object continuity
- Franchise → diagnosis → trajectory → timeline → alternate history.
- League → structure → trends → eras/rivalries/records.
- Owner → observed history → context-controlled inference → proposal fit.
- Player/Asset → current role/value → historical value/career state → transactions.
- Opportunity → current action path → saved/monitored opportunity → historical analogues.
- Trade → draft → Decision → counters → saved scenario → historical comparison.
- History → cross-object index rather than a disconnected archive.

## 2. Current-state IA audit

### Global shell
Current navigation exposes eleven near-peer destinations: Home, My Team, Players & Assets, League Comparison, Trade Center, Opportunities, Behavioral Intelligence, What-If, Simulator, Analytics Terminal and Reports. Desktop and mobile largely expose the same flat list. Several fundamentally different jobs share one generic-panel scaffold, legacy Home markup remains in `index.html`, and product behavior is spread across many additive companion scripts.

Problem: too many persistent mobile destinations; workflows and durable objects are treated as peers; generic cards/tables dominate unrelated jobs; the navigation says what FSFFL contains instead of what the owner should do next.

### Home
Current: opportunity, competitive outlook, roster vulnerability, positional pressure, workflow shortcuts, runtime status and unavailable/roadmap note.

Problem: still a grid of equal-weight cards; overlaps Franchise diagnosis; current opportunity depends on an already-loaded Opportunity workspace because Home correctly avoids launching deep Search; real change/activity is unavailable without a governed history read contract; technical status is too close to the core story.

Primary ownership: **priority and recency — what deserves attention now.**

### My Team
Current: wins/playoff/title/state, position strength, franchise-driver companion, starter/bench/taxi/IR tables, picks, workflow buttons and evidence details.

Problem: strong facts but diagnosis and inventory are mixed; important conclusions compete with long tables; competitive totals repeat Home/League; optionality/age/picks are not yet organized into a coherent short-vs-long-term story.

Primary ownership: **Franchise diagnosis — what carries the team, where it breaks, and what options/assets it has.** Full roster is a subview.

### League Comparison
Current: managed-team ranks, state guide, seven leader tiles, sortable all-team table, positional edge map and definitions.

Problem: still a leaderboard/dashboard; repeats Home/My Team totals; the positional edge map is the strongest distinct component; existing state/position/value/pick evidence can describe league structure without a master score.

Primary ownership: **League structure — competitive tiers, positional scarcity/wealth, picks/assets and complementary needs.**

### Opportunities
Current: summary counts, tabs/search, roster-aware context, send/receive packages, Value distance, bilateral Decision, owner history, triage, closest-market-match vs evaluated spotlight, changed-state evaluation, Behavioral fit, plain-English evaluation brief, waiver evaluator and authority detail.

Problem: capability-rich but table-first/model-process-first; intent/posture is not the dominant interaction; Value distance is visually prominent enough to be mistaken for quality; roster fit/counterparty plausibility/tradeoffs are fragmented.

Primary ownership: **Personalized Market — what should I do given my objective?** Strongest FSFFL Opportunity and Closest Market Match must remain visibly distinct.

### Trade Center
Current: two-sided builder/filters, asset Value, analyze, fast bilateral read, roster-adjusted Value/cuts, lineup impact, Behavioral context, Simulation, Decision brief, frontier/counters and advanced details.

Problem: excellent underlying intelligence but multiple explainer layers compete; headline, both-side case, risk, Simulation, economics and next action should read as one Decision Room. Simulation must visibly populate from changed-state authority, not feel like optional technical work.

Primary ownership: **Decision Room — one concrete trade and its governed consequences, alternatives and next move.**

### Behavioral Intelligence
Current: owner selector, move/trade/player/pick counts, observed summary, position activity, completed deal shapes, repeat counterparties, inference-readiness and provenance.

Problem: strong governance but still count/panel-first. It should feel like an Owner dossier with relationships, repeated observed patterns, recency/coverage/stability and responsible approach guidance. Unavailable inference should not dominate every profile.

Primary ownership: **Owner dossier / negotiation intelligence.**

### Players & Assets
Keep as a durable object explorer, but reach it through global/contextual drill-downs rather than giving it equal mobile persistence. Future asset history attaches naturally here.

### What-If / Simulator
Treat as one Scenarios family, launched contextually from Franchise/Trade. Future Alternate History belongs here.

### Analytics / Reports
Keep accessible as expert/deep surfaces, but secondary on mobile. Future History/Publications can expand without destabilizing core navigation.

## 3. Proposed end-state navigation

### Mobile persistent navigation
1. **Home** — What matters now?
2. **Franchise** — What is driving my team?
3. **League** — How does the league fit together?
4. **Market** — What should I do?
5. **More** — Decision/tools/objects/explore drawer

More contains: Trade Center / Decision Room; Players & Assets; Owners; Scenarios; Reports/Publications; Analytics Terminal; future History; settings/status.

Trade Center remains one tap from every relevant CTA and prominent in More. It does not need to consume a permanent mobile slot to remain a primary workflow.

### Desktop groups
- Primary: Home, Franchise, League, Market.
- Decisions/workflows: Trade Center, Players & Assets, Owners, Scenarios.
- Explore: Reports/Publications, Analytics, future History.

Durable product objects: Franchise, League, Player/Asset, Owner, Opportunity, Trade, History.

## 4. Surface ownership

| Concept | Primary home | Secondary references |
| --- | --- | --- |
| Priority / what matters now | Home | links outward |
| Competitive profile | Franchise | Home summary; League comparison |
| Position strength / fragility | Franchise | League edge map; Trade changed-state impact |
| League structure / scarcity | League | Market targeting context |
| Current player/pick Value | Player/Asset + Franchise inventory | Trade economics; Market plausibility |
| Strongest action opportunity | Market | Home teaser |
| Search market plausibility | Market | Trade frontier |
| Bilateral trade consequences | Trade Center | Market evaluated summary |
| Changed-state Simulation | Trade Center / Scenarios | Franchise stress test |
| Owner observed history | Owner dossier | Market/Trade context |
| Proposal fit | Trade Center | Owner supporting evidence |
| Historical facts | History + object timelines | Home milestones |
| Methodology/provenance | Evidence layer | secondary everywhere |

## 5. Remove / relocate / combine

- Replace the flat eleven-destination mobile nav.
- Stop using generic metric grids as the default surface grammar.
- Home: reduce Franchise-detail duplication; keep prioritized signals/actions.
- Franchise: demote long roster/pick tables into secondary Roster/Assets views.
- League: demote repeated leader tiles and giant table; lead with structure/edge map.
- Market: demote raw Search table; lead with intent, strongest opportunity, closest market match and reasoned candidates.
- Trade Center: consolidate overlapping explainer companions into one Decision Room hierarchy.
- Owner: demote raw count grids; lead with observed patterns, evidence strength/recency and relationships.
- Move runtime/readiness to secondary global status except when blocking.
- Group What-If + Simulator under Scenarios.
- Put Analytics + Reports under Explore/More on mobile while preserving direct routes/deep links.

## 6. Backend information currently inaccessible to the desired UX

1. **Previous distinct State/change feed** — read-only Analytics/API contract over durable PIT history; enables Home “since last visit,” Franchise trajectory and future history.
2. **Franchise diagnostic read model** — product/analytics aggregation of existing authoritative outputs if repeated multi-endpoint composition becomes slow/fragile; never a new score.
3. **League structure read model** — descriptive grouping/ranks from state, position strength and Value/pick portfolios; no UI-invented thresholds.
4. **Opportunity intent/Search contract** — posture/objective must flow into Search policy/admission/evaluation budget, not presentation-only filtering, and never overwrite calculated competitive state.
5. **Behavioral evidence-strength contract** — coverage/recency/stability/confidence must come from Behavioral authority when empirically supportable.

## 7. Recommended implementation sequence

### Slice A — New product shell/navigation
Mobile Home/Franchise/League/Market/More; grouped desktop nav; clear page/object language; preserve every existing route and deep link.

### Slice B — Home Command Center
Priority feed rather than equal cards; one dominant best-next-action region; compact outlook/risk references; explicit future change/activity slot with no fabricated data; no Home-triggered deep Search.

### Slice C — Franchise diagnosis
Diagnosis default; roster/assets secondary; competitive profile, strengths/weaknesses, resilience, core assets, optionality and draft capital.

### Slice D — League structure
Positional edge map central; competitive-state and asset/pick structure; descriptive complementary needs; giant table demoted.

### Slice E — Market / Opportunities
Intent/posture first; posture materially affects governed Search attention; Strongest FSFFL Opportunity separate from Closest Market Match; reasoned mobile candidates; investigate real poor-target examples and repair the earliest authoritative issue if confirmed.

### Slice F — Trade Center Decision Room
Consolidate presentation layers; headline + both-side case + risk + next action; visibly functional changed-state Simulation; needs before/after, lineup, economics, proposal fit and counters as core sections; methodology secondary.

### Slice G — Owner dossier
Owner-first observed patterns, relationships, recency/coverage and representative trades; inference only when authority returns it; proposal-fit deep links.

### Slice H — Integration/validation
Remove obsolete duplicate companions/legacy scaffolding safely; mobile/deep-link tests; latency; real beta useful-discovery log; do not exit Phase 3 before the canonical roadmap gate.

## Product success check

Without reading model documentation, an owner should answer:
- Home: What deserves my attention?
- Franchise: What is actually driving my team?
- League: Where are the league’s structural edges and imbalances?
- Market: What should I do given my objective?
- Trade Center: What happens if I make this trade, and what should I do next?
- Owner: What does completed evidence say about this manager, and how should I use it?

The user should not need to know which NEXT module supplied the answer. Authority/provenance remains inspectable underneath the answer, not in place of it.
