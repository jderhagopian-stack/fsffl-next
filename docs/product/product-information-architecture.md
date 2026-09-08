# FSFFL NEXT Product Information Architecture

## Product rule

Every major surface must earn its place by answering a different user question. Presentation may sort, filter, group, explain, and route into deeper investigation, but it does not calculate model truth, invent coefficients, or collapse unrelated authoritative concepts into an opaque master score.

The governing flow remains:

`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

## Dashboard jobs-to-be-done

| Surface | Primary user question | Product job | Must not become |
| --- | --- | --- | --- |
| Home | What should I care about right now? | Prioritize a small set of distinct current signals and route insight → investigation → action. | A duplicate team dashboard, league leaderboard, or giant navigation menu. |
| My Team | What is really driving my franchise? | Diagnose lineup, depth, position strength, fragility, age/value shape, draft capital, flexibility, and specific strengths/weaknesses. | A roster table with summary metrics attached. |
| League Comparison | How are the franchises meaningfully different? | Explain league structure, franchise archetypes, positional scarcity, competitive tiers, value distribution, and meaningful contrasts. | My Team repeated twelve times or one sortable master score. |
| Opportunities | Where is there something worth doing? | Present governed Search/Trade Finder discovery, nearby structures, counterparty fit, and why candidates surfaced. | A competing browser search algorithm or a second Decision engine. |
| Trade Center | What happens if I make this specific trade? | Build and analyze a concrete bilateral deal using governed Decision outputs. | General discovery or universal player valuation. |
| Behavioral Intelligence | How does this owner actually make decisions? | Describe evidence-backed historical tendencies, confidence, recency, sample size, and representative examples. | A shallow owner label, hidden Market Value adjustment, or invented acceptance probability. |
| Franchise Timeline | What actually changed this franchise over time? | Connect meaningful historical inflection points to state changes and later investigation. | A noisy transaction feed. |
| Historical Trade Review | Was this decision good then, and how did it turn out? | Present governed point-in-time decision grade separately from retrospective outcome, with evidence completeness and uncertainty. | Browser recalculation of historical grades or hindsight leakage into the point-in-time grade. |
| What If / Alternate History | What plausible path might have followed a different decision? | Branch from governed historical/current state into explicit modeled scenarios and show uncertainty. | A factual claim about what definitely would have happened. |
| Analytics Terminal | Let me investigate the league myself. | Deep read-only exploration, matrices, heat maps, value differences, behavior, history, and provenance. | Another recommendation engine. |
| Reports | Explain this to me as a finished analysis. | Produce coherent plain-English narrative with evidence, uncertainty, charts/tables, conclusions, and why/why not. | Another interactive dashboard. |

## Current evidence inventory

### Available now

These product modules can be built from existing governed contracts without creating new model truth:

- optimized projected starters and roster roles;
- current player age data;
- player forecast observations and season fantasy-point projections;
- Value profiles and owned draft-pick inventory;
- league-relative position strength;
- current competitive state and governed Simulation outcomes;
- roster resilience, including largest single-player lineup drop, forecasted bench count, and missing forecast count;
- league named-metric rankings without a composite score;
- Behavioral owner profiles with event/trade counts, position acquisition/disposal counts, pick/FAAB activity, consolidation/diversification/balanced trade counts, counterparties, and seasons observed;
- existing governed Opportunity/Search and Trade Decision surfaces;
- current-state What-If / Simulator roster-availability scenarios;
- read-only Analytics and Reports foundations.

### Clean API/report contracts needed

Do not approximate these in Presentation. Add structured contracts when the authoritative layer is ready:

- change since last visit / state-to-state deltas and notable movement;
- a Home-ready governed opportunity teaser/result contract that can reuse Search output without rerunning Search;
- richer My Team diagnostics such as age-curve interpretation, depth/replacement exposure by position, top-heavy/balanced characterization, future-flexibility explanation, and explicit upgrade/surplus evidence when these are not already authoritative fields;
- league archetype evidence and league-wide scarcity/distribution summaries where a label requires more than direct display grouping;
- Behavioral confidence/stability/recency fields and representative transaction evidence suitable for first-class owner drill-down;
- historical franchise event stream tied to point-in-time states and meaningful state changes;
- Historical Trade Grader product/report contract exposing point-in-time decision, retrospective outcome, evidence completeness, uncertainty, and provenance separately;
- Alternate History scenario contract capable of branching from historical state and carrying later modeled consequences without implying certainty;
- persisted/reusable derived intelligence metadata needed to avoid unnecessary recomputation across surfaces.

### Model capability not yet assumed available

Treat the following as unavailable until an authoritative contract exists; do not invent them in UI code:

- universal cross-domain "importance" or franchise health score;
- owner acceptance probability unless an explicitly governed model is promoted;
- causal claims that a historical event definitely produced a later outcome;
- deterministic alternate-history outcomes;
- historical grades reconstructed in the browser;
- stable behavioral preference declarations from a single or tiny sample.

## First bounded slice: Home prioritization

Home should stop rendering generic league leaderboards, generic team summary metrics, and a roster preview as its main experience. Those belong to League Comparison and My Team.

The first Home attention board uses only evidence already present in the loaded Team Analytics view:

1. **Competitive outlook** — governed Simulation / Team Utility outcome and calculated competitive state.
2. **Roster vulnerability** — governed roster-resilience evidence, especially largest single-player lineup drop and forecast coverage.
3. **Position to investigate** — direct league-relative position-strength evidence, showing the weakest current position and strongest position for context.
4. **Insight → action routes** — Opportunities for discovery, League Comparison for structure, Trade Center for a concrete deal, and Analytics Terminal for self-directed investigation.

These signals are deliberately not combined or ranked against one another. Home is prioritization by distinct job/category, not a new analytical score.

Until governed history and reusable Search-result contracts exist, Home must explicitly avoid fabricating "biggest change since last visit," historical milestone alerts, owner-behavior alerts, or a best-opportunity claim.

## Next coherent slices

1. **My Team franchise diagnostic** — move from inventory/report toward drivers: depth, fragility, age/value distribution, replacement exposure, leverage, flexibility, upgrade priorities, and tradable surplus using authoritative evidence only.
2. **League Comparison differentiation** — archetypes, current-strength-vs-long-term-value structure, positional heat maps, scarcity, concentration, and competitive tiers.
3. **Shared drill-down language** — reusable metric-with-context, evidence/provenance, uncertainty, before/after, behavior evidence, timeline event, and mobile drill-down patterns.
4. **Behavioral Intelligence foundation** — first-class owner navigation and descriptive evidence view; add stronger tendency statements only when confidence/recency contracts exist.
5. **Franchise Timeline + Historical Trade Review shell** — read-only shells around historical state/event and grader contracts; no browser reconstruction.
6. **Alternate History integration** — expand beyond current roster shocks only after historical branching contracts exist.
7. **Analytics Terminal depth** — matrices/heat maps/history/provenance, while remaining read-only.
8. **Reports polish** — narrative synthesis from the same structured governed outputs.

## Mobile and performance rules

- Show the most decision-relevant information first and progressively disclose evidence details.
- Prefer drill-down sheets/sections to giant tables on small screens.
- Reuse already-loaded authoritative state and derived artifacts before requesting new work.
- Do not launch expensive Simulation/Search simply because a dashboard rendered.
- Show useful available evidence while slower governed stages are still attaching.
- Keep technical pipeline status accessible but secondary to the user-facing result.

## Performance development list

Maintain and refine these items during UI work:

- reusable league-intelligence snapshots keyed to canonical state/model versions;
- reusable Search/Opportunity result artifacts for Home teasers and drill-downs;
- state-delta artifacts for "since last visit" without recomputing historical truth;
- lazy-load deep surfaces and large tables;
- cheap presentation filters/grouping before expensive model work;
- scenario/result caching for exact repeated governed analyses;
- progressive API contracts that distinguish available, loading, unavailable, and stale evidence;
- instrumentation for endpoint/model-stage latency so commercial-quality bottlenecks can be identified rather than guessed.
